from pathlib import Path
from tempfile import NamedTemporaryFile
from webbrowser import open_new_tab

import pandas as pd

from trad_setlist_helper import match, parse_set
from trad_setlist_helper.html import setlist_to_html

HERE = Path(__file__).parent

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
    HERE / "bcs-setlist-example.csv",
    header=None,
    names=["set", "type"],
)

results = []
for i_set, (set_input, type_input) in enumerate(
    setlist_input.itertuples(index=False),
    start=1,
):
    line = f"{type_input}: {set_input}"
    queries = parse_set(line)
    results.append([match(query) for query in queries])

html = setlist_to_html(results)
with NamedTemporaryFile(
    "w",
    suffix=".html",
    delete=False,
    encoding="utf-8",
) as f:
    f.write(html)
    open_new_tab(f.name)
