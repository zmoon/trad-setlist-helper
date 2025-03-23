import js  # type: ignore[import]
from pyscript import document  # type: ignore[import]

import trad_setlist_helper
from trad_setlist_helper import match, parse_set, load_aliases
from trad_setlist_helper.html import setlist_to_html

trad_setlist_helper.USE_CWD_FILES = True

# Trigger data load to memory
output = document.querySelector("#output")
output.innerText = "Loading data..."
_ = load_aliases()
output.innerText += " done"


def submit(event):
    input = document.querySelector("#input").value
    output_el = document.querySelector("#output")

    # Remove possible previous errors (class py-error)
    for el in document.querySelectorAll(".py-error"):
        el.remove()

    output_el.innerText = "processing..."
    results = []
    for line in input.splitlines():
        queries = parse_set(line)
        results.append([match(query) for query in queries])

    output_el.innerHTML = setlist_to_html(results, fullpage=False, render=False)

    js.renderAbc()
