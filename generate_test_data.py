import csv
import random
from pathlib import Path

random.seed(42)  # reproducible output

NUM_ROWS = 200
OUTPUT_DIR = Path(".")

FIRST_NAMES = ["Alice", "Bob", "Carla", "David", "Elena", "Frank", "Grace", "Hassan", "Ivy", "Jamal"]
LAST_NAMES = ["Smith", "Johnson", "Garcia", "Lee", "Brown", "Davis", "Martinez", "Wilson", "Clark", "Lewis"]
REGIONS = ["North", "South", "East", "West", "Central"]
STATUSES = ["active", "inactive", "pending"]


def generate_source_rows(n: int) -> list[dict]:
    rows = []
    for i in range(1, n + 1):
        rows.append({
            "id": i,
            "first_name": random.choice(FIRST_NAMES),
            "last_name": random.choice(LAST_NAMES),
            "region": random.choice(REGIONS),
            "amount": round(random.uniform(10, 5000), 2),
            "status": random.choice(STATUSES),
        })
    return rows


def build_target_rows(source_rows: list[dict]) -> list[dict]:
    target = [dict(row) for row in source_rows]  # deep-ish copy

    # 1. Drop a few rows entirely (simulate "missing in target")
    drop_ids = random.sample(range(1, NUM_ROWS + 1), k=5)
    target = [row for row in target if row["id"] not in drop_ids]
    print(f"Dropped from target (missing_in_target expected): {sorted(drop_ids)}")

    # 2. Mutate a few values (simulate "value mismatches")
    mismatch_candidates = [row for row in target if row["id"] not in drop_ids]
    mismatch_rows = random.sample(mismatch_candidates, k=8)
    mismatch_ids = []
    for row in mismatch_rows:
        field_to_break = random.choice(["amount", "status", "region"])
        if field_to_break == "amount":
            row["amount"] = round(row["amount"] + random.uniform(1, 50), 2)
        elif field_to_break == "status":
            row["status"] = random.choice([s for s in STATUSES if s != row["status"]])
        else:
            row["region"] = random.choice([r for r in REGIONS if r != row["region"]])
        mismatch_ids.append(row["id"])
    print(f"Mutated in target (value_mismatches expected): {sorted(mismatch_ids)}")

    # 3. Duplicate a few rows (simulate "duplicate_keys_target")
    dup_candidates = [row for row in target if row["id"] not in drop_ids]
    dup_rows = random.sample(dup_candidates, k=3)
    for row in dup_rows:
        target.append(dict(row))
    print(f"Duplicated in target (duplicate_keys_target expected): {[r['id'] for r in dup_rows]}")

    # 4. Add a couple rows only in target (simulate "missing_in_source")
    extra_start = NUM_ROWS + 1
    for i in range(extra_start, extra_start + 3):
        target.append({
            "id": i,
            "first_name": random.choice(FIRST_NAMES),
            "last_name": random.choice(LAST_NAMES),
            "region": random.choice(REGIONS),
            "amount": round(random.uniform(10, 5000), 2),
            "status": random.choice(STATUSES),
        })
    print(f"Extra rows only in target (missing_in_source expected): {list(range(extra_start, extra_start + 3))}")

    return target


def add_source_duplicates(source_rows: list[dict]) -> list[dict]:
    rows = list(source_rows)
    dup_rows = random.sample(source_rows, k=2)
    for row in dup_rows:
        rows.append(dict(row))
    print(f"Duplicated in source (duplicate_keys_source expected): {[r['id'] for r in dup_rows]}")
    return rows


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    fieldnames = ["id", "first_name", "last_name", "region", "amount", "status"]

    source_rows = generate_source_rows(NUM_ROWS)
    target_rows = build_target_rows(source_rows)
    source_rows = add_source_duplicates(source_rows)

    write_csv(OUTPUT_DIR / "source.csv", source_rows, fieldnames)
    write_csv(OUTPUT_DIR / "target.csv", target_rows, fieldnames)

    print(f"\nGenerated source.csv ({len(source_rows)} rows) and target.csv ({len(target_rows)} rows)")


if __name__ == "__main__":
    main()