import os
import time
import json
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import settings
from .catalog import catalog_manager
from .agent_negotiator import merchant_negotiator, BuyerRFQ
from .buyer_agent_sim import buyer_agent_sim
from .guardrails import guardrail_engine
from .razorpay_client import razorpay_gateway
from .audit_ledger import audit_ledger
from .failure_simulator import failure_simulator

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Agent-to-Agent (A2A) Commerce Protocol Gateway implementing NPCI's Unified Agent Protocol (UAP) powered by Razorpay"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static frontend directory
current_dir = os.path.dirname(os.path.abspath(__file__))
frontend_dir = os.path.join(os.path.dirname(current_dir), "frontend")
if not os.path.exists(frontend_dir):
    os.makedirs(frontend_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/style.css")
async def get_root_css():
    return FileResponse(os.path.join(frontend_dir, "style.css"), media_type="text/css")

@app.get("/app.js")
async def get_root_js():
    return FileResponse(os.path.join(frontend_dir, "app.js"), media_type="application/javascript")

# Request Models
class IntentRequest(BaseModel):
    user_intent: str
    user_budget: float = 8000.0
    requested_skus: Optional[List[str]] = None

class GatedCheckoutRequest(BaseModel):
    trace_id: str
    quote: Dict[str, Any]
    customer_name: Optional[str] = "Aarav Sharma"
    customer_email: Optional[str] = "aarav.sharma@example.com"

class MockPaymentCaptureRequest(BaseModel):
    order_id: str
    amount: float
    trace_id: str

# ----------------- UAP & Gateway Endpoints ----------------- #

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return "<h1>RazorUAP Gateway Running. (Frontend index.html not yet deployed)</h1>"

@app.get("/uap/status")
async def get_system_status():
    integrity = audit_ledger.verify_integrity()
    return {
        "gateway": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "mode": razorpay_gateway.get_mode_label(),
        "is_mock_mode": razorpay_gateway.is_mock_mode,
        "razorpay_key_id": settings.RAZORPAY_KEY_ID[:12] + "...",
        "bounds": settings.BOUNDS.model_dump() if hasattr(settings.BOUNDS, "model_dump") else settings.BOUNDS.dict(),
        "ledger_integrity": integrity
    }

@app.get("/uap/catalog")
async def get_uap_catalog():
    """Agent-readable catalog adhering to schema.org / UAP specifications."""
    return catalog_manager.get_uap_catalog_manifest()

@app.post("/uap/negotiate")
async def a2a_negotiate(rfq: BuyerRFQ):
    """Direct A2A Negotiation endpoint for external AI Buyer Agents."""
    trace_id = f"TRC_EXT_{int(time.time())}"
    return merchant_negotiator.process_rfq(rfq, trace_id=trace_id)

@app.post("/uap/execute-intent")
async def execute_buyer_intent(request: IntentRequest):
    """
    Autonomous Buyer Agent entrypoint:
    Dispatches intent, queries catalog, negotiates dynamic bundle, and prepares gated quote.
    """
    result = buyer_agent_sim.execute_intent_pipeline(
        user_intent=request.user_intent,
        user_budget=request.user_budget,
        requested_skus=request.requested_skus
    )
    return result

@app.post("/uap/gated-checkout")
async def gated_checkout(request: GatedCheckoutRequest):
    """
    Gated Transaction Step:
    Validates HMAC PreAuth Token, executes Razorpay Order & Payment Link creation.
    """
    result = buyer_agent_sim.authorize_and_transact(
        trace_id=request.trace_id,
        quote=request.quote,
        customer_name=request.customer_name or "Aarav Sharma",
        customer_email=request.customer_email or "aarav.sharma@example.com"
    )
    if result.get("status") == "GATE_REJECTED":
        raise HTTPException(status_code=403, detail=result.get("error"))
    return result

@app.post("/uap/mock-payment-capture")
async def mock_payment_capture(request: MockPaymentCaptureRequest):
    """
    Simulates payment capture and signature verification from Razorpay Webhook.
    """
    confirmation = razorpay_gateway.generate_mock_payment_confirmation(
        order_id=request.order_id,
        amount=request.amount
    )
    
    # Verify signature
    is_valid = razorpay_gateway.verify_payment_signature(
        razorpay_order_id=confirmation["razorpay_order_id"],
        razorpay_payment_id=confirmation["razorpay_payment_id"],
        razorpay_signature=confirmation["razorpay_signature"]
    )

    if is_valid:
        audit_ledger.record_event(
            trace_id=request.trace_id,
            event_type="PAYMENT_CAPTURED_AND_VERIFIED",
            actor="RAZORPAY_WEBHOOK",
            payload=confirmation
        )

    return {
        "verified": is_valid,
        "payment_confirmation": confirmation
    }

@app.post("/uap/webhook")
async def handle_razorpay_webhook(
    request: Request,
    x_razorpay_signature: Optional[str] = Header(None, alias="X-Razorpay-Signature")
):
    """
    Razorpay Live/Test Webhook Endpoint:
    Receives events (payment.captured, payment.failed, payment_link.paid),
    verifies HMAC-SHA256 signature against RAZORPAY_WEBHOOK_SECRET,
    and commits verified events to the immutable audit ledger.
    """
    raw_body = await request.body()
    body_str = raw_body.decode("utf-8")
    sig = x_razorpay_signature or request.headers.get("x-razorpay-signature") or ""

    if not sig:
        raise HTTPException(status_code=400, detail="Missing X-Razorpay-Signature header")

    is_valid = razorpay_gateway.verify_webhook_signature(body_str, sig)
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    try:
        payload = json.loads(body_str)
    except Exception:
        payload = {"raw": body_str}

    event_type = payload.get("event", "unknown_event")
    order_id = (
        payload.get("payload", {}).get("payment", {}).get("entity", {}).get("order_id") or
        payload.get("payload", {}).get("payment_link", {}).get("entity", {}).get("order_id") or
        payload.get("payload", {}).get("order", {}).get("entity", {}).get("id") or
        f"evt_{int(time.time())}"
    )

    audit_ledger.record_event(
        trace_id=order_id,
        event_type=f"WEBHOOK_{event_type.upper().replace('.', '_')}",
        actor="RAZORPAY_WEBHOOK",
        payload={
            "event": event_type,
            "signature_verified": True,
            "account_id": payload.get("account_id"),
            "event_id": payload.get("id") or payload.get("event_id")
        }
    )

    return {
        "status": "ok",
        "event": event_type,
        "verified": True,
        "order_id": order_id
    }

@app.get("/uap/audit-trail")
async def get_audit_trail(trace_id: Optional[str] = None):
    """Returns append-only cryptographically chained audit ledger entries."""
    entries = audit_ledger.get_entries(trace_id=trace_id, limit=50)
    integrity = audit_ledger.verify_integrity()
    return {
        "integrity": integrity,
        "count": len(entries),
        "entries": [(e.model_dump() if hasattr(e, "model_dump") else e.dict()) for e in entries]
    }

@app.post("/uap/simulate-failure/{scenario}")
async def trigger_failure_scenario(scenario: str):
    """Triggers one of the 3 handled failure modes required for the Razorpay submission."""
    if scenario == "budget_breach":
        return failure_simulator.simulate_budget_cap_breach()
    elif scenario == "stockout":
        return failure_simulator.simulate_inventory_race_condition()
    elif scenario == "adversarial_exploit":
        return failure_simulator.simulate_adversarial_discount_exploit()
    else:
        raise HTTPException(status_code=400, detail=f"Unknown failure scenario '{scenario}'")
