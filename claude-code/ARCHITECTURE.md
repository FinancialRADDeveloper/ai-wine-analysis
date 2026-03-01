# AI Wine Analysis Platform - System Architecture

## Project Codename: **Sommelier**

> A multi-service data platform using wine data as a proxy for hedge fund front-office systems design.
> Demonstrates: data ingestion from disparate sources, normalization pipelines, event-driven
> architecture, analytics dashboards, and LLM-powered recommendation/scoring.

---

## 1. Executive Summary

This project builds a production-grade data platform that ingests wine data from multiple
providers, normalizes it into a canonical format, stores it in a central database with full
audit trails, serves it through analytics dashboards, and applies LLM-powered scoring to
recommend wines based on personal preference history.

Every architectural decision maps directly to a hedge fund front-office pattern:

| Wine Domain | Finance Domain |
|---|---|
| Wine retailers (Wine Society, Berry Bros, Majestic) | Market data vendors (Bloomberg, Refinitiv, ICE) |
| Bottle of wine (canonical schema) | Security / instrument (security master) |
| Price across retailers | Bid/ask from different venues |
| Tasting notes | Research reports / analyst commentary |
| Wine preference scoring | Alpha signal / conviction score |
| Reconciliation across providers | Market data reconciliation |
| Correction/amendment workflow | Corporate actions / price corrections |
| Personal consumption history | Portfolio / trade history |

---

## 2. System Architecture Overview

```
                         SOMMELIER - HIGH LEVEL ARCHITECTURE
    ===================================================================

    DATA SOURCES                  INGESTION              PROCESSING
    ============                  =========              ==========

    +---------------+
    | Wine Society  |--+
    | (CSV/HTML)    |  |      +------------------+    +------------------+
    +---------------+  |      |                  |    |                  |
                       +----->|   S3 Landing     |--->|  Step Functions  |
    +---------------+  |      |   Zone           |    |  Pipeline        |
    | Berry Bros    |--+      |  (Raw Files)     |    |                  |
    | (JSON/API)    |  |      +------------------+    |  1. Parse        |
    +---------------+  |            |                  |  2. Validate     |
                       |            v                  |  3. Normalize    |
    +---------------+  |      +------------------+    |  4. Reconcile    |
    | Majestic      |--+      |  SQS Queue       |    |  5. Load         |
    | (HTML/CSV)    |         |  + DLQ            |    +------------------+
    +---------------+         +------------------+           |
                                                             v
    +---------------+                               +------------------+
    | X-Wines       |-----(bulk CSV load)---------->|  Aurora PG       |
    | (Kaggle 100K) |                               |  + pgvector      |
    +---------------+                               |                  |
                                                    |  - wines         |
    +---------------+                               |  - wine_prices   |
    | Vivino        |-----(API/scrape)              |  - providers     |
    | (ratings)     |                               |  - ratings       |
    +---------------+                               |  - embeddings    |
                                                    |  - audit_log     |
                                                    +------------------+
                                                       |          |
                                          +------------+          +----------+
                                          |                                  |
                                          v                                  v
                                 +------------------+            +------------------+
                                 |  FastAPI          |            |  Plotly Dash     |
                                 |  REST API         |            |  Dashboard       |
                                 |                   |            |                  |
                                 |  /v1/wines        |            |  - Price trends  |
                                 |  /v1/prices       |            |  - Recon breaks  |
                                 |  /v1/recommend    |            |  - Region maps   |
                                 |  /v1/score        |            |  - Consumption   |
                                 |  /v1/chat         |            |  - LLM scoring   |
                                 +------------------+            +------------------+
                                          |
                                          v
                                 +------------------+
                                 |  LLM Agent       |
                                 |  (Claude)        |
                                 |                  |
                                 |  Tools:          |
                                 |  - search_wines  |
                                 |  - semantic_search|
                                 |  - collab_filter |
                                 |  - score_wine    |
                                 |  - compare_prices|
                                 +------------------+
```

---

## 3. Data Sources Strategy

### 3.1 Primary Dataset: X-Wines (Kaggle)

The **X-Wines dataset** provides the foundation: 100,646 wines, 21M ratings, 62 countries,
10 years of data. This is our "historical market data" -- the large reliable dataset that
populates the canonical wine master and provides the collaborative filtering training data.

- **License**: Open / research-friendly
- **Format**: CSV
- **Fields**: wine name, country, region, type, grape varieties, ABV, ratings, vintage
- **Source**: https://github.com/rogerioxavier/X-Wines

### 3.2 Live Provider Data (The Three Retailers)

These simulate **live market data feeds** arriving from different vendors in different formats:

