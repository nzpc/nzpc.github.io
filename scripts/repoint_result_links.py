#!/usr/bin/env python3
"""Repoint data/results/<year>.yaml scoreboard links to the merged WinningTeams
tab anchors, and drop the now-redundant teamAnchor lines.

Category scoreboards are merged into WinningTeams<year>.html#<anchor>, so both
`scoreboard:` and `teamAnchor:` should point there. We rewrite `scoreboard:` to
the anchor and remove `teamAnchor:` (the results-table shortcode now emits a
single link).

Edits the YAML textually to preserve comments / formatting / ordering.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "results"

CATEGORY_ANCHOR = {
    "School": "School",
    "Tertiary Junior": "TJunior",
    "Tertiary Intermediate": "TIntermediate",
    "Tertiary Open": "TOpen",
    "Open": "Open",
}


def main():
    for f in sorted(DATA.glob("*.yaml")):
        year = f.stem
        lines = f.read_text(encoding="utf-8").splitlines()
        out = []
        current_cat = None
        for line in lines:
            cat_m = re.match(r"\s*-?\s*category:\s*(.+?)\s*$", line)
            if cat_m:
                current_cat = cat_m.group(1).strip().strip('"').strip("'")
            if re.match(r"\s*teamAnchor:\s*", line):
                # drop redundant teamAnchor line
                continue
            sb_m = re.match(r"(\s*)scoreboard:\s*(.+?)\s*$", line)
            if sb_m and current_cat in CATEGORY_ANCHOR:
                indent = sb_m.group(1)
                anchor = CATEGORY_ANCHOR[current_cat]
                new = f"{indent}scoreboard: /Scoreboards/{year}/WinningTeams{year}.html#{anchor}"
                out.append(new)
                continue
            out.append(line)
        f.write_text("\n".join(out) + "\n", encoding="utf-8")
        print(f"repointed: {f.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
