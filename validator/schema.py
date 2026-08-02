from dataclasses import dataclass
from .connectors.base import SchemaInfo


@dataclass
class SchemaDiff:
    missing_in_target: list[str]
    missing_in_source: list[str]
    type_mismatches: list[tuple[str, str, str]]  # (column, source_type, target_type)


def compare_schemas(source: SchemaInfo, target: SchemaInfo, field_map: dict[str, str]) -> SchemaDiff:
    """
    field_map maps source_column -> target_column (from the matcher).
    Detects columns present on one side but not mapped, and type mismatches
    for mapped columns.
    """
    source_cols = {c.name: c.dtype for c in source.columns}
    target_cols = {c.name: c.dtype for c in target.columns}

    mapped_targets = set(field_map.values())
    missing_in_target = [c for c in source_cols if c not in field_map]
    missing_in_source = [c for c in target_cols if c not in mapped_targets]

    type_mismatches = []
    for src_col, tgt_col in field_map.items():
        src_type = source_cols.get(src_col)
        tgt_type = target_cols.get(tgt_col)
        if src_type and tgt_type and _normalize_type(src_type) != _normalize_type(tgt_type):
            type_mismatches.append((src_col, src_type, tgt_type))

    return SchemaDiff(
        missing_in_target=missing_in_target,
        missing_in_source=missing_in_source,
        type_mismatches=type_mismatches,
    )


def _normalize_type(dtype: str) -> str:
    """Rough normalization so e.g. VARCHAR(255) vs object both read as 'string'."""
    dtype = dtype.lower()
    if "int" in dtype:
        return "integer"
    if "float" in dtype or "double" in dtype or "decimal" in dtype or "numeric" in dtype:
        return "float"
    if "char" in dtype or "text" in dtype or "object" in dtype or "string" in dtype:
        return "string"
    if "date" in dtype or "time" in dtype:
        return "datetime"
    if "bool" in dtype:
        return "boolean"
    return dtype