| Provider | Delivery Mechanism | Format | Update Frequency |
|---|---|---|---|
| Wine Society | Mock FTP drop -> S3 | CSV (scraped catalog) | Weekly |
| Berry Bros & Rudd | Mock REST API -> S3 | JSON | Daily |
| Majestic Wine | File system watcher -> S3 | HTML -> parsed CSV | Weekly |

**Important**: Rather than scraping live (fragile, possibly ToS-violating), we:
1. Manually curate sample datasets from each retailer (50-200 wines each)
2. Store them as provider-format files
3. Mock the delivery mechanisms (FTP drop = file copy to S3 path, API = scheduled Lambda)
4. The system processes them as if they arrived live

This mirrors reality: in finance, you never demo with a live Bloomberg feed either.

### 3.3 Supplementary Data

| Source | Purpose | Delivery |
|---|---|---|
| Wine-Searcher API (trial: 100 calls/day free) | Critic scores, price comparison | REST API |
| WineVybe API (via RapidAPI) | Additional ratings data | REST API |
| Vivino (Apify scraper or manual) | User ratings, tasting notes | Batch CSV |

---

## 4. Data Model: The Canonical "Bottle of Wine"

### 4.1 The Wine Master (= Security Master)

This is the hardest problem. In finance, the security master maps vendor-specific identifiers
to a canonical instrument. Here, we map each retailer's wine representation to a canonical form.

**The "ISIN" of wine**: `{producer}::{region}::{grape_primary}::{vintage}`
With a SHA-256 hash as the canonical ID.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        CANONICAL WINE SCHEMA                             │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  wine_id          UUID (PK)           # Canonical identifier             │
│  canonical_name   VARCHAR(500)        # Normalized name                  │
│  producer         VARCHAR(200)        # Winery / Chateau / Domain        │
│  region           VARCHAR(200)        # Bordeaux, Barossa, Napa          │
│  sub_region       VARCHAR(200)        # Appellation / sub-AVA            │
│  country          CHAR(2)            # ISO 3166-1 alpha-2               │
│  wine_type        ENUM               # Red, White, Rose, Sparkling,     │
│                                       # Fortified, Dessert              │
│  grape_varieties  JSONB              # [{"grape": "Cabernet Sauvignon", │
│                                       #   "percentage": 60}, ...]       │
│  vintage          INTEGER            # Year (NULL for NV)               │
│  abv              DECIMAL(4,2)       # Alcohol by volume                │
│  bottle_size_ml   INTEGER            # 750, 375, 1500, etc.            │
│  closure_type     VARCHAR(50)        # Cork, Screw cap, etc.           │
│  organic          BOOLEAN            # Organic/biodynamic              │
│                                                                          │
│  -- Metadata                                                             │
│  created_at       TIMESTAMPTZ        # When first seen                  │
│  updated_at       TIMESTAMPTZ        # Last modification                │
│  source_providers JSONB              # Which providers have this wine   │
│                                                                          │
│  -- Tasting Profile (normalized from multiple sources)                   │
│  tasting_notes    TEXT               # Consolidated tasting notes       │
│  flavor_profile   JSONB              # {"fruit": 8, "oak": 5,          │
│                                       #  "tannin": 7, "acidity": 6,    │
│                                       #  "body": 7, "sweetness": 2}    │
│                                                                          │
│  -- Vector embedding for semantic search                                 │
│  embedding        vector(1536)       # text-embedding-3-small           │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Wine Prices (= Market Data - Bi-Temporal)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                      WINE PRICES (BI-TEMPORAL)                           │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  id               BIGSERIAL (PK)                                         │
│  wine_id          UUID (FK -> wines)                                     │
│  provider_id      VARCHAR(50)        # "wine-society", "bbr", etc.      │
│                                                                          │
│  price            NUMERIC(12,2)                                          │
│  currency         CHAR(3)            # GBP, EUR, USD                    │
│  price_type       ENUM               # RETAIL, SALE, CASE, EN_PRIMEUR   │
│  case_size        INTEGER            # Usually 6 or 12                   │
│                                                                          │
│  -- Business time: when was this price valid?                            │
│  valid_from       DATE NOT NULL                                          │
│  valid_to         DATE DEFAULT '9999-12-31'                              │
│                                                                          │
│  -- System time: when did we learn about this price?                     │
│  known_from       TIMESTAMPTZ DEFAULT now()                              │
│  known_to         TIMESTAMPTZ DEFAULT '9999-12-31'                       │
│                                                                          │
│  -- Lineage                                                              │
│  ingestion_id     UUID NOT NULL                                          │
│  source_file      VARCHAR(500)       # S3 URI                           │
│  source_file_hash VARCHAR(64)        # SHA-256                          │
│  source_row       INTEGER                                                │
│  superseded_by    BIGINT (FK -> self)                                    │
│                                                                          │
│  EXCLUDE USING gist (                                                    │
│    wine_id WITH =,                                                       │
│    provider_id WITH =,                                                   │
│    tstzrange(known_from, known_to) WITH &&,                              │
│    daterange(valid_from, valid_to) WITH &&                               │
│  )                                                                       │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 4.3 Personal Consumption (= Trade / Position History)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                      CONSUMPTION HISTORY                                 │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  id               BIGSERIAL (PK)                                         │
│  wine_id          UUID (FK -> wines)  # What was consumed               │
│  consumed_date    DATE               # When                              │
│  quantity         INTEGER            # Bottles                           │
│  purchase_price   NUMERIC(12,2)      # What I paid                      │
│  purchase_source  VARCHAR(100)       # Where I bought it                │
│  occasion         VARCHAR(200)       # Dinner party, Tuesday night, etc │
│  personal_rating  DECIMAL(3,1)       # 1-10 scale                       │
│  personal_notes   TEXT               # Free-form tasting notes          │
│  would_buy_again  BOOLEAN                                                │
│  paired_with      JSONB              # Food pairings                    │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Service Architecture (Detailed)

