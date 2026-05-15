def remove_null_properties(obj):
    if isinstance(obj, dict):
        return {k: remove_null_properties(v) for k, v in obj.items() if v is not None}
    elif isinstance(obj, list):
        return [remove_null_properties(v) for v in obj if v is not None]
    else:
        return obj
