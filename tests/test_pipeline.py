import os
import subprocess
import sys

import duckdb
import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DBT_PROJECT_DIR = os.path.join(PROJECT_ROOT, "dbt_warehouse")
TEST_DB_PATH = os.path.join(PROJECT_ROOT, "tests", "_tmp_test_warehouse.duckdb")
TEST_RAW_DIR = os.path.join(PROJECT_ROOT, "tests", "_tmp_test_raw")

sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

from generate_sources import (  # noqa: E402
    generate_billing_invoices,
    generate_crm_accounts,
    generate_product_usage_events,
)


def test_generate_crm_accounts_shape_and_keys():
    accounts = generate_crm_accounts(n_accounts=50, seed=1)
    assert len(accounts) == 50
    assert accounts["account_id"].is_unique
    assert accounts["plan"].isin(["starter", "growth", "scale", "enterprise"]).all()


def test_generate_billing_invoices_reference_valid_accounts():
    accounts = generate_crm_accounts(n_accounts=20, seed=2)
    invoices = generate_billing_invoices(accounts, seed=2)
    assert len(invoices) > 0
    assert set(invoices["account_id"]).issubset(set(accounts["account_id"]))
    assert (invoices["amount_usd"] > 0).all()


def test_generate_product_usage_events_reference_valid_accounts():
    accounts = generate_crm_accounts(n_accounts=20, seed=3)
    events = generate_product_usage_events(accounts, seed=3)
    assert set(events["account_id"]).issubset(set(accounts["account_id"]))


@pytest.fixture(scope="module")
def built_warehouse():
    """Runs the real generate -> load -> dbt run pipeline against a throwaway DB."""
    os.makedirs(TEST_RAW_DIR, exist_ok=True)

    subprocess.run(
        [sys.executable, os.path.join(PROJECT_ROOT, "src", "generate_sources.py"),
         "--out_dir", TEST_RAW_DIR, "--n_accounts", "30", "--seed", "7"],
        check=True,
    )
    subprocess.run(
        [sys.executable, os.path.join(PROJECT_ROOT, "src", "load_raw.py"),
         "--raw_dir", TEST_RAW_DIR, "--db_path", TEST_DB_PATH],
        check=True,
    )

    profile_override = f"""
unified_data_warehouse:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: "{TEST_DB_PATH}"
      schema: main
"""
    test_profiles_dir = os.path.join(PROJECT_ROOT, "tests", "_tmp_profiles")
    os.makedirs(test_profiles_dir, exist_ok=True)
    with open(os.path.join(test_profiles_dir, "profiles.yml"), "w") as f:
        f.write(profile_override)

    subprocess.run(
        ["dbt", "run"],
        cwd=DBT_PROJECT_DIR,
        env={**os.environ, "DBT_PROFILES_DIR": test_profiles_dir},
        check=True,
    )

    yield TEST_DB_PATH

    for path in (TEST_DB_PATH,):
        if os.path.exists(path):
            os.remove(path)


def test_account_360_has_one_row_per_account(built_warehouse):
    con = duckdb.connect(built_warehouse)
    n_accounts = con.execute("SELECT COUNT(*) FROM raw.crm_accounts").fetchone()[0]
    n_mart_rows = con.execute("SELECT COUNT(*) FROM main_marts.account_360").fetchone()[0]
    n_distinct = con.execute("SELECT COUNT(DISTINCT account_id) FROM main_marts.account_360").fetchone()[0]
    assert n_mart_rows == n_accounts
    assert n_mart_rows == n_distinct


def test_account_360_revenue_is_non_negative(built_warehouse):
    con = duckdb.connect(built_warehouse)
    min_revenue = con.execute("SELECT MIN(lifetime_paid_revenue_usd) FROM main_marts.account_360").fetchone()[0]
    assert min_revenue >= 0


def test_account_360_has_no_null_account_ids(built_warehouse):
    con = duckdb.connect(built_warehouse)
    n_nulls = con.execute("SELECT COUNT(*) FROM main_marts.account_360 WHERE account_id IS NULL").fetchone()[0]
    assert n_nulls == 0