### 5.1 Ingestion Pipeline

```
    INGESTION PIPELINE (Step Functions Orchestration)
    =================================================

    Provider Files Land in S3
              |
              v
    +-------------------+     +-------------------+
    | S3 Event          |---->| SQS Ingestion     |
    | Notification      |     | Queue             |
    +-------------------+     | + DLQ             |
                              +-------------------+
                                       |
                                       v
    +--------------------------------------------------------------+
    |                    STEP FUNCTIONS WORKFLOW                     |
    |                                                               |
    |  +------------------+    +------------------+                 |
    |  | 1. DETECT        |    | Identify provider |                |
    |  |    PROVIDER       |--->| from filename /   |                |
    |  |                  |    | S3 prefix / metadata|               |
    |  +------------------+    +------------------+                 |
    |           |                                                    |
    |           v                                                    |
    |  +------------------+    +------------------+                 |
    |  | 2. PARSE         |    | Provider-specific |                |
    |  |    (Adapter)      |--->| parsing logic     |                |
    |  |                  |    | CSV/JSON/HTML     |                |
    |  +------------------+    +------------------+                 |
    |           |                                                    |
    |           v                                                    |
    |  +------------------+    +------------------+                 |
    |  | 3. VALIDATE      |    | Pydantic models   |                |
    |  |    (Pydantic)     |--->| Valid -> continue  |                |
    |  |                  |    | Invalid -> quarantine|              |
    |  +------------------+    +------------------+                 |
    |           |                                                    |
    |           v                                                    |
    |  +------------------+    +------------------+                 |
    |  | 4. NORMALIZE     |    | Map to canonical   |                |
    |  |    (Adapter)      |--->| wine schema        |                |
    |  |                  |    | Entity resolution  |                |
    |  +------------------+    +------------------+                 |
    |           |                                                    |
    |           v                                                    |
    |  +------------------+    +------------------+                 |
    |  | 5. RECONCILE     |    | Cross-provider     |                |
    |  |                  |--->| price comparison   |                |
    |  |                  |    | Variance detection |                |
    |  +------------------+    +------------------+                 |
    |           |                                                    |
    |           v                                                    |
    |  +------------------+    +------------------+                 |
    |  | 6. LOAD          |    | Bi-temporal insert |                |
    |  |    (Aurora PG)    |--->| Refresh mat views  |                |
    |  |                  |    | Publish events     |                |
    |  +------------------+    +------------------+                 |
    |                                                               |
    +--------------------------------------------------------------+
              |
              v
    +-------------------+
    | EventBridge       |
    | "data-normalized" |
    | event published   |
    +-------------------+
```

### 5.2 Provider Adapter Pattern

```
    PROVIDER ADAPTER PATTERN (Strategy + Registry)
    ================================================

    +-------------------+
    |  ProviderAdapter   |  <-- Abstract base class
    |  (ABC)            |
    +-------------------+
    | + detect()        |  Can this adapter handle the file?
    | + parse()         |  Raw bytes -> ProviderRawRecords
    | + normalize()     |  ProviderRawRecord -> NormalizedWine
    +-------------------+
              ^
              |
    +---------+---------+---------+---------+
    |         |         |         |         |
    v         v         v         v         v
  +-------+ +-------+ +-------+ +-------+ +-------+
  |Wine   | |Berry  | |Majestic| |Vivino | |Wine  |
  |Society| |Bros   | |Adapter | |Adapter| |Searcher|
  |Adapter| |Adapter| |        | |       | |Adapter|
  +-------+ +-------+ +-------+ +-------+ +-------+
  | CSV    | | JSON  | | HTML   | | JSON  | | XML   |
  | format | | format| | parse  | | API   | | REST  |
  +-------+ +-------+ +-------+ +-------+ +-------+

    ADAPTER_REGISTRY = {
        "wine-society": WineSocietyAdapter,
        "bbr":          BerryBrosAdapter,
        "majestic":     MajesticAdapter,
        "vivino":       VivinoAdapter,
        "wine-searcher": WineSearcherAdapter,
    }

    # Adding a new provider = one new file, zero changes elsewhere
```

