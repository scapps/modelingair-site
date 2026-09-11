#!/usr/bin/env python3
"""
build.py — generate the Atmospheric Modeling @ Drexel website from the academic vault.

Usage:
    python3 build.py                 # uses vault_path from site.yaml
    python3 build.py --vault PATH    # override the vault location
    python3 build.py --check         # list what would be published, write nothing

Everything public comes from two places:
  1. The vault (30-Record/ and 40-People/), filtered by the allowlist rules in
     PUBLISH RULES below and by an optional `web:` frontmatter flag.
  2. The content/ folder in this repo, for prose the vault does not hold
     (home-page research descriptions, legacy publications and alumni that
     predate the vault, contact details).

The output goes to docs/, which GitHub Pages serves.
"""

import argparse
import datetime as dt
import html
import re
import shutil
import sys
from pathlib import Path

import markdown
import yaml

HERE = Path(__file__).resolve().parent
CONFIG = yaml.safe_load((HERE / "site.yaml").read_text())
CONTENT = HERE / "content"
TEMPLATES = HERE / "templates"
OUT = HERE / "docs"

# ----------------------------------------------------------------------------
# PUBLISH RULES — the allowlist. Nothing outside these lists reaches the site.
# ----------------------------------------------------------------------------

# Publication statuses that appear, and the heading each one is grouped under.
PUB_STATUS = {
    "published": "published",
    "accepted": "in press",
    "in-press": "in press",
    "revision": "submitted",
    "in-review": "submitted",
    "submitted": "submitted",
}
# idea, in-prep, withdrawn never appear.

# Person roles that appear on the Team page. Colleagues, collaborators,
# letter-writers, chairs and staff never appear unless the note says web: true.
PEOPLE_ROLES = {"phd-student", "ms-student", "undergrad", "postdoc", "visiting-student", "highschool"}
CURRENT_STATUS = {"current", "prospective", "active"}

# Person fields that may be published. stipend, account, conflicted,
# lastcontact and the note body are never read for the site.
PEOPLE_FIELDS = {"role", "status", "degree", "affiliation", "start", "end", "placement", "coadvisor", "web_bio", "webbio"}

# Proposal statuses that appear on the Funding section.
PROPOSAL_STATUS = {"awarded"}

# Software statuses that appear.
SOFTWARE_STATUS = {"released", "in-development", "archived"}

ROLE_LABEL = {
    "phd-student": "Ph.D. student",
    "ms-student": "M.S. student",
    "undergrad": "Undergraduate researcher",
    "postdoc": "Postdoctoral researcher",
    "visiting-student": "Visiting student",
    "highschool": "High school researcher",
}

# ----------------------------------------------------------------------------
# Vault reading
# ----------------------------------------------------------------------------

FM_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)
WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")


class Note:
    def __init__(self, path: Path):
        self.path = path
        self.slug = path.stem
        text = path.read_text(encoding="utf-8")
        m = FM_RE.match(text)
        self.fm = {}
        if m:
            try:
                self.fm = yaml.safe_load(m.group(1)) or {}
            except yaml.YAMLError as e:
                warn(f"{path.name}: unreadable frontmatter ({e}); skipped")
                self.fm = {"_broken": True}
            self.body = text[m.end():]
        else:
            self.body = text
        # Normalise keys: the vault pads keys with spaces for alignment.
        self.fm = {str(k).strip(): v for k, v in self.fm.items()}

    def get(self, key, default=None):
        v = self.fm.get(key, default)
        if isinstance(v, str):
            v = v.strip()
        return default if v in ("", None) else v

    @property
    def web(self):
        """None if unset, True/False if the note carries a web: flag."""
        v = self.fm.get("web")
        if v is None:
            return None
        if isinstance(v, bool):
            return v
        return str(v).strip().lower() in ("true", "yes", "1")

    @property
    def title(self):
        m = re.search(r"^# (.+)$", self.body, re.M)
        return m.group(1).strip() if m else self.slug

    def section(self, name):
        """Return the text under a `## name` heading, or None."""
        m = re.search(rf"^## {re.escape(name)}\s*\n(.*?)(?=^## |\Z)", self.body, re.M | re.S)
        return m.group(1).strip() if m else None

    def first_paragraph(self):
        """First paragraph after the H1, with backtick editorial notes removed."""
        after = re.split(r"^# .+$", self.body, maxsplit=1, flags=re.M)
        text = after[1] if len(after) > 1 else self.body
        for para in re.split(r"\n\s*\n", text):
            p = para.strip()
            if not p or p.startswith("#") or p.startswith("`"):
                continue
            return p
        return ""

    def web_summary(self):
        """Prose to show for this note: a `## Web` section if present, else the first paragraph."""
        return self.section("Web") or self.first_paragraph()


