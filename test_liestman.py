from tempfile import NamedTemporaryFile
from webbrowser import open_new_tab

from trad_setlist_helper import get_member_sets
from trad_setlist_helper.html import setlist_to_html

member_id = 23280

setlist = get_member_sets(member_id)

html = setlist_to_html(setlist)
with NamedTemporaryFile(
    "w",
    suffix=".html",
    delete=False,
    encoding="utf-8",
) as f:
    f.write(html)
    open_new_tab(f.name)