### 5.3 Event-Driven Communication

```
    EVENT FLOW ARCHITECTURE
    ========================

    +-------------+
    | Ingestion   |    publishes:
    | Service     |-----> "wine.data.received"
    |             |-----> "wine.data.normalized"
    |             |-----> "wine.data.validation_failed"
    +-------------+

    +-------------+
    | Reconcile   |    publishes:
    | Service     |-----> "wine.recon.completed"
    |             |-----> "wine.recon.break_detected"
    +-------------+

    +-------------+
    | Scoring     |    publishes:
    | Service     |-----> "wine.score.updated"
    +-------------+

            All events flow through:
            +-------------------+
            |   EventBridge     |
            |                   |
            |   Rules:          |
            |   - "wine.data.*" |----> SQS -> Normalization Lambda
            |   - "wine.recon.*"|----> SQS -> Dashboard refresh
            |   - "wine.score.*"|----> SQS -> Cache invalidation
            +-------------------+

    Event Schema (all events):
    {
        "source": "sommelier.ingestion",
        "detail-type": "wine.data.normalized",
        "detail": {
            "ingestion_id": "uuid",
            "provider": "bbr",
            "record_count": 150,
            "error_count": 3,
            "timestamp": "2024-01-15T10:30:00Z",
            "correlation_id": "uuid"
        }
    }
```

---

## 6. LLM Recommendation Engine

### 6.1 Hybrid Architecture (Three Signals)

```
    RECOMMENDATION ENGINE - HYBRID ENSEMBLE
    =========================================

    User Query: "Find me something like the 2019 Barolo I loved"
                              |
                              v
                    +-------------------+
                    |  LLM Orchestrator  |
                    |  (Claude Agent)    |
                    +-------------------+
                    |  Decides which     |
                    |  tools to call     |
                    +-------------------+
                       /      |      \
                      /       |       \
                     v        v        v
           +-----------+ +----------+ +----------------+
           | Signal 1  | | Signal 2 | | Signal 3       |
           | CONTENT   | | COLLAB   | | RAG            |
           | FILTER    | | FILTER   | | SEMANTIC SEARCH|
           +-----------+ +----------+ +----------------+
           | sklearn    | | surprise | | pgvector HNSW  |
           | cosine sim | | SVD      | | + BM25 hybrid  |
           | over wine  | | over     | | over tasting   |
           | attributes | | 21M user | | notes &        |
           | (factors)  | | ratings  | | descriptions   |
           +-----------+ +----------+ +----------------+
                  |            |              |
                  v            v              v
              score_1      score_2        score_3
                  \            |              /
                   \           |             /
                    v          v            v
                  +------------------------+
                  | ENSEMBLE SCORER        |
                  | final = w1*s1 +        |
                  |         w2*s2 +        |
                  |         w3*s3          |
                  | (weights from MLflow)  |
                  +------------------------+
                              |
                              v
                  +------------------------+
                  | LLM EXPLANATION        |
                  | Claude generates       |
                  | human-readable reason  |
                  | for the recommendation |
                  +------------------------+
                              |
                              v
                    "Based on your love of tannic,
                     complex reds from Piedmont,
                     I'd suggest this Brunello..."

    FINANCE MAPPING:
    ================
    Content Filter  = Factor model (attributes as risk factors)
    Collab Filter   = Peer analysis / relative value
    RAG             = NLP signal from research reports
    Ensemble        = Alpha combination / portfolio construction
    Value Ratio     = Sharpe ratio (quality / price)
    MLflow          = Backtesting framework
```

### 6.2 Agent Tool Architecture

