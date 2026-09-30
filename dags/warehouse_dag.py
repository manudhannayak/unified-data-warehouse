"""
Airflow DAG orchestrating the unified data warehouse pipeline:

    extract synthetic sources -> load raw -> dbt run -> dbt test

In production, the extract task would be replaced by real connectors
(Fivetran/Airbyte, or custom extractors) pulling from the CRM, billing
system, and product event stream, and `load_raw` / the dbt `dev` target
would point at Snowflake instead of the local DuckDB file. The DAG
structure and dependency graph stay the same either way.

Drop this file into your Airflow DAGs folder, or run it standalone with:
    python dags/warehouse_dag.py
to execute the same steps outside of an Airflow scheduler for local testing.
"""
import os
import subprocess
import sys
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DBT_PROJECT_DIR = os.path.join(PROJECT_ROOT, "dbt_warehouse")


def run_step(description: str, cmd: list[str], cwd: str | None = None, env: dict | None = None):
    print(f"\n=== {description} ===")
    result = subprocess.run(cmd, cwd=cwd or PROJECT_ROOT, env={**os.environ, **(env or {})})
    if result.returncode != 0:
        raise RuntimeError(f"Step failed: {description} (exit code {result.returncode})")


def extract_sources():
    run_step(
        "Extract: generate synthetic source data",
        [sys.executable, "src/generate_sources.py", "--out_dir", "data/raw"],
    )


def load_raw():
    run_step(
        "Load: raw CSVs -> warehouse",
        [sys.executable, "src/load_raw.py", "--raw_dir", "data/raw", "--db_path", "data/warehouse.duckdb"],
    )


def dbt_run():
    run_step(
        "Transform: dbt run",
        ["dbt", "run"],
        cwd=DBT_PROJECT_DIR,
        env={"DBT_PROFILES_DIR": "."},
    )


def dbt_test():
    run_step(
        "Validate: dbt test",
        ["dbt", "test"],
        cwd=DBT_PROJECT_DIR,
        env={"DBT_PROFILES_DIR": "."},
    )


try:
    from airflow import DAG
    from airflow.operators.python import PythonOperator

    default_args = {"owner": "data-eng", "retries": 1}

    with DAG(
        dag_id="unified_data_warehouse",
        description="Extract CRM/billing/usage sources, load, transform with dbt, and validate.",
        schedule="@daily",
        start_date=datetime(2026, 1, 1),
        catchup=False,
        default_args=default_args,
        tags=["warehouse", "dbt"],
    ) as dag:
        extract_task = PythonOperator(task_id="extract_sources", python_callable=extract_sources)
        load_task = PythonOperator(task_id="load_raw", python_callable=load_raw)
        transform_task = PythonOperator(task_id="dbt_run", python_callable=dbt_run)
        test_task = PythonOperator(task_id="dbt_test", python_callable=dbt_test)

        extract_task >> load_task >> transform_task >> test_task

except ImportError:
    dag = None  # Airflow isn't installed in this environment; see `if __name__` below.


if __name__ == "__main__":
    # Lets you run the whole pipeline locally without an Airflow scheduler.
    extract_sources()
    load_raw()
    dbt_run()
    dbt_test()
    print("\nPipeline completed successfully.")
