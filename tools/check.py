#!/usr/bin/env python3
"""Contrôles automatiques du site généré (_site/), lancés avant chaque mise en ligne.

    python3 tools/check.py

S'arrête avec une erreur si : un lien interne est cassé, une page n'a pas la politique de sécurité (CSP),
contient un script en ligne ou l'adresse email en clair, n'a pas exactement un titre h1, si les liens entre
langues (hreflang) ne sont pas réciproques, si le plan du site (sitemap.xml) est incohérent, si un marqueur {{nom}}
n'a pas été remplacé ou si config/site.yml contient une erreur ; si une page anglaise ou portugaise contient un texte
français destiné aux lecteurs d'écran (aria-label, alt, title, placeholder, titre d'un dessin SVG), ou si les données
structurées (JSON-LD) sont illisibles ou incomplètes.

Affiche aussi des avertissements, sans bloquer la mise en ligne : titre de page de plus de 60 caractères, description
de moins de 120 ou de plus de 155 caractères, titre ou description identique sur plusieurs pages d'une même langue.
Bloque aussi toute page qui contient encore un repère de texte à fournir ([À COMPLÉTER…], [HISTOIRE À FOURNIR…]).
"""
import json
import html
import os
import re
import sys
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "_site")
DOMAIN = "https://chanceleno.com"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as configfile  # noqa: E402  (tools/config.py)
CONFIG = configfile.load()
EMAIL = CONFIG["email"]
I18N = json.load(open(os.path.join(ROOT, "content", "i18n.json"), encoding="utf-8"))
ATTRS = ("aria-label", "alt", "title", "placeholder")
EAGER = {"/images/logo.webp", "/images/accueil.webp"}   # haut de page : logo et photo de l'accueil
IGNORED = {"google8a6c94d578320138.html"}
A_FOURNIR = re.compile(r"\[(?:À COMPLÉTER|A COMPLETER|HISTOIRE À FOURNIR)[^\]]*\]", re.I)   # texte provisoire, jamais publié   # fichier de vérification Google, servi tel quel


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.ids, self.alts, self.metas, self.scripts, self.handlers = [], set(), {}, {}, [], []
        self.h1 = 0
        self.imgs = []
        self.canonical = None
        self.title = ""
        self._in_title = False
        self._script = None
        self.lang = None
        self.labels = []        # textes lus par les lecteurs d'écran (attributs, titre des dessins SVG)
        self.ld = []            # blocs JSON-LD (texte brut)
        self.faq = 0            # questions fréquentes (<details class="faq">)
        self._svg = 0
        self._svg_title = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        for k in a:
            if k.startswith("on"):
                self.handlers.append("%s %s" % (tag, k))
        if tag == "html":
            self.lang = a.get("lang")
        for k in ATTRS:
            if a.get(k):
                self.labels.append(a[k])
        if tag == "svg":
            self._svg += 1
        if tag == "title" and self._svg:
            self._svg_title = ""
        if tag == "details" and "faq" in (a.get("class") or "").split():
            self.faq += 1
        if tag == "h1":
            self.h1 += 1
        if tag == "img":
            self.imgs.append(a)
        if tag == "title" and not self._svg:
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
            if self._svg_title is not None:
                self.labels.append(self._svg_title)
                self._svg_title = None
        if tag == "svg":
            self._svg -= 1
        if tag == "script":
            self._script = None

    def handle_data(self, d):
        if self._in_title:
            self.title += d
        if self._svg_title is not None:
            self._svg_title += d
        if self._script is not None and self._script.get("type") == "application/ld+json":
            self.ld.append(d)
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
    code = CONFIG["goatcounter"]
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
                for m in sorted(set(re.findall(r"\{\{[a-z_]+\}\}|data-si=", txt))):
                    errors.append("%s : marqueur non remplacé %s" % (rel, m))
            if f.endswith(".html") and f not in IGNORED:
                p = Page()
                p.feed(open(full, encoding="utf-8").read())
                p.a_fournir = A_FOURNIR.search(open(full, encoding="utf-8").read())
                url = rel[:-len("index.html")] if rel.endswith("/index.html") else rel
                pages[url] = p
    warnings = []
    seen = {}               # (langue, "titre"/"description", texte) -> pages
    for url, p in pages.items():
        errors += check_jsonld(url, p, pages)
        if p.lang in ("en", "pt"):
            for v in p.labels:
                e = I18N.get(" ".join(v.split()))
                if e and e.get(p.lang) and e[p.lang] != " ".join(v.split()):
                    errors.append("%s : texte français non traduit pour les lecteurs d'écran (%r)" % (url, v))
        if "noindex" not in p.metas.get("robots", ""):
            t, d = p.title.strip(), p.metas.get("description", "")
            if len(t) > 60:
                warnings.append("%s : titre de %d caractères (60 au plus conseillés)" % (url, len(t)))
            if not 120 <= len(d) <= 155:
                warnings.append("%s : description de %d caractères (120 à 155 conseillés)" % (url, len(d)))
            seen.setdefault((p.lang, "titre", t), []).append(url)
            seen.setdefault((p.lang, "description", d), []).append(url)
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
        for img in p.imgs:
            src = img.get("src", "")
            if not img.get("width") or not img.get("height") or img.get("alt") is None:
                errors.append("%s : image sans dimensions ou sans texte alternatif (%s)" % (url, src))
            if src.endswith((".jpg", ".jpeg", ".png")):
                errors.append("%s : image non convertie en WebP (%s)" % (url, src))
            if src not in EAGER and img.get("loading") != "lazy":
                errors.append("%s : image hors haut de page sans chargement différé (%s)" % (url, src))
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
    for loc, date in re.findall(r"<loc>([^<]+)</loc>(?:(?!</url>).)*?<lastmod>([^<]*)</lastmod>", sm, re.S):
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
            errors.append("sitemap.xml : date <lastmod> invalide pour %s (%r)" % (loc, date))
    for f in (".well-known/security.txt", "robots.txt", "CNAME", "404.html", "favicon.ico", "apple-touch-icon.png",
              "images/icon-192.png", IGNORED.copy().pop()):
        if not os.path.isfile(os.path.join(OUT, f)):
            errors.append("fichier manquant : %s" % f)
    for u, p in sorted(pages.items()):
        if p.a_fournir:
            errors.append("%s : repère de texte à fournir %s" % (u, p.a_fournir.group(0)))
    for (lang, kind, _), urls in sorted(seen.items()):
        if len(urls) > 1:
            warnings.append("%s identique sur %d pages (%s) : %s" % (kind.capitalize(), len(urls), lang, ", ".join(sorted(urls))))
    if warnings:
        print("Avertissements référencement (%d, non bloquants) :" % len(warnings))
        for w in warnings:
            print("  - " + w)
    if errors:
        print("ERREUR : %d problème(s) dans le site généré :" % len(errors))
        for e in errors:
            print("  - " + e)
        sys.exit(1)
    print("Contrôles OK : %d pages, %d dans le plan du site." % (len(pages), len(locs)))


