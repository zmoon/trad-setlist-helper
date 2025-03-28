"""Create HTML of the popular tunes."""
# mypy: disable-error-code="typeddict-item, union-attr"

import pandas as pd

from trad_setlist_helper import load_tunes, starts, Result
from trad_setlist_helper.html import HEAD_SNIPPET, RENDER_SNIPPET, tune_to_html


TOC_NAV_SNIPPET = """\
<nav id="js-toc-bar" class="is-position-fixed" style="right: 0; background: rgba(245, 245, 245, 0.8);">
<div class="toc js-toc"></div>
</nav>
"""

TOC_SNIPPET = """\
<script src="https://cdnjs.cloudflare.com/ajax/libs/tocbot/4.32.2/tocbot.min.js"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/tocbot/4.32.2/tocbot.css">
<script>
tocbot.init({
  // Where to render the table of contents.
  tocSelector: '.js-toc',
  // Where to grab the headings to build the table of contents.
  contentSelector: '.js-toc-content',
  // Which headings to grab inside of the contentSelector element.
  headingSelector: 'h1, h2, h3',
  // For headings inside relative or absolute positioned containers within content.
  hasInnerContainers: false,
  // # of heading levels that should not be collapsed.
  collapseDepth: 0,
});
</script>
"""

tunes = load_tunes()
popularity = pd.read_json(
    "https://raw.githubusercontent.com/adactio/TheSession-data/main/json/tune_popularity.json"
)

# Note:
# - only tunes with >=10 are included in the popularity data
# - currently tune 12130 is in the popularity data but not in the tunes data
#   (a weird tune page with no settings)
tunes = (
    tunes.merge(popularity[["tune_id", "tunebooks"]], how="inner", on="tune_id")
    .sort_values(["type", "tunebooks"], ascending=[True, False])
    .drop_duplicates(["tune_id"], keep="first")
    .reset_index(drop=True)
)

to_take = {
    "jig": 300,
    "reel": 300,
    "hornpipe": 100,
    "slip jig": 100,
    "polka": 100,
    "waltz": 50,
}

now = pd.Timestamp.utcnow().strftime(r"%Y-%m-%d %H:%MZ")

intro = f"""\
{TOC_NAV_SNIPPET}
The most poular tunes on <a href="https://thesession.org/">The Session</a>,
according to
<a href="https://github.com/adactio/TheSession-data/blob/main/json/tune_popularity.json">the data dump</a>,
as of {now}.
"""
body = ""
for type_, n in to_take.items():
    body += f'<h2 id="{type_}s">{type_.capitalize()}s</h2>\n'
    df = tunes.query(f"type == '{type_}'").head(n)
    for i, row in enumerate(df.itertuples(index=False), start=1):
        d: Result = {
            "name": row.name,
            "tune_id": row.tune_id,
            "setting_id": row.setting_id,
            "type": row.type,
            "key": row.key[:4],  # type: ignore[index]
            "starts": starts(row.abc.replace("\r\n", "")),  # type: ignore[arg-type]
            "name_input": row.name,
        }
        if (i - 1) % 20 == 0:
            a, b = i, min(i + 19, n)
            body += f'<h3 id="{type_}s-{a}-{b}">{a}&ndash;{b}</h3>\n'
        body += f'<h4 id="{type_}-{i}">{row.name} ({row.key[:4]} {row.type})</h4>'  # type: ignore[index, str-bytes-safe]
        body += f"{i}.&ensp;({row.tunebooks})&ensp;"
        body += tune_to_html(d) + "\n"

html = (
    HEAD_SNIPPET
    + "<body>\n"
    + intro
    + '\n<div class="js-toc-content">\n'
    + body
    + "</div>\n"
    + RENDER_SNIPPET
    + TOC_SNIPPET
    + "</body>\n</html>"
)

with open("popular.html", "w", encoding="utf-8") as f:
    f.write(html)