def warn(msg):
    print(f"  ! {msg}", file=sys.stderr)


def load_notes(vault: Path, sub: str):
    d = vault / sub
    if not d.exists():
        warn(f"{sub} not found in vault")
        return []
    notes = []
    for p in sorted(d.glob("*.md")):
        n = Note(p)
        if n.fm.get("_broken"):
            continue
        notes.append(n)
    return notes


# ----------------------------------------------------------------------------
# Selection
# ----------------------------------------------------------------------------

def allowed(note: Note, rule: bool) -> bool:
    """Combine the allowlist rule with the note's own web: flag."""
    if note.web is False:
        return False
    if note.web is True:
        return True
    return rule


def select_publications(vault, people_by_slug):
    out = []
    for n in load_notes(vault, "30-Record/publications"):
        status = str(n.get("status", "")).lower()
        if not allowed(n, status in PUB_STATUS):
            continue
        group = PUB_STATUS.get(status, "published")
        cite = n.web_summary()
        cite = re.sub(r"\*\*(.+?)\*\*", r"\1", cite)          # drop bold
        cite = re.sub(r"\s*\n\s*", " ", cite)                  # unwrap lines
        # Mark group students with an asterisk, the convention on the old site.
        for link in n.fm.get("students") or []:
            for slug in WIKILINK_RE.findall(str(link)) or [str(link)]:
                person = people_by_slug.get(slug)
                surname = (person.title.split()[-1] if person else slug.split("-")[-1]).strip()
                cite = re.sub(rf"\b({re.escape(surname)}, [A-Z]\.(?: ?[A-Z]\.)*)", "\\1\u2042", cite, count=1, flags=re.I)  # placeholder, becomes * after markdown
        year = n.get("year") or (re.match(r"(\d{4})", n.slug) or [None, None])[1]
        out.append({
            "group": group,
            "year": int(year) if year else 0,
            "citation": cite,
            "doi": str(n.get("doi", "")).replace("https://doi.org/", ""),
            "venue": n.get("venue", ""),
            "slug": n.slug,
        })
    return out


def select_software(vault):
    out = []
    for n in load_notes(vault, "30-Record/software"):
        status = str(n.get("status", "")).lower()
        if not allowed(n, status in SOFTWARE_STATUS):
            continue
        out.append({
            "name": n.get("name") or n.title,
            "status": status,
            "summary": n.web_summary(),
            "repo": n.get("repo", ""),
            "doi": str(n.get("doi", "")).replace("https://doi.org/", ""),
            "license": n.get("license", ""),
            "release": str(n.get("release", "")),
        })
    return out


def select_talks(vault):
    out = []
    for n in load_notes(vault, "30-Record/talks"):
        if not allowed(n, True):
            continue
        date = str(n.get("date", ""))
        year = int(date[:4]) if re.match(r"\d{4}", date) else 0
        out.append({
            "title": n.title,
            "venue": n.get("venue", ""),
            "institution": n.get("institution", ""),
            "kind": str(n.get("kind", "")).replace("-", " "),
            "date": date,
            "year": year,
            "bygroup": bool(n.get("bygroup", False)),
        })
    out.sort(key=lambda t: t["date"], reverse=True)
    return out


def select_funding(vault):
    out = []
    for n in load_notes(vault, "30-Record/proposals"):
        status = str(n.get("status", "")).lower()
        if not allowed(n, status in PROPOSAL_STATUS):
            continue
        starts, ends = str(n.get("starts", "")), str(n.get("ends", ""))
        period = " – ".join(x[:4] for x in (starts, ends) if x and x != "None")
        out.append({
            "title": n.title,
            "agency": n.get("agency", ""),
            "program": n.get("program", ""),
            "role": n.get("role", ""),
            "period": period,
            "starts": starts,
            "area": n.get("area", "research"),
        })
    out.sort(key=lambda f: f["starts"], reverse=True)
    return out


