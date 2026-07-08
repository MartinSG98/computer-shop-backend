# ADR-0001: HTTP API (API Gateway v2) over REST API

- Status: Accepted
- Date: 2026-07-09

## Context

The backend is a FastAPI app fronted by API Gateway via a Mangum proxy. API
Gateway offers REST API (v1) and HTTP API (v2). The endpoint is read-heavy (the
catalog loads on every visit) and cost matters (see infra ADR-0001).

## Decision

Use HTTP API (v2) with a single `$default` proxy route to one Lambda; FastAPI
does all routing.

## Consequences

- Roughly 70% cheaper per request than REST API, with lower latency.
- Request validation and response shaping stay in FastAPI/Pydantic instead of
  gateway config.
- HTTP API's native JWT authorizer is used for the admin routes (see infra
  ADR-0002).
- Mangum auto-detects the event payload format, so the handler would port to
  REST API unchanged if we ever need it.

## Alternatives considered

- REST API (v1): its main extras (request validation, mapping templates, usage
  plans) are already covered by FastAPI, at higher per-request cost. Rejected.
  Reconsider only if we need API keys + usage plans, gateway response caching, or
  edge-optimized endpoints.
- Lambda Function URL / ALB: no managed JWT authorizer or throttling, which we
  rely on.

See the backend README "Why HTTP API instead of REST API".
