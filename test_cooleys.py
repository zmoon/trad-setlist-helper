from trad_setlist_helper import match, Query


query: Query = {
    "name": "Cooley's",
    "type": "reel",
    "key": "Edor",
    "tune_id": None,
}
print(query)
result = match(query)
print("->", result)

assert result["tune_id"] == 1
assert result["setting_id"] == 1