def select_honors(vault):
    out = []
    for n in load_notes(vault, "30-Record/honors"):
        if not allowed(n, True):
            continue
        out.append({"title": n.title, "org": n.get("org", ""), "year": str(n.get("year", ""))})
    out.sort(key=lambda h: h["year"], reverse=True)
    return out


def select_people(vault):
    current, alumni, by_slug = [], [], {}
    home = CONFIG.get("home_affiliation", "Drexel")
    for n in load_notes(vault, "40-People"):
        by_slug[n.slug] = n
        role = str(n.get("role", "")).lower()
        affiliation = str(n.get("affiliation", ""))
        rule = role in PEOPLE_ROLES and home.lower() in affiliation.lower()
        if not allowed(n, rule):
            continue
        status = str(n.get("status", "")).lower()
        start, end = str(n.get("start", "")), str(n.get("end", ""))
        years = " – ".join(x[:4] for x in (start, end) if x and x != "None")
        if status in CURRENT_STATUS and years:
            years = f"{start[:4]} – present"
        person = {
            "name": n.title,
            "role": ROLE_LABEL.get(role, role.replace("-", " ").title()),
            "degree": n.get("degree", ""),
            "affiliation": "" if home.lower() in affiliation.lower() else affiliation,
            "years": years,
            "placement": WIKILINK_RE.sub(r"\1", str(n.get("placement", "") or "")).replace("-", " ").title()
                         if n.get("placement") and "[[" in str(n.get("placement")) else n.get("placement", ""),
            "bio": n.section("Web bio") or n.get("webbio") or n.get("web_bio") or "",
        }
        (current if status in CURRENT_STATUS else alumni).append(person)
    alumni.sort(key=lambda p: p["years"][-4:], reverse=True)
    return current, alumni, by_slug


# ----------------------------------------------------------------------------
# Rendering
# ----------------------------------------------------------------------------

def esc(s):
    return html.escape(str(s or ""), quote=True)


def md(text):
    return markdown.markdown(text or "", extensions=["smarty"])


def read_content(name):
    p = CONTENT / name
    return p.read_text(encoding="utf-8") if p.exists() else ""


def content_yaml(name):
    p = CONTENT / name
    return yaml.safe_load(p.read_text(encoding="utf-8")) or [] if p.exists() else []


def link(url, text=None):
    if not url:
        return ""
    return f'<a href="{esc(url)}">{esc(text or url)}</a>'


def doi_link(doi):
    return link(f"https://doi.org/{doi}", f"doi:{doi}") if doi else ""


DOI_IN_TEXT = re.compile(r"\s*(?:https?://doi\.org/|doi:\s*)10\.\S+?(?=[\s,;)]|$)\.?", re.I)


def cite_html(citation, doi):
    """Citation text as inline HTML: *italics* rendered, inline DOIs removed, one DOI link appended."""
    text = DOI_IN_TEXT.sub("", citation).strip()
    text = re.sub(r"\(\s*\)", "", text)                       # empty parentheses left behind
    text = re.sub(r"\s{2,}", " ", text)
    if not doi:
        m = DOI_IN_TEXT.search(citation)
        doi = re.sub(r"^(https?://doi\.org/|doi:\s*)", "", m.group(0).strip(), flags=re.I).rstrip(".") if m else ""
    inner = markdown.markdown(esc(text), extensions=["smarty"])
    inner = re.sub(r"^<p>|</p>$", "", inner.strip()).replace("\u2042", "*")
    return f"{inner} {doi_link(doi)}".strip()


def page(title, body, active):
    tpl = (TEMPLATES / "base.html").read_text(encoding="utf-8")
    nav = "".join(
        f'<a href="{href}"{" class=active" if key == active else ""}>{label}</a>'
        for key, href, label in CONFIG["nav"]
    )
    return (tpl.replace("{{title}}", esc(title))
               .replace("{{site_title}}", esc(CONFIG["site_title"]))
               .replace("{{tagline}}", esc(CONFIG["tagline"]))
               .replace("{{nav}}", nav)
               .replace("{{body}}", body)
               .replace("{{year}}", str(dt.date.today().year))
               .replace("{{built}}", dt.date.today().isoformat())
               .replace("{{css}}", (TEMPLATES / "style.css").read_text(encoding="utf-8")))


