from __future__ import annotations

import re
from string import ascii_uppercase
from typing import Iterable, TYPE_CHECKING

if TYPE_CHECKING:
    from . import Result


HEAD_SNIPPET = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Setlist</title>
  <script src="https://cdn.jsdelivr.net/npm/abcjs@6.4.4/dist/abcjs-basic-min.js"></script>
</head>
"""

RENDER_SNIPPET = """\
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


def tune_to_html(tune: Result, *, div_id: str | None = None) -> str:
    if div_id is None:
        div_id = f"music-{tune['tune_id']}"

    abc = f"K: {tune['key']}\nP: A\n{tune['starts'][0]}"
    for part_label, other_part in zip(ascii_uppercase[1:], tune["starts"][1:]):
        abc += f"\nP: {part_label}\n{other_part}"

    tune_id = tune["tune_id"]
    setting_id = tune["setting_id"]
    url = f"https://thesession.org/tunes/{tune_id}#setting{setting_id}"

    return f'<a href="{url}">link</a><div id="{div_id}"><pre>{abc}</pre></div>'


def set_to_html(set: Iterable[Result], *, heading: str | None = None) -> str:
    if heading is None:
        # TODO: include type or types
        heading = " / ".join(tune["name_input"].strip() for tune in set)

    # Ensure only single spaces separate words
    heading = re.sub(r"\s{2,}", " ", heading)

    # Replace fancy quote for 's
    heading = heading.replace("’", "&rsquo;")

    s = f"<h2>{heading}</h2>\n"
    s += "<ol>\n"

    s += "\n".join(f"  <li>{tune_to_html(tune)}</li>" for tune in set)
    s += "\n</ol>"

    return s


def setlist_to_html(
    sets: Iterable[Iterable[Result]],
    *,
    render: bool = True,
    fullpage: bool = True,
) -> str:
    s = ""
    if fullpage:
        s += HEAD_SNIPPET + "<body>\n"

    s += "\n".join(set_to_html(set) for set in sets)

    if render:
        s += "\n" + RENDER_SNIPPET

    if fullpage:
        s += "</body>\n</html>"

    return s
