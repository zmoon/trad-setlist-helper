from trad_setlist_helper import match, Query


def test_cooleys() -> None:
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
    assert result["name"] == "Cooley's"
    assert result["type"] == "reel"
    assert result["key"] == "Edor"
    assert result["name_input"] == "Cooley's"


if __name__ == "__main__":
    test_cooleys()
