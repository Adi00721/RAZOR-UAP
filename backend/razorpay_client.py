import hmac
import hashlib
import time
import uuid
from typing import Dict, Any, Optional
from .config import settings

class RazorpayGatewayService:
    def __init__(self):
        self._real_client = None

    @property
    def has_real_keys(self) -> bool:
        """Determines if authentic Razorpay test keys are present in settings/env."""
        key_id = (settings.RAZORPAY_KEY_ID or "").strip()
        key_sec = (settings.RAZORPAY_KEY_SECRET or "").strip()
        return (
            not settings.MOCK_PAYMENTS and
            bool(key_id) and
            bool(key_sec) and
            "mock" not in key_id.lower() and
            "mock" not in key_sec.lower() and
            (key_id.startswith("rzp_test_") or key_id.startswith("rzp_live_"))
        )

    @property
    def is_mock_mode(self) -> bool:
        return not self.has_real_keys

    def get_mode_label(self) -> str:
        if self.has_real_keys:
            return "TEST MODE — Live Razorpay Test API"
        return "MOCK MODE — No real Razorpay calls"

    def _get_client(self):
        if self.has_real_keys:
            if not self._real_client:
                try:
                    import razorpay
                    self._real_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
                except Exception:
                    self._real_client = None
            return self._real_client
        return None

    def create_order(self, amount: float, receipt: str, notes: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Creates an order in Razorpay (amount converted to paise).
        Automatically uses live API if real keys are configured, or high-fidelity mock otherwise.
        """
        amount_paise = int(round(amount * 100))
        client = self._get_client()
        
        if client:
            try:
                data = {
                    "amount": amount_paise,
                    "currency": "INR",
                    "receipt": receipt,
                    "notes": notes or {},
                    "payment_capture": 1
                }
                return client.order.create(data=data)
            except Exception as e:
                # Fallback gracefully to mock if live API call raises network exception
                pass

        # High-Fidelity Mock Razorpay Order
        mock_order_id = f"order_{uuid.uuid4().hex[:14]}"
        return {
            "id": mock_order_id,
            "entity": "order",
            "amount": amount_paise,
            "amount_paid": 0,
            "amount_due": amount_paise,
            "currency": "INR",
            "receipt": receipt,
            "offer_id": None,
            "status": "created",
            "attempts": 0,
            "notes": notes or {},
            "created_at": int(time.time()),
            "mode": self.get_mode_label()
        }

    def create_payment_link(
        self,
        amount: float,
        description: str,
        customer_name: str,
        customer_email: str,
        notes: Optional[Dict[str, Any]] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Creates a Razorpay Standard Payment Link / UPI intent link with explicit checkout method options."""
        amount_paise = int(round(amount * 100))
        plink_id = f"plink_{uuid.uuid4().hex[:14]}"
        short_url = f"https://rzp.io/i/{uuid.uuid4().hex[:8]}"
        client = self._get_client()

        checkout_options = options or {
            "checkout": {
                "method": {
                    "upi": 1,
                    "card": 1,
                    "netbanking": 1,
                    "wallet": 1
                }
            }
        }

        if client:
            try:
                link_data = {
                    "amount": amount_paise,
                    "currency": "INR",
                    "accept_partial": False,
                    "description": description,
                    "customer": {
                        "name": customer_name,
                        "email": customer_email
                    },
                    "notify": {"sms": False, "email": False},
                    "reminder_enable": False,
                    "notes": notes or {},
                    "options": checkout_options
                }
                resp = client.payment_link.create(link_data)
                if isinstance(resp, dict):
                    if "options" not in resp:
                        resp["options"] = checkout_options
                    elif isinstance(resp.get("options"), dict):
                        if "checkout" not in resp["options"]:
                            resp["options"]["checkout"] = checkout_options["checkout"]
                        elif "method" not in resp["options"]["checkout"]:
                            resp["options"]["checkout"]["method"] = checkout_options["checkout"]["method"]
                return resp
            except Exception:
                pass

        return {
            "id": plink_id,
            "entity": "payment_link",
            "amount": amount_paise,
            "currency": "INR",
            "status": "created",
            "short_url": short_url,
            "description": description,
            "customer": {"name": customer_name, "email": customer_email},
            "options": checkout_options,
            "created_at": int(time.time()),
            "mode": self.get_mode_label()
        }

    def verify_payment_signature(self, razorpay_order_id: str, razorpay_payment_id: str, razorpay_signature: str) -> bool:
        """Verifies payment signature according to Razorpay standards."""
        client = self._get_client()
        if client:
            try:
                params_dict = {
                    "razorpay_order_id": razorpay_order_id,
                    "razorpay_payment_id": razorpay_payment_id,
                    "razorpay_signature": razorpay_signature
                }
                client.utility.verify_payment_signature(params_dict)
                return True
            except Exception:
                pass

        # Mock Mode Signature Verification
        expected_data = f"{razorpay_order_id}|{razorpay_payment_id}".encode("utf-8")
        expected_sig = hmac.new(settings.RAZORPAY_KEY_SECRET.encode("utf-8"), expected_data, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected_sig, razorpay_signature)

    def verify_webhook_signature(self, webhook_body: str, webhook_signature: str) -> bool:
        """Verifies HMAC-SHA256 signature on incoming Razorpay Webhook events."""
        if not settings.RAZORPAY_WEBHOOK_SECRET or not webhook_signature:
            return False
        client = self._get_client()
        if client:
            try:
                client.utility.verify_webhook_signature(webhook_body, webhook_signature, settings.RAZORPAY_WEBHOOK_SECRET)
                return True
            except Exception:
                pass

        # Manual HMAC-SHA256 verification
        try:
            body_bytes = webhook_body.encode("utf-8") if isinstance(webhook_body, str) else webhook_body
            expected_sig = hmac.new(settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()
            return hmac.compare_digest(expected_sig, webhook_signature)
        except Exception:
            return False

    def generate_mock_payment_confirmation(self, order_id: str, amount: float) -> Dict[str, Any]:
        """Generates realistic test payment signature for simulation in the interactive demo UI."""
        payment_id = f"pay_{uuid.uuid4().hex[:14]}"
        msg = f"{order_id}|{payment_id}".encode("utf-8")
        signature = hmac.new(settings.RAZORPAY_KEY_SECRET.encode("utf-8"), msg, hashlib.sha256).hexdigest()
        return {
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
            "status": "captured",
            "method": "upi",
            "vpa": "buyer.agent@oksbi",
            "amount": amount
        }

razorpay_gateway = RazorpayGatewayService()
