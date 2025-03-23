"""
Given a list of tune sets, match them to The Session and create a
document that includes the start of the tune
and a link to the the tune page
for each tune in each set.
"""

from __future__ import annotations

import logging
import re
from functools import lru_cache
from pathlib import Path
from string import ascii_lowercase
from typing import TypedDict, TYPE_CHECKING, NotRequired

__version__ = "0.0.2.dev0"

if TYPE_CHECKING:
    import pandas as pd

HERE = Path(__file__).parent

logger = logging.getLogger(__name__)

USE_CWD_FILES = False
"""Use downloaded tunes/aliases JSON files in the CWD.
Set before calling :func:`match` (or :func:`load_tunes` / :func:`load_aliases`).
"""


@lru_cache(1)
def load_tunes() -> pd.DataFrame:
    if USE_CWD_FILES:
        import pandas as pd

        df = pd.read_json("tunes.json")
    else:
        from pyabc2.sources import the_session

        # TODO: cache the files to disk, maybe as json.gz, instead of downloading every session
        df = the_session.load_meta("tunes")

    return df[["tune_id", "setting_id", "type", "mode", "abc", "name"]].rename(
        columns={"mode": "key"}
    )
    # TODO: rename in pyabc2?


@lru_cache(1)
def load_aliases() -> pd.DataFrame:
    import pandas as pd

    if USE_CWD_FILES:
        df = pd.read_json("aliases.json")
    else:
        from pyabc2.sources import the_session

        df = the_session.load_meta("aliases")

    # TODO: should the primary name get preferential treatment?
    # Note we have to explicitly add primary name as an alias
    return pd.concat(
        [
            load_tunes()[["tune_id", "name"]].rename(columns={"name": "alias"}),
            df[["tune_id", "alias"]],
        ],
        ignore_index=True,
    ).drop_duplicates()


def normalize_key(key: str) -> str:
    """The Session key format.

    - Mode full name, in lowercase
    - No space between tonic and mode
    """

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
    """The Session tune type format.

    - Lowercase
    - Singular
    """
    type_ = type_.lower()
    if type_.endswith("s"):
        type_ = type_[:-1]
    return type_


def normalize_name(name: str) -> str:
    """The Session name format.

    - Capitalize first letter of each word
    - "..., The" instead of "The ..."
    - Replace fancy quote with normal single quote / apostrophe
    """
    name = name.replace("’", "'")
    name = " ".join(
        word.capitalize() if word[0] in ascii_lowercase else word
        for word in name.split()
    )
    if name.startswith("The "):
        name = name[4:] + ", The"
    return name


def take_measures(abc: str, *, n: int = 5) -> str:
    i = c = 0
    while c < n:
        if abc[i] == "|":
            c += 1
        i += 1
    return abc[:i]


def starts(abc, *, n: int = 5) -> list[str]:
    # Take first few bars
    start = take_measures(abc, n=n)

    # Try to find the start of next parts, looking for |: or ||
    # Reject || at end and |: that follows ||
    offset = 10
    i_part_cands = []
    for m in re.finditer(r"\|[:|]", abc[offset:]):
        i = m.start() + offset
        if "|" in abc[i - 3 : i]:
            continue
        if len(abc) - i < 10:
            continue
        i_part_cands.append(i)
    logger.debug(f"part start candidates: {i_part_cands}")

    starts = [start]
    for i_part in i_part_cands:
        starts.append(
            take_measures(abc[i_part:], n=7)
        )  # FIXME: counting not accounting for the || and such

    return starts


class Query(TypedDict):
    name: str
    """Tune name, e.g. 'The Frost is All Over'."""

    type: NotRequired[str | None]
    """Tune type, e.g. 'reel'. Optional."""

    key: NotRequired[str | None]
    """Key/mode, e.g. 'D', 'Am', 'Edor'. Optional."""

    tune_id: NotRequired[int | None]
    """Tune ID on The Session (if known). Optional."""


class Result(TypedDict):
    name: str
    """Name in the result (normalized The Session format)."""

    tune_id: int
    """Tune ID on The Session."""

    setting_id: int
    """Setting ID on The Session."""

    type: str
    """Type of the tune (unique for a tune ID)."""

    key: str
    """Key/mode of the tune according to The Session setting selected, e.g. 'Edor'."""

    starts: list[str]
    """List of ABC notation strings for the start of each part."""

    name_input: str
    """Name in the query."""