```
    LLM AGENT TOOLS
    ================

    +----------------------------------------------+
    |              Claude Agent                      |
    |                                                |
    |  System Prompt:                                |
    |  "You are a wine sommelier with access to      |
    |   a database of 100K wines and the user's      |
    |   personal consumption history. Use your       |
    |   tools to find, score, and recommend wines."  |
    |                                                |
    +----------------------------------------------+
                         |
           +-------------+-------------+
           |             |             |
           v             v             v
    +-----------+  +-----------+  +-----------+
    | TOOL 1    |  | TOOL 2    |  | TOOL 3    |
    | search_   |  | semantic_ |  | get_      |
    | wines_by_ |  | search_   |  | similar_  |
    | attributes|  | tasting_  |  | users_    |
    |           |  | notes     |  | wines     |
    | SQL query |  | pgvector  |  | surprise  |
    | builder   |  | + BM25    |  | SVD       |
    +-----------+  +-----------+  +-----------+
           |             |             |
           v             v             v
    +-----------+  +-----------+
    | TOOL 4    |  | TOOL 5    |
    | score_    |  | compare_  |
    | wine      |  | prices    |
    |           |  |           |
    | Structured|  | Cross-    |
    | output    |  | provider  |
    | via       |  | price     |
    | Pydantic  |  | lookup    |
    +-----------+  +-----------+
```

---

## 7. Dashboard Architecture

```
    PLOTLY DASH DASHBOARD
    ======================

    +------------------------------------------------------------------+
    |  SOMMELIER DASHBOARD                                    [Login]   |
    +------------------------------------------------------------------+
    |                                                                    |
    |  +---SIDEBAR-----------+  +---MAIN PANEL-----------------------+ |
    |  |                     |  |                                     | |
    |  | Filters:            |  |  TAB: Price Analytics               | |
    |  | [x] Region          |  |  +-------------------------------+  | |
    |  | [x] Grape           |  |  | Price trends by region        |  | |
    |  | [x] Vintage Range   |  |  | (time series, multiple Y-axes)|  | |
    |  | [x] Price Range     |  |  +-------------------------------+  | |
    |  | [x] Provider        |  |  +-------------------------------+  | |
    |  |                     |  |  | Price distribution heatmap    |  | |
    |  | Quick Views:        |  |  | (region x vintage)           |  | |
    |  | > My Consumption    |  |  +-------------------------------+  | |
    |  | > Recon Breaks      |  |                                     | |
    |  | > Top Rated         |  |  TAB: Reconciliation                | |
    |  | > LLM Recommender   |  |  +-------------------------------+  | |
    |  | > Pipeline Status   |  |  | Provider price comparison    |  | |
    |  |                     |  |  | (scatter: provider A vs B)   |  | |
    |  +---------------------+  |  +-------------------------------+  | |
    |                           |  | Breaks table (variance > 5%) |  | |
    |                           |  | Drill-down to source records |  | |
    |                           |  +-------------------------------+  | |
    |                           |                                     | |
    |                           |  TAB: My Wine Journey               | |
    |                           |  +-------------------------------+  | |
    |                           |  | Consumption over time         |  | |
    |                           |  | Rating distribution           |  | |
    |                           |  | Spend by region / grape       |  | |
    |                           |  | Personal taste profile radar  |  | |
    |                           |  +-------------------------------+  | |
    |                           |                                     | |
    |                           |  TAB: LLM Sommelier                 | |
    |                           |  +-------------------------------+  | |
    |                           |  | Chat interface                |  | |
    |                           |  | "Find me a wine like..."     |  | |
    |                           |  | Structured score cards       |  | |
    |                           |  | Recommendation explanations  |  | |
    |                           |  +-------------------------------+  | |
    |                           |                                     | |
    |                           |  TAB: Pipeline Monitor              | |
    |                           |  +-------------------------------+  | |
    |                           |  | Ingestion status by provider  |  | |
    |                           |  | Records processed / failed    |  | |
    |                           |  | Data freshness gauges         |  | |
    |                           |  | Step Functions execution log  |  | |
    |                           |  +-------------------------------+  | |
    |                           +-------------------------------------+ |
    +------------------------------------------------------------------+
```

---

## 8. Technology Stack

### 8.1 Summary Table

