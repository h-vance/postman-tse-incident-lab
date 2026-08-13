# Incident 003: Incorrect Endpoint

## Customer ticket

> Bluebird Commerce receives `404 Not Found` while retrieving customer `cus_123`, even though the customer exists in the dashboard.

All names and identifiers are fictional.

## Environment

- Customer: Bluebird Commerce
- Environment: Production
- Attempted endpoint: `GET /v1/customer/cus_123`
- Documented endpoint: `GET /v1/customers/cus_123`
- Impact: Integration cannot retrieve customer data

## Clarifying questions

1. What exact method and full URL are being sent?
2. Does the response identify a missing route or missing resource?
3. Which API version is configured?
4. Does the documented plural route succeed?
5. Did the endpoint path change recently?

## Initial hypotheses

| Hypothesis | Evidence for | Evidence against | Status |
|---|---|---|---|
| Client uses the wrong route | Response is 404 | Exact response reason not yet checked | Strong |
| Customer record is absent | Requested resource returns 404 | Dashboard shows the customer | Possible |
| Authentication failed | Request did not succeed | Authentication failures use 401 or 403 | Weak |

## Postman reproduction

```http
GET {{base_url}}/v1/customer/cus_123
```

Expected: `200 OK`  
Actual: `404 route_not_found`

## Evidence log

| Tool/source | Result | Interpretation |
|---|---|---|
| Postman | `404 route_not_found` | The requested route does not exist |
| Request comparison | `/customer/` differs from documented `/customers/` | Path construction is incorrect |
| Corrected request | `/v1/customers/cus_123` returns `200` | Customer exists and service is healthy |

## Confirmed facts versus inference

Confirmed:

- The singular route does not exist.
- The documented plural route returns the expected customer.

Inference:

- A client configuration or hard-coded path probably omitted the trailing `s`.

## Root cause and resolution

The integration used `/v1/customer/` instead of `/v1/customers/`. Correct the path and confirm that the production client uses the documented API version and endpoint.

## Verification

- Corrected request returns `200 OK`.
- Response customer ID is `cus_123`.
- Production configuration matches the documented route.

## Customer response

> We reproduced the request and found that it targets `/v1/customer/cus_123`, which is not a valid route. Please update the integration to use `/v1/customers/cus_123`. The corrected endpoint returns the expected customer successfully.

## Engineering handoff

No handoff is required for a client-side path correction. Escalate only if the documented route returns an unexpected response.

## Lessons learned

- Record the exact method and URL before investigating the data layer.
- `route_not_found` and `resource_not_found` imply different next steps.
- A successful corrected request provides a known-good comparison.
