CANONICAL_METALS = ["gold", "silver", "platinum", "palladium"]
_METAL_ALIASES = {
    "oro": "gold",
    "argento": "silver",
    "platino": "platinum",
    "palladio": "palladium",
}


def normalize_metals(post: dict) -> None:
    """Coerce the metals array to canonical English values, in place.

    The translation/proofread steps sometimes emit Italian names ("oro") even
    though the schema requires English. Map known aliases back, drop anything
    unrecognized, and dedupe while preserving order.
    """
    raw = post.get("metals")
    if not isinstance(raw, list):
        return
    seen = []
    for m in raw:
        if not isinstance(m, str):
            continue
        key = m.strip().lower()
        canonical = _METAL_ALIASES.get(key, key)
        if canonical in CANONICAL_METALS and canonical not in seen:
            seen.append(canonical)
    post["metals"] = seen


def missing_fields(object: dict) -> bool:
    fields = {
        'title': str,
        'slug': str,
        'body': str,
        'sentiment': str,
        'metals': list,
        'impact_score': int,
        'meta_description': str,
    }

    for field, expected_type in fields.items():
        value = object.get(field)
        if not value:
            return True
        if type(value) != expected_type:
            return True

    return False