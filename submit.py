#!/usr/bin/env python3
"""
B12 Application Submission Script
Runs via GitHub Actions CI and POSTs a signed payload to B12's submission endpoint.
"""

import hashlib
import hmac
import json
import os
import urllib.request
from datetime import datetime, timezone


# ── Configuration ─────────────────────────────────────────────────────────────
# Fill in your details here (or pass them as environment variables in the
# GitHub Actions workflow so nothing sensitive is committed to the repo).

NAME          = os.environ.get("APPLICANT_NAME",    "Your Name")
EMAIL         = os.environ.get("APPLICANT_EMAIL",   "you@example.com")
RESUME_LINK   = os.environ.get("RESUME_LINK",       "https://your-resume.example.com")

# These two are best set dynamically by the CI environment (see the workflow).
REPOSITORY_LINK = os.environ.get("REPOSITORY_LINK", "https://github.com/your-username/your-repo")
ACTION_RUN_LINK = os.environ.get("ACTION_RUN_LINK", "https://github.com/your-username/your-repo/actions/runs/0")

# Submission endpoint
ENDPOINT = "https://b12.io/apply/submission"

# Signing secret – keep this in a repository secret or environment variable;
# never hard-code it in plaintext in a production repo.
SIGNING_SECRET = os.environ.get("B12_SIGNING_SECRET", "hello-there-from-b12")
# ──────────────────────────────────────────────────────────────────────────────


def build_payload() -> dict:
    """Construct the submission payload with an ISO 8601 UTC timestamp."""
    return {
        "action_run_link": ACTION_RUN_LINK,
        "email":           EMAIL,
        "name":            NAME,
        "repository_link": REPOSITORY_LINK,
        "resume_link":     RESUME_LINK,
        "timestamp":       datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") +
                           f"{datetime.now(timezone.utc).microsecond // 1000:03d}Z",
    }


def canonicalize(payload: dict) -> bytes:
    """
    Serialize the payload to a compact, alphabetically-sorted JSON string
    and return it as UTF-8 bytes.
    """
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def sign(body: bytes, secret: str) -> str:
    """Return 'sha256=<hex-digest>' HMAC-SHA256 of body using secret as the key."""
    mac = hmac.new(secret.encode("utf-8"), body, hashlib.sha256)
    return f"sha256={mac.hexdigest()}"


def post(body: bytes, signature: str) -> dict:
    """Send the signed POST request and return the parsed JSON response."""
    req = urllib.request.Request(
        ENDPOINT,
        data=body,
        method="POST",
        headers={
            "Content-Type":    "application/json; charset=utf-8",
            "X-Signature-256": signature,
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    payload   = build_payload()
    body      = canonicalize(payload)
    signature = sign(body, SIGNING_SECRET)

    print("── Submission payload ──────────────────────────────────")
    print(body.decode("utf-8"))
    print(f"\n── X-Signature-256: {signature}")
    print("\n── Posting to B12 …")

    response = post(body, signature)

    if response.get("success"):
        print("\n✅  Submission accepted!")
        print(f"    Receipt: {response['receipt']}")
    else:
        raise RuntimeError(f"Unexpected response from B12: {response}")


if __name__ == "__main__":
    main()