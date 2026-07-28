# Incident 002 — Insufficient Permissions

## Customer ticket

> Northstar Analytics can authenticate successfully, but its integration receives `403 Forbidden` when requesting the administrative report.

All names and identifiers are fictional.

## Environment

- Customer: Northstar Analytics
- Environment: Production
- Endpoint: `GET /v1/admin/reports`
- Impact: Operations team cannot retrieve the report

## Clarifying questions

1. Is the response `401` or `403`?
2. What authentication scheme is used?
3. Which safe token fingerprint reaches the API?
4. Which scopes or role does the token possess?
5. Does a known admin token succeed?

## Initial hypotheses

| Hypothesis | Evidence for | Evidence against | Status |
|---|---|---|---|
| Token lacks required scope | Server returns 403 | Not yet compared with admin token | Strong |
| Token is invalid | Request involves authentication | Invalid tokens normally return 401 | Weak |
| Route is unavailable | Customer cannot retrieve report | Server returned an authorization decision | Weak |

## Postman reproduction

```http
GET {{base_url}}/v1/admin/reports
Authorization: Bearer {{viewer_token}}
```

Expected: `200 OK`  
Actual: `403 Forbidden`

## Evidence log

| Tool/source | Result | Interpretation |
|---|---|---|
| Postman | `403 insufficient_scope` | Identity is known but permission is denied |
| Response | Required scope is `reports:admin` | Failure is authorization, not malformed JSON |
| Corrected request | Admin token returns `200 authorized` | Route and service are healthy |

## Confirmed facts versus inference

Confirmed:

- The viewer token reaches the endpoint.
- The endpoint requires `reports:admin`.
- A token with the required permission succeeds.

Inference:

- The customer may have selected a credential intended for read-only use.

## Root cause and resolution

The integration used a valid viewer token that lacked the required administrative scope. Replace it with an approved credential carrying `reports:admin`; do not broaden the existing token without authorization.

## Verification

- Correct token fingerprint appears in the evidence.
- Request returns `200 OK`.
- Report data is present.

## Customer response

> We confirmed that the credential is valid, but it does not have the `reports:admin` permission required by this endpoint. Please use an approved administrative credential for this request. Once updated, send a new test request and share the timestamp so we can verify access.

## Engineering handoff

No handoff is required when the documented permission resolves the request. Escalate if a correctly scoped token continues returning `403`.

## Lessons learned

- `401` usually asks, “Who are you?”
- `403` means the identity is known but not permitted.
- The safest fix uses the least privilege required for the task.