def render_home(data):
    body = [f'<section class="hero"><h1>{esc(CONFIG["site_title"])}</h1><p class="lead">{esc(CONFIG["tagline"])}</p></section>']
    body.append(f'<section class="prose">{md(read_content("home.md"))}</section>')
    # Recent news: newest published paper, newest talk, newest award.
    items = []
    pubs = [p for p in data["publications"] if p["group"] == "published"]
    if pubs:
        p = max(pubs, key=lambda x: x["year"])
        items.append(f'<li><span class="tag">Paper</span> {cite_html(p["citation"], p["doi"])}</li>')
    if data["talks"]:
        t = data["talks"][0]
        items.append(f'<li><span class="tag">Talk</span> {esc(t["title"])} — {esc(t["venue"])}, {esc(t["date"])}</li>')
    if data["funding"]:
        f = data["funding"][0]
        items.append(f'<li><span class="tag">Funding</span> {esc(f["title"])} ({esc(f["agency"])})</li>')
    if items:
        body.append('<section><h2>Recent</h2><ul class="news">' + "".join(items) + "</ul></section>")
    return page("Interests", "\n".join(body), "home")


def render_publications(data):
    pubs = data["publications"]
    body = ['<h1>Publications</h1>']
    scholar = CONFIG.get("scholar_url")
    if scholar:
        body.append(f'<p class="muted">{link(scholar, "Google Scholar profile")}. An asterisk marks a student or researcher in the group.</p>')
    pending = [p for p in pubs if p["group"] in ("submitted", "in press")]
    if pending:
        body.append('<h2>Submitted or in press</h2><ol class="pubs">')
        for p in sorted(pending, key=lambda x: -x["year"]):
            body.append(f'<li>{cite_html(p["citation"], p["doi"])} <span class="muted">({esc(p["group"])})</span></li>')
        body.append("</ol>")
    published = [p for p in pubs if p["group"] == "published"]
    legacy = content_yaml("legacy-publications.yaml")
    for item in legacy:
        published.append({"year": int(item["year"]), "citation": item["citation"], "doi": item.get("doi", ""), "group": "published"})
    years = sorted({p["year"] for p in published}, reverse=True)
    for y in years:
        body.append(f"<h2>{y}</h2><ol class=\"pubs\">")
        for p in [p for p in published if p["year"] == y]:
            body.append(f'<li>{cite_html(p["citation"], p["doi"])}</li>')
        body.append("</ol>")
    return page("Publications", "\n".join(body), "publications")


def render_research(data):
    body = ['<h1>Research</h1>', f'<section class="prose">{md(read_content("research.md"))}</section>']
    if data["software"]:
        body.append("<h2>Software</h2>")
        for s in data["software"]:
            meta = " · ".join(x for x in [
                link(s["repo"], "Repository") if s["repo"] else "",
                doi_link(s["doi"]),
                f"{esc(s['license'])} license" if s["license"] else "",
                f"Released {esc(s['release'])}" if s["release"] and s["release"] != "None" else "",
                "In development" if s["status"] == "in-development" else "",
            ] if x)
            body.append(f'<article class="card"><h3>{esc(s["name"])}</h3><div class="prose">{md(s["summary"])}</div><p class="meta">{meta}</p></article>')
    if data["funding"]:
        body.append("<h2>Funding</h2><ul class=\"list\">")
        for f in data["funding"]:
            src = ", ".join(x for x in [f["agency"], f["program"]] if x)
            role = f" — {esc(f['role'])}" if f["role"] and CONFIG.get("show_roles", True) else ""
            body.append(f'<li><strong>{esc(f["title"])}</strong><br><span class="muted">{esc(src)}{role}{" · " + esc(f["period"]) if f["period"] else ""}</span></li>')
        body.append("</ul>")
    if data["talks"]:
        body.append("<h2>Presentations</h2>")
        for y in sorted({t["year"] for t in data["talks"]}, reverse=True):
            body.append(f"<h3>{y}</h3><ul class=\"list\">")
            for t in [t for t in data["talks"] if t["year"] == y]:
                where = ", ".join(x for x in [t["venue"], t["institution"]] if x and x != t["venue"] or x == t["venue"])
                where = t["venue"] if not t["institution"] or t["institution"] == t["venue"] else f'{t["venue"]}, {t["institution"]}'
                flag = ' <span class="tag">group member</span>' if t["bygroup"] else ""
                body.append(f'<li>{esc(t["title"])}{flag}<br><span class="muted">{esc(where)} · {esc(t["kind"])} · {esc(t["date"])}</span></li>')
            body.append("</ul>")
    if data["honors"]:
        body.append("<h2>Honors</h2><ul class=\"list\">")
        for h in data["honors"]:
            body.append(f'<li>{esc(h["title"])} <span class="muted">— {esc(h["org"])}, {esc(h["year"])}</span></li>')
        body.append("</ul>")
    return page("Research", "\n".join(body), "research")


