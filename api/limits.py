PLAN_LIMITS = {
    "free": {"max_rows_per_validation": 10_000, "connectors": {"file"}},
    "pro": {"max_rows_per_validation": None, "connectors": {"file", "sql", "databricks"}},
    "team": {"max_rows_per_validation": None, "connectors": {"file", "sql", "databricks"}},
}


def get_plan_limits(plan: str) -> dict:
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])