# Realflow Webhook Server

This project implements a simple Flask-based webhook for the Realflow AI Voice Assistant (built using Vapi).  
It receives structured tool call data, consolidates lead details for each call, and returns a single JSON summary through HTTP endpoints.  
The app is deployed and live on Vercel.

---

## Deliverables

- **Vapi Assistant ID:** `c6dbb24c-90ed-4906-9221-a1685e45d266`
- **Webhook Endpoint (POST):** `https://realflow-webhook.vercel.app/webhook`
- **Fetch Latest JSON (GET):** `https://realflow-webhook.vercel.app/get_json`
- **Health Check (GET):** `https://realflow-webhook.vercel.app/`