def person_card(p):
    lines = [f'<h3>{esc(p["name"])}</h3>', f'<p class="role">{esc(p["role"])}']
    if p.get("degree"):
        lines.append(f' · {esc(p["degree"])}')
    if p.get("years"):
        lines.append(f' · {esc(p["years"])}')
    lines.append("</p>")
    if p.get("affiliation"):
        lines.append(f'<p class="muted">{esc(p["affiliation"])}</p>')
    if p.get("placement"):
        lines.append(f'<p class="muted">Now: {esc(p["placement"])}</p>')
    if p.get("bio"):
        lines.append(f'<div class="prose">{md(p["bio"])}</div>')
    return '<article class="card person">' + "".join(lines) + "</article>"


def render_team(data):
    body = ["<h1>Team</h1>"]
    pi = CONFIG.get("pi", {})
    body.append('<h2>Principal investigator</h2>' + person_card({
        "name": pi.get("name", ""), "role": pi.get("title", ""), "bio": pi.get("bio", ""),
    }))
    if data["current"]:
        body.append('<h2>Current members</h2><div class="grid">' + "".join(person_card(p) for p in data["current"]) + "</div>")
    alumni = list(data["alumni"])
    for item in content_yaml("legacy-team.yaml"):
        alumni.append({"name": item["name"], "role": item.get("role", ""), "degree": item.get("degree", ""),
                       "years": str(item.get("years", "")), "placement": item.get("placement", ""), "bio": item.get("note", "")})
    if alumni:
        body.append('<h2>Alumni</h2><div class="grid">' + "".join(person_card(p) for p in alumni) + "</div>")
    return page("Team", "\n".join(body), "team")


def render_contact():
    return page("Contact", "<h1>Contact</h1><section class=\"prose\">" + md(read_content("contact.md")) + "</section>", "contact")


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------

def collect(vault: Path):
    current, alumni, by_slug = select_people(vault)
    return {
        "publications": select_publications(vault, by_slug),
        "software": select_software(vault),
        "talks": select_talks(vault),
        "funding": select_funding(vault),
        "honors": select_honors(vault),
        "current": current,
        "alumni": alumni,
    }


def report(data):
    print("Publishing from the vault:")
    for k in ("publications", "software", "talks", "funding", "honors", "current", "alumni"):
        print(f"  {k:13s} {len(data[k])}")
        for item in data[k]:
            label = item.get("citation") or item.get("title") or item.get("name")
            print(f"      - {label[:90]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", default=None)
    ap.add_argument("--check", action="store_true", help="report what would be published; write nothing")
    args = ap.parse_args()
    vault = Path(args.vault or CONFIG["vault_path"]).expanduser()
    if not vault.exists():
        sys.exit(f"Vault not found at {vault}. Set vault_path in site.yaml or pass --vault.")
    data = collect(vault)
    report(data)
    if args.check:
        return
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    (OUT / "index.html").write_text(render_home(data), encoding="utf-8")
    (OUT / "publications.html").write_text(render_publications(data), encoding="utf-8")
    (OUT / "research.html").write_text(render_research(data), encoding="utf-8")
    (OUT / "team.html").write_text(render_team(data), encoding="utf-8")
    (OUT / "contact.html").write_text(render_contact(), encoding="utf-8")
    (OUT / ".nojekyll").write_text("")
    if CONFIG.get("domain"):
        (OUT / "CNAME").write_text(CONFIG["domain"] + "\n")
    assets = HERE / "assets"
    if assets.exists():
        shutil.copytree(assets, OUT / "assets")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
