# Incident 001 — Revoked API Key

## Customer ticket

> Acme Health's production webhook integration began returning `401 Unauthorized` after an API-key rotation. Only the `acme-prod` workspace is affected.

All names and identifiers are fictional.

## Environment

- Customer: Acme Health
- Workspace: `acme-prod`
- Environment: Production
- Endpoint: `POST /v1/webhooks`
- Impact: Webhook events are rejected

## Clarifying questions

1. What exact status and response body are returned?
2. When did the failures begin?
3. Which component sends the webhook request?
4. Did that component restart after the key changed?
5. What safe key fingerprint reaches the API?

## Initial hypotheses

| Hypothesis | Evidence for | Evidence against | Status |
|---|---|---|---|
| Sending process retained the revoked key | Failure followed rotation | Configuration reportedly changed | Strong |
| New key is malformed | A malformed key can produce 401 | Not yet observed by server | Possible |
| Platform authentication outage | Requests fail authentication | Only one workspace is affected | Weak |

## Postman reproduction

```http
POST {{base_url}}/v1/webhooks
x-api-key: {{revoked_api_key}}
Content-Type: application/json

{
  "workspace": "acme-prod",
  "event": "webhook.test"
}
```

Expected: `202 Accepted`  
Actual: `401 Unauthorized`

## Evidence log

| Tool/source | Result | Interpretation |
|---|---|---|
| Postman | `401 api_key_revoked` | Request reached the authentication layer |
| Response | `key_fingerprint=key_revoked_91af` | Server received the revoked credential |
| Local API log | Matching request ID, path, status, and fingerprint | Client and server evidence correlate |
| Corrected request | Active key returns `202 accepted` | Request structure and endpoint are valid |

## Confirmed facts versus inference

Confirmed:

- The server received the revoked credential fingerprint.
- The server rejected it with `api_key_revoked`.
- The active credential succeeds without changing the request body or endpoint.

Inference:

- A sending service or worker probably retained the old environment value.
- The exact configuration source still requires customer-side verification.

## Root cause and resolution

The webhook process continued using the revoked key. Update the credential used by the actual sending component, then restart or redeploy that component so it reloads the environment value.

## Verification

- New fingerprint appears in the server evidence.
- Test request returns `202 Accepted`.
- No subsequent requests use the revoked fingerprint.

## Customer response

> We confirmed that webhook requests from your production workspace are arriving with the previously revoked API-key fingerprint. Please verify that the service or worker sending requests to `/v1/webhooks` is configured with the new key, restart or redeploy that component, and send a test request with its timestamp so we can confirm the update.

## Engineering handoff

No handoff is required because the API correctly rejects a revoked credential. Escalate only if the confirmed active credential continues returning `401`.

## Lessons learned

- A customer configuration statement is context; server evidence is verification.
- A safe fingerprint supports comparison without exposing the secret.
- A process may require restart or redeployment after an environment change.