| Layer | Technology | Rationale |
|---|---|---|
| **Language** | Python 3.12+ | Fund standard for quant/data work |
| **Dependency Mgmt** | uv (or Poetry) | Deterministic resolution, fast, workspace support |
| **API Framework** | FastAPI | Async, Pydantic-native, auto OpenAPI docs |
| **Dashboard** | Plotly Dash | Financial-grade charting, callback architecture |
| **Database** | PostgreSQL 16 + pgvector | Bi-temporal queries, JSONB, vector search, partitioning |
| **DB Access** | SQLAlchemy Core + Alembic | Query builder (not ORM), versioned migrations |
| **Data Validation** | Pydantic v2 | Rust-core performance, canonical data contracts |
| **Message Bus** | EventBridge + SQS | Content-based routing, DLQ, schema registry |
| **Orchestration** | Step Functions | Visual monitoring, built-in retry/audit trail |
| **Compute** | Lambda (events) + Fargate (services) | Serverless where possible, containers for long-running |
| **LLM** | Claude (Anthropic API) | Tool use, structured outputs, agentic patterns |
| **Embeddings** | text-embedding-3-small (OpenAI) | Cost-effective, sufficient quality for wine notes |
| **Vector Search** | pgvector (HNSW index) | Single DB, no extra infra, SQL-native |
| **Collab Filter** | surprise (SVD) | Proven, lightweight, good for demo scale |
| **Experiment Tracking** | MLflow | Industry standard, tracks weights/metrics/models |
| **IaC** | AWS CDK (Python) | Same language as app, high-level constructs |
| **Local Dev** | Docker Compose + LocalStack | One-command environment |
| **CI/CD** | GitHub Actions | PR checks, linting, tests, deployment |
| **Logging** | structlog (JSON) | Structured, correlation IDs, CloudWatch compatible |
| **Monitoring** | CloudWatch + Managed Grafana | Native AWS integration, no infra to manage |
| **Tracing** | AWS X-Ray | Distributed tracing across Lambda/ECS |

### 8.2 Why NOT These Alternatives

| Rejected | Reason |
|---|---|
| Django | Too heavy for microservices; ORM/admin are anti-patterns here |
| Flask | No async, no native Pydantic, requires many extensions |
| Streamlit | Prototype tool, not production dashboard; limited layout control |
| React | Requires dedicated frontend skills; Dash keeps everything Python |
| DynamoDB | Analytics workload needs joins/aggregations; key-value is wrong model |
| Kafka (MSK) | Massive operational overhead for tens of thousands of records/day |
| Kubernetes (EKS) | Overkill without a platform team; Fargate removes cluster mgmt |
| LangChain | Framework overhead; clean Python with Claude tools is more impressive |
| Pinecone | Vendor dependency; pgvector is free and lives in your existing DB |
| Terraform | HCL requires context-switching; CDK uses same Python as the app |
| Celery | Requires broker + workers + Flower; Step Functions is serverless |
| SageMaker | We call LLM APIs, not self-hosting models |

---

## 9. Repository Structure

