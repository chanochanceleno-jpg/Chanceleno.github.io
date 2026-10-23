#!/usr/bin/env python3
"""Surveillance hebdomadaire du site (lancée chaque lundi par .github/workflows/surveillance.yml).

Contrôle : config/site.yml ; génération du site et liens internes (tools/build.py, tools/check.py) ; liens vers
d'autres sites ; pages du site en ligne en FR, EN et PT ; plan du site en ligne (sitemap.xml). En cas de
problème, le rapport (en français) sert de texte à l'issue GitHub ouverte par le workflow, et le script s'arrête
avec le code 1.

    python3 tools/surveillance.py                                   # contrôle complet
    python3 tools/surveillance.py --site http://localhost:8766      # site en ligne remplacé par un serveur local
    python3 tools/surveillance.py --sans-externes --rapport r.md    # sans les liens vers d'autres sites
"""
import argparse
import concurrent.futures
import datetime
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urlsplit, urlunsplit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "_site")
DOMAIN = "https://chanceleno.com"
UA = "Mozilla/5.0 (compatible; surveillance-chanceleno.com; +https://chanceleno.com)"
BLOCKED = {401, 403, 429, 999}   # sites qui refusent les robots (LinkedIn répond 999) : signalés, pas en erreur


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "a" and re.match(r"^https?://", a.get("href") or ""):
            self.links.add(a["href"])


def fetch(url, method="GET", timeout=25):
    """(code HTTP, texte) ; code 0 et message si le site ne répond pas."""
    req = urllib.request.Request(url, method=method, headers={"User-Agent": UA, "Accept-Language": "fr,en;q=0.8"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read(2_000_000) if method == "GET" else b""
            return r.status, body.decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:   # adresse inconnue, délai dépassé, certificat…
        return 0, str(getattr(e, "reason", e))


def check_external(url):
    code, msg = fetch(url, "HEAD")
    if code in (0, 403, 404, 405, 429) or code >= 500:
        code, msg = fetch(url)          # certains sites refusent HEAD ; second essai en GET
    if code == 0:
        code, msg = fetch(url)          # nouvel essai après une coupure réseau
    return url, code, msg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default=DOMAIN, help="adresse du site en ligne à contrôler")
    ap.add_argument("--rapport", help="fichier où écrire le rapport (Markdown)")
    ap.add_argument("--sans-externes", action="store_true", help="ne pas contrôler les liens vers d'autres sites")
    args = ap.parse_args()
    site = args.site.rstrip("/")
    problems, notes = [], []

    # 1. configuration
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import config as configfile
    try:
        configfile.load()
    except SystemExit as e:
        problems.append(("Configuration (config/site.yml)", str(e)))

    # 2. génération et contrôles du site (liens internes, sécurité, plan du site…)
    for script in ("build.py", "check.py"):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", script)], capture_output=True, text=True)
        if r.returncode:
            problems.append(("tools/" + script, (r.stdout + r.stderr).strip()[-3000:]))
            break
    generated = []
    if os.path.isfile(os.path.join(OUT, "sitemap.xml")):
        with open(os.path.join(OUT, "sitemap.xml"), encoding="utf-8") as f:
            generated = [urlsplit(u).path for u in re.findall(r"<loc>([^<]+)</loc>", f.read())]

    # 3. liens vers d'autres sites (une seule fois par adresse, sans les paramètres)
    if not args.sans_externes and os.path.isdir(OUT):
        links = set()
        for d, _, files in os.walk(OUT):
            for f in files:
                if f.endswith(".html"):
                    p = Links()
                    with open(os.path.join(d, f), encoding="utf-8") as fh:
                        p.feed(fh.read())
                    links |= {urlunsplit(urlsplit(u)._replace(query="", fragment="")) for u in p.links}
        links = sorted(u for u in links if not u.startswith(DOMAIN))
        with concurrent.futures.ThreadPoolExecutor(8) as ex:
            for url, code, msg in ex.map(check_external, links):
                if code in BLOCKED:
                    notes.append("%s : le site refuse les contrôles automatiques (code %d), à vérifier à la main si besoin" % (url, code))
                elif code == 0 or code >= 400:
                    problems.append(("Lien vers un autre site", "%s : %s" % (url, "code %d" % code if code else "ne répond pas (%s)" % msg)))

    # 4. site en ligne : plan du site et chaque page en FR, EN et PT
    code, sm = fetch(site + "/sitemap.xml")
    if code != 200:
        problems.append(("Plan du site en ligne", "%s/sitemap.xml : %s" % (site, "code %d" % code if code else "ne répond pas (%s)" % sm)))
    else:
        live = [urlsplit(u).path for u in re.findall(r"<loc>([^<]+)</loc>", sm)]
        if not live:
            problems.append(("Plan du site en ligne", "sitemap.xml ne contient aucune page"))
        if generated and set(live) != set(generated):
            miss, extra = sorted(set(generated) - set(live)), sorted(set(live) - set(generated))
            problems.append(("Plan du site en ligne", "différent du site généré depuis main (dernière publication échouée ?)"
                             + ("\n  absentes en ligne : " + ", ".join(miss) if miss else "")
                             + ("\n  en trop en ligne : " + ", ".join(extra) if extra else "")))

    def page(path):
        code, body = fetch(site + path)
        return path, code, body
    with concurrent.futures.ThreadPoolExecutor(8) as ex:
        for path, code, body in ex.map(page, generated):
            lang = "en" if path.startswith("/en/") else "pt" if path.startswith("/pt/") else "fr"
            if code != 200:
                problems.append(("Page en ligne", "%s%s : %s" % (site, path, "code %d" % code if code else "ne répond pas (%s)" % body)))
            elif '<html lang="%s"' % lang not in body or "<title>" not in body:
                problems.append(("Page en ligne", "%s%s : contenu inattendu (langue %s ou titre absents)" % (site, path, lang)))

    # rapport
    today = datetime.date.today().strftime("%d/%m/%Y")
    lines = ["## Surveillance du site du %s" % today, ""]
    if problems:
        lines += ["**%d problème(s) détecté(s)** sur %s. Que faire ? Voir la rubrique « Surveillance hebdomadaire » "
                  "du README." % (len(problems), site), ""]
        for title, detail in problems:
            lines += ["- **%s** :" % title, "  ```", "  " + detail.replace("\n", "\n  "), "  ```"]
    else:
        lines += ["Aucun problème : configuration, liens, %d pages en ligne (FR, EN, PT) et plan du site corrects." % len(generated)]
    if notes:
        lines += ["", "Pour information :"] + ["- " + n for n in notes]
    report = "\n".join(lines) + "\n"
    print(report)
    if args.rapport:
        with open(args.rapport, "w", encoding="utf-8") as f:
            f.write(report)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
