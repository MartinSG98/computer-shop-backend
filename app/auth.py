"""Admin authorization.

The `/admin/*` routes sit behind the API Gateway Cognito JWT authorizer, which
guarantees a valid token before the request ever reaches the Lambda. That only
proves the caller is *authenticated*, not that they are an admin, so this module
does the *authorization* step: it reads the `cognito:groups` claim and requires
membership of the `admins` group.

Mangum injects the raw API Gateway event into the ASGI scope as `aws.event`.
When there is no event (local dev, tests, anything not behind the gateway) there
are no claims to check, so the guard is a no-op, mirroring the repository layer's
"fall back to in-memory when nothing is configured" behaviour.
"""

import re
from typing import Any, Mapping

from fastapi import HTTPException, Request

ADMIN_GROUP = "admins"


def _groups_from_claims(claims: Mapping[str, Any]) -> set[str]:
    raw = claims.get("cognito:groups")
    if raw is None:
        return set()
    if isinstance(raw, (list, tuple)):
        return {str(group) for group in raw}
    # The HTTP API JWT authorizer serializes the array claim as a string, e.g.
    # "[admins manager]". Strip the brackets and split on commas/whitespace.
    text = str(raw).strip().strip("[]")
    return {group for group in re.split(r"[,\s]+", text) if group}


def require_admin(request: Request) -> None:
    """FastAPI dependency: 403 unless the caller is in the admins group."""
    event = request.scope.get("aws.event")
    if not event:
        # No gateway event: local/dev/tests. Nothing to enforce here.
        return

    claims = (
        event.get("requestContext", {})
        .get("authorizer", {})
        .get("jwt", {})
        .get("claims", {})
    )
    if ADMIN_GROUP not in _groups_from_claims(claims):
        raise HTTPException(status_code=403, detail="Admin access required")