```
ai-wine-analysis/
|
+-- README.md                          # Project overview + finance mapping
+-- ARCHITECTURE.md                    # This document
+-- Makefile                           # Developer experience (make up, make test, etc.)
+-- docker-compose.yml                 # Full local stack
+-- pyproject.toml                     # Root workspace (uv)
+-- .github/
|   +-- workflows/
|       +-- ci.yml                     # Lint, type-check, test on PR
|       +-- deploy.yml                 # CDK deploy on merge to main
|
+-- infrastructure/                    # AWS CDK stacks (Python)
|   +-- app.py
|   +-- stacks/
|       +-- networking.py              # VPC, subnets, security groups
|       +-- database.py                # Aurora Serverless v2
|       +-- ingestion.py               # S3, SQS, Step Functions, Lambdas
|       +-- api.py                     # ECS Fargate, ALB
|       +-- monitoring.py              # CloudWatch alarms, dashboards
|
+-- services/
|   +-- shared/                        # Shared libraries (Pydantic models, DB utils)
|   |   +-- models/
|   |   |   +-- wine.py                # Canonical wine schema
|   |   |   +-- price.py               # Bi-temporal price model
|   |   |   +-- provider.py            # Provider raw record types
|   |   |   +-- events.py              # EventBridge event schemas
|   |   |   +-- lineage.py             # Data lineage model
|   |   +-- db/
|   |   |   +-- connection.py          # SQLAlchemy engine/session
|   |   |   +-- tables.py              # SQLAlchemy Core table definitions
|   |   +-- config.py                  # Environment-aware configuration
|   |
|   +-- ingestion/                     # Ingestion pipeline service
|   |   +-- Dockerfile
|   |   +-- adapters/
|   |   |   +-- base.py                # ProviderAdapter ABC
|   |   |   +-- registry.py            # Adapter registry
|   |   |   +-- wine_society.py        # Wine Society parser/normalizer
|   |   |   +-- berry_bros.py          # BBR parser/normalizer
|   |   |   +-- majestic.py            # Majestic parser/normalizer
|   |   |   +-- vivino.py              # Vivino parser/normalizer
|   |   |   +-- wine_searcher.py       # Wine-Searcher parser/normalizer
|   |   +-- pipeline/
|   |   |   +-- parse.py               # Stage 1: Parse
|   |   |   +-- validate.py            # Stage 2: Validate
|   |   |   +-- normalize.py           # Stage 3: Normalize
|   |   |   +-- reconcile.py           # Stage 4: Reconcile
|   |   |   +-- load.py                # Stage 5: Load to DB
|   |   +-- handlers/
|   |       +-- s3_event.py            # Lambda: S3 -> SQS trigger
|   |       +-- step_function.py       # Step Functions state handlers
|   |
|   +-- api/                           # FastAPI REST API
|   |   +-- Dockerfile
|   |   +-- main.py                    # FastAPI app creation
|   |   +-- routers/
|   |   |   +-- wines.py               # /v1/wines CRUD + search
|   |   |   +-- prices.py              # /v1/prices (bi-temporal queries)
|   |   |   +-- recommendations.py     # /v1/recommend
|   |   |   +-- scoring.py             # /v1/score
|   |   |   +-- chat.py                # /v1/chat (LLM agent endpoint)
|   |   |   +-- consumption.py         # /v1/consumption (personal history)
|   |   |   +-- health.py              # /health, /ready
|   |   +-- middleware/
|   |       +-- logging.py             # Request/response logging
|   |       +-- correlation.py         # Correlation ID propagation
|   |
|   +-- dashboard/                     # Plotly Dash analytics UI
|   |   +-- Dockerfile
|   |   +-- app.py                     # Dash app creation
|   |   +-- layouts/
|   |   |   +-- sidebar.py             # Filter sidebar
|   |   |   +-- price_analytics.py     # Price trends tab
|   |   |   +-- reconciliation.py      # Recon breaks tab
|   |   |   +-- consumption.py         # Personal wine journey tab
|   |   |   +-- llm_sommelier.py       # Chat + scoring tab
|   |   |   +-- pipeline_monitor.py    # Ingestion status tab
|   |   +-- callbacks/
|   |       +-- filters.py             # Sidebar filter callbacks
|   |       +-- charts.py              # Chart update callbacks
|   |
|   +-- recommendation/                # LLM + ML recommendation engine
|   |   +-- Dockerfile
|   |   +-- agent/
|   |   |   +-- orchestrator.py        # Claude agent loop
|   |   |   +-- tools.py               # Tool definitions
|   |   |   +-- tool_handlers.py       # Tool execution logic
|   |   +-- engines/
|   |   |   +-- content_filter.py      # scikit-learn cosine similarity
|   |   |   +-- collab_filter.py       # surprise SVD
|   |   |   +-- semantic_search.py     # pgvector + BM25 hybrid
|   |   |   +-- ensemble.py            # Weighted combination
|   |   +-- embeddings/
|   |   |   +-- generator.py           # Batch embedding generation
|   |   |   +-- store.py               # pgvector read/write
|   |   +-- scoring/
|   |       +-- wine_scorer.py         # Structured output scoring
|   |       +-- value_ratio.py         # Quality / price (= Sharpe)
|   |
|   +-- scoring-batch/                 # Batch scoring pipeline
|       +-- run.py                     # Nightly batch scorer
|       +-- features.py                # Feature computation
|
+-- migrations/                        # Alembic database migrations
|   +-- alembic.ini
|   +-- versions/
|       +-- 001_initial_schema.py
|       +-- 002_add_bi_temporal.py
|       +-- 003_add_pgvector.py
|
+-- data/                              # Sample data for development
|   +-- providers/
|   |   +-- wine-society/
|   |   |   +-- sample_catalog.csv
|   |   +-- bbr/
|   |   |   +-- sample_wines.json
|   |   +-- majestic/
|   |       +-- sample_listing.html
|   +-- x-wines/
|       +-- README.md                  # Instructions to download X-Wines
|
+-- tests/
|   +-- unit/
|   |   +-- test_adapters/
|   |   +-- test_models/
|   |   +-- test_pipeline/
|   |   +-- test_recommendation/
|   +-- integration/
|   |   +-- test_ingestion_e2e.py
|   |   +-- test_api_endpoints.py
|   |   +-- test_recommendation_flow.py
|   +-- contract/
|       +-- test_event_schemas.py      # EventBridge contract tests
|       +-- test_api_contracts.py      # OpenAPI spec validation
|
+-- docs/
    +-- finance-mapping.md             # Detailed wine-to-finance analogy
    +-- data-model.md                  # Schema documentation
    +-- runbooks/                      # Operational runbooks
        +-- ingestion-failure.md
        +-- recon-break.md
```

---

## 10. Key Financial Patterns Implemented

### 10.1 Bi-Temporal Data (Point-in-Time Queries)

The most important pattern. Enables:
- **Business time**: "What was the price of Chateau Margaux 2015 on March 15?"
- **System time**: "What did our system believe the price was at 3pm on March 16?"

### 10.2 Idempotent Processing

Every pipeline stage is idempotent. Reprocessing the same file produces the same result
without duplicates. Critical for SQS at-least-once delivery.

### 10.3 Data Lineage

