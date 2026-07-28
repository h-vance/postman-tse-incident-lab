#!/usr/bin/env python3
"""Deterministic local API for Postman troubleshooting practice."""

from __future__ import annotations

import argparse
import json
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlsplit


DEMO_CREDENTIALS = {
    "revoked-demo-key": "key_revoked_91af",
    "active-demo-key": "key_active_72c1",
    "viewer-demo-token": "token_viewer_4d20",
    "admin-demo-token": "token_admin_8b31",
}
MAX_BODY_BYTES = 4_096
READ_TIMEOUT_SECONDS = 5


class LabRequestHandler(BaseHTTPRequestHandler):
    """Serve deterministic success and failure responses without logging secrets."""

    server_version = "TSEIncidentLab/1.0"

    def do_GET(self) -> None:  # noqa: N802
        self.request_id = uuid.uuid4().hex[:12]
        parsed = urlsplit(self.path)

        if parsed.path == "/health":
            self._respond(HTTPStatus.OK, {"status": "healthy"}, "healthy")
            return

        if parsed.path == "/v1/admin/reports":
            self._handle_admin_reports()
            return

        if parsed.path == "/v1/customers/cus_123":
            self._respond(
                HTTPStatus.OK,
                {
                    "status": "found",
                    "customer": {"id": "cus_123", "name": "Bluebird Commerce"},
                },
                "customer_found",
            )
            return

        if parsed.path == "/v1/usage":
            self._handle_usage(parse_qs(parsed.query))
            return

        self._respond(
            HTTPStatus.NOT_FOUND,
            {
                "error": "route_not_found",
                "message": f"No route exists for {parsed.path}",
            },
            "route_not_found",
        )

    def do_POST(self) -> None:  # noqa: N802
        self.request_id = uuid.uuid4().hex[:12]
        parsed = urlsplit(self.path)

        if parsed.path != "/v1/webhooks":
            self._respond(
                HTTPStatus.NOT_FOUND,
                {
                    "error": "route_not_found",
                    "message": f"No route exists for {parsed.path}",
                },
                "route_not_found",
            )
            return

        body = self._read_json_body()
        if body is None:
            return

        if not isinstance(body.get("workspace"), str) or not isinstance(
            body.get("event"), str
        ):
            self._respond(
                HTTPStatus.BAD_REQUEST,
                {
                    "error": "invalid_payload",
                    "message": "workspace and event must be strings",
                },
                "invalid_payload",
            )
            return

        api_key = self.headers.get("x-api-key", "")
        fingerprint = self._fingerprint(api_key)

        if not api_key:
            self._respond(
                HTTPStatus.UNAUTHORIZED,
                {
                    "error": "api_key_missing",
                    "message": "The x-api-key header is required",
                },
                "api_key_missing",
                fingerprint,
            )
            return

        if api_key == "revoked-demo-key":
            self._respond(
                HTTPStatus.UNAUTHORIZED,
                {
                    "error": "api_key_revoked",
                    "message": "The supplied API key has been revoked",
                    "key_fingerprint": fingerprint,
                },
                "api_key_revoked",
                fingerprint,
            )
            return

        if api_key != "active-demo-key":
            self._respond(
                HTTPStatus.UNAUTHORIZED,
                {
                    "error": "api_key_invalid",
                    "message": "The supplied API key is not recognized",
                },
                "api_key_invalid",
                fingerprint,
            )
            return

        self._respond(
            HTTPStatus.ACCEPTED,
            {
                "status": "accepted",
                "workspace": body["workspace"],
                "event": body["event"],
                "key_fingerprint": fingerprint,
            },
            "webhook_accepted",
            fingerprint,
        )

    def _handle_admin_reports(self) -> None:
        authorization = self.headers.get("Authorization", "")
        scheme, _, token = authorization.partition(" ")
        fingerprint = self._fingerprint(token)

        if scheme != "Bearer" or not token:
            self._respond(
                HTTPStatus.UNAUTHORIZED,
                {
                    "error": "authorization_header_missing",
                    "message": "A Bearer token is required",
                },
                "authorization_header_missing",
                fingerprint,
            )
            return

        if token == "viewer-demo-token":
            self._respond(
                HTTPStatus.FORBIDDEN,
                {
                    "error": "insufficient_scope",
                    "message": "The reports:admin scope is required",
                    "token_fingerprint": fingerprint,
                },
                "insufficient_scope",
                fingerprint,
            )
            return

        if token != "admin-demo-token":
            self._respond(
                HTTPStatus.UNAUTHORIZED,
                {
                    "error": "token_invalid",
                    "message": "The Bearer token is not recognized",
                },
                "token_invalid",
                fingerprint,
            )
            return

        self._respond(
            HTTPStatus.OK,
            {
                "status": "authorized",
                "report": {"open_incidents": 3, "services_healthy": 12},
                "token_fingerprint": fingerprint,
            },
            "report_authorized",
            fingerprint,
        )

    def _handle_usage(self, query: dict[str, list[str]]) -> None:
        raw_attempt = query.get("attempt", [""])[0]
        try:
            attempt = int(raw_attempt)
        except ValueError:
            attempt = 0

        if attempt < 1:
            self._respond(
                HTTPStatus.BAD_REQUEST,
                {
                    "error": "invalid_attempt",
                    "message": "attempt must be a positive integer",
                },
                "invalid_attempt",
            )
            return

        if attempt > 3:
            self._respond(
                HTTPStatus.TOO_MANY_REQUESTS,
                {
                    "error": "rate_limit_exceeded",
                    "message": "Retry after 30 seconds",
                    "limit": 3,
                },
                "rate_limit_exceeded",
                extra_headers={"Retry-After": "30"},
            )
            return

        self._respond(
            HTTPStatus.OK,
            {
                "status": "within_limit",
                "attempt": attempt,
                "remaining": 3 - attempt,
            },
            "within_limit",
        )

    def _read_json_body(self) -> dict[str, Any] | None:
        media_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if media_type != "application/json":
            self._respond(
                HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                {
                    "error": "content_type_required",
                    "message": "Content-Type must be application/json",
                },
                "content_type_required",
            )
            return None

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                raise ValueError
            if length > MAX_BODY_BYTES:
                self._respond(
                    HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                    {
                        "error": "request_too_large",
                        "message": f"Request body must not exceed {MAX_BODY_BYTES} bytes",
                    },
                    "request_too_large",
                )
                return None
            self.connection.settimeout(READ_TIMEOUT_SECONDS)
            payload = self.rfile.read(length)
            body = json.loads(payload)
        except TimeoutError:
            self._respond(
                HTTPStatus.REQUEST_TIMEOUT,
                {"error": "request_timeout", "message": "Request body timed out"},
                "request_timeout",
            )
            return None
        except (ValueError, json.JSONDecodeError):
            self._respond(
                HTTPStatus.BAD_REQUEST,
                {"error": "invalid_json", "message": "Request body must be valid JSON"},
                "invalid_json",
            )
            return None

        if not isinstance(body, dict):
            self._respond(
                HTTPStatus.BAD_REQUEST,
                {"error": "invalid_json", "message": "Request body must be an object"},
                "invalid_json",
            )
            return None

        return body

    @staticmethod
    def _fingerprint(credential: str) -> str:
        if not credential:
            return "none"
        return DEMO_CREDENTIALS.get(credential, "unknown")

    def _respond(
        self,
        status: HTTPStatus,
        payload: dict[str, Any],
        reason: str,
        fingerprint: str = "none",
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        response = {"request_id": self.request_id, **payload}
        encoded = json.dumps(response, indent=2).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("X-Request-ID", self.request_id)
        for name, value in (extra_headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(encoded)

        path = urlsplit(self.path).path
        safe_paths = {
            "/health",
            "/v1/webhooks",
            "/v1/admin/reports",
            "/v1/customer/cus_123",
            "/v1/customers/cus_123",
            "/v1/usage",
        }
        logged_path = path if path in safe_paths else "<unmatched>"
        print(
            f"request_id={self.request_id} method={self.command} path={logged_path} "
            f"status={status.value} reason={reason} "
            f"credential_fingerprint={fingerprint}",
            flush=True,
        )

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8088)
    args = parser.parse_args()

    server = ThreadingHTTPServer(("127.0.0.1", args.port), LabRequestHandler)
    server.daemon_threads = True
    print(f"TSE Incident Lab listening on http://127.0.0.1:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
