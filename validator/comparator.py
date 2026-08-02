import hashlib
from dataclasses import dataclass, field
import pandas as pd


@dataclass
class ComparisonResult:
    source_row_count: int
    target_row_count: int
    matched_rows: int
    missing_in_target: int
    missing_in_source: int
    value_mismatches: int
    duplicate_keys_source: int
    duplicate_keys_target: int
    mismatch_samples: list[dict] = field(default_factory=list)


def compare_data(
    source_df: pd.DataFrame,
    target_df: pd.DataFrame,
    field_map: dict[str, str],
    key_columns: list[str],
    sample_limit: int = 50,
) -> ComparisonResult:
    reverse_map = {v: k for k, v in field_map.items()}
    target_renamed = target_df.rename(columns=reverse_map)

    compare_cols = list(field_map.keys())
    source_slim = source_df[compare_cols].copy()
    target_slim = target_renamed[compare_cols].copy()

    dup_source = source_slim.duplicated(subset=key_columns).sum()
    dup_target = target_slim.duplicated(subset=key_columns).sum()

    source_slim["_row_hash"] = source_slim.apply(_hash_row, axis=1)
    target_slim["_row_hash"] = target_slim.apply(_hash_row, axis=1)

    source_indexed = source_slim.set_index(key_columns)
    target_indexed = target_slim.set_index(key_columns)

    common_keys = source_indexed.index.intersection(target_indexed.index)
    missing_in_target = source_indexed.index.difference(target_indexed.index)
    missing_in_source = target_indexed.index.difference(source_indexed.index)

    mismatches = []
    mismatch_count = 0  # <-- track true count separately from the capped sample list
    matched = 0
    for key in common_keys:
        src_hash = source_indexed.loc[key, "_row_hash"]
        tgt_hash = target_indexed.loc[key, "_row_hash"]
        if isinstance(src_hash, pd.Series):
            src_hash = src_hash.iloc[0]
        if isinstance(tgt_hash, pd.Series):
            tgt_hash = tgt_hash.iloc[0]

        if src_hash == tgt_hash:
            matched += 1
        else:
            mismatch_count += 1
            if len(mismatches) < sample_limit:
                mismatches.append({
                    "key": key,
                    "source": source_indexed.loc[key].drop("_row_hash").to_dict(),
                    "target": target_indexed.loc[key].drop("_row_hash").to_dict(),
                })

    return ComparisonResult(
        source_row_count=len(source_df),
        target_row_count=len(target_df),
        matched_rows=matched,
        missing_in_target=len(missing_in_target),
        missing_in_source=len(missing_in_source),
        value_mismatches=mismatch_count,  # <-- use the true count, not len(mismatches)
        duplicate_keys_source=int(dup_source),
        duplicate_keys_target=int(dup_target),
        mismatch_samples=mismatches,
    )


def _hash_row(row: pd.Series) -> str:
    row_str = "|".join(str(v) for v in row.values)
    return hashlib.sha256(row_str.encode("utf-8")).hexdigest()