# Sommelier - AI Wine Analysis Platform

A multi-service data platform that ingests wine data from UK retailers, normalises it into a canonical format, and serves it through analytics dashboards. Built to demonstrate hedge fund front-office architecture patterns (security master, bi-temporal pricing, data lineage, reconciliation) using wine as the domain.

## What does it do?

- **Scrapes wine data** from The Wine Society (CSV import + web scraper), with Berry Bros & Rudd and Majestic Wine planned
- **Normalises everything** into a single canonical schema, so a bottle of wine has one identity regardless of which retailer sells it
- **Tracks prices bi-temporally** -- we know both when a price was valid in the real world and when our system learned about it
- **Visualises your purchase history** through an interactive Plotly Dash dashboard
- **Stores data** in PostgreSQL with pgvector for future AI-powered recommendations

## Prerequisites

You need these installed on your machine before starting:

| Tool | Version | Check with | Install |
|------|---------|------------|---------|
| **Python** | 3.11+ | `python --version` | [python.org](https://www.python.org/downloads/) |
| **Docker Desktop** | Any recent | `docker --version` | [docker.com](https://www.docker.com/products/docker-desktop/) |
| **Git** | Any recent | `git --version` | [git-scm.com](https://git-scm.com/downloads) |
| **Make** (optional) | Any | `make --version` | Comes with Xcode (Mac), `sudo apt install make` (Linux), or `winget install GnuWin32.Make` (Windows) |

> **Windows users**: If you don't have `make`, you can run the commands from the Makefile directly. Each section below shows both the `make` shortcut and the raw command.

## Quick start

### 1. Clone the repo

```bash
git clone https://github.com/FinancialRADDeveloper/ai-wine-analysis.git
cd ai-wine-analysis/claude-code
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it:

```bash
# Mac / Linux
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Windows (Git Bash)
source .venv/Scripts/activate
```

You should see `(.venv)` at the start of your terminal prompt.

### 3. Install dependencies

```bash
# With make:
make dev

# Without make:
pip install -e ".[dev,collab]"
```

This installs everything: the application, dev tools (pytest, black, mypy), and collaborative filtering dependencies.

> **Troubleshooting**: If `psycopg2-binary` fails to install on Windows, try `pip install psycopg2-binary` separately first. On Mac, you may need `brew install postgresql` for the pg_config header.

### 4. Set up environment variables

```bash
cp .env.example .env
```

Open `.env` in your editor and fill in your values. The database defaults already match the Docker Compose config, so for local dev you only need to add API keys if you want LLM features:

```
ANTHROPIC_API_KEY=sk-ant-...   # Optional: for wine recommendations
OPENAI_API_KEY=sk-...          # Optional: for embeddings
WINE_SOCIETY_EMAIL=...         # Optional: for order scraping
WINE_SOCIETY_PASSWORD=...      # Optional: for order scraping
```

### 5. Start the database

```bash
# With make:
make docker-up

# Without make:
docker compose up -d
```

This starts three services:

| Service | Port | What it does |
|---------|------|--------------|
| **PostgreSQL 16** (+ pgvector) | 5432 | Main database |
| **LocalStack** | 4566 | Mock AWS (S3, SQS, EventBridge) |
| **MLflow** | 5000 | ML experiment tracking |

Check they're running:

```bash
docker compose ps
```

You should see all three containers with status `Up` or `healthy`.

### 6. Run database migrations

```bash
# With make:
make db-migrate

# Without make:
alembic upgrade head
```

This creates four tables: `wines`, `wine_prices`, `consumption_history`, and `audit_log`.

### 7. Run the tests

```bash
# With make:
make test

# Without make:
pytest tests/ -v --tb=short
```

All tests should pass. If they do, your environment is set up correctly.

## What can I do now?

### View the dashboard

If you have a Wine Society CSV export, place it in:

```
data/wine_society/raw/
```

Then run:

```bash
# With make:
make dashboard

# Without make:
python -m services.dashboard.app
```

Open http://127.0.0.1:8050 in your browser. You'll see an interactive dashboard with your purchase history: spending timeline, wine type breakdown, price distribution, regional analysis, and more.

### Import Wine Society CSV data

```bash
# With make:
make import-csv

# Without make:
python -m scrapers.wine_society.csv_importer
```

### Run the linter and formatter

```bash
# Check formatting (won't change files):
black --check scrapers/ services/ tests/

# Fix formatting:
make format

# Run the linter:
make lint
```

## Project structure

```
claude-code/
├── scrapers/                    # Data acquisition layer
│   ├── common/
│   │   └── base_scraper.py      # Base class: rate limiting, robots.txt, retry
│   ├── wine_society/
│   │   ├── csv_importer.py      # Parse Wine Society CSV exports
│   │   └── order_scraper.py     # Selenium scraper for order history
│   ├── berry_bros/              # (planned)
│   └── majestic/                # (planned)
│
├── services/
│   ├── shared/
│   │   ├── models/
│   │   │   ├── wine.py          # Canonical Wine schema
│   │   │   ├── price.py         # Bi-temporal WinePrice
│   │   │   ├── provider.py      # Raw records per retailer
│   │   │   └── lineage.py       # Data provenance tracking
│   │   ├── config.py            # Environment settings
│   │   └── db/
│   │       └── connection.py    # SQLAlchemy engine/session
│   │
│   ├── ingestion/
│   │   ├── adapters/
│   │   │   └── base.py          # Provider adapter interface + registry
│   │   ├── pipeline/            # (planned) parse/validate/normalise/load
│   │   └── handlers/            # (planned) S3/SQS event handlers
│   │
│   ├── dashboard/
│   │   └── app.py               # Plotly Dash UI (working)
│   │
│   ├── api/
│   │   └── main.py              # FastAPI (skeleton)
│   │
│   └── recommendation/          # (planned) content/collab/semantic/ensemble
│
├── migrations/
│   └── versions/
│       ├── 001_initial_schema.py
│       └── 002_add_pgvector_embeddings.py
│
├── tests/
│   └── unit/
│       ├── test_models/         # Wine, Price, Provider model tests
│       └── test_scrapers/       # BaseScraper, WineSociety scraper tests
│
├── data/                        # Local data files (gitignored)
│   ├── wine_society/raw/        # Place CSV exports here
│   ├── berry_bros/
│   └── majestic/
│
├── docker-compose.yml           # PostgreSQL + LocalStack + MLflow
├── pyproject.toml               # Dependencies and tool config
├── Makefile                     # All automation commands
├── .env.example                 # Template for environment variables
└── ARCHITECTURE.md              # Detailed system design document
```

## Key concepts

### Finance-to-wine mapping

This project maps hedge fund data infrastructure patterns to the wine domain:

| Finance concept | Wine equivalent | Where in the code |
|-----------------|-----------------|-------------------|
| Security master (ISIN) | Canonical wine schema | `services/shared/models/wine.py` |
| Market data vendor | Wine retailer (TWS, BBR, Majestic) | `scrapers/` |
| Vendor feed handler | Provider adapter | `services/ingestion/adapters/base.py` |
| EOD price tick | Wine price observation | `services/shared/models/price.py` |
| Bi-temporal store | Price valid_from/known_from | `migrations/versions/001_initial_schema.py` |
| Data lineage | Source file, hash, row number | `services/shared/models/lineage.py` |
| Trade/position history | Personal consumption log | `consumption_history` table |

### Bi-temporal pricing

Every price is recorded with two time dimensions:

- **Business time** (`valid_from` / `valid_to`): When was this price actually valid?
- **System time** (`known_from` / `known_to`): When did our system learn about this price?

This means we can answer questions like "what did we think the price was on Tuesday?" separately from "what was the actual price on Tuesday?" -- essential for detecting silent price changes and building accurate backtests.

### Provider adapters

Each retailer delivers data differently. The adapter pattern (`services/ingestion/adapters/base.py`) defines a contract:

1. **detect()** -- "Is this file from my retailer?"
2. **parse()** -- Raw bytes to provider-specific records
3. **normalize_wine()** -- Provider record to canonical Wine
4. **normalize_price()** -- Provider record to WinePrice

Adding a new retailer means creating one file with one class. Zero changes to existing code.

## Common issues

**`docker compose up` fails with "port 5432 already in use"**
You have another PostgreSQL running. Either stop it (`brew services stop postgresql` on Mac) or change the port in `docker-compose.yml`.

**`alembic upgrade head` fails with "connection refused"**
The database isn't ready yet. Wait a few seconds after `docker compose up -d` and try again, or check `docker compose ps` to confirm PostgreSQL is healthy.

**`pip install` fails on `psycopg2-binary`**
On some systems you need PostgreSQL development headers. Try: `brew install postgresql` (Mac), `sudo apt install libpq-dev` (Ubuntu), or use the Docker-based workflow instead.

**Tests fail with import errors**
Make sure you installed with `pip install -e ".[dev]"` (the `-e .` is important -- it installs the project in editable mode so Python can find the packages).

## Useful commands

| Command | What it does |
|---------|--------------|
| `make help` | Show all available commands |
| `make dev` | Install everything (production + dev + collab) |
| `make test` | Run the test suite |
| `make format` | Auto-format all code with black |
| `make lint` | Check code quality with ruff |
| `make dashboard` | Start the Dash dashboard on :8050 |
| `make api` | Start the FastAPI server on :8000 |
| `make docker-up` | Start PostgreSQL, LocalStack, MLflow |
| `make docker-down` | Stop all Docker services |
| `make db-migrate` | Apply database migrations |
| `make clean` | Remove caches and build artifacts |
