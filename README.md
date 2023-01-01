# New Zealand Programming Contest

The site at [nzpc.github.io] began as a `wget` mirror of the site hosted at AUT.

The HTML and CSS has been redone from base Bootstrap 5 CSS. (The CDN source is used rather than hosting a customised Bootstrap CSS within this website.)

The site is built using the Hugo static site generator (SSG).

## Some key files and folders

* `content/`---contains the material that Hugo dynamically transforms into HTML (usually into `public/` by default).
  * Files of type `.html` are embedded in header/footer. Files of type `.md` are also first converted to HTML from Markdown.* Note that Hugo does some URL mapping, e.g., `content/results/2018.html` actually appears at `/results/2018/` on the site that gets generated.
* `layouts/`---contains header/footer code used in built HTML pages, and also contains the custom 404 error page.
* `static/`---these files get mixed into the generated website, but unlike material from `content/`, this content is copied over unmodified by Hugo.
* `.github/`---contains the Git commit hooks to build the website and update GitHub Pages
* (optional) `.devcontainer/` and `.vscode/`---I use this to preview changes I am making locally within Visual Studio Code, using Hugo running on Docker Desktop.