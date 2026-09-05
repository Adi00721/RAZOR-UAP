import uuid
import time
from typing import Dict, Any, List, Optional
from .catalog import catalog_manager
from .agent_negotiator import merchant_negotiator, BuyerRFQ
from .guardrails import guardrail_engine
from .razorpay_client import razorpay_gateway
from .audit_ledger import audit_ledger

class AutonomousBuyerAgent:
    def __init__(self, buyer_id: str = "BUYER_AGENT_ALEX_01"):
        self.buyer_id = buyer_id

    def execute_intent_pipeline(self, user_intent: str, user_budget: float, requested_skus: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        End-to-end UAP workflow:
        1. Parse intent & browse catalog
        2. Issue A2A RFQ to Merchant Agent
        3. Receive Bounded Quote
        4. Prepare Gated Check
        """
        trace_id = f"TRC_{uuid.uuid4().hex[:12].upper()}"
        
        # Step 1: Log Intent
        audit_ledger.record_event(
            trace_id=trace_id,
            event_type="USER_INTENT_DISPATCHED",
            actor=self.buyer_id,
            payload={"user_intent": user_intent, "user_budget": user_budget}
        )

        # Step 2: Auto-detect SKUs from catalog if not provided
        sku_list = requested_skus or []
        if not sku_list:
            intent_lower = user_intent.lower()
            all_prods = catalog_manager.get_all()
            for prod in all_prods:
                name_words = [w.lower() for w in prod.name.split()]
                if any(w in intent_lower for w in name_words if len(w) > 3):
                    if prod.id not in sku_list:
                        sku_list.append(prod.id)
            if not sku_list and all_prods:
                sku_list = [all_prods[0].id] # Default to first product if open-ended

        # Step 3: Transmit A2A RFQ
        rfq = BuyerRFQ(
            rfq_id=f"RFQ_{uuid.uuid4().hex[:8].upper()}",
            buyer_agent_id=self.buyer_id,
            target_intent=user_intent,
            requested_sku_ids=sku_list,
            buyer_budget_cap=user_budget,
            requested_discount_pct=10.0 # Autonomous agent asks for 10% volume discount
        )

        # Step 4: Merchant Agent evaluates and replies with Quote
        merchant_response = merchant_negotiator.process_rfq(rfq, trace_id=trace_id)

        if merchant_response["status"] != "SUCCESS":
            return {
                "trace_id": trace_id,
                "status": merchant_response["status"],
                "message": merchant_response["message"],
                "quote": None,
                "gate_status": "LOCKED"
            }

        quote = merchant_response["quote"]
        offered_price = quote["final_offered_price"]

        # Step 5: Buyer Agent verifies budget compatibility
        is_budget_ok = offered_price <= user_budget
        
        return {
            "trace_id": trace_id,
            "status": "QUOTE_READY_FOR_GATED_APPROVAL" if is_budget_ok else "BUDGET_EXCEEDED",
            "message": "Quote prepared with dynamic bundle discount. Awaiting explicit user gate authorization.",
            "budget_analysis": {
                "user_budget": user_budget,
                "offered_price": offered_price,
                "savings": quote["raw_mrp_total"] - offered_price,
                "within_budget": is_budget_ok
            },
            "quote": quote,
            "gate_status": "AWAITING_HUMAN_AUTH" if is_budget_ok else "BUDGET_LOCK"
        }

    def authorize_and_transact(self, trace_id: str, quote: Dict[str, Any], customer_name: str = "Aarav Sharma", customer_email: str = "aarav.sharma@example.com") -> Dict[str, Any]:
        """
        Executes the Gated Phase:
        1. Verifies HMAC PreAuth Token
        2. Creates Razorpay Order & Payment Link
        3. Records completion in Audit Trail
        """
        quote_id = quote["quote_id"]
        gated_token = quote["gated_preauth_token"]
        amount = quote["final_offered_price"]

        # Gate Verification
        is_valid, verification_msg = guardrail_engine.verify_gated_token(
            token=gated_token,
            quote_id=quote_id,
            buyer_agent_id=self.buyer_id,
            amount=amount
        )

        if not is_valid:
            audit_ledger.record_event(
                trace_id=trace_id,
                event_type="GATE_VERIFICATION_FAILED",
                actor="GUARDRAIL_ENGINE",
                payload={"quote_id": quote_id, "reason": verification_msg}
            )
            return {
                "status": "GATE_REJECTED",
                "error": verification_msg
            }

        # Gate Passed: Log human authorization event
        audit_ledger.record_event(
            trace_id=trace_id,
            event_type="GATE_AUTHORIZED_BY_USER",
            actor="USER_HUMAN_GATE",
            payload={"quote_id": quote_id, "amount": amount, "verification": verification_msg}
        )

        # Trigger Razorpay Order Creation
        receipt_id = f"rcpt_{uuid.uuid4().hex[:8]}"
        rzp_order = razorpay_gateway.create_order(
            amount=amount,
            receipt=receipt_id,
            notes={
                "uap_trace_id": trace_id,
                "quote_id": quote_id,
                "buyer_agent": self.buyer_id,
                "bundle_applied": quote.get("bundle_applied", False)
            }
        )

        # Trigger Razorpay Payment Link
        rzp_plink = razorpay_gateway.create_payment_link(
            amount=amount,
            description=f"RazorUAP Order: {quote.get('bundle_name') or 'Electronics Setup'}",
            customer_name=customer_name,
            customer_email=customer_email,
            notes={"order_id": rzp_order["id"], "trace_id": trace_id}
        )

        # Log Order Creation in Audit Ledger
        audit_ledger.record_event(
            trace_id=trace_id,
            event_type="RAZORPAY_ORDER_CREATED",
            actor="RAZORPAY_GATEWAY",
            payload={
                "razorpay_order_id": rzp_order["id"],
                "amount_in_paise": rzp_order["amount"],
                "currency": rzp_order["currency"],
                "payment_link": rzp_plink["short_url"]
            }
        )

        return {
            "status": "TRANSACTION_AUTHORIZED",
            "razorpay_order": rzp_order,
            "razorpay_payment_link": rzp_plink,
            "verification_status": verification_msg,
            "trace_id": trace_id
        }

buyer_agent_sim = AutonomousBuyerAgent()
