"""
Generates synthetic data for three source systems a mid-size SaaS company
would actually have to unify: CRM accounts, billing invoices, and product
usage events. Mirrors the shape of a real multi-source ingestion problem
(different grains, different keys, some referential noise) without using
any real company or customer data.

Usage:
    python src/generate_sources.py --out_dir data/raw --n_accounts 200 --seed 42
"""
import argparse
import os
import random
from datetime import datetime, timedelta

import pandas as pd

PLANS = ["starter", "growth", "scale", "enterprise"]
INDUSTRIES = ["healthcare", "retail", "fintech", "manufacturing", "education", "logistics"]
REGIONS = ["NA", "EMEA", "APAC", "LATAM"]
EVENT_TYPES = ["login", "report_viewed", "export_created", "api_call", "dashboard_created"]


def generate_crm_accounts(n_accounts: int, seed: int) -> pd.DataFrame:
    rng = random.Random(seed)
    rows = []
    start = datetime(2023, 1, 1)
    for i in range(1, n_accounts + 1):
        created = start + timedelta(days=rng.randint(0, 900))
        rows.append(
            {
                "account_id": f"ACC-{i:05d}",
                "account_name": f"Account {i}",
                "industry": rng.choice(INDUSTRIES),
                "region": rng.choice(REGIONS),
                "plan": rng.choices(PLANS, weights=[0.35, 0.30, 0.20, 0.15])[0],
                "created_at": created.date().isoformat(),
                "is_churned": rng.random() < 0.12,
            }
        )
    return pd.DataFrame(rows)


def generate_billing_invoices(accounts: pd.DataFrame, seed: int) -> pd.DataFrame:
    rng = random.Random(seed + 1)
    plan_base_price = {"starter": 49, "growth": 199, "scale": 599, "enterprise": 1999}
    rows = []
    invoice_id = 1
    for _, acct in accounts.iterrows():
        created = datetime.fromisoformat(acct["created_at"])
        n_invoices = rng.randint(1, 18)
        for m in range(n_invoices):
            invoice_date = created + timedelta(days=30 * m)
            base = plan_base_price[acct["plan"]]
            amount = round(base * rng.uniform(0.9, 1.3), 2)
            rows.append(
                {
                    "invoice_id": f"INV-{invoice_id:06d}",
                    "account_id": acct["account_id"],
                    "invoice_date": invoice_date.date().isoformat(),
                    "amount_usd": amount,
                    "paid": rng.random() > 0.04,
                }
            )
            invoice_id += 1
    return pd.DataFrame(rows)


def generate_product_usage_events(accounts: pd.DataFrame, seed: int) -> pd.DataFrame:
    rng = random.Random(seed + 2)
    rows = []
    event_id = 1
    for _, acct in accounts.iterrows():
        created = datetime.fromisoformat(acct["created_at"])
        # Churned accounts generate fewer/older events; active accounts more/recent.
        n_events = rng.randint(5, 40) if not acct["is_churned"] else rng.randint(0, 8)
        for _ in range(n_events):
            event_time = created + timedelta(days=rng.randint(0, 700), minutes=rng.randint(0, 1440))
            rows.append(
                {
                    "event_id": f"EVT-{event_id:07d}",
                    "account_id": acct["account_id"],
                    "event_type": rng.choice(EVENT_TYPES),
                    "event_timestamp": event_time.isoformat(),
                }
            )
            event_id += 1
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out_dir", type=str, default="data/raw")
    parser.add_argument("--n_accounts", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    accounts = generate_crm_accounts(args.n_accounts, args.seed)
    invoices = generate_billing_invoices(accounts, args.seed)
    events = generate_product_usage_events(accounts, args.seed)

    accounts.to_csv(os.path.join(args.out_dir, "crm_accounts.csv"), index=False)
    invoices.to_csv(os.path.join(args.out_dir, "billing_invoices.csv"), index=False)
    events.to_csv(os.path.join(args.out_dir, "product_usage_events.csv"), index=False)

    print(f"Generated {len(accounts)} accounts, {len(invoices)} invoices, {len(events)} usage events -> {args.out_dir}")


if __name__ == "__main__":
    main()
