# ADR-0002: Repository pattern with an in-memory fallback

- Status: Accepted
- Date: 2026-07-09

## Context

The API reads products and categories and reads/writes orders. It should run
locally and in tests with zero AWS setup, while using DynamoDB in the cloud.

## Decision

Define a repository interface (ABC) per aggregate with two implementations, an
in-memory one (seed data) and a DynamoDB one, chosen at runtime by a cached
factory: use DynamoDB when the table env var is set, otherwise fall back to the
in-memory store.

## Consequences

- The app boots and serves with no AWS credentials or tables. Tests run fully
  offline: API tests use the in-memory repos, and the DynamoDB implementations
  are tested against `moto`.
- Swapping data stores is a factory change, not an application change.
- The in-memory and DynamoDB paths must stay behaviourally consistent; tests
  cover both.

## Alternatives considered

- Calling DynamoDB directly from the route handlers: couples the app to AWS and
  is hard to test offline. Rejected.
- A full ORM / data-mapper layer: overkill for a handful of access patterns.
