import os
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

class BoundingRules(BaseModel):
    # The Bar: Financial Bounds required by Razorpay
    max_discount_percentage: float = 15.0          # Maximum dynamic discount agent can ever concede
    margin_floor_percentage: float = 20.0          # Hard floor on merchant profit margin
    max_single_transaction_limit: float = 25000.0  # Max transaction amount allowed for agentic execution
    min_order_value_for_bundle: float = 3000.0     # Threshold required to qualify for bundle discount
    quote_validity_seconds: int = 600              # Gated quote expires after 10 minutes

class Settings:
    PROJECT_NAME: str = "RazorUAP - Agent-to-Agent Commerce Gateway"
    VERSION: str = "1.0.0"
    
    # Financial Bounding Constraints (The Bar)
    MAX_DISCOUNT_PERCENT: float = 15.0
    MIN_GROSS_MARGIN_PERCENT: float = 20.0
    MAX_TRANSACTION_LIMIT_INR: float = 25000.0
    QUOTE_VALIDITY_SECONDS: int = 600
    
    # Razorpay Test Credentials (Leave blank or set 'mock' for local simulation)
    RAZORPAY_KEY_ID: str = os.getenv("RAZORPAY_KEY_ID", "rzp_test_mock_agent_key")
    RAZORPAY_KEY_SECRET: str = os.getenv("RAZORPAY_KEY_SECRET", "mock_secret_key_buildathon_2026")
    RAZORPAY_WEBHOOK_SECRET: str = os.getenv("RAZORPAY_WEBHOOK_SECRET", "rzp_webhook_secret_2026")
    
    # Mode: True for Deterministic Mock Engine; False for Live Razorpay API
    MOCK_PAYMENTS: bool = os.getenv("MOCK_PAYMENTS", "true").lower() in ("true", "1", "yes")
    
    # Cryptographic Gating Secret for HMAC-SHA256 PreAuthorizationQuoteTokens
    HMAC_GATE_SECRET: str = os.getenv("HMAC_GATE_SECRET", "razorpay_uap_gate_hmac_secret_2026")
    
    # Gemini API Key (Optional; fallback rule engine activates automatically if missing)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Server configuration
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    
    BOUNDS: BoundingRules = BoundingRules(
        max_discount_percentage=MAX_DISCOUNT_PERCENT,
        margin_floor_percentage=MIN_GROSS_MARGIN_PERCENT,
        max_single_transaction_limit=MAX_TRANSACTION_LIMIT_INR,
        quote_validity_seconds=QUOTE_VALIDITY_SECONDS
    )

settings = Settings()
