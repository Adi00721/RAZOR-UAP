# Architecture & Protocol Design: RazorUAP

> **Track:** AI Growth & Agentic Commerce (C-Commerce)  
> **Built for:** Razorpay AI Buildathon 2026  
> **Protocol Reference:** NPCI Unified Agent Protocol (UAP) & Agentic Commerce Protocol (ACP / x402)

---

## 1. System Overview

**RazorUAP** is an Agent-to-Agent (A2A) Commerce Protocol Gateway that makes any merchant "transactable" by autonomous AI buyers while anchoring all financial interactions within Razorpay's payments infrastructure.

As NPCI advances the Unified Agent Protocol (UAP) in India and global protocols (ACP, AP2, x402) define machine-to-machine checkout, the fundamental problem is trust, safety, and financial bounding:
* How does a merchant allow autonomous bots to negotiate without suffering economic loss?
* How does a buyer agent ensure it is not being overcharged?
* How does every money action remain explainable, bounded, gated, and auditable?

RazorUAP solves this through a dual-agent negotiation engine governed by a **Deterministic Financial Guardrail Engine** and settled via **Razorpay Test APIs**.

```
[ Human User ]
      │ (Prompt & Budget Cap)
      ▼
[ Autonomous Buyer Agent ] ◄═══════════════════════════════════════════════════╗
      │                                                                         ║
      │ 1. GET /uap/catalog (schema.org JSON-LD)                                ║
      │ 2. POST /uap/negotiate (Structured Buyer RFQ)                           ║
      ▼                                                                         ║ UAP Protocol
[ RazorUAP Gateway ]                                                            ║ (JSON-RPC)
      ├── [ Merchant Sales Agent (Vulcan) ] ── (Synergy Bundle Detection)       ║
      │                                                                         ║
      ├── [ Financial Guardrail Engine ] ───────────────────────────────────────╢
      │         ├── Bounded: Max 15% Disc | Min 20% Margin | ₹25k Txn Cap       ║
      │         ├── Explainable: Generates Mathematical Explainability Token    ║
      │         └── Gated: HMAC-SHA256 Signed PreAuth Token                     ║
      │                                                                         ║
      └── [ Razorpay Settlement Service ] ──────────────────────────────────────╝
                ├── POST /v1/orders (amount in paise)
                ├── POST /v1/payment_links (UPI / Hosted checkout)
                └── Webhook Signature Verification (HMAC-SHA256)
                      │
                      ▼
            [ Immutable Audit Ledger ]
            (SHA-256 Cryptographic Hash Chaining)
```

---

## 2. Core Modules

### 2.1 Agent-Readable Catalog (`/uap/catalog`)
Standard e-commerce catalogs are built for human eyes (HTML/CSS). In the UAP standard, catalogs must be machine-readable, exposing:
* Standardized `schema.org/Product` metadata
* Real-time available stock
* B2B / Wholesale cost basis (internal)
* Synergy graphs: Declares compatible SKUs that create dynamic bundling opportunities (e.g., Mechanical Keyboard $\leftrightarrow$ Wrist Rest; ANC Headphones $\leftrightarrow$ GaN Charger).

### 2.2 Merchant Negotiator Agent (`backend/agent_negotiator.py`)
* Evaluates incoming `BuyerRFQ` payloads.
* Identifies bundling opportunities to increase Average Order Value (AOV) — driving AI Growth.
* Proposes concessions within safe margins.

### 2.3 Financial Guardrail Engine (`backend/guardrails.py`) — Satisfying "The Bar"
The core innovation of RazorUAP is that the LLM is **never allowed to authorize financial transactions unilaterally**. All proposals are filtered through deterministic Python guardrails:

1. **Bounded:**
   $$\text{Discount}_{\text{proposed}} \le 15.0\%$$
   $$\text{Margin}_{\text{gross}} = \frac{\text{Offered Price} - \text{Total Cost Basis}}{\text{Offered Price}} \ge 20.0\%$$
   $$\text{Cart Total} \le \text{Single Transaction Cap } (\text{₹}25,000)$$

2. **Explainable:**
   Every quote produces an `ExplainabilityToken` containing:
   * Rule-by-rule evaluation logs (Cap Check, Discount Check, Margin Check).
   * Mathematical proof of margin preservation.
   * Natural language rationale digestible by both machines and humans.

3. **Gated:**
   Transactions utilize a **Two-Phase Commit**:
   * *Phase 1 (Quote & PreAuth):* System computes quote and issues an HMAC-SHA256 token:
     $$\text{Token} = \text{HMAC}_{\text{Secret}}(\text{QuoteID} \parallel \text{BuyerID} \parallel \text{Amount} \parallel \text{ExpiresAt})$$
   * *Phase 2 (Settlement):* The Buyer Agent cannot execute checkout without presenting the valid, signed token backed by explicit user authorization.

### 2.4 Cryptographic Audit Ledger (`backend/audit_ledger.py`)
An append-only, tamper-evident ledger where each block includes the SHA-256 hash of the previous block:
$$\text{Hash}_n = \text{SHA256}(\text{Index} \parallel \text{Timestamp} \parallel \text{TraceID} \parallel \text{EventType} \parallel \text{Actor} \parallel \text{Payload} \parallel \text{Hash}_{n-1})$$
Any alteration of past quotes, prices, or orders immediately invalidates the entire subsequent chain.

---

## 3. Razorpay Integration Points

| Razorpay Component | Implementation in RazorUAP |
| :--- | :--- |
| **Orders API** (`/v1/orders`) | Invoked during Gated Phase. Amount calculated in paise (`int(amount * 100)`), tagged with UAP `trace_id` in `notes`. |
| **Payment Links API** (`/v1/payment_links`) | Generates instant UPI / Card payment short URL (`https://rzp.io/i/...`) for one-click settlement. |
| **Utility Signature Verification** | Validates `razorpay_order_id`, `razorpay_payment_id`, and `razorpay_signature` using HMAC-SHA256 with `key_secret`. |
| **Dual Mode Engine** | Runs seamlessly in **Mock Mode** for offline/zero-config hackathon demoing, and hot-swaps to **Live Test API** when `RAZORPAY_KEY_ID` and `SECRET` are populated. |
