# RazorUAP — Agent-to-Agent (A2A) Commerce Protocol Gateway

> **Track:** AI Growth & Agentic Commerce (C-Commerce)  
> **Event:** Razorpay AI Buildathon 2026  
> **Status:** Submission Ready • Automated Test Suite Passing 100%

---

## ⚡ What is RazorUAP?

**RazorUAP** is an Agent-to-Agent (A2A) Commerce Gateway compliant with NPCI's Unified Agent Protocol (UAP) and emerging agentic standards (ACP / x402), powered by Razorpay. It makes any D2C or enterprise merchant **"transactable"** by autonomous AI buyer agents.

### Highlights: Meeting "The Bar"
* **Explainable:** Emits step-by-step mathematical `ExplainabilityToken` justifying all bundle pricing, margin retention, and dynamic discounts.
* **Bounded:** Programmatic bounds: maximum 15% discount, minimum 20% gross margin floor, ₹25,000 single transaction cap.
* **Gated:** Two-Phase Commit using HMAC-SHA256 PreAuth tokens with a 10-minute expiry; money cannot move without explicit user authorization.
* **Audit Trail:** Append-only, tamper-evident event ledger with SHA-256 cryptographic hash chaining.
* **Handled Failure:** Deterministic resilience against budget breaches, stockout race conditions, and adversarial prompt injections.
* **Razorpay Integration:** Full test-mode support for Razorpay Orders API, Payment Links, and Webhook Signature Verification.

---

## 🚀 Quick Start (Windows / Mac / Linux)

### 1. Prerequisites
* Python 3.9+ installed
* (Optional) Razorpay Test Keys (`RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`). If omitted, RazorUAP runs automatically in high-fidelity **Simulated Mock Test Mode**.

### 2. Installation
Open PowerShell or Command Prompt in this folder:
```powershell
pip install -r requirements.txt
```

### 3. Run Automated Validation Suite
Verify all criteria and failure modes:
```powershell
python test_e2e.py
```

### 4. Launch the Gateway & Interactive UI
```powershell
python -m uvicorn backend.main:app --reload --port 8000
```
Or double-click `run.bat` on Windows.

Open your browser at:
👉 **[http://localhost:8000](http://localhost:8000)**

---

## 📂 Project Structure

```
razorpay-uap-agent/
├── backend/
│   ├── main.py                  # FastAPI Application & UAP Endpoints
│   ├── config.py                # Razorpay keys & financial bounding parameters
│   ├── catalog.py               # Machine-readable catalog (schema.org / UAP)
│   ├── guardrails.py            # Financial Guardrail Engine (The Bar)
│   ├── agent_negotiator.py      # Merchant Sales Agent (Synergy Bundles)
│   ├── buyer_agent_sim.py       # Autonomous Buyer Agent Simulator
│   ├── razorpay_client.py       # Dual-mode Razorpay client (Test / Mock)
│   ├── audit_ledger.py          # Cryptographically chained SHA-256 Audit Trail
│   └── failure_simulator.py     # Deterministic Handled Failure modules
├── frontend/
│   ├── index.html               # Interactive Dashboard
│   ├── style.css                # Dark-mode fintech styling
│   └── app.js                   # Client controller & live stream
├── test_e2e.py                  # 9-point automated test suite
├── ARCHITECTURE.md              # Deep-dive architecture & protocol design
├── 2AM_CHALLENGES.md            # "What broke at 2 AM, and how you got out"
├── DEMO_SCRIPT.md               # 5-minute video presentation script
├── requirements.txt             # Project dependencies
└── run.bat                      # 1-click Windows runner
```

---

## 🔑 Setting Real Razorpay Test Keys (Optional)

Create a `.env` file in this directory or set environment variables:
```ini
RAZORPAY_KEY_ID=rzp_test_YourTestKeyIdHere
RAZORPAY_KEY_SECRET=YourTestKeySecretHere
MOCK_PAYMENTS=false
```

When `MOCK_PAYMENTS=false`, RazorUAP calls your live Razorpay Dashboard test instance directly.
