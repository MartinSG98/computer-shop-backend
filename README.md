# Computer Shop backend

![CI](https://github.com/MartinSG98/computer-shop-backend/actions/workflows/ci.yml/badge.svg)

FastAPI backend for Computer Shop, a web shop for PC parts. You browse 127 parts in 12 categories, from processors and graphics cards to monitors and mice. You can put a PC together in the configurator, check out, and ask a support agent about the stock in a chat window. Shop admins sign in to a sales dashboard with revenue, orders, best sellers and sales by category.

This repo holds the API: the catalog, checkout, the admin sales metrics and the chat route. It runs on AWS Lambda behind an API Gateway HTTP API, with DynamoDB for data and S3 plus CloudFront for product images, and it also runs locally with no AWS setup at all. The browser client is [computer_shop_ui](https://github.com/MartinSG98/computer_shop_ui). The chat route forwards to [computer-shop-support-agent](https://github.com/MartinSG98/computer-shop-support-agent), and the configurator's build score comes from [computer-shop-build-eval](https://github.com/MartinSG98/computer-shop-build-eval), a separate Lambda on the same HTTP API. The infrastructure is the Terraform module [tf-module-computer_shop](https://github.com/MartinSG98/tf-module-computer_shop), applied through [tf-stack-computer_shop](https://github.com/MartinSG98/tf-stack-computer_shop).

Architecture decisions are recorded in [docs/adr](docs/adr/README.md), one numbered file per decision. Cross-cutting ones, such as the cost posture and admin authentication, live in the Terraform module.

## How it works

1. **The gateway.** An API Gateway HTTP API sends every request to one Lambda through a `$default` route, and FastAPI does all the routing. Requests under `/admin/` pass a Cognito JWT authorizer first. `POST /evaluate` on the same API goes to the build evaluator's own Lambda, so this app never sees it.
2. **The app.** `app/lambda_handler.py` wraps the FastAPI app with Mangum, which turns API Gateway events into ASGI requests. The same app runs under uvicorn on your machine.
3. **The data.** Products, categories and orders each sit behind a small repository interface with two implementations, one in memory and one on DynamoDB. A cached factory picks DynamoDB when the table's environment variable is set and falls back to the seed data in `app/seed_data.py` when it is not ([ADR 0002](docs/adr/0002-repository-pattern-in-memory-fallback.md)).
4. **The catalog.** Every product has a price, stock, a description and display specs. Products in the eight buildable categories also carry typed compatibility attributes (socket, TDP, form factor, memory type and slots, GPU length, cooler height, radiator size, wattage and so on), which the configurator in the UI checks builds against. Processors, graphics cards and motherboards have a tier from 1 (entry) to 4 (flagship) that the configurator, the build evaluator and the support agent use to compare parts. Monitors, keyboards, mice and headsets have no attributes.
5. **Images.** Product images live in S3 and are served by CloudFront. DynamoDB stores only the object key, and the API returns a full `image_url` built from `CDN_BASE_URL`.
6. **Checkout and the dashboard.** `POST /orders` prices the cart from the catalog and stores the order. The admin routes aggregate the orders table into dashboard metrics.
7. **Chat.** `POST /chat` passes one customer message to the support agent on Bedrock AgentCore Runtime and returns its reply.

## Running locally

Requires Python 3.11 or newer.

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API starts on http://127.0.0.1:8000. Check it is alive at http://127.0.0.1:8000/health and browse the interactive API reference at http://127.0.0.1:8000/docs. With no table variables set it serves the seed catalog from memory and keeps orders in memory until the process stops, so there are no AWS calls and no keys to set up. Every `image_url` stays `null` until `CDN_BASE_URL` is set, and `POST /chat` answers 503 until `AGENT_RUNTIME_ARN` points at a runtime. The default CORS origins let the UI's Vite dev server on port 5173 call the API.

## Configuration

Everything is read from environment variables and nothing is required. There is no `.env` file support. On Lambda the Terraform module sets the three table names, `CDN_BASE_URL`, `CORS_ALLOW_ORIGINS` and `AGENT_RUNTIME_ARN`.

| Variable | Default | Purpose |
|---|---|---|
| `PRODUCTS_TABLE` | unset | DynamoDB table for products. Unset serves the in-memory seed catalog |
| `CATEGORIES_TABLE` | unset | DynamoDB table for categories, with the same fallback |
| `ORDERS_TABLE` | unset | DynamoDB table for orders. Unset keeps orders in memory for the life of the process |
| `AWS_REGION` | unset | Region for the DynamoDB and AgentCore clients. Lambda sets it automatically |
| `DYNAMODB_ENDPOINT_URL` | unset | Endpoint override, for example DynamoDB Local |
| `CDN_BASE_URL` | unset | CloudFront base URL that image keys are appended to. Unset makes every `image_url` `null` |
| `CORS_ALLOW_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated browser origins allowed to call the API |
| `AGENT_RUNTIME_ARN` | unset | AgentCore runtime that `POST /chat` invokes. Unset makes the route answer 503 |

Each table variable works on its own, so you can read the catalog from DynamoDB and still keep orders in memory.

## API

| Method | Path | What it does |
|---|---|---|
| GET | `/health` | Liveness check, `{"status": "ok"}` |
| GET | `/categories` | The category taxonomy, sorted by `sort_order` |
| GET | `/products` | The whole catalog, `?category=<slug>` for one category |
| GET | `/products/{product_id}` | One product |
| POST | `/orders` | Place an order from product ids and quantities, priced on the server |
| GET | `/admin/overview` | Dashboard metrics: KPIs, sales per day, top products, sales by category. Admins only |
| GET | `/admin/orders` | Every order, most recent first. Admins only |
| POST | `/chat` | One customer message to the support agent, returns its reply |

An unknown product id answers 404, and so does an unknown category slug, so a typo or a stale link is easy to tell from a real category with no products (which returns `[]`). Filtering by category happens in the app over a scan. Once the catalog is large, the next step is a DynamoDB index on `category`. Prices and totals are decimals and come back as JSON strings such as `"999.00"`, so money never goes through a float. Request bodies that fail validation answer 422.

## Checkout

`POST /orders` takes product ids and quantities only and returns the stored order:

```json
{"username": "user-normal", "items": [{"product_id": "gpu-gigabyte-rtx-5080", "quantity": 1}]}
→ {"id": "ord_...", "username": "user-normal", "created_at": "...", "currency": "USD", "total": "999.00", "items": [...]}
```

- **Prices** come from the catalog. The server looks up every product and sets the name, category and unit price itself, so the caller can never choose what it pays.
- **Line items** snapshot the name, category and unit price at the time of purchase, so old orders and the dashboard stay correct when the catalog is later re-priced or re-categorised.
- **Limits.** A cart needs 1 to 50 lines and quantities from 1 to 100. Anything else answers 422, and an unknown product id answers 404.
- **The username** is a label the UI sends from its signed-in session. Checkout is a public route and the server does not verify it, so it is never used for anything that needs trust.

Order ids are `ord_` followed by 12 hex characters. Orders go to DynamoDB when `ORDERS_TABLE` is set and to the in-memory store otherwise.

## Admin dashboard

The `/admin/*` routes are protected in two steps.

1. **Authentication at the edge.** API Gateway runs a Cognito JWT authorizer on `/admin/*` only, so an anonymous caller never reaches the Lambda while the catalog stays public. The bearer has to be the Cognito ID token, because that one carries both the `aud` claim the authorizer checks and the `cognito:groups` claim the app reads. A separate `OPTIONS /admin/{proxy+}` route skips the authorizer so that browser preflights, which carry no token, still work.
2. **Authorization in the app.** A valid token only proves who the caller is. `require_admin` in `app/auth.py` reads `cognito:groups` from the authorizer's claims and answers 403 unless the caller is in the `admins` group. The HTTP API passes that claim as a string like `[admins manager]`, and the parser handles both that and a real list. With no API Gateway event, locally and in the tests, there are no claims to check and the guard lets every request through.

`GET /admin/overview` computes everything from one scan of the orders table, with no secondary index, to stay inside the free tier:

- `summary`: order count, revenue, average order value (rounded half up to the cent) and units sold
- `sales_over_time`: revenue and order count per day, oldest first
- `top_products`: the ten best sellers by units, with revenue breaking ties
- `sales_by_category`: units and revenue per category, highest revenue first

The aggregation lives in `app/metrics.py` as plain functions over a list of orders, so it is tested without DynamoDB or HTTP.

## Support agent chat

`POST /chat` passes one customer message to the support agent and returns its reply:

```json
{"message": "Whats your cheapest GPU?", "session_id": "<33 to 100 characters>"}
→ {"reply": "The cheapest GPU we have is ..."}
```

- **The session id** comes from the UI, one UUID per chat window, and the backend passes it through unchanged. AgentCore routes the same id to the same warm session, which is how follow-up questions keep their context, and the backend stays stateless. AgentCore needs at least 33 characters, so a shorter id fails validation with a 422 instead of failing deep inside the call.
- **The message cap** of 500 characters bounds the Bedrock token spend per request.
- **Not configured.** With `AGENT_RUNTIME_ARN` unset the route answers `503 Chat is not configured`.
- **Upstream failures** of any kind answer `502 Support agent unavailable`. The real error only goes to the logs, because AWS error texts can contain ARNs.

The UI never calls the agent directly. Going through the API keeps the runtime private, reuses the API's CORS setup and leaves room for rate limiting later. `app/agent_client.py` is the only place that knows the agent's contract, `{"prompt": "..."}` in and `{"reply": "..."}` out.

## Product images

DynamoDB stores only an S3 object key per product (`image_key`). The API never returns the key. It returns `image_url`, which is `CDN_BASE_URL` plus the key, or `null` when either is missing. Storing the key and not the URL means the CDN domain can change without rewriting any records.

Processors share one image per platform: `cpus/amd.jpg`, `cpus/intel.jpg`, `cpus/amd-am4.jpg` and `cpus/intel-lga1700.jpg`. Every other product has its own image named after its id, for example `coolers/cooler-noctua-nh-d15-g2.jpg`. Categories can have an image key too, but the seed sets none.

To upload images, put them under `seed_images/` in the same folder layout as the keys and sync the folder to the images bucket:

```bash
aws s3 sync seed_images/ s3://<images-bucket>/   # name from: terraform output images_bucket_name
```

`seed_images/` is git-ignored, because the images live in S3 and not in the repo. Use JPG files. The AWS CLI sets the `Content-Type` from the extension, so CloudFront serves them inline. New keys show up straight away, but overwriting an existing key needs a CloudFront invalidation:

```bash
aws cloudfront create-invalidation --distribution-id <id> --paths "/<prefix>/*"
```

## Seeding DynamoDB

`scripts/seed_dynamodb.py` loads `app/seed_data.py` into real tables:

```bash
export AWS_REGION=eu-west-2
export PRODUCTS_TABLE=computer-shop-products       # terraform output products_table_name
export CATEGORIES_TABLE=computer-shop-categories   # terraform output categories_table_name
python -m scripts.seed_dynamodb
```

`PRODUCTS_TABLE` is required and `CATEGORIES_TABLE` is optional. The script also honours `DYNAMODB_ENDPOINT_URL` for DynamoDB Local. A table that does not exist yet is created with `id` (products) or `slug` (categories) as a string partition key and 5 read and 5 write capacity units, which keeps it inside the DynamoDB always-free tier of 25 of each per account. Unset attributes are not written, so peripherals have no `attributes` map at all.

Re-running the script is safe. It overwrites every seed row and deletes rows whose key is no longer in the seed, so the tables always match `app/seed_data.py`. Orders are never seeded.

## Why HTTP API instead of REST API

- **Cost.** An HTTP API is about 70 percent cheaper per request than a REST API, which matters for a read-heavy catalog that loads on every visit.
- **Latency and setup.** It is faster and simpler, with built-in CORS and JWT authorizers.
- **No duplicated features.** A REST API's main extras are request validation and request and response mapping. FastAPI and Pydantic already do both, so behind a Mangum proxy those gateway features would only repeat the app and add cost.
- **No lock-in.** Mangum detects the event format, so the same handler would work unchanged behind a REST API.

A REST API would only be worth it for API keys with usage plans (per-client throttling and quotas), gateway-level response caching or edge-optimized endpoints. For caching a catalog that rarely changes, CloudFront in front of the HTTP API is the better lever. See [ADR 0001](docs/adr/0001-http-api-over-rest-api.md).

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

The API tests run against the in-memory repositories and the DynamoDB tests run against AWS mocked with moto, so you need no AWS account and no network. They cover:

- health, the product list and single products, prices serialized as strings, and `image_url` with and without a CDN
- categories in order, no raw image keys in responses, filtering by category, and that every seed product's category exists
- checkout: totals priced on the server, an optional username, unknown products, empty carts and zero quantities
- the admin guard (group parsing, no gateway event, admins and non-admins), the dashboard metrics and both admin endpoints
- chat with the agent call stubbed out: forwarding, 503 when not configured, 502 on failure, 422 for short session ids and long messages
- CORS for an allowed and an unlisted origin
- the three DynamoDB repositories, including an order round trip with decimal money

## Deployment

Two GitHub Actions workflows run on `main`.

- **CI** (`.github/workflows/ci.yml`) runs on every push to `main` and every pull request. It installs `requirements-dev.txt` on Python 3.11 and runs `pytest -q`. DynamoDB is mocked, so it needs no AWS credentials.
- **Deploy** (`.github/workflows/deploy.yml`) runs on pushes to `main`, except ones that only touch Markdown files, `docs/` or `.github/`, and can also be started by hand.

The deploy goes in three steps:

1. **Build.** The workflow installs `requirements-lambda.txt` into a package folder, copies `app/` next to it and zips it. That file leaves out uvicorn to keep the package small, and it pins boto3 1.43.26 instead of relying on the copy bundled with the Lambda runtime, which can be older than the `bedrock-agentcore` client the chat route needs. The runner is Linux x86_64, so the wheels it installs run on Lambda.
2. **Authenticate.** It assumes the deploy role through GitHub OIDC, so no AWS keys are stored anywhere. The role ARN comes from the repository variable `AWS_DEPLOY_ROLE_ARN`, set to `terraform output github_deploy_role_arn`. It is a variable and not a secret because the role's trust policy decides who can assume it.
3. **Deploy.** `aws lambda update-function-code` uploads the zip to the `computer-shop-api` function in eu-west-2.

Deploys share a concurrency group, so a second push waits for the first instead of cancelling it. Terraform owns the function's configuration (Python 3.11, handler `app.lambda_handler.handler`, the environment variables) and ignores code changes, so CI and Terraform never fight over the function.

## Structure

```
app/
├── main.py              FastAPI app, CORS and every route
├── config.py            settings from environment variables
├── models.py            products with compatibility attributes, categories, orders, dashboard and chat shapes
├── repository.py        repository interfaces with in-memory and DynamoDB implementations
├── seed_data.py         the catalog: 12 categories and 127 products
├── metrics.py           sales aggregation for the admin dashboard
├── auth.py              require_admin, the admins group check
├── agent_client.py      the AgentCore call behind /chat
└── lambda_handler.py    Mangum handler for Lambda
scripts/
└── seed_dynamodb.py     create the tables if missing, load the seed, prune stale rows
tests/                   API, checkout, admin, chat, CORS and moto-backed DynamoDB tests
docs/adr/                architecture decision records
.github/workflows/       ci.yml (tests) and deploy.yml (Lambda code deploy)
requirements.txt         runtime packages plus uvicorn for local runs
requirements-dev.txt     adds pytest, httpx and moto
requirements-lambda.txt  the lean Lambda package
```
