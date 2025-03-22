from trad_setlist_helper import match


# Example
query = {
    "name": "Cooley's",
    "type": "reel",
    "mode": "Edor",
    "tune_id": None,
}
print(query)
print("->", match(query))
