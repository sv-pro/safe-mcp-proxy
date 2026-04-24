# Publishing

This page explains how to build and deploy the wiki as a static site.

The wiki is built with [mkdocs](https://www.mkdocs.org/) and the [mkdocs-material](https://squidfunk.github.io/mkdocs-material/) theme. Configuration lives in `mkdocs.yml` at the repo root. Doc-only dependencies are in `requirements-docs.txt` — they are separate from the runtime project and not required to run the proxy.

## Local preview

```bash
pip install -r requirements-docs.txt
mkdocs serve
```

Visit http://localhost:8000. Changes to `wiki/` files are reflected live.

## Deploy to Vercel

1. Connect the repository to a Vercel project.
2. Leave framework preset as **Other**.
3. Vercel reads `vercel.json` automatically:
   - Build command: `pip install -r requirements-docs.txt && mkdocs build`
   - Output directory: `site`
4. Deploy. No further configuration needed.

Every push to the tracked branch triggers a new deployment.

## Deploy to GitHub Pages

```bash
pip install -r requirements-docs.txt
mkdocs gh-deploy
```

This builds the site and force-pushes to the `gh-pages` branch. Enable GitHub Pages in repository settings pointing at that branch.

## Known limitation — wikilinks

Wiki pages use `[[page-name]]` cross-reference syntax (Obsidian-style). This syntax is used for AI navigation and is not parsed by mkdocs — it renders as literal text `[[page-name]]` in the published HTML.

The published site is a human-readable reference. AI consumers navigate via the raw markdown files directly.

## Build output

The build writes to `site/` at the repo root. This directory is listed in `.gitignore` and should not be committed.