def check_jsonld(url, p, pages):
    """Données structurées : JSON lisible, schema.org, et cohérence des blocs générés (FAQ, fil d'Ariane, auteur)."""
    errors = []
    for raw in p.ld:
        try:
            ld = json.loads(raw)
        except ValueError as e:
            errors.append("%s : données structurées illisibles (%s)" % (url, e))
            continue
        if ld.get("@context") != "https://schema.org" or not ld.get("@type"):
            errors.append("%s : données structurées sans @context schema.org ou sans @type" % url)
            continue
        t = ld["@type"]
        if t == "FAQPage":
            qs = ld.get("mainEntity") or []
            if len(qs) != p.faq or not all(q.get("name") and q.get("acceptedAnswer", {}).get("text") for q in qs):
                errors.append("%s : FAQ des données structurées incomplète (%d questions pour %d affichées)" % (url, len(qs), p.faq))
        if t == "BreadcrumbList":
            items = ld.get("itemListElement") or []
            for i, it in enumerate(items):
                path = urlsplit(it.get("item", "")).path
                if it.get("position") != i + 1 or not it.get("name") or not it.get("item", "").startswith(DOMAIN) or path not in pages:
                    errors.append("%s : fil d'Ariane incorrect (%s)" % (url, it))
            if items and urlsplit(items[-1]["item"]).path != url:
                errors.append("%s : le fil d'Ariane ne se termine pas par la page elle-même" % url)
        person = ld.get("founder") if t == "Organization" else ld.get("author") if t == "Article" else None
        if person is not None and (person.get("@id") != DOMAIN + "/#fondateur" or not person.get("name")):
            errors.append("%s : fondateur ou auteur sans identifiant %s/#fondateur" % (url, DOMAIN))
    if p.faq and not any('"FAQPage"' in raw for raw in p.ld):
        errors.append("%s : questions fréquentes sans données structurées FAQPage" % url)
    return errors


def _lang(url, p):
    for l, h in p.alts.items():
        if l != "x-default" and urlsplit(h).path == url:
            return l
    return None


if __name__ == "__main__":
    main()
