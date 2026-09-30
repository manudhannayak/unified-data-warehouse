# Multi-Source Unified Data Warehouse

A dbt + Airflow pipeline that unifies three source systems a real SaaS
company would have to stitch together — CRM accounts, billing invoices, and
product usage events — into a single `account_360` mart, with data-quality
tests enforced at every layer.

## Architecture

```
CRM export ──┐
Billing export ──┼──► raw.* tables ──► dbt staging (clean/standardize) ──► dbt marts (join/aggregate) ──► account_360
Usage events ──┘

Orchestrated by: Airflow DAG (extract -> load -> dbt run -> dbt test), daily
```

- **Extract** (`src/generate_sources.py`): synthetic CRM/billing/usage data
  with realistic shape (different grains, keys, and referential structure).
  In production this step is a real extractor (Fivetran/Airbyte or custom)
  pulling from the actual CRM, billing system, and event stream.
- **Load** (`src/load_raw.py`): loads the raw extracts into the warehouse's
  `raw` schema.
- **Transform** (`dbt_warehouse/`): a dbt project with a `staging` layer
  (one model per source, cleaned/typed) and a `marts` layer (`dim_accounts`,
  `fct_revenue_monthly`, `fct_engagement_monthly`, and the unified
  `account_360` mart), with 17 dbt tests (`unique`, `not_null`,
  `accepted_values`, `relationships`) enforcing data quality across layers.
- **Orchestrate** (`dags/warehouse_dag.py`): an Airflow DAG chaining
  extract → load → `dbt run` → `dbt test`. Runs standalone with plain
  `python dags/warehouse_dag.py` too, so the whole pipeline is testable
  without an Airflow install.

## Why DuckDB locally, Snowflake in production

This project targets **Snowflake** in production, but developing and testing
against a live Snowflake warehouse isn't practical for a portfolio project
(cost, credentials, network access). So the local/CI path runs the exact
same dbt SQL against **DuckDB** — dbt abstracts most of the dialect
differences, and the few DuckDB-specific functions used here (`date_trunc`,
`date_diff`, `filter (where ...)`) have direct Snowflake equivalents.
Switching environments is a one-line change: uncomment the `prod` Snowflake
target in `dbt_warehouse/profiles.yml` and point `DBT_TARGET` at it. Nothing
in `models/` needs to change.

## Getting started

```bash
pip install -r requirements.txt

# Run the full pipeline (extract -> load -> transform -> test)
python dags/warehouse_dag.py

# Or step by step:
python src/generate_sources.py --out_dir data/raw --n_accounts 200
python src/load_raw.py --raw_dir data/raw --db_path data/warehouse.duckdb
cd dbt_warehouse && DBT_PROFILES_DIR=. dbt run && DBT_PROFILES_DIR=. dbt test
```

To query the result:

```bash
python -c "import duckdb; print(duckdb.connect('data/warehouse.duckdb').execute('select * from main_marts.account_360 limit 10').df())"
```

To run it on a real Airflow instance, drop `dags/warehouse_dag.py` into your
`AIRFLOW_HOME/dags` folder — it registers a daily-scheduled DAG named
`unified_data_warehouse` when the `airflow` package is importable, and falls
back to a plain script when it isn't.

## Tests

```bash
pytest tests/ -v
```

Covers: synthetic source-data generation (shape, key uniqueness, referential
validity) and, by running the real `generate -> load -> dbt run` pipeline
against a throwaway DuckDB file, that `account_360` ends up with exactly one
row per account, no null keys, and non-negative revenue figures.

## Project structure

```
unified-data-warehouse/
├── src/
│   ├── generate_sources.py   # Synthetic CRM/billing/usage data generator
│   └── load_raw.py            # Loads raw CSVs into the warehouse's raw schema
├── dbt_warehouse/
│   ├── dbt_project.yml
│   ├── profiles.yml            # DuckDB locally; commented Snowflake target for prod
│   └── models/
│       ├── staging/            # stg_crm_accounts, stg_billing_invoices, stg_product_usage_events
│       └── marts/               # dim_accounts, fct_revenue_monthly, fct_engagement_monthly, account_360
├── dags/
│   └── warehouse_dag.py        # Airflow DAG (also runnable standalone)
├── tests/
│   └── test_pipeline.py
├── requirements.txt
└── README.md
```

## Tech stack

Python, dbt (staging/marts modeling, testing), DuckDB (local dev warehouse)
/ Snowflake (production target), Apache Airflow (orchestration), pandas,
pytest.

## Notes & limitations

- All source data is synthetic, generated for this project — no real
  customer, account, or billing data is used anywhere.
- The DAG's extract step regenerates synthetic data each run rather than
  hitting a real API, so the "extract" stage should be read as a stand-in
  for wherever Fivetran/Airbyte/a custom connector would sit in production.
