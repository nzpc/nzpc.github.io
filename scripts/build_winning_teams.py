#!/usr/bin/env python3
"""Generate the merged per-year WinningTeams<year>.html archive pages.

Single source of truth: each year's winner data in data/results/<year>.yaml,
augmented with:
  * team photos scraped from the ORIGINAL Word-exported WinningTeams pages
    (only 2020-2025 have those), stashed on first run in
    static/Scoreboards/<year>/_winning_source.html,
  * the category scoreboard content (a real DOMjudge <table class="scoreboard">
    or a set of Files/*.jpg screenshots) scraped from each category scoreboard
    page named in the YAML.

Output: a self-framed WinningTeams<year>.html with a switchable per-category
widget. Each category pane shows the winner card first, then a collapsible
scoreboard block. The standalone category pages are then redundant (removed by
scripts/cleanup_category_pages.py) and data links repoint to #anchors.

Re-runnable: photos + scoreboards are re-scraped from the stashed originals /
category pages every run, so editing the YAML or this template regenerates all
pages deterministically.
"""
import re
import sys
from pathlib import Path

import yaml
from bs4 import BeautifulSoup, Tag

ROOT = Path(__file__).resolve().parent.parent
SCOREBOARDS = ROOT / "static" / "Scoreboards"
DATA = ROOT / "data" / "results"
# Stash of the original Word WinningTeams pages, kept OUTSIDE static/ so Hugo
# never publishes it. Used to recover team photos/details on regeneration.
STASH_DIR = ROOT / "scripts" / ".winning_source"

YEARS = [str(y) for y in range(2015, 2026)]  # 2015..2025

# Canonical anchor id per category label (matches historical WinningTeams ids).
CATEGORY_ANCHOR = {
    "School": "School",
    "Tertiary Junior": "TJunior",
    "Tertiary Intermediate": "TIntermediate",
    "Tertiary Open": "TOpen",
    "Open": "Open",
}

# Map a category label -> the token used in original Word photo cells / filenames.
PHOTO_KEYS = {
    "School": ["school"],
    "Tertiary Junior": ["tertjunior", "tjunior", "junior"],
    "Tertiary Intermediate": ["tertint", "tintermediate", "intermediate"],
    "Tertiary Open": ["tertopen", "topen"],
    "Open": ["open"],
}

HEADER_HTML = """
<div class="nzpc-archive-header">
  <div class="nzpc-archive-inner">
    <a class="nzpc-archive-brand" href="/">
      <img src="/images/NZPC.png" alt="NZPC logo">
      <span>New Zealand Programming Contest</span>
    </a>
    <nav class="nzpc-archive-nav">
      <a href="/">Home</a>
      <a href="/register/">Registration</a>
      <a href="/documentation/">Documentation</a>
      <a href="/results/">Results</a>
    </nav>
  </div>
</div>
"""

FOOTER_HTML = """
<div class="nzpc-archive-footer">
  <div class="nzpc-archive-inner">
    Copyright &copy; 2023 to 2026 New Zealand Programming Contest.
  </div>
</div>
"""

WIDGET_SCRIPT = """
(function () {
  document.querySelectorAll('.nzpc-wt-widget').forEach(function (w) {
    var tabs = w.querySelectorAll('.nzpc-wt-tab');
    var panes = w.querySelectorAll('.nzpc-wt-pane');
    tabs.forEach(function (t) {
      t.addEventListener('click', function () {
        tabs.forEach(function (x) { x.classList.remove('nzpc-active'); });
        panes.forEach(function (p) { p.classList.remove('nzpc-active'); });
        t.classList.add('nzpc-active');
        var pane = w.querySelector('#' + t.getAttribute('data-target'));
        if (pane) pane.classList.add('nzpc-active');
        if (location.hash !== '#' + t.getAttribute('data-cat'))
          history.replaceState(null, '', '#' + t.getAttribute('data-cat'));
      });
    });
    // open the tab named in the URL hash, if any
    var h = (location.hash || '').replace('#', '');
    if (h) {
      var target = w.querySelector('.nzpc-wt-tab[data-cat="' + h + '"]');
      if (target) target.click();
    }
  });
})();
"""

