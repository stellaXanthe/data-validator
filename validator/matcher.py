import Levenshtein
from .connectors.base import SchemaInfo


def match_fields(source: SchemaInfo, target: SchemaInfo, fuzzy_threshold: float = 0.8) -> dict[str, str]:
    """
    Auto-match source columns to target columns.
    1. Exact name match (case-insensitive) first.
    2. Fuzzy match (Levenshtein similarity) for anything left unmatched.
    Returns a dict: {source_column: target_column}
    """
    source_names = [c.name for c in source.columns]
    target_names = [c.name for c in target.columns]

    field_map: dict[str, str] = {}
    used_targets: set[str] = set()

    # Pass 1: exact match (case-insensitive)
    target_lookup = {t.lower(): t for t in target_names}
    for s in source_names:
        if s.lower() in target_lookup:
            field_map[s] = target_lookup[s.lower()]
            used_targets.add(target_lookup[s.lower()])

    # Pass 2: fuzzy match for remaining
    unmatched_sources = [s for s in source_names if s not in field_map]
    unmatched_targets = [t for t in target_names if t not in used_targets]

    for s in unmatched_sources:
        best_match, best_score = None, 0.0
        for t in unmatched_targets:
            score = _similarity(s, t)
            if score > best_score:
                best_match, best_score = t, score
        if best_match and best_score >= fuzzy_threshold:
            field_map[s] = best_match
            unmatched_targets.remove(best_match)

    return field_map


def _similarity(a: str, b: str) -> float:
    distance = Levenshtein.distance(a.lower(), b.lower())
    max_len = max(len(a), len(b))
    return 1 - (distance / max_len) if max_len else 0.0