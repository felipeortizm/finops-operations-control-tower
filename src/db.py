import os
from pathlib import Path

from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
SQL = ROOT / "sql"


def engine():
    url = os.environ.get("DATABASE_URL", f"sqlite:///{ROOT / 'finops_demo.db'}")
    return create_engine(url, future=True)


def read_sql(name):
    return (SQL / name).read_text(encoding="utf-8").strip().rstrip(";")


def install_views(connection):
    connection.execute(text("CREATE VIEW hourly_metrics AS " + read_sql("01_hourly_metrics.sql")))
    connection.execute(text("CREATE VIEW portfolio_metrics AS " + read_sql("02_portfolio_metrics.sql")))


def rows(connection, sql_file, **params):
    return [dict(row) for row in connection.execute(text(read_sql(sql_file)), params).mappings()]