FONT_LINKS = (
    '<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;'
    '0,9..144,600;0,9..144,700;1,9..144,400&family=Open+Sans:ital,wght@0,400;0,600;0,700;'
    '1,400&display=swap" rel="stylesheet"/>'
)


def load_year_data(year: str) -> dict | None:
    f = DATA / f"{year}.yaml"
    if not f.exists():
        return None
    return yaml.safe_load(f.read_text(encoding="utf-8"))


# Filename stems used by the standalone category scoreboard pages, by category.
CATEGORY_FILE_STEMS = {
    "School": ["School", "Scoreboard_School"],
    "Tertiary Junior": ["TertiaryJunior", "Scoreboard_Tertiary_Junior"],
    "Tertiary Intermediate": ["TertiaryIntermediate", "Scoreboard_Tertiary_Intermediate"],
    "Tertiary Open": ["TertiaryOpen", "Scoreboard_Tertiary_Open"],
    "Open": ["Open", "Scoreboard_Open"],
}


def category_scoreboard_file(year: str, category: str, scoreboard_url: str) -> Path | None:
    """Locate the ORIGINAL standalone category scoreboard page.

    We do NOT trust the YAML `scoreboard` field alone, because after link
    repointing it points at WinningTeams<year>.html#anchor (which would be
    circular). Instead resolve by filename convention within the year dir,
    trying .html then .htm. Fall back to the URL only if it is a real category
    page (not a WinningTeams anchor).
    """
    ydir = SCOREBOARDS / year
    for stem in CATEGORY_FILE_STEMS.get(category, []):
        for ext in (".html", ".htm"):
            p = ydir / f"{stem}{ext}"
            if p.exists():
                return p
    # Fallback: honour an explicit non-WinningTeams URL.
    if scoreboard_url and "WinningTeams" not in scoreboard_url and "#" not in scoreboard_url:
        p = ROOT / "static" / scoreboard_url.lstrip("/")
        if p.exists():
            return p
    return None


_PREV_CACHE: dict = {}


def prev_scoreboard(year: str, anchor: str) -> str:
    """Recover a previously-generated scoreboard body for a category, so the
    generator remains idempotent after the source category pages are deleted."""
    if year not in _PREV_CACHE:
        page = SCOREBOARDS / year / f"WinningTeams{year}.html"
        _PREV_CACHE[year] = (
            BeautifulSoup(page.read_text(encoding="utf-8", errors="replace"), "html.parser")
            if page.exists()
            else None
        )
    soup = _PREV_CACHE[year]
    if soup is None:
        return ""
    btn = soup.find("button", attrs={"data-cat": anchor})
    if not btn:
        return ""
    pane = soup.find(id=btn.get("data-target"))
    if not pane:
        return ""
    body = pane.find("div", class_="nzpc-wt-scoreboard-body")
    return body.decode_contents() if body else ""


def stash_original(year: str) -> BeautifulSoup | None:
    """Return the ORIGINAL WinningTeams markup for photo scraping.

    First run: read the live WinningTeams<year>.html and stash it. Later runs:
    read from the stash so regeneration is idempotent even after we overwrite
    the page with the generated widget.
    """
    STASH_DIR.mkdir(parents=True, exist_ok=True)
    stash = STASH_DIR / f"{year}.html"
    live = SCOREBOARDS / year / f"WinningTeams{year}.html"
    if stash.exists():
        return BeautifulSoup(stash.read_text(encoding="utf-8", errors="replace"), "html.parser")
    if not live.exists():
        return None
    text = live.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(text, "html.parser")
    # The redesign step may have already run: the pristine Word table is then
    # preserved inside <template id="nzpc-wt-source">. Recover it from there.
    tpl = soup.find("template", id="nzpc-wt-source")
    if tpl is not None:
        inner = tpl.decode_contents()
        stash.write_text(inner, encoding="utf-8")
        return BeautifulSoup(inner, "html.parser")
    if "nzpc-wt-widget" in text:
        # Generated but no recoverable source.
        return None
    stash.write_text(text, encoding="utf-8")
    return soup


