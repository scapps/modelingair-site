# modelingair.com

The website for Atmospheric Modeling @ Drexel, generated from the Obsidian academic vault. Nothing on the site is written twice: record notes in the vault are the source, and the site is a view over them.

## How it works

`build.py` reads the vault, applies the publishing rules below, and writes static HTML to `docs/`. GitHub Pages serves `docs/` at modelingair.com. Editorial prose that the vault does not hold (the home-page research descriptions, contact details, and alumni or papers that predate the vault) lives in `content/` and `site.yaml` in this repository.

## Updating the site

Run `./update.sh` from this folder. It rebuilds the site from the vault, commits the result, and pushes it; GitHub Pages refreshes within a minute or two. `python3 build.py --check` prints what would be published without writing anything, which is the quick way to confirm that a new record note will appear.

One-time setup on a new computer: `pip3 install -r requirements.txt`, and confirm that `vault_path` in `site.yaml` points at the vault.

## What is published

Only these vault notes reach the site, and only these fields of them.

| Vault folder | Published when | Shown |
|---|---|---|
| `30-Record/publications/` | `status` is published, accepted, in-press, submitted, in-review, or revision | The citation paragraph under the H1 (or a `## Web` section), `doi`, `year`; students named in `students:` get an asterisk |
| `30-Record/software/` | `status` is released, in-development, or archived | `name`, the first paragraph (or `## Web`), `repo`, `doi`, `license`, `release` |
| `30-Record/talks/` | always | H1, `venue`, `institution`, `kind`, `date`, `bygroup` |
| `30-Record/proposals/` | `status` is awarded | H1, `agency`, `program`, `role`, `starts`/`ends` years. Never `amount` or `account` |
| `30-Record/honors/` | always | H1, `org`, `year` |
| `40-People/` | `role` is a student or postdoc role and `affiliation` contains Drexel | H1, `role`, `degree`, `start`/`end` years, `placement`, and a `## Web bio` section if one exists. The note body is otherwise never read, so `## Who`, `stipend`, `account`, and `conflicted` never leave the vault |

Two frontmatter flags override the rules for any note: `web: false` hides a note the rules would publish, and `web: true` publishes one they would skip (for example, a colleague on the Team page or an in-preparation paper you want listed).

A `## Web` section in a record note, or `## Web bio` in a person note, replaces the automatically chosen paragraph, so public-facing wording can be tuned without touching the record itself.

## Pre-vault material

The vault's record layer starts around 2022, so the earlier body of work comes from the CV (`CV_9_26.docx`) and lives in `content/legacy-*.yaml`: publications 1–33, earlier funding, invited and student presentations, honors, all research mentees, and GEOS-Chem-hyd (which has no vault software note yet). The generator merges these with the vault and skips any legacy entry that matches a vault note (by DOI for publications, by name for people and software, by title for talks, funding, and honors), so giving something a vault note never produces a duplicate and never requires editing a legacy file. The legacy files are the place to fix a typo in an old entry; they are not the place to add new work, which belongs in the vault.

## Layout

```
build.py            the generator
update.sh           rebuild, commit, push
site.yaml           title, tagline, domain, PI block, navigation, vault path
content/            home.md, research.md, contact.md, legacy-*.yaml
templates/          base.html and style.css
assets/             images and other static files, copied into docs/assets/
docs/               generated output, served by GitHub Pages (do not edit by hand)
```

## First deployment

1. Create a GitHub repository (for example `modelingair-site`) and push this folder to it.
2. In the repository settings, under Pages, set the source to the `main` branch and the `/docs` folder.
3. The site is served at `https://<username>.github.io/modelingair-site/`. The pages use relative links, so no path configuration is needed.
