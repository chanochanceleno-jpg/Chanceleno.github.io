#!/usr/bin/env python3
"""Contrôles automatiques du site généré (_site/), lancés avant chaque mise en ligne.

    python3 tools/check.py

S'arrête avec une erreur si : un lien interne est cassé, une page n'a pas la politique de sécurité (CSP),
contient un script en ligne ou l'adresse email en clair, n'a pas exactement un titre h1, si les liens entre
langues (hreflang) ne sont pas réciproques ou si le plan du site (sitemap.xml) est incohérent.
"""
import html
import os
import re
import sys
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "_site")
DOMAIN = "https://chanceleno.com"
EMAIL = "contact@chanceleno.com"
IGNORED = {"google8a6c94d578320138.html"}   # fichier de vérification Google, servi tel quel


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.ids, self.alts, self.metas, self.scripts, self.handlers = [], set(), {}, {}, [], []
        self.h1 = 0
        self.canonical = None
        self.title = ""
        self._in_title = False
        self._script = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        for k in a:
            if k.startswith("on"):
                self.handlers.append("%s %s" % (tag, k))
        if tag == "h1":
            self.h1 += 1
        if tag == "title":
            self._in_title = True
        if tag == "a" and a.get("href"):
            self.links.append(a["href"])
        if tag in ("link", "script", "img") and (a.get("href") or a.get("src")):
            if not (tag == "link" and a.get("rel") in ("canonical", "alternate")):
                self.links.append(a.get("href") or a.get("src"))
        if tag == "link" and a.get("rel") == "alternate" and a.get("hreflang"):
            self.alts[a["hreflang"]] = a["href"]
        if tag == "link" and a.get("rel") == "canonical":
            self.canonical = a["href"]
        if tag == "meta":
            k = a.get("name") or a.get("property") or a.get("http-equiv")
            if k:
                self.metas[k] = a.get("content", "")
        if tag == "script":
            self._script = a

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag == "script":
            self._script = None

    def handle_data(self, d):
        if self._in_title:
            self.title += d
        if self._script is not None and d.strip() and "src" not in self._script and self._script.get("type") != "application/ld+json":
            self.scripts.append(d.strip()[:60])


def target(path):
    """Fichier servi par GitHub Pages pour une adresse du site, ou None."""
    p = os.path.join(OUT, unquote(path).lstrip("/"))
    if path.endswith("/"):
        p = os.path.join(p, "index.html")
    if os.path.isfile(p):
        return p
    if os.path.isfile(os.path.join(p, "index.html")):
        return os.path.join(p, "index.html")
    return None


def allowed_origins():
    """Seuls domaines externes autorisés par la CSP : FormSubmit (formulaires) et le compte GoatCounter configuré."""
    import yaml
    with open(os.path.join(ROOT, "config", "site.yml"), encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    code = str((cfg.get("statistiques") or {}).get("goatcounter") or "").strip()
    return {"https://formsubmit.co"} | ({"https://%s.goatcounter.com" % code} if code else set())


def main():
    if not os.path.isdir(OUT):
        sys.exit("Lancer d'abord : python3 tools/build.py")
    errors = []
    allowed = allowed_origins()
    pages = {}
    for d, _, files in os.walk(OUT):
        for f in files:
            full = os.path.join(d, f)
            rel = "/" + os.path.relpath(full, OUT).replace(os.sep, "/")
            if f.endswith((".html", ".js", ".css", ".xml", ".txt", ".json")):
                txt = open(full, encoding="utf-8").read()
                if EMAIL in txt and rel != "/.well-known/security.txt":
                    errors.append("%s : adresse email en clair" % rel)
            if f.endswith(".html") and f not in IGNORED:
                p = Page()
                p.feed(open(full, encoding="utf-8").read())
                url = rel[:-len("index.html")] if rel.endswith("/index.html") else rel
                pages[url] = p
    for url, p in pages.items():
        csp = p.metas.get("Content-Security-Policy", "")
        if "script-src 'self'" not in csp or "form-action 'self' https://formsubmit.co" not in csp:
            errors.append("%s : politique de sécurité (CSP) absente ou incomplète" % url)
        extra = set(re.findall(r"https://[^\s;]+", csp)) - allowed
        if extra:
            errors.append("%s : domaine externe non prévu dans la CSP %s" % (url, sorted(extra)))
        if p.metas.get("referrer") != "strict-origin-when-cross-origin":
            errors.append("%s : balise referrer absente" % url)
        if p.scripts:
            errors.append("%s : script en ligne interdit par la CSP (%s)" % (url, p.scripts[0]))
        if p.handlers:
            errors.append("%s : attribut on…= interdit par la CSP (%s)" % (url, p.handlers[0]))
        if p.h1 != 1:
            errors.append("%s : %d titre(s) h1 au lieu d'un" % (url, p.h1))
        if not p.title.strip():
            errors.append("%s : pas de <title>" % url)
        indexable = "noindex" not in p.metas.get("robots", "")
        if indexable:
            if len(p.metas.get("description", "")) < 40:
                errors.append("%s : description absente ou trop courte" % url)
            if p.canonical != DOMAIN + url:
                errors.append("%s : canonical incorrect (%s)" % (url, p.canonical))
            if set(p.alts) != {"fr", "en", "pt", "x-default"}:
                errors.append("%s : liens hreflang incomplets %s" % (url, sorted(p.alts)))
            for l, h in p.alts.items():
                other = pages.get(urlsplit(h).path)
                if other is None:
                    errors.append("%s : hreflang %s vers une page absente (%s)" % (url, l, h))
                elif l != "x-default" and other.alts.get(_lang(url, p)) != DOMAIN + url:
                    errors.append("%s : hreflang %s non réciproque (%s)" % (url, l, h))
        for link in p.links:
            u = urlsplit(html.unescape(link))
            if u.scheme or link.startswith(("mailto:", "tel:", "//")):
                continue
            if u.path.startswith("/"):
                t = target(u.path)
                if not t:
                    errors.append("%s : lien cassé %s" % (url, link))
                elif u.fragment and t.endswith(".html"):
                    other = pages.get(u.path) or pages.get(u.path.rstrip("/") + "/")
                    if other and u.fragment not in other.ids:
                        errors.append("%s : ancre introuvable %s" % (url, link))
            elif u.fragment and not u.path and u.fragment not in p.ids and link != "#":
                errors.append("%s : ancre introuvable %s" % (url, link))
    # plan du site
    sm = open(os.path.join(OUT, "sitemap.xml"), encoding="utf-8").read()
    locs = [urlsplit(x).path for x in re.findall(r"<loc>([^<]+)</loc>", sm)]
    for loc in locs:
        if loc not in pages:
            errors.append("sitemap.xml : %s n'existe pas" % loc)
    for url, p in pages.items():
        if "noindex" not in p.metas.get("robots", "") and url not in locs:
            errors.append("sitemap.xml : page indexable absente %s" % url)
    for f in (".well-known/security.txt", "robots.txt", "CNAME", "404.html", IGNORED.copy().pop()):
        if not os.path.isfile(os.path.join(OUT, f)):
            errors.append("fichier manquant : %s" % f)
    if errors:
        print("ERREUR : %d problème(s) dans le site généré :" % len(errors))
        for e in errors:
            print("  - " + e)
        sys.exit(1)
    print("Contrôles OK : %d pages, %d dans le plan du site." % (len(pages), len(locs)))


def _lang(url, p):
    for l, h in p.alts.items():
        if l != "x-default" and urlsplit(h).path == url:
            return l
    return None


if __name__ == "__main__":
    main()
