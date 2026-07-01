# Computer Shop API

Backend for the Computer Shop app. A FastAPI service that runs locally with zero
external setup and is designed to deploy to AWS Lambda behind API Gateway, with
DynamoDB as the data store.

## Status

v0.6 — assortment API with categories, order capture + checkout, a Cognito-gated
admin sales dashboard, CORS for a browser frontend, and a chat route that proxies
to the support agent on Bedrock AgentCore. Runs locally with zero setup, deploys
to AWS Lambda behind API Gateway, reads from DynamoDB when configured, and serves
product images via S3 + CloudFront.

## Data store

The repository implementation is chosen at runtime from the environment:

| Env var | Effect |
| --- | --- |
| _(none)_ | In-memory seed data. Zero setup — just run. |
| `PRODUCTS_TABLE` | Use DynamoDB for products; value is the table name. |
| `CATEGORIES_TABLE` | Use DynamoDB for categories; value is the table name. |
| `ORDERS_TABLE` | Use DynamoDB for orders; value is the table name. |
| `AWS_REGION` | AWS region (set automatically on Lambda). |
| `DYNAMODB_ENDPOINT_URL` | Optional override, e.g. DynamoDB Local. |
| `CDN_BASE_URL` | CloudFront base URL for images (see below). |
| `CORS_ALLOW_ORIGINS` | Comma-separated allowed origins (see below). |
| `AGENT_RUNTIME_ARN` | AgentCore runtime for `/chat`; unset disables the route (503). |

Each table is independent: set `PRODUCTS_TABLE`, `CATEGORIES_TABLE`, and
`ORDERS_TABLE` for a fully DynamoDB-backed app, or leave them unset to run
entirely on in-memory data (orders then live only for the process lifetime).

Seed real tables (creates them if missing):

```powershell
$env:AWS_REGION = "eu-west-2"
$env:PRODUCTS_TABLE = "computer-shop-products"
$env:CATEGORIES_TABLE = "computer-shop-categories"
python -m scripts.seed_dynamodb
```

Key schema: products use partition key `id` (String), categories use `slug`
(String). Both are provisioned 5 RCU / 5 WCU to stay within the DynamoDB
always-free tier (25/25 per account).

Re-running the seed is idempotent and **prunes** rows no longer present in
`app/seed_data.py`, so the tables always match the seed.

## Product images

Images live in **S3** and are served via **CloudFront** (both provisioned by the
Terraform stack). DynamoDB stores only the S3 object key (`image_key`, e.g.
`cpus/amd.jpg` or `coolers/<id>.jpg`); the API never stores or returns the raw
key. Instead it returns a computed `image_url` built from `CDN_BASE_URL` + the key:

- `CDN_BASE_URL` set and product has a key → `image_url` is the full CloudFront URL.
- No `CDN_BASE_URL`, or product has no image → `image_url` is `null`.

Storing the key (not the full URL) means the CDN domain can change without
rewriting any records.

### Uploading images

Place files under `seed_images/` so the folder mirrors the S3 keys (e.g.
`seed_images/cpus/amd.jpg`), then sync to the images bucket:

```powershell
aws s3 sync seed_images/ s3://<images-bucket>/   # name from: terraform output images_bucket_name
```

`seed_images/` is gitignored — images live in S3, not the repo. Use JPG (the AWS
CLI sets `Content-Type` automatically so CloudFront serves inline). **Overwriting**
an existing key needs a CloudFront invalidation
(`aws cloudfront create-invalidation --distribution-id <id> --paths "/<prefix>/*"`);
brand-new keys don't.

## Categories

Products belong to one category, referenced by a URL-safe `slug` (e.g.
`graphics-cards`). Categories are a first-class entity with their own data
(`name`, `description`, `sort_order`, optional image). The seed taxonomy covers a
full PC build (processors, CPU coolers, motherboards, memory, graphics cards,
storage, power supplies, cases) plus monitors, keyboards, mice, and headsets.

