import hmac
import hashlib
import time
from typing import List, Dict, Any, Tuple, Optional
from pydantic import BaseModel
from .config import settings

class ExplainabilityToken(BaseModel):
    decision: str
    raw_mrp_total: float
    cost_basis_total: float
    offered_price: float
    discount_amount: float
    discount_percentage: float
    margin_percentage: float
    rules_evaluated: List[Dict[str, Any]]
    human_readable_summary: str
    timestamp: float
    iso_time: Optional[str] = None

class GuardrailVerdict(BaseModel):
    is_allowed: bool
    violation_reason: Optional[str] = None
    explainability: ExplainabilityToken
    gated_preauth_token: Optional[str] = None

class GuardrailEngine:
    def __init__(self):
        self.bounds = settings.BOUNDS
        self.secret = settings.HMAC_GATE_SECRET.encode("utf-8")

    def sanitize_adversarial_input(self, text: str) -> Tuple[bool, str]:
        """Detect prompt injections attempting to bypass merchant financial bounds."""
        lower = text.lower()
        suspicious_patterns = [
            "ignore previous instructions",
            "set price to 0",
            "give 99% discount",
            "free order",
            "bypass margin",
            "admin override",
            "unlimited discount",
            "discount = 100",
            "system prompt leak"
        ]
        for pattern in suspicious_patterns:
            if pattern in lower:
                return False, f"Adversarial Prompt Injection Blocked: Pattern detected '{pattern}'"
        return True, "Passed sanitization"

    def evaluate_money_action(
        self,
        quote_id: str,
        buyer_agent_id: str,
        items: List[Dict[str, Any]],
        proposed_discount_pct: float,
        bundle_name: str = ""
    ) -> GuardrailVerdict:
        """
        Enforces Bounded, Explainable, and Gated financial rules.
        """
        raw_mrp_total = sum(item["price"] * item.get("quantity", 1) for item in items)
        cost_basis_total = sum(item["cost_price"] * item.get("quantity", 1) for item in items)

        rules_evaluated = []
        is_allowed = True
        violation_reason = None

        # Rule 1: Single Transaction Cap
        cap_check = raw_mrp_total <= self.bounds.max_single_transaction_limit
        rules_evaluated.append({
            "rule": "Single Transaction Spending Cap",
            "threshold": f"<= ₹{self.bounds.max_single_transaction_limit}",
            "observed": f"₹{raw_mrp_total}",
            "passed": cap_check
        })
        if not cap_check:
            is_allowed = False
            violation_reason = f"Cart value ₹{raw_mrp_total} exceeds maximum agent transaction limit of ₹{self.bounds.max_single_transaction_limit}"

        # Rule 2: Maximum Discount Cap
        discount_check = proposed_discount_pct <= self.bounds.max_discount_percentage
        rules_evaluated.append({
            "rule": "Maximum Discount Bounding",
            "threshold": f"<= {self.bounds.max_discount_percentage}%",
            "observed": f"{proposed_discount_pct:.2f}%",
            "passed": discount_check
        })
        if not discount_check and is_allowed:
            is_allowed = False
            violation_reason = f"Proposed discount {proposed_discount_pct:.2f}% exceeds hard bounding limit of {self.bounds.max_discount_percentage}%"

        # Calculate Offered Price and Resulting Margin
        actual_discount_pct = proposed_discount_pct if is_allowed else 0.0
        discount_amount = (actual_discount_pct / 100.0) * raw_mrp_total
        offered_price = round(raw_mrp_total - discount_amount, 2)
        
        # Gross Margin = (Selling Price - Cost Price) / Selling Price
        gross_profit = offered_price - cost_basis_total
        margin_percentage = round((gross_profit / offered_price) * 100.0, 2) if offered_price > 0 else 0.0

        # Rule 3: Margin Floor
        margin_check = margin_percentage >= self.bounds.margin_floor_percentage
        rules_evaluated.append({
            "rule": "Merchant Gross Margin Floor",
            "threshold": f">= {self.bounds.margin_floor_percentage}%",
            "observed": f"{margin_percentage:.2f}%",
            "passed": margin_check
        })
        if not margin_check and is_allowed:
            is_allowed = False
            violation_reason = f"Resulting margin {margin_percentage:.2f}% breaches merchant margin floor of {self.bounds.margin_floor_percentage}%"

        # Rule 4: Bundle eligibility check
        if proposed_discount_pct > 0 and len(items) > 1:
            bundle_val_check = raw_mrp_total >= self.bounds.min_order_value_for_bundle
            rules_evaluated.append({
                "rule": "Bundle Synergy Eligibility",
                "threshold": f">= ₹{self.bounds.min_order_value_for_bundle}",
                "observed": f"₹{raw_mrp_total}",
                "passed": bundle_val_check
            })
            if not bundle_val_check and is_allowed:
                is_allowed = False
                violation_reason = f"Cart total ₹{raw_mrp_total} below bundle discount threshold of ₹{self.bounds.min_order_value_for_bundle}"

        # Construct Explainability Token
        decision_label = "APPROVED_BOUNDED" if is_allowed else "REJECTED_BOUND_VIOLATION"
        if is_allowed:
            summary = (
                f"Approved: Applied {actual_discount_pct:.1f}% discount ({bundle_name or 'Synergy Offer'}). "
                f"Total MRP: ₹{raw_mrp_total:.2f}, Final Price: ₹{offered_price:.2f}. "
                f"Merchant preserves healthy gross margin of {margin_percentage:.1f}% (Floor: {self.bounds.margin_floor_percentage}%)."
            )
        else:
            summary = f"Rejected: {violation_reason}. Transaction bounded by financial safety policies."

        now_ts = time.time()
        iso_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now_ts))

        explainability = ExplainabilityToken(
            decision=decision_label,
            raw_mrp_total=round(raw_mrp_total, 2),
            cost_basis_total=round(cost_basis_total, 2),
            offered_price=offered_price,
            discount_amount=round(discount_amount, 2),
            discount_percentage=round(actual_discount_pct, 2),
            margin_percentage=margin_percentage,
            rules_evaluated=rules_evaluated,
            human_readable_summary=summary,
            timestamp=now_ts,
            iso_time=iso_str
        )

        # Generate Gated Pre-Authorization Token if approved
        gated_token = None
        if is_allowed:
            gated_token = self.generate_gated_token(quote_id, buyer_agent_id, offered_price)

        return GuardrailVerdict(
            is_allowed=is_allowed,
            violation_reason=violation_reason,
            explainability=explainability,
            gated_preauth_token=gated_token
        )

    def generate_gated_token(self, quote_id: str, buyer_agent_id: str, amount: float) -> str:
        """Creates a tamper-proof HMAC-SHA256 gated token with expiration."""
        expires_at = int(time.time()) + self.bounds.quote_validity_seconds
        payload = f"{quote_id}:{buyer_agent_id}:{amount:.2f}:{expires_at}"
        signature = hmac.new(self.secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"{payload}:{signature}"

    def verify_gated_token(self, token: str, quote_id: str, buyer_agent_id: str, amount: float) -> Tuple[bool, str]:
        """Verifies that a payment request carries a valid, non-expired, gated authorization token."""
        try:
            parts = token.split(":")
            if len(parts) != 5:
                return False, "Malformed gated token structure"
            
            t_quote_id, t_buyer_id, t_amount_str, t_expires_str, signature = parts
            
            # Check expiration
            expires_at = int(t_expires_str)
            if time.time() > expires_at:
                return False, "Gated authorization token has expired (exceeded 10 min window)"

            # Check matches
            if t_quote_id != quote_id:
                return False, "Quote ID mismatch on gated authorization"
            if t_buyer_id != buyer_agent_id:
                return False, "Buyer Agent ID mismatch on gated authorization"
            if abs(float(t_amount_str) - amount) > 0.01:
                return False, "Amount tampered on gated authorization token"

            # Recompute signature
            recomputed_payload = f"{t_quote_id}:{t_buyer_id}:{t_amount_str}:{t_expires_str}"
            expected_sig = hmac.new(self.secret, recomputed_payload.encode("utf-8"), hashlib.sha256).hexdigest()

            if not hmac.compare_digest(expected_sig, signature):
                return False, "Cryptographic signature verification failed on gated token"

            return True, "Token verified: User/Agent Gate Authorization Confirmed"
        except Exception as e:
            return False, f"Token verification error: {str(e)}"

guardrail_engine = GuardrailEngine()
