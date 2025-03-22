"""
Given list of tune sets, match them to The Session and create a Markdown
document that includes the start of the tune (in ABC notation)
and a link to the the tune page.

Would be nice to add:
- fuzzy name matching
- fuzzy key/mode matching (e.g. same key sig, maybe even min and dor matching)
- default to Norbeck for the transcription if available
"""
from __future__ import annotations

import re
# from functools import lru_cache as cache
from pathlib import Path
from string import ascii_lowercase, ascii_uppercase
from typing import TypedDict

import pandas as pd
from pyabc2.sources import the_session

HERE = Path(__file__).parent

TUNES = the_session.load_meta("tunes")[
    ["tune_id", "setting_id", "type", "mode", "abc", "name"]
]

# Include primary name as an alias
ALIASES = pd.concat(
    [
        TUNES[["tune_id", "name"]].rename(columns={"name": "alias"}),
        the_session.load_meta("aliases")[["tune_id", "alias"]],
    ],
    ignore_index=True,
).drop_duplicates()
# TODO: should the primary name get preferential treatment?


def normalize_key(key: str) -> str:
    # TODO: not very general, should add full name option to Key class
    from pyabc2.key import _MODE_ABBR_TO_FULL

    if len(key) == 1:
        key = key + "maj"
    elif key.endswith("m"):
        key = key[:-1] + "min"

    if len(key) > 4:
        return key

    return key[0].upper() + _MODE_ABBR_TO_FULL[key[1:].lower()]


def normalize_type(type_: str) -> str:
    type_ = type_.lower()
    if type_.endswith("s"):
        type_ = type_[:-1]
    return type_


def take_measures(abc: str, *, n: int = 5) -> str:
    i = c = 0
    while c < n:
        if abc[i] == "|":
            c += 1
        i += 1
    return abc[:i]


class Query(TypedDict):
    name: str
    type: str
    mode: str | None
    tune_id: int | None


class Result(TypedDict):
    url: str
    key: str
    starts: list[str]


def match(query: Query) -> Result:
    # Replace fancy single quote/apostrophe with ASCII single quote
    query["name"] = query["name"].replace("’", "'")
    query["name"] = " ".join(
        word.capitalize() if word[0] in ascii_lowercase else word
        for word in query["name"].split()
    )
    if query["name"].startswith("The "):
        query["name"] = query["name"][4:] + ", The"

    # Normalize to full mode name
    if query["mode"] is not None:
        query["mode"] = normalize_key(query["mode"])

    # First try to match name
    possible_ids = sorted(
        ALIASES.query("alias == @query['name']").tune_id.unique()
    )
    if not possible_ids:
        raise ValueError(f"No tune found with name/alias {query['name']!r}")

    # Now narrow based on type and key
    s_query = "tune_id == @possible_ids and type == @query['type']"
    if query["mode"] is not None:
        s_query += " and mode == @query['mode']"
    if query.get("tune_id") is not None:
        s_query += " and tune_id == @query['tune_id']"
    matches = TUNES.query(s_query)

    if matches.empty:
        raise ValueError(
            f"No {query['name']!r} tune found for "
            f"type {query['type']!r} and key {query['mode']!r}"
        )
    elif matches.tune_id.nunique() > 1:
        matches_ = (
            matches.drop(columns="setting_id")
            .drop_duplicates(["tune_id", "type", "mode"], keep="first")
        )
        raise ValueError(
            f"Multiple {query['name']!r} tunes found for "
            f"type {query['type']!r} and key {query['mode']!r}:\n{matches_}"
        )

    # Pick the oldest matching setting
    setting_id = matches.setting_id.min()
    url = f"https://thesession.org/tunes/{matches.tune_id.iloc[0]}#setting{setting_id}"
    abc = (
        matches.sort_values(by="setting_id", ascending=True)
        .abc.iloc[0]
        .replace("\r\n", "")
    )

    # Take first few bars
    start = take_measures(abc, n=5)

    # Try to find the start of next parts, looking for |: or ||
    # Reject || at end and |: that follows ||
    offset = 10
    i_part_cands = []
    for m in re.finditer(r"\|[:|]", abc[offset:]):
        i = m.start() + offset
        if "|" in abc[i - 3:i]:
            continue
        if len(abc) - i < 10:
            continue
        i_part_cands.append(i)
    print(i_part_cands)

    starts = [start]
    for i_part in i_part_cands:
        starts.append(take_measures(abc[i_part:], n=7))  # FIXME: counting not accounting for the || and such

    return {
        "url": url,
        "key": matches["mode"].iloc[0][:4],  # TODO: not general
        "starts": starts,
    }