Filter products with `GET /products?category=<slug>`:

- unknown slug → `404` (so a typo/stale link is distinguishable from...)
- valid slug with no products → empty list `[]` (...an empty category)

Filtering is currently done in-app. The scaling path, once the catalog is large,
is a DynamoDB GSI on `category` so it becomes an indexed query instead of a scan.

## Orders and checkout

`POST /orders` records an order. The client sends only product ids and
quantities; the server looks up each product in the catalog and sets the price,
name, and category itself, so the amount charged can never be chosen by the
caller.

```json
{"username": "user-normal", "items": [{"product_id": "gpu-...", "quantity": 1}]}
→ {"id": "ord_...", "total": "599.99", "currency": "USD", "items": [...], "created_at": "..."}
```

- Line items **snapshot** the name, category, and unit price at purchase time, so
  historical orders and the sales metrics stay correct when the catalog is later
  re-priced or re-categorised.
- Money is computed and stored as `Decimal` (serialized as a string in JSON), so
  it never round-trips through float. Orders persist to DynamoDB when
  `ORDERS_TABLE` is set, otherwise to the in-memory store.
- Checkout is a **public** route. `username` is a best-effort label the frontend
  sends from its signed-in context; it is not server-verified, so it is not an
  authorization fact. Validation: empty carts and zero / over-100 quantities are
  rejected (422), and an unknown product id returns 404.

## Admin dashboard (Cognito)

The `/admin/*` routes are gated by Cognito. At the edge, API Gateway runs a
**JWT authorizer** on those routes only, so an unauthenticated caller never
reaches the Lambda while the public catalog stays open. The bearer must be the
Cognito **ID token**, since that carries both the `aud` claim the authorizer
checks and the `cognito:groups` claim the app reads.

A valid token only proves the caller is authenticated, not that they are an
admin. So `require_admin` (in `app/auth.py`) does the authorization step: it
reads `cognito:groups` from the authorizer claims and requires the **`admins`**
group, returning 403 otherwise. With no gateway event present (local dev, tests)
it is a no-op, matching the repository's "in-memory when nothing is configured"
behaviour.

- `GET /admin/overview` — dashboard metrics (KPIs, sales over time, top products,
  sales by category), computed in a single pass over one scan of the orders
  table. No secondary index, to stay within the free tier.
- `GET /admin/orders` — recent orders, most recent first.

## Support agent chat

`POST /chat` proxies one customer message to the support agent (a Strands + Nova
Lite agent on Bedrock AgentCore Runtime, see the `computer-shop-support-agent`
repo) and returns its reply:

```json
{"message": "Whats your cheapest GPU?", "session_id": "<33-100 chars>"}
→ {"reply": "The cheapest GPU we have is ..."}
```

- The **session id** is generated by the frontend (one UUID per chat window) and
  passed through unchanged; AgentCore routes the same id to the same warm session,
  which is what gives follow-up questions their context. The backend stays
  stateless. The 33-char minimum is an AgentCore requirement, enforced at
  validation (422).
- The **message cap** (500 chars) bounds the Bedrock token spend per request.
- `AGENT_RUNTIME_ARN` unset → `503 Chat is not configured` (e.g. local dev).
- Any upstream failure → `502 Support agent unavailable`, with the real error in
  the logs only — AWS error texts can contain ARNs and don't belong in responses.

The frontend never calls the agent directly: the proxy keeps the runtime private,
reuses the API's CORS setup, and leaves room for auth/rate limiting later.

## CORS

The API enables CORS so a browser frontend can call it. Allowed origins come from
`CORS_ALLOW_ORIGINS` (comma-separated); when unset it defaults to the local Vite
dev server (`http://localhost:5173`, `http://127.0.0.1:5173`). In production, set
it to the deployed frontend origin, e.g.:

```
CORS_ALLOW_ORIGINS=https://shop.example.com
```

