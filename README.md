# New Zealand Programming Contest

The website for the New Zealand Programming Contest (NZPC), published to
[nzpc.github.io](https://nzpc.github.io/).

Built with the [Hugo](https://gohugo.io/) static site generator. Styling is
plain CSS layered over Bootstrap 5 (loaded from a CDN); there is no SCSS build
step. The brand palette is deep indigo `#1a2156` (primary) and warm red
`#c03b2f` (secondary), with Fraunces for headings and Libertinus Serif for body
text (both from Google Fonts).

The site is **information-driven**: most content lives in central data files
(`config.toml` and `data/`), and templates render it. To change what the site
says, you usually edit a data file, not HTML.

---

## Where things live

| Path | What it is |
|------|-----------|
| `config.toml` | Site-wide settings and the central **params** store (contest year/date, DOMjudge URL, logo, copyright). |
| `data/` | The information store: categories, sites, and per-year results. Editing these updates the site. |
| `content/` | The pages. `.md` and `.html` files become pages; Hugo maps e.g. `content/register/index.html` to `/register/`. |
| `layouts/` | Templates. `partials/` are shared building blocks; `shortcodes/` are widgets you drop into content with `{{< name >}}`. |
| `static/` | Copied to the site unchanged. Includes `images/`, PDFs (`ProblemSets/`, `Editorials/`), the CSS (`style/overrides.css`), and the `Scoreboards/` archive. |
| `scripts/` | One-off / maintenance Python scripts for the scoreboard archive (see below). |

All custom styling is in a single file: `static/style/overrides.css`.

---

## How to update common things

### Contest year, date, key URLs, logo
Edit `config.toml` under `[params]`. These values flow to every page
(e.g. the home hero date, the DOMjudge link). In content you can print any
param with `{{< siteparam "contestDateText" >}}`.

### Contest sites and site directors
Edit `data/sites.yaml`. One entry per site drives **both** the Sites table and
the Registration contact table. Each entry has `site`, `host`,
`director` (`name`, `email`), and an optional `localPage`.

### Categories and entry fees
Edit `data/categories.yaml` (one entry per category: `name`, `description`,
`fee`). This drives the Categories table.

### Adding or updating a results year
Everything for a contest year is one file: `data/results/<year>.yaml`.

1. Create `data/results/<year>.yaml`. Minimum shape:

   ```yaml
   year: 2026
   dateText: Saturday 8 August 2026         # optional
   problemsPDF: /ProblemSets/NZPC_2026.pdf   # optional; adds a "Contest Problems" tab
   statisticsPDF: /Editorials/2026/Statistics.pdf  # optional; adds a "Statistics" tab
   editorials:                               # optional; one tab per entry
     - label: 3 and 10 points
       url: /Editorials/2026/Editorials3-10.pdf
   winners:
     - category: School                      # School | Tertiary Junior |
       team: Example Team                     #   Tertiary Intermediate |
       institution: Example School            #   Tertiary Open | Open
       points: 123                            # optional
       note: "Optional highlighted note"      # optional
       scoreboard: /Scoreboards/2026/WinningTeams2026.html#School
   ```

2. Put any PDFs in `static/ProblemSets/` and `static/Editorials/<year>/`.

3. That's it — the results **index** (`/results/`) and the year page
   (`/results/2026/`) are generated automatically from the data file. You do
   **not** need to create a content page; `content/results/_content.gotmpl`
   builds one page per year, rendered by `layouts/results/single.html`.

The year page shows a tabbed widget: **Winners**, **Contest Problems**, one tab
per **Editorial** document, and **Statistics**. The `scoreboard` link points at
the merged Winning Teams page anchor for that category (see below).

### Editing a normal page (Home, Registration, Documentation, Rules, Guides)
Edit the matching file in `content/`. Pages are composed from small widgets via
shortcodes, e.g. the Registration page uses `{{< registration-table >}}`.
Available shortcodes (in `layouts/shortcodes/`):

| Shortcode | Renders |
|-----------|---------|
| `{{< siteparam "key" >}}` | A value from `config.toml [params]`. |
| `{{< home-features >}}` | Home page quick-link cards. |
| `{{< categories-table >}}` | Categories/fees table from `data/categories.yaml`. |
| `{{< sites-table >}}` | Sites table from `data/sites.yaml`. |
| `{{< registration-table >}}` | Registration contact table from `data/sites.yaml`. |
| `{{< contest-docs >}}` | Documentation card grid (rules + guides). |
| `{{< results-index >}}` | The results archive landing content. |

---

## The Scoreboards archive

`static/Scoreboards/<year>/` holds one **Winning Teams** page per year
(`WinningTeams<year>.html`). Each is a self-contained page (site header/footer
baked in) with a switchable tab per category. Each category tab shows the
winning team, then a collapsible scoreboard (an old DOMjudge HTML table for
2015–2021, or screenshot images for 2022–2025).

These pages are **generated** by `scripts/build_winning_teams.py` from:

* `data/results/<year>.yaml` (winner details, category order), and
* team photos / scoreboards recovered from the original archived pages
  (stashed under `scripts/.winning_source/`).

You normally don't edit the generated HTML by hand. To regenerate after
changing data or the script:

```sh
python3 scripts/build_winning_teams.py
```

`scripts/repoint_result_links.py` is a helper that rewrites each
`data/results/*.yaml` `scoreboard:` link to the merged
`WinningTeams<year>.html#<anchor>` form; run it if you add a year and want the
links normalised.

---

## Building and previewing locally

Hugo is not required to be installed locally — a Docker image is used.

Preview server (live reload at <http://localhost:1313/>):

```sh
docker run --rm -u "$(id -u):$(id -g)" -v "$PWD":/src -w /src \
  -p 1313:1313 hugomods/hugo:std \
  hugo server --bind 0.0.0.0 --baseURL http://localhost:1313/
```

One-off production build into `public/`:

```sh
rm -f .hugo_build.lock
docker run --rm -u "$(id -u):$(id -g)" -v "$PWD":/src -w /src \
  hugomods/hugo:std hugo --minify
```

`.devcontainer/` and `.vscode/` support previewing inside VS Code with Docker.

## Deployment

Pushing to the repository triggers the GitHub Actions workflow in `.github/`,
which builds the site with Hugo and publishes it to GitHub Pages. `CNAME` sets
the custom domain.

## Notes

* Hugo ≥ 0.164 blocks `text/html` content by default; `config.toml` enables it
  with `[security] allowContent = ['.*']` — keep this.
* `public/` and `public_check/` are build outputs and are git-ignored.
