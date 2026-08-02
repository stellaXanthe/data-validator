from rich.console import Console
from rich.table import Table
from .comparator import ComparisonResult

console = Console()


def print_report(result: ComparisonResult):
    table = Table(title="Data Validation Report")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Source row count", str(result.source_row_count))
    table.add_row("Target row count", str(result.target_row_count))
    table.add_row("Matched rows", str(result.matched_rows))
    table.add_row("Missing in target", str(result.missing_in_target))
    table.add_row("Missing in source", str(result.missing_in_source))
    table.add_row("Value mismatches", str(result.value_mismatches))
    table.add_row("Duplicate keys (source)", str(result.duplicate_keys_source))
    table.add_row("Duplicate keys (target)", str(result.duplicate_keys_target))

    console.print(table)

    if result.mismatch_samples:
        console.print("\n[bold yellow]Sample mismatches:[/bold yellow]")
        for m in result.mismatch_samples[:5]:
            console.print(f"Key: {m['key']}")
            console.print(f"  Source: {m['source']}")
            console.print(f"  Target: {m['target']}\n")