# Example
query = {
    "name": "Cooley's",
    "type": "reel",
    "mode": "Edor",
    "tune_id": None,
}
print(query)
print("->", match(query))

# Table from Brian's email as CSV via Excel
# Had to:
# - add a lot of "The "s
# - specify ID in some cases,
#   where adding key still resulted in multiple matches using aliases
# - "Tobin's Favorite" (American spelling) is an alias on the website,
#   but not in the data
#   (maybe should contact Jeremy about this)
# -
setlist_input = pd.read_csv(
    HERE / "bcs-first-setlist.csv",
    header=None,
    names=["set", "type"],
)


s = "# Set list\n"
s_html_body = "<h1>Set list</h1>\n"
for i_set, (set_input, type_input) in enumerate(setlist_input.itertuples(index=False), start=1):
    tunes = [
        tune.strip()
        for tune in set_input.split("/")
    ]
    type_inputs = [s.strip() for s in type_input.split(",")]
    if len(type_inputs) == len(tunes):
        types = [normalize_type(s) for s in type_inputs]
    elif len(type_inputs) == 1:
        types = [normalize_type(type_inputs[0])] * len(tunes)
    elif len(type_inputs) == 2:
        a, b = type_inputs
        a_is_plural = a.endswith("s")
        b_is_plural = b.endswith("s")
        if len(tunes) < 2:
            raise ValueError("Too many types")
        elif len(tunes) == 2:
            types = [normalize_type(a), normalize_type(b)]
        else:
            if a_is_plural and b_is_plural:
                raise ValueError(
                    f"Ambiguous type input {type_input!r}. "
                    "Try specifying type for each tune "
                    "(e.g. 'slip jig, jig, reel')."
                )
            elif a_is_plural:
                types = [normalize_type(a)] * (len(tunes) - 1) + [normalize_type(b)]
            elif b_is_plural:
                types = [normalize_type(a)] + [normalize_type(b)] * (len(tunes) - 1)
            else:
                raise ValueError("Not enough types")
    else:
        raise ValueError(
            f"Unsupported type input {type_input!r}. "
            "Try specifying type for each tune (e.g. 'slip jig, jig, reel')."
        )

    set_input_ = " / ".join(re.sub(r"\[[0-9]+\]", "", tune).strip() for tune in tunes)
    set_input_ = re.sub(r"\s{2,}", " ", set_input_)
    s += f"\n#### {type_input}: {set_input_}\n\n"
    s_html_body += f"<h2>{type_input}: {set_input_.replace("’", "&rsquo;")}</h2>\n"
    s_html_body += "<ol>\n"
    for i_tune, (tune, type_) in enumerate(zip(tunes, types), start=1):
        # Optional key in parens or ID in brackets
        m = re.fullmatch(r"(.+?)\s*(?:\((.+?)\))?\s*(?:\[(.+?)\])?", tune)
        if m is None:
            raise ValueError(f"Could not parse tune input {tune!r}")
        name_, key, id_ = m.groups()
        if id_ is not None:
            id_ = int(id_)

        query = {
            "name": name_,
            "type": type_,
            "mode": key,
            "tune_id": id_,
        }
        result = match(query)
        print(tune)
        print("->", result)

        s += f"{i_tune}. `{result['key']}` `{result['starts'][0]}` [link]({result['url']})\n"
        music_id = f"music-{i_set}-{i_tune}-a"  # TODO: other parts
        abc = (
            f"K: {result['key']}\n"
            "P: A\n"
            f"{result['starts'][0]}"
        )
        for part_label, other_part in zip(ascii_uppercase[1:], result["starts"][1:]):
            abc += f"\nP: {part_label}\n{other_part}"
        s_html_body += (
            f"<li><a href='{result["url"]}'>link</a>"
            f"<div id={music_id!r}><pre>{abc}</pre></div>"
            f'</li>\n'
        )
    s_html_body += "</ol>\n"

with open(HERE / "bcs-first-setlist.md", "w") as f:
    f.write(s)

s_html_body += """\
<script>
// Find all divs with ID music-* and render them
document.querySelectorAll('div[id^="music-"]').forEach(function (div) {
    var abc = div.querySelector('pre').textContent;
    ABCJS.renderAbc(
        div,
        abc,
        {
            scale: 0.6,
            staffwidth: 350,
        },
    );
});
</script>
"""

with open(HERE / "bcs-first-setlist.html", "w") as f:
    f.write("""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Set list</title>
  <script src='https://cdn.jsdelivr.net/npm/abcjs@6.4.4/dist/abcjs-basic-min.js'></script>
</head>
<body>
""")
    # f.write("<body>\n")
    f.write(s_html_body)
    f.write("</body>\n</html>")