def scrape_details(year: str) -> dict:
    """category-label -> {lines, notes, img_src, img_alt} from the original page.

    The original Word WinningTeams pages carry richer detail (member names,
    red-highlighted notes, photos) than the YAML, so prefer them for 2020-2025.
    Keyed by base category; the first matching row per category wins.
    """
    soup = stash_original(year)
    out = {}
    if soup is None:
        return out
    table = soup.find("table")
    if table is None:
        return out
    for tr in table.find_all("tr"):
        tds = tr.find_all("td", recursive=False)
        if not tds or tds[0].get("colspan"):
            continue
        details_td = tds[0]
        photo_td = tds[1] if len(tds) > 1 else None
        anchor = details_td.find("a", id=True)
        ps = details_td.find_all("p")
        heading = " ".join(ps[0].get_text(" ", strip=True).split()) if ps else ""
        label = None
        for cat in CATEGORY_ANCHOR:
            if heading.lower().startswith(cat.lower()):
                label = cat
                break
        if not label and anchor:
            aid = anchor.get("id", "")
            for cat, anc in CATEGORY_ANCHOR.items():
                if aid.rstrip("2") == anc:
                    label = cat
                    break
        if not label or label in out:
            continue

        raw_lines, notes = [], []
        for j, p in enumerate(ps):
            if p.find("a", href=re.compile(r"#Menu")):
                continue
            txt = " ".join(p.get_text(" ", strip=True).split())
            if not txt or (j == 0 and txt == heading):
                continue
            if "color:red" in (p.get("style") or "").lower():
                notes.append(txt)
            else:
                raw_lines.append(txt)

        # Malformed Word nesting can make one <p> swallow its siblings, then the
        # siblings repeat standalone. For each blob, strip out any other line's
        # text that also appears standalone, keeping only the blob's unique
        # remainder. Then de-duplicate.
        others = list(raw_lines)
        lines = []
        for t in raw_lines:
            remainder = t
            for o in others:
                if o != t and o in remainder:
                    remainder = remainder.replace(o, " ")
            remainder = " ".join(remainder.split())
            if remainder and remainder not in lines:
                lines.append(remainder)

        img = None
        if photo_td:
            for cand in photo_td.find_all("img"):
                src = cand.get("src") or ""
                if src and "image004" not in src:
                    img = cand
                    break
        out[label] = {
            "lines": lines,
            "notes": notes,
            "img_src": img.get("src") if img else None,
            "img_alt": (img.get("alt") or f"{label} winners") if img else None,
        }
    return out


def extract_scoreboard(page: Path) -> tuple[str, list[str]]:
    """Return (inner_html, extra_css_hrefs) for a category scoreboard page.

    inner_html is either a restyled DOMjudge <table class="scoreboard"> or a
    sequence of <img> screenshots, resolved to absolute /Scoreboards/... URLs.
    """
    soup = BeautifulSoup(page.read_text(encoding="utf-8", errors="replace"), "html.parser")
    year_dir = f"/Scoreboards/{page.parent.name}/"

    def absolutise(src: str) -> str:
        src = src.lstrip()
        if src.startswith(("http://", "https://", "/")):
            return src
        return year_dir + src.lstrip("./")

    table = soup.find("table", class_="scoreboard")
    if table is not None:
        # Unwrap team links: the old external DOMjudge server is gone, so the
        # hrefs 404. Keep the team-name text, drop the dead link.
        for a in table.find_all("a"):
            a.unwrap()
        for im in table.find_all("img", src=True):
            im["src"] = absolutise(im["src"])
        for span in table.select("span.heart"):
            span.decompose()
        return str(table), []

    # Otherwise gather screenshot images from the content area.
    imgs = []
    for img in soup.find_all("img"):
        src = img.get("src") or ""
        low = src.lower()
        if "nzpc_logo" in low or "/images/nzpc" in low or not src:
            continue  # skip banner / site logo
        if "files/" in low or low.endswith((".jpg", ".jpeg", ".png", ".gif")):
            imgs.append(f'<img src="{absolutise(src)}" alt="{img.get("alt") or "Scoreboard"}" loading="lazy"/>')
    return "\n".join(imgs), []


