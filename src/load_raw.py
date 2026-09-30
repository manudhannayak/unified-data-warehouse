"""
Loads the raw CSV extracts into the warehouse's raw schema.

Uses DuckDB locally (zero setup, runs the same SQL dbt will build on top
of) as a stand-in for the Snowflake database this project targets in
production -- only the connection profile in dbt_warehouse/profiles.yml
changes to point at a real warehouse; the SQL models are unchanged since
dbt abstracts the dialect differences dbt-duckdb/dbt-snowflake don't
already handle.

Usage:
    python src/load_raw.py --raw_dir data/raw --db_path data/warehouse.duckdb
"""
import argparse
import os

import duckdb


TABLES = {
    "crm_accounts": "crm_accounts.csv",
    "billing_invoices": "billing_invoices.csv",
    "product_usage_events": "product_usage_events.csv",
}


def load_raw(raw_dir: str, db_path: str):
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    con = duckdb.connect(db_path)
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")

    for table_name, csv_file in TABLES.items():
        csv_path = os.path.join(raw_dir, csv_file)
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Missing source file: {csv_path}. Run src/generate_sources.py first.")
        con.execute(
            f"CREATE OR REPLACE TABLE raw.{table_name} AS SELECT * FROM read_csv_auto('{csv_path}', header=True)"
        )
        count = con.execute(f"SELECT COUNT(*) FROM raw.{table_name}").fetchone()[0]
        print(f"Loaded raw.{table_name}: {count} rows")

    con.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw_dir", type=str, default="data/raw")
    parser.add_argument("--db_path", type=str, default="data/warehouse.duckdb")
    args = parser.parse_args()
    load_raw(args.raw_dir, args.db_path)


if __name__ == "__main__":
    main()