Every record carries its provenance: source file (S3 URI), file hash (SHA-256), row number,
ingestion ID, pipeline version (git SHA), adapter version.

### 10.4 Reconciliation

Cross-provider matching detects when retailers disagree on price. Flags breaks > 5% variance.
Golden record selection via priority waterfall.

### 10.5 Event Sourcing (for corrections)

Price corrections stored as immutable events. Current state derived from event replay.
Full history preserved for audit.

### 10.6 Four-Eyes Principle

Manual overrides require maker-checker workflow (requested_by != approved_by).

### 10.7 Circuit Breaker

External provider calls wrapped in circuit breakers to prevent cascade failures.

### 10.8 Structured Observability

JSON logging with correlation IDs. Every request traceable end-to-end.
SLIs/SLOs defined for ingestion latency, data freshness, recon break rate.

---

## 11. Implementation Phases

### Phase 1: Foundation (Week 1-2)
- [ ] Repository setup (uv workspace, Docker Compose, CI)
- [ ] PostgreSQL + pgvector schema + Alembic migrations
- [ ] Shared Pydantic models (canonical wine, bi-temporal price, lineage)
- [ ] Ingest X-Wines dataset (100K wines bulk load)
- [ ] Basic FastAPI with /v1/wines and /v1/prices endpoints

### Phase 2: Ingestion Pipeline (Week 3-4)
- [ ] Provider adapter framework (ABC + registry)
- [ ] Wine Society adapter (CSV)
- [ ] Berry Bros adapter (JSON)
- [ ] Majestic adapter (HTML parse)
- [ ] Validation + quarantine logic
- [ ] Normalization + entity resolution
- [ ] Step Functions workflow (local with LocalStack)
- [ ] S3 -> SQS -> Lambda trigger chain

### Phase 3: Analytics & Dashboard (Week 5-6)
- [ ] Bi-temporal query API (as-of-date, as-at)
- [ ] Reconciliation service + breaks detection
- [ ] Plotly Dash: Price Analytics tab
- [ ] Plotly Dash: Reconciliation Breaks tab
- [ ] Plotly Dash: Personal Consumption tab
- [ ] Pipeline Monitor tab

### Phase 4: LLM Recommendation Engine (Week 7-8)
- [ ] Embedding generation (tasting notes -> pgvector)
- [ ] Content-based filtering (scikit-learn)
- [ ] Collaborative filtering (surprise SVD)
- [ ] RAG semantic search (pgvector + BM25 hybrid)
- [ ] Ensemble scorer with MLflow tracking
- [ ] Claude agent with 5 tools
- [ ] Structured output wine scoring
- [ ] Chat endpoint + Dash integration

### Phase 5: Production Polish (Week 9-10)
- [ ] AWS CDK infrastructure stacks
- [ ] Structured logging + correlation IDs
- [ ] CloudWatch alarms + SLOs
- [ ] Runbooks for key failure modes
- [ ] Contract tests (events + API)
- [ ] System design document with finance mapping
- [ ] Demo walkthrough script

---

## 12. Cost Estimate (Development)

| Service | Monthly Cost |
|---|---|
| PostgreSQL (local Docker) | $0 |
| LocalStack (free tier) | $0 |
| Claude API (development) | ~$10-20 |
| OpenAI embeddings (100K wines, one-time) | ~$0.50 |
| MLflow (local) | $0 |
| GitHub (free tier) | $0 |
| **Total development cost** | **~$10-20/month** |

---

## 13. Sources & References

### Wine Data
- [X-Wines Dataset](https://github.com/rogerioxavier/X-Wines) - 100K wines, 21M ratings
- [Kaggle Wine Reviews](https://www.kaggle.com/datasets/zynicide/wine-reviews) - 130K reviews
- [Wine-Searcher API](https://www.wine-searcher.com/trade/api) - 100 free calls/day trial
- [WineVybe API](https://winevybe.com/apis/) - via RapidAPI
- [UCI Wine Dataset](http://archive.ics.uci.edu/dataset/109/wine) - CC BY 4.0

### Architecture
- [Event-Driven Microservices with Kafka and Python](https://www.toptal.com/microservices/event-driven-microservices-kafka-python)
- [FastAPI for Microservices: Design Patterns](https://talent500.com/blog/fastapi-microservices-python-api-design-patterns-2025/)
- [Microservices Architecture with Python](https://techifysolutions.com/blog/microservices-based-architecture-with-python-deep-dive/)

### LLM / ML
- [Anthropic: Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)
- [Claude Structured Outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)
- [MLflow](https://mlflow.org/)
- [Improving Recommendation Systems with LLMs](https://eugeneyan.com/writing/recsys-llm/)
