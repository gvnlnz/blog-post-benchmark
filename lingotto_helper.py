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