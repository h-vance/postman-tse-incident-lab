# Incident 004: Rate-Limited Client

## Customer ticket

> Orbit Metrics reports intermittent failures while polling usage data. Requests succeed initially, then begin returning `429 Too Many Requests`.

All names and identifiers are fictional.

## Environment

- Customer: Orbit Metrics
- Environment: Production
- Endpoint: `GET /v1/usage`
- Limit: Three requests per demonstration window
- Impact: Usage synchronization pauses

## Clarifying questions

1. What status and response headers are returned?
2. How frequently does the client send requests?
3. Does the response include `Retry-After`?
4. Does the client retry immediately or use backoff?
5. Are multiple workers sharing the same limit?

## Initial hypotheses

| Hypothesis | Evidence for | Evidence against | Status |
|---|---|---|---|
| Client exceeds the request limit | Failures begin after successful requests | Retry evidence not yet inspected | Strong |
| API service is unavailable | Requests fail intermittently | API returns a structured 429 | Weak |
| Authentication expired | Requests stop succeeding | Authentication failures use 401 | Weak |

## Postman reproduction

```http
GET {{base_url}}/v1/usage?attempt=4
```

Expected: `200 OK`  
Actual: `429 Too Many Requests` with `Retry-After: 30`

For deterministic local runs, `attempt` represents the customer's observed request
number; this lab validates 429 response semantics and client handling, not a
production-grade rate-limit counter or clock.

## Evidence log

| Tool/source | Result | Interpretation |
|---|---|---|
| Postman | `429 rate_limit_exceeded` | Server is intentionally throttling the client |
| Response headers | `Retry-After: 30` | Client has an explicit safe retry time |
| Corrected request | Attempt within limit returns `200` | Endpoint and service remain healthy |

## Confirmed facts versus inference

Confirmed:

- The fourth simulated attempt exceeds the documented limit.
- The API instructs the client to wait 30 seconds.
- A request within the limit succeeds.

Inference:

- The production client may retry too aggressively or run multiple uncoordinated workers.

## Root cause and resolution

The client exceeded the request limit and did not respect the server's retry guidance. Honor `Retry-After`, add bounded exponential backoff with jitter, and coordinate retries across workers.

## Verification

- Requests remain within the documented limit.
- Client waits at least the specified retry interval after 429.
- No immediate retry storm appears in logs.

## Customer response

> We confirmed that the API is rate limiting requests after the allowed threshold and is returning `Retry-After: 30`. Please update the client to pause for the specified interval before retrying and avoid immediate parallel retries. The endpoint remains healthy for requests within the limit.

## Engineering handoff

No handoff is required when the client exceeds a documented limit. Escalate if correctly paced traffic continues receiving unexpected 429 responses.

## Lessons learned

- A 429 is a controlled service response, not proof of an outage.
- `Retry-After` is operational evidence and should drive the next action.
- Safe retry logic must prevent synchronized retry storms.