def match(query: Query) -> Result:
    name_in = query["name"]
    name = normalize_name(query["name"])
    if (key := query.get("key")) is not None:
        key = normalize_key(key)
    if (tune_type := query.get("type")) is not None:
        tune_type = normalize_type(tune_type)
    tune_id = query.get("tune_id")

    # First try to match name
    possible_ids = sorted(load_aliases().query("alias == @name")["tune_id"].unique())
    if not possible_ids:
        raise ValueError(f"No tune found with name/alias {name!r}")

    # Now narrow based on type and key
    s_query = "tune_id == @possible_ids"
    if tune_type is not None:
        s_query += " and type == @tune_type"
    if key is not None:
        s_query += " and key == @key"
    if tune_id is not None:
        s_query += " and tune_id == @tune_id"
    matches = load_tunes().query(s_query)

    if matches.empty:
        raise ValueError(
            f"No {name_in!r} tune found for type {tune_type!r} and key {key!r}"
        )
    elif matches["tune_id"].nunique() > 1:
        matches_ = matches.drop(columns="setting_id").drop_duplicates(
            ["tune_id", "type", "key"], keep="first"
        )
        raise ValueError(
            f"Multiple {name_in!r} tunes found for "
            f"type {tune_type!r} and key {key!r}:\n{matches_}"
        )

    # Pick the oldest matching setting
    setting_id = matches["setting_id"].min()
    tune_id_out = matches["tune_id"].iloc[0]
    if tune_id is not None:
        assert tune_id == tune_id_out
    tune_type_out = matches["type"].iloc[0]
    if tune_type is not None:
        assert tune_type == tune_type_out
    key_out = matches["key"].iloc[0][:4]  # TODO: get abbr in a more general way
    if key is not None:
        assert key.startswith(key_out)
    abc = (
        matches.sort_values(by="setting_id", ascending=True)
        .abc.iloc[0]
        .replace("\r\n", "")
    )
    starts_ = starts(abc)

    return {
        "name": name,
        "tune_id": int(tune_id_out),
        "setting_id": int(setting_id),
        "type": tune_type_out,
        "key": key_out,
        "starts": starts_,
        "name_input": name_in,
    }


def parse_set_type(type_input: str, num_tunes: int, /) -> list[str]:
    """Based on the type input string and known number of tunes,
    return a list of tune types for the set.

    Example type input strings:

    - 'reels'
    - 'jigs, reel'
    - 'hornpipe, reels'
    - 'slip jig, jig'
    """
    type_inputs = [s.strip() for s in type_input.split(",")]
    if len(type_inputs) == num_tunes:
        types = [normalize_type(s) for s in type_inputs]
    elif len(type_inputs) == 1:
        types = [normalize_type(type_inputs[0])] * num_tunes
    elif len(type_inputs) == 2:
        a, b = type_inputs
        a_is_plural = a.endswith("s")
        b_is_plural = b.endswith("s")
        if num_tunes < 2:
            raise ValueError("Too many types")
        elif num_tunes == 2:
            types = [normalize_type(a), normalize_type(b)]
        else:
            if a_is_plural and b_is_plural:
                raise ValueError(
                    f"Ambiguous type input {type_input!r}. "
                    "Try specifying type for each tune "
                    "(e.g. 'slip jig, jig, reel')."
                )
            elif a_is_plural:
                types = [normalize_type(a)] * (num_tunes - 1) + [normalize_type(b)]
            elif b_is_plural:
                types = [normalize_type(a)] + [normalize_type(b)] * (num_tunes - 1)
            else:
                raise ValueError("Not enough types")
    else:
        raise ValueError(
            f"Unsupported type input {type_input!r}. "
            "Try specifying type for each tune (e.g. 'slip jig, jig, reel')."
        )

    return types


def parse_tune(tune_input: str, /) -> Query:
    """Parse a tune input string.

    Examples:

    - Cooley's
    - Cooley's (Edor)
    - Cooley's (Edor) [1]
    - Cooley's [1]
    """
    # Optional key in parens or ID in brackets
    # TODO: support setting ID with a [tune:setting] syntax
    m = re.fullmatch(r"(.+?)\s*(?:\((.+?)\))?\s*(?:\[(.+?)\])?", tune_input)
    if m is None:
        raise ValueError(f"Could not parse tune input {tune_input!r}")
    name_, key_, id_ = m.groups()
    if id_ is not None:
        id_ = int(id_)

    return {
        "name": name_,
        "key": key_,
        "tune_id": id_,
    }


def parse_set(set_line: str, /) -> list[Query]:
    """
    Examples:

    - reels: Cooley's / The Maid Behind the Bar / The Silver Spear
    """
    type_input, tunes_input = set_line.split(":", 1)
    tune_inputs = [tune.strip() for tune in tunes_input.split("/")]
    n = len(tune_inputs)

    types = parse_set_type(type_input, n)
    queries = [parse_tune(tune) for tune in tune_inputs]

    for query, type_ in zip(queries, types):
        query["type"] = type_

    return queries


def get_member_set(member_id: int, set_id: int) -> list[Result]:
    import requests

    url = f"https://thesession.org/members/{member_id}/sets/{set_id}?format=json"
    r = requests.get(url)
    r.raise_for_status()
    data = r.json()

    results = []
    for setting in data["settings"]:
        url = setting["url"]
        tune_id = int(url.split("/")[-1].split("#")[0])
        d: Result = {
            "name": setting["name"],
            "tune_id": tune_id,
            "setting_id": setting["id"],
            "type": setting["type"],
            "key": setting["key"],
            "starts": starts(setting["abc"].replace("! ", "")),
            "name_input": setting["name"],
        }
        results.append(d)

    return results


def get_member_sets(member_id: int) -> list[list[Result]]:
    import requests

    url = f"https://thesession.org/members/{member_id}/sets?format=json"
    r = requests.get(url)
    r.raise_for_status()
    data = r.json()

    sets = []
    for set in data["sets"]:
        set_id = set["id"]
        sets.append(get_member_set(member_id, set_id))

    return sets
