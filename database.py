
"""
TimeTrack persistence layer using Supabase PostgreSQL.
Maintains the same functions used by main.py.
"""

import os
from functools import lru_cache

from supabase import create_client

from dotenv import load_dotenv
load_dotenv()

@lru_cache(maxsize=1)
def get_client():
    """Create and reuse the Supabase client."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        raise RuntimeError(
            "Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY "
            "in your environment."
        )

    return create_client(url, key)


def init_db():
    """
    The table is created in the Supabase SQL Editor.
    No local database initialization is required.
    """
    pass


def _row_to_dict(row: dict) -> dict:
    return {
        "id": row["id"],
        "employee_name": row["employee_name"],
        "project": row["project"],
        "entry_date": str(row["entry_date"]),
        "hours": row["hours"],
        "description": row.get("description") or "",
    }


def list_all_entries() -> list[dict]:
    response = (
        get_client()
        .table("time_entries")
        .select("*")
        .order("entry_date", desc=True)
        .order("id", desc=True)
        .execute()
    )

    return [_row_to_dict(row) for row in response.data]


def log_time(
    employee_name: str,
    project: str,
    entry_date: str,
    hours: float,
    description: str = "",
) -> dict:
    if hours <= 0:
        raise ValueError("hours must be a positive number")

    record = {
        "employee_name": employee_name,
        "project": project,
        "entry_date": entry_date,
        "hours": hours,
        "description": description,
    }

    response = (
        get_client()
        .table("time_entries")
        .insert(record)
        .execute()
    )

    if not response.data:
        raise RuntimeError("Supabase did not return the inserted entry.")

    return _row_to_dict(response.data[0])


def get_timesheet(
    employee_name: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    query = (
        get_client()
        .table("time_entries")
        .select("*")
        .eq("employee_name", employee_name)
    )

    if start_date:
        query = query.gte("entry_date", start_date)

    if end_date:
        query = query.lte("entry_date", end_date)

    response = query.order("entry_date").execute()

    return [_row_to_dict(row) for row in response.data]


def list_projects() -> list[str]:
    response = (
        get_client()
        .table("time_entries")
        .select("project")
        .execute()
    )

    return sorted({
        row["project"]
        for row in response.data
    })


def get_project_summary(project: str) -> dict:
    response = (
        get_client()
        .table("time_entries")
        .select("employee_name, hours")
        .eq("project", project)
        .execute()
    )

    if not response.data:
        raise ValueError(
            f"No time logged against project '{project}'"
        )

    by_employee = {}

    for row in response.data:
        employee = row["employee_name"]
        by_employee[employee] = (
            by_employee.get(employee, 0) + float(row["hours"])
        )

    return {
        "project": project,
        "total_hours": sum(by_employee.values()),
        "by_employee": by_employee,
    }
