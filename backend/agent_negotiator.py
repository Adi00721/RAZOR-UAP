import uuid
import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from .catalog import catalog_manager, Product
from .guardrails import guardrail_engine, GuardrailVerdict
from .audit_ledger import audit_ledger

class BuyerRFQ(BaseModel):
    rfq_id: str
    buyer_agent_id: str
    target_intent: str             # e.g. "Mechanical keyboard and wrist rest for ergonomic setup"
    requested_sku_ids: List[str]   # e.g. ["SKU-KB-01"]
    buyer_budget_cap: float        # e.g. 7000.0
    requested_discount_pct: Optional[float] = 0.0

class MerchantNegotiatorAgent:
    def __init__(self):
        self.merchant_agent_id = "MERCHANT_AGENT_VULCAN_01"

    def process_rfq(self, rfq: BuyerRFQ, trace_id: str) -> Dict[str, Any]:
        """
        Processes incoming Request-For-Quote from an autonomous AI Buyer Agent.
        Identifies synergy upsells, computes dynamic pricing within strict bounds,
        and evaluates guardrails.
        """
        # Step 1: Record incoming RFQ in Audit Ledger
        audit_ledger.record_event(
            trace_id=trace_id,
            event_type="A2A_RFQ_RECEIVED",
            actor="BUYER_AGENT",
            payload=rfq.model_dump() if hasattr(rfq, "model_dump") else rfq.dict()
        )

        # Step 2: Adversarial Sanitization check
        is_clean, reason = guardrail_engine.sanitize_adversarial_input(rfq.target_intent)
        if not is_clean:
            audit_ledger.record_event(
                trace_id=trace_id,
                event_type="ADVERSARIAL_INJECTION_BLOCKED",
                actor=self.merchant_agent_id,
                payload={"reason": reason}
            )
            return {
                "status": "REJECTED_SECURITY_POLICY",
                "message": reason,
                "quote": None
            }

        # Step 3: Fetch requested products
        selected_products: List[Product] = []
        for sku in rfq.requested_sku_ids:
            p = catalog_manager.get_by_id(sku)
            if p:
                selected_products.append(p)

        if not selected_products:
            # Fallback semantic search based on intent keywords
            search_results = catalog_manager.search(query=rfq.target_intent.split()[0], max_price=rfq.buyer_budget_cap)
            if search_results:
                selected_products.append(search_results[0])

        if not selected_products:
            return {
                "status": "NO_MATCHING_PRODUCTS",
                "message": "No available catalog items matched the agent's intent or budget.",
                "quote": None
            }

        # Step 4: AI Growth / C-Commerce Dynamic Upsell & Synergy Detection
        upsell_sku = None
        for p in selected_products:
            for synergy_sku in p.synergies:
                if synergy_sku not in [x.id for x in selected_products]:
                    synergy_prod = catalog_manager.get_by_id(synergy_sku)
                    if synergy_prod and synergy_prod.stock > 0:
                        # Check if adding this fits within reasonable budget
                        temp_total = sum(x.price for x in selected_products) + synergy_prod.price
                        if temp_total * 0.90 <= rfq.buyer_budget_cap * 1.15: # Within 15% of budget
                            upsell_sku = synergy_prod
                            break
            if upsell_sku:
                break

        bundle_items = list(selected_products)
        bundle_applied = False
        bundle_name = ""
        proposed_discount = rfq.requested_discount_pct or 0.0

        if upsell_sku:
            bundle_items.append(upsell_sku)
            bundle_applied = True
            bundle_name = f"Smart Bundle Synergy ({selected_products[0].name} + {upsell_sku.name})"
            # Reward bundle with 10% discount if buyer requested none, or respect buyer's request up to bounds
            proposed_discount = max(10.0, proposed_discount)

        # Step 5: Guardrail Financial Evaluation (Explainable, Bounded, Gated)
        quote_id = f"QTE_{uuid.uuid4().hex[:10].upper()}"
        item_dicts = [{"id": p.id, "name": p.name, "price": p.price, "cost_price": p.cost_price, "quantity": 1} for p in bundle_items]
        
        verdict: GuardrailVerdict = guardrail_engine.evaluate_money_action(
            quote_id=quote_id,
            buyer_agent_id=rfq.buyer_agent_id,
            items=item_dicts,
            proposed_discount_pct=proposed_discount,
            bundle_name=bundle_name
        )

        # Record Guardrail Evaluation in Audit Ledger
        audit_ledger.record_event(
            trace_id=trace_id,
            event_type="GUARDRAIL_EVALUATED",
            actor="GUARDRAIL_ENGINE",
            payload={
                "quote_id": quote_id,
                "is_allowed": verdict.is_allowed,
                "explainability": verdict.explainability.model_dump() if hasattr(verdict.explainability, "model_dump") else verdict.explainability.dict()
            }
        )

        quote_payload = {
            "quote_id": quote_id,
            "merchant_agent_id": self.merchant_agent_id,
            "buyer_agent_id": rfq.buyer_agent_id,
            "status": "OFFERED" if verdict.is_allowed else "REJECTED_BOUND_VIOLATION",
            "bundle_applied": bundle_applied,
            "bundle_name": bundle_name,
            "items": item_dicts,
            "raw_mrp_total": verdict.explainability.raw_mrp_total,
            "final_offered_price": verdict.explainability.offered_price,
            "discount_percentage": verdict.explainability.discount_percentage,
            "gated_preauth_token": verdict.gated_preauth_token,
            "explainability": verdict.explainability.model_dump() if hasattr(verdict.explainability, "model_dump") else verdict.explainability.dict(),
            "validity_seconds": 600,
            "created_at": time.time()
        }

        # Step 6: Log Quote issuance
        audit_ledger.record_event(
            trace_id=trace_id,
            event_type="A2A_QUOTE_ISSUED",
            actor=self.merchant_agent_id,
            payload={
                "quote_id": quote_id,
                "amount": verdict.explainability.offered_price,
                "status": quote_payload["status"]
            }
        )

        return {
            "status": "SUCCESS" if verdict.is_allowed else "BOUND_VIOLATION",
            "message": verdict.explainability.human_readable_summary,
            "quote": quote_payload
        }

merchant_negotiator = MerchantNegotiatorAgent()