## Endpoints

- `GET /health` — liveness probe
- `GET /products` — full assortment (called on app load)
- `GET /products?category=<slug>` — assortment filtered to a category (404 if unknown)
- `GET /products/{product_id}` — single product (404 if unknown)
- `GET /categories` — category taxonomy, sorted by `sort_order`
- `POST /orders` — place an order (public; prices resolved server-side)
- `GET /admin/overview` — sales dashboard metrics (admins only)
- `GET /admin/orders` — recent orders, newest first (admins only)
- `POST /chat` — one message to the support agent (503 when not configured)

## Requirements

- Python 3.11+

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows (PowerShell: .venv\Scripts\Activate.ps1)
# source .venv/bin/activate   # macOS / Linux

pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then open:

- http://127.0.0.1:8000/health — health check
- http://127.0.0.1:8000/docs — interactive API docs (auto-generated by FastAPI)

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

API tests run against the in-memory repository; DynamoDB tests run against a
mocked AWS (moto), so no AWS account or network is needed.

## Deploy to AWS Lambda

The same app runs on Lambda via Mangum. Set the function handler to:

```
app.lambda_handler.handler
```

Put it behind API Gateway (HTTP API). Infrastructure (Lambda, API Gateway,
DynamoDB, S3/CloudFront, OIDC) is managed by Terraform in the
`tf-module-computer_shop` / `tf-stack-computer_shop` repos.

### Continuous deployment (CI)

`.github/workflows/deploy.yml` deploys the Lambda code on every push to `main`
(and via manual dispatch):

1. Builds a lean package from `requirements-lambda.txt` (no uvicorn; boto3 is
   pinned rather than runtime-provided, since the bundled SDK can predate the
   `bedrock-agentcore` service `/chat` needs) plus the `app/` package — the
   Linux runner produces Lambda-compatible wheels.
2. Authenticates via **GitHub OIDC** (no stored access keys), assuming the deploy
   role.
3. Runs `aws lambda update-function-code`.

Setup: add a repository **variable** `AWS_DEPLOY_ROLE_ARN` (Settings → Secrets and
variables → Actions → Variables) set to `terraform output github_deploy_role_arn`.
It's a variable, not a secret — the role's OIDC trust restricts who can assume it.
Terraform owns the function config and ignores code changes, so CI and Terraform
don't conflict.

### Why HTTP API instead of REST API

- **Cost** — HTTP API is ~70% cheaper per request than REST API, which matters
  for a read-heavy endpoint hit on every app load.
- **Lower latency** and simpler setup (built-in CORS and JWT auth).
- **No redundant features** — REST API's main extras are request validation and
  request/response mapping. FastAPI (Pydantic) already does both, so with a
  Mangum proxy integration those gateway features would only duplicate the app
  and add cost.
- **Not locked in** — Mangum auto-detects the event payload format, so the same
  handler works unchanged if we ever move to REST API.

Reach for REST API only if you need API keys + usage plans (per-client
throttling/quotas), gateway-level response caching, or edge-optimized endpoints.
For caching a rarely-changing assortment, CloudFront in front of HTTP API is
usually the better lever than switching to REST API.

## Related

Part of the Computer Shop project:

- [computer_shop_ui](https://github.com/MartinSG98/computer_shop_ui) — React/Vite/Mantine frontend
- [computer-shop-build-eval](https://github.com/MartinSG98/computer-shop-build-eval) — PC build scorer + suggestions (eval Lambda)
- [computer-shop-support-agent](https://github.com/MartinSG98/computer-shop-support-agent) — customer support agent (Bedrock AgentCore Runtime)
- [tf-module-computer_shop](https://github.com/MartinSG98/tf-module-computer_shop) — Terraform infrastructure module
- [tf-stack-computer_shop](https://github.com/MartinSG98/tf-stack-computer_shop) — Terraform deployment stack