def build_page(year: str, data: dict) -> str | None:
    winners = data.get("winners") or []
    if not winners:
        return None
    details = scrape_details(year)  # richer info from original pages (2020-2025)

    tabs, panes = [], []
    for i, w in enumerate(winners):
        cat = w.get("category", "Winners")
        anchor = CATEGORY_ANCHOR.get(cat, re.sub(r"\W+", "", cat))
        pid = f"wt-{year}-{i}"
        active = " nzpc-active" if i == 0 else ""
        orig = details.get(cat, {})

        tabs.append(
            f'<button class="nzpc-wt-tab{active}" type="button" role="tab" '
            f'data-target="{pid}" data-cat="{anchor}">{cat}</button>'
        )

        # Winner card: prefer the richer original lines/notes, else YAML.
        lines = []
        notes = []
        if orig.get("lines"):
            lines = [f'<p>{t}</p>' for t in orig["lines"]]
            notes = list(orig.get("notes") or [])
        else:
            if w.get("team"):
                lines.append(f'<p>{w["team"]}</p>')
            if w.get("institution"):
                lines.append(f'<p>{w["institution"]}</p>')
            if w.get("points") is not None:
                lines.append(f'<p>{w["points"]} points</p>')
        if w.get("note"):
            notes.append(w["note"])
        note_html = "".join(f'<p class="nzpc-wt-note">{n}</p>' for n in notes)

        if orig.get("img_src"):
            media = f'<img src="{orig["img_src"]}" alt="{orig["img_alt"]}" loading="lazy"/>'
        else:
            media = '<div class="nzpc-wt-nophoto">No photograph available</div>'

        # Scoreboard block. Prefer the original category page; if it has been
        # deleted, recover the block we generated on a previous run so the
        # script stays idempotent after cleanup.
        sb_html, _ = "", []
        sb_file = category_scoreboard_file(year, cat, w.get("scoreboard", ""))
        if sb_file is not None:
            sb_html, _ = extract_scoreboard(sb_file)
        if not sb_html:
            sb_html = prev_scoreboard(year, anchor)
        scoreboard_block = ""
        if sb_html:
            scoreboard_block = (
                '<details class="nzpc-wt-scoreboard">'
                f'<summary>{cat} scoreboard</summary>'
                f'<div class="nzpc-wt-scoreboard-body">{sb_html}</div>'
                "</details>"
            )

        panes.append(
            f'<div class="nzpc-wt-pane{active}" id="{pid}" role="tabpanel">'
            '<div class="nzpc-wt-card">'
            f'<div class="nzpc-wt-info"><h2 class="nzpc-wt-cat">{cat}</h2>'
            f'{"".join(lines)}{note_html}</div>'
            f'<div class="nzpc-wt-media">{media}</div>'
            "</div>"
            f"{scoreboard_block}"
            "</div>"
        )

    date_text = data.get("dateText")
    subtitle = f'<p class="nzpc-wt-subtitle">Held on {date_text}.</p>' if date_text else ""

    widget = (
        '<div class="nzpc-wt-widget">'
        f'<h1 class="nzpc-wt-title">NZPC {year} \u2014 Winning Teams</h1>'
        f"{subtitle}"
        f'<div class="nzpc-wt-tabs" role="tablist">{"".join(tabs)}</div>'
        f'<div class="nzpc-wt-panes">{"".join(panes)}</div>'
        "</div>"
    )

    html = (
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
        '<meta charset="utf-8"/>\n'
        '<meta content="width=device-width, initial-scale=1" name="viewport"/>\n'
        f"<title>NZPC {year} \u2014 Winning Teams</title>\n"
        '<link href="/favicon.ico" rel="icon" sizes="any"/>\n'
        '<link href="/apple-touch-icon.png" rel="apple-touch-icon"/>\n'
        f"{FONT_LINKS}\n"
        '<link href="/style/overrides.css" rel="stylesheet"/>\n'
        "</head>\n<body>\n"
        f"{HEADER_HTML}\n{widget}\n{FOOTER_HTML}\n"
        f"<script>{WIDGET_SCRIPT}</script>\n"
        "</body>\n</html>\n"
    )
    return html


def main():
    written = 0
    for year in YEARS:
        data = load_year_data(year)
        if not data:
            print(f"  skip {year}: no data", file=sys.stderr)
            continue
        html = build_page(year, data)
        if html is None:
            print(f"  skip {year}: no winners", file=sys.stderr)
            continue
        out = SCOREBOARDS / year / f"WinningTeams{year}.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")
        written += 1
        print(f"generated: {out.relative_to(ROOT)}")
    print(f"\n{written} WinningTeams pages generated.")


if __name__ == "__main__":
    main()
