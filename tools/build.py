#!/usr/bin/env python3
"""Générateur du site chanceleno.com.

Lit les sources du dossier content/ (textes en français + traductions) et les fichiers de static/,
puis écrit le site complet, en français, anglais et portugais, dans le dossier _site/.

    python3 tools/build.py            # génère _site/
    python3 tools/build.py --serve    # génère puis affiche le site sur http://localhost:8000

Données modifiables (identité, coordonnées, tarifs, cartes Marchés, références…) : config/site.yml, lu et vérifié
par tools/config.py. Dans les textes, un marqueur {{nom}} est remplacé par la valeur correspondante (voir TOKENS).
Modules nécessaires : python3 -m pip install -r tools/requirements.txt (PyYAML, Pillow).
"""
import datetime
import html
import json
import os
import re
import shutil
import sys
from html.parser import HTMLParser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as configfile  # noqa: E402  (tools/config.py)
from icones import ICONS  # noqa: E402  (tools/icones.py)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "content")
STATIC = os.path.join(ROOT, "static")
OUT = os.path.join(ROOT, "_site")
LANGS = ["fr", "en", "pt"]
OG_LOCALE = {"fr": "fr_FR", "en": "en_GB", "pt": "pt_PT"}

def csp(stats):
    """Politique de sécurité du contenu, commune à toutes les pages (voir le lot Sécurité). Le domaine des
    statistiques GoatCounter n'est autorisé (envoi des comptages) que si un code est configuré."""
    gc = " " + stats if stats else ""
    return ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self'%s; font-src 'self'; "
            "connect-src 'self' https://formsubmit.co%s; form-action 'self' https://formsubmit.co; base-uri 'self'; "
            "object-src 'none'; frame-src 'none'; upgrade-insecure-requests") % (gc, gc)


def rd(*p):
    with open(os.path.join(*p), encoding="utf-8") as f:
        return f.read()


def rjson(*p):
    return json.loads(rd(*p))


# Images affichées dans les pages : converties en WebP et redimensionnées à la génération (Pillow), avec leurs
# dimensions et un chargement différé. Taille maximale = 2 fois la taille affichée (écrans haute densité) ;
# par défaut 1600 px de large. Les originaux restent publiés (icône, données structurées, partage), sauf ceux des
# emplacements photo ci-dessous (PHOTO_DIRS), souvent lourds, dont seule la version WebP est publiée.
IMAGE_SIZES = {"/images/logo.png": {"hauteur": 68}, "/images/fondateur.jpg": {"largeur": 680}}
EAGER = {"/images/logo.png"}   # images du haut de page, chargées immédiatement
_webp = {}
# Emplacements photo (voir config/site.yml, rubrique photos) : fichier présent = photo affichée.
PHOTO_EXT = (".jpg", ".jpeg", ".png")
PHOTO_SIZES = {"accueil": {"largeur": 1200}, "secteurs": {"largeur": 1600}, "marches": {"largeur": 900},
               "references": {"largeur": 240}}
PHOTO_DIRS = ["secteurs", "marches", "references"]


def photo(name):
    """Adresse de la photo static/images/<name>.jpg|jpeg|png si elle existe (majuscules acceptées), sinon None."""
    folder, base = os.path.split(name)
    d = os.path.join(STATIC, "images", folder)
    if not os.path.isdir(d):
        return None
    for f in sorted(os.listdir(d)):
        stem, ext = os.path.splitext(f)
        if stem.lower() == base.lower() and ext.lower() in PHOTO_EXT:
            src = "/images/" + (folder + "/" if folder else "") + f
            IMAGE_SIZES.setdefault(src, PHOTO_SIZES[folder or base])
            return src
    return None


def webp(src):
    """Crée (une seule fois) la version WebP d'une image du site et renvoie (adresse, largeur, hauteur)."""
    if src not in _webp:
        try:
            from PIL import Image
        except ImportError:
            raise SystemExit("Le module Pillow est nécessaire : python3 -m pip install -r tools/requirements.txt")
        from PIL import ImageOps
        try:
            im = ImageOps.exif_transpose(Image.open(os.path.join(STATIC, src.lstrip("/"))))
        except OSError as e:
            raise SystemExit("Image illisible : static%s (%s). Enregistrez-la à nouveau en JPG ou PNG." % (src, e))
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGBA" if "A" in im.mode or "transparency" in im.info else "RGB")
        w, h = im.size
        size = IMAGE_SIZES.get(src, {"largeur": 1600})
        if "hauteur" in size and h > size["hauteur"]:
            w, h = round(w * size["hauteur"] / h), size["hauteur"]
        if "largeur" in size and w > size["largeur"]:
            w, h = size["largeur"], round(h * size["largeur"] / w)
        if (w, h) != im.size:
            im = im.resize((w, h), Image.LANCZOS)
        out = os.path.splitext(src)[0] + ".webp"
        im.save(os.path.join(OUT, out.lstrip("/")), "WEBP", quality=82, method=6)
        _webp[src] = (out, w, h)
    return _webp[src]


def optimize_images(page):
    def one_img(m):
        tag = m.group(0)
        src = re.search(r'\ssrc="([^"]+)"', tag)
        if not src or not re.match(r"^/images/[^\"]+\.(png|jpe?g)$", src.group(1), re.I):
            return tag
        out, w, h = webp(src.group(1))
        tag = tag.replace('src="%s"' % src.group(1), 'src="%s"' % out)
        extra = ""
        if " width=" not in tag:
            extra += ' width="%d" height="%d"' % (w, h)
        if "loading=" not in tag and src.group(1) not in EAGER:
            extra += ' loading="lazy"'
        if "decoding=" not in tag:
            extra += ' decoding="async"'
        return tag[:-1].rstrip("/").rstrip() + extra + ">"
    return re.sub(r"<img\b[^>]*>", one_img, page)


SITE = None   # sources chargées (Site), pour le remplacement des marqueurs dans wr()


def wr(path, s):
    full = os.path.join(OUT, path.lstrip("/"))
    if full.endswith("/"):
        full += "index.html"
    if full.endswith(".html"):
        lang = re.search(r'<html lang="([a-z]+)"', s)
        s = optimize_images(SITE.fill(s, lang.group(1) if lang else None))
    elif SITE:
        s = SITE.fill(s, None)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(s)


def esc(s):
    return html.escape(s, quote=True)


def norm(t):
    return re.sub(r"\s+", " ", t).strip()


def mask(email):
    """Adresse email écrite « nom(at)domaine » dans le code des pages (reconstituée par assets/mail.js)."""
    return email.replace("@", "(at)")


def cgv_text(lang):
    """Texte des CGV (content/legal/cgv.<langue>.html), sans les commentaires. Vide = page non publiée."""
    p = os.path.join(CONTENT, "legal", "cgv.%s.html" % lang)
    t = rd(p) if os.path.isfile(p) else ""
    return re.sub(r"<!--.*?-->", "", t, flags=re.S).strip()


def drop_empty(page, values):
    """Élément marqué data-si="clé" : retiré (avec son contenu) si la valeur de la clé est vide ; sinon seul
    l'attribut est retiré. Sert aux liens facultatifs (réseaux sociaux, CGV)."""
    while True:
        m = re.search(r'<([a-z0-9]+)\b[^>]*?( data-si="([a-z_]+)")[^>]*>', page)
        if not m:
            return page
        tag, key = m.group(1), m.group(3)
        if key not in values:
            raise SystemExit("data-si inconnu : %r" % key)
        if values[key]:
            page = page[:m.start(2)] + page[m.end(2):]
            continue
        depth, pos = 1, m.end()
        for t in re.finditer(r"<(/?)%s\b[^>]*>" % tag, page[m.end():]):
            depth += -1 if t.group(1) else 1
            if depth == 0:
                pos = m.end() + t.end()
                break
        else:
            raise SystemExit("Balise <%s data-si> non fermée" % tag)
        start = m.start()
        line = re.search(r"\n[ \t]*$", page[:start])
        if line and (pos == len(page) or page[pos] == "\n"):
            start = line.start()     # élément seul sur sa ligne : la ligne entière disparaît
        page = page[:start] + page[pos:]


class Site:
    """Toutes les sources chargées, et les erreurs relevées pendant la génération."""

    def __init__(self):
        self.site = rjson(CONTENT, "site.json")
        self.i18n = {k: v for k, v in rjson(CONTENT, "i18n.json").items()}
        self.data = rjson(CONTENT, "data.json")
        self.light = rjson(CONTENT, "layout", "light.json")
        self.blocs = rjson(CONTENT, "layout", "blocs.json")
        self.domain = self.site["domaine"]
        self.config = c = configfile.load()
        self.year = datetime.date.today().year
        # statistiques GoatCounter : code du compte (ex. « chanceleno »), vide = aucun comptage
        self.stats = "https://%s.goatcounter.com" % c["goatcounter"] if c["goatcounter"] else ""
        # CGV : publiées seulement quand le texte existe dans les trois langues
        cgv = {l: cgv_text(l) for l in LANGS}
        if any(cgv.values()) and not all(cgv.values()):
            raise SystemExit("CGV : texte présent en %s mais absent en %s (content/legal/cgv.<langue>.html). Les trois langues "
                             "sont nécessaires pour publier la page." % (", ".join(l for l in LANGS if cgv[l]),
                                                                         ", ".join(l for l in LANGS if not cgv[l])))
        self.cgv = cgv if all(cgv.values()) else None
        self.used = set()          # textes de i18n.json réellement utilisés
        self.missing = {}          # texte français sans traduction -> pages concernées
        self.pages = {}            # identifiant de page -> {langue: chemin}
        for pid, p in self.site["pages"].items():
            self.pages[pid] = {l: p[l]["chemin"] for l in LANGS}
        for i, s in enumerate(self.data["secteurs"]):
            self.pages["secteur-%d" % i] = {l: self.site["secteurs_base"][l] + s["adresse"][l] + "/" for l in LANGS}
        self.sitemap = []          # (chemin, {langue: chemin}, date)

    def url(self, pid, lang):
        return self.pages[pid][lang]

    # --- valeurs de config/site.yml utilisables dans les textes : {{nom}}
    def tokens(self, lang):
        c, f = self.config, self.config["france"]
        v = {"email": mask(c["email"]), "email_nom": c["email"].split("@")[0], "email_domaine": c["email"].split("@")[1],
             "formsubmit": c["formsubmit"], "wa_europe": c["wa_europe"], "wa_afrique": c["wa_afrique"],
             "wa_europe_num": re.sub(r"\D", "", c["wa_europe"]), "wa_afrique_num": re.sub(r"\D", "", c["wa_afrique"]),
             "delai_rapport": str(c["delai_rapport"]), "delai_reponse": str(c["delai_reponse"]), "annee": str(self.year),
             "france_nom": f["denomination"], "angola_nom": c["angola"]["denomination"], "cgv": "oui" if self.cgv else ""}
        v.update(c["reseaux"])
        if lang:
            B = self.blocs[lang]
            n = c["prix_audit"]
            amount = "{:,}".format(n) if isinstance(n, int) else ("%.2f" % n)
            if lang != "en":
                amount = amount.replace(",", "\u202f").replace(".", ",")
            v["prix_audit"] = B["prix"].format(montant=amount)
            v["france_statut"] = B["statut_immatriculee"].format(**self.france_display()) if f["immatriculee"] else B["statut_attente"]
            v["accueil_description"] = c["accueil_description"][lang]
        return v

    def fill(self, page, lang):
        """Après traduction : blocs construits depuis config/site.yml, liens facultatifs, puis marqueurs {{nom}}."""
        if lang:
            for name, fn in (("MARCHES", self.markets_html), ("IDENTITE", self.legal_html), ("ENTITES", self.entities_html),
                             ("REFERENCES", self.references_html), ("CGV", lambda l: self.cgv[l] if self.cgv else ""),
                             ("RESEAUX", self.socials_html), ("SUIVEZ", self.follow_html)):
                if "<!--%s-->" % name in page:
                    block = fn(lang)
                    # bloc vide : la ligne du repère disparaît aussi (page identique à une page sans ce bloc)
                    page = page.replace("<!--%s-->" % name, block) if block else re.sub(r"[ \t]*<!--%s-->\n*" % name, "", page)
        values = self.tokens(lang)
        page = drop_empty(page, values)

        def one(m):
            if m.group(1) not in values:
                raise SystemExit("Marqueur inconnu {{%s}} : voir la liste dans README.md" % m.group(1))
            return esc(values[m.group(1)]).replace("&#x27;", "'")
        return re.sub(r"\{\{([a-z_]+)\}\}", one, page)

    # --- blocs construits depuis config/site.yml
    def entity_text(self, which, lang):
        """Une entité, en une phrase (mentions légales)."""
        c, B = self.config, self.blocs[lang]
        if which == "angola":
            a = c["angola"]
            parts = [B["nif"].format(nif=a["nif"]), B["siege"].format(adresse=a["adresse"]), B["tel"].format(tel=c["wa_afrique"])]
            return a["denomination"] + " — " + " — ".join(parts) + "."
        f = self.france_display()
        if not f["immatriculee"]:
            return B["france_attente"].format(nom=f["denomination"], ville=f["ville"])
        parts = [B["capital"].format(**f), B["siren"].format(**f), B["rcs"].format(**f)] + \
            ([B["tva"].format(**f)] if f["tva"] else []) + \
            [B["siege"].format(adresse=f["adresse"]), B["president"].format(**f), B["tel"].format(tel=c["wa_europe"])]
        return f["denomination"] + " — " + " — ".join(parts) + "."

    def france_display(self):
        """Société française, avec des espaces insécables dans les numéros (SIREN, RCS, capital non coupés en fin de ligne)."""
        f = dict(self.config["france"])
        for k in ("siren", "rcs", "capital"):
            f[k] = re.sub(r"(?<=\d) (?=\d)|(?<=\d) (?=€)|(?<=[A-Za-z]) (?=\d)", "\u00a0", f[k])
        return f

    def legal_html(self, lang):
        c, B = self.config, self.blocs[lang]
        ed = c["editeur"]
        other = "france" if ed == "angola" else "angola"
        pub = B["publication"].format(directeur=c["directeur"], email=mask(c["email"]))
        e = lambda t: esc(t).replace("&#x27;", "'")
        return "<h3>%s</h3><p>%s %s</p><h3>%s</h3><p>%s</p>" % (
            e(B["h_editeur"]), e(self.entity_text(ed, lang)), e(pub), e(B["h_autre"][other]), e(self.entity_text(other, lang)))

    def entities_html(self, lang):
        """Les deux entités, dans le pied de page."""
        c, B = self.config, self.blocs[lang]
        a, f = c["angola"], self.france_display()
        e = lambda t: esc(t).replace("&#x27;", "'")
        tel = lambda n: '<a href="https://wa.me/%s">%s</a>' % (re.sub(r"\D", "", n), e(n))
        ao = [e(a["ville"] + ", " + B["pays"]["AO"]), e(B["nif"].format(nif=a["nif"])), tel(c["wa_afrique"])]
        if f["immatriculee"]:
            fr = [e(f["ville"] + ", " + B["pays"]["FR"]), e(B["siren"].format(**f) + " · " + B["rcs"].format(**f))] + \
                ([e(B["tva"].format(**f))] if f["tva"] else []) + [tel(c["wa_europe"])]
        else:
            fr = [e(f["ville"] + ", " + B["pays"]["FR"] + " — " + B["statut_attente"]), e(B["pied_attente"]), tel(c["wa_europe"])]
        return "\n      ".join("<div><strong>%s</strong><br>%s</div>" % (e(n), "<br>".join(lines))
                                for n, lines in ((a["denomination"], ao), (f["denomination"], fr)))

    def markets_html(self, lang):
        e = lambda t: esc(t).replace("&#x27;", "'")
        out = []
        for c in self.config["marches"]:
            if not c["affiche"]:
                continue
            src = photo("marches/" + c["id"])
            img = '<img class="node-photo" src="%s" alt="%s">' % (src, e(c["titre"][lang])) if src else ""
            out.append('<div>%s<span class="role">%s</span><h3>%s</h3><p class="muted">%s</p></div>' % (
                img, e(c["role"][lang]), e(c["titre"][lang]), e(c["texte"][lang])))
        return "\n      ".join(out)

    def references_html(self, lang):
        """Section « Ils nous font confiance » : seulement les références autorisées, traduites dans cette langue."""
        e = lambda t: esc(t).replace("&#x27;", "'")
        refs = [r for r in self.config["references"] if r["autorisation"] and r["temoignage"][lang]]
        if not refs:
            return ""
        items = []
        for r in refs:
            img = ""
            if r["photo"]:
                src = photo("references/" + os.path.splitext(r["photo"])[0])
                img = '<img src="%s" alt="%s">' % (src, e(r["nom"]))
            meta = " · ".join(x for x in (r["secteur"][lang], r["pays"][lang]) if x)
            items.append('<figure class="ref">%s<blockquote><p>%s</p></blockquote><figcaption><strong>%s</strong>%s</figcaption></figure>' % (
                img, e(r["temoignage"][lang]), e(r["nom"]), "<span>%s</span>" % e(meta) if meta else ""))
        return ('<div class="band dark" id="references">\n    <div class="wrap">\n      <h2>%s</h2>\n      <div class="refs">%s</div>\n'
                '    </div>\n  </div>' % (e(self.blocs[lang]["references_titre"]), "".join(items)))

    # --- réseaux sociaux : icônes (pied de page, Contact) et données structurées
    SOCIAL = [("linkedin_page", "linkedin", "LinkedIn"), ("instagram", "instagram", "Instagram"),
              ("facebook", "facebook", "Facebook"), ("youtube", "youtube", "YouTube"), ("tiktok", "tiktok", "TikTok")]

    def socials_html(self, lang):
        """Rangée d'icônes des comptes officiels, dans l'ordre de SOCIAL (TikTok, compte du fondateur, en dernier)."""
        B, r = self.blocs[lang], self.config["reseaux"]
        items = []
        for key, icon, name in self.SOCIAL:
            if not r[key]:
                continue
            label = B["reseau_tiktok"] if key == "tiktok" else B["reseau"].format(r=name)
            items.append('<li><a href="%s" target="_blank" rel="noopener noreferrer" aria-label="%s"><svg viewBox="0 0 24 24" '
                         'width="20" height="20" fill="currentColor" aria-hidden="true" focusable="false"><path d="%s"/></svg></a></li>'
                         % (esc(r[key]), esc(label).replace("&#x27;", "'"), ICONS[icon]))
        if not items:
            return ""
        return '<ul class="socials" aria-label="%s">%s</ul>' % (esc(B["reseaux_groupe"]), "".join(items))

    def follow_html(self, lang):
        """Page Contact : « Suivez-nous » suivi des icônes."""
        icons = self.socials_html(lang)
        return '<div class="follow"><p>%s</p>%s</div>' % (esc(self.blocs[lang]["suivez"]), icons) if icons else ""

    def same_as(self):
        """Comptes de l'entreprise (schema.org Organization) : sans le profil LinkedIn ni le TikTok du fondateur."""
        r = self.config["reseaux"]
        return [r[k] for k in ("linkedin_page", "instagram", "facebook", "youtube") if r[k]]

    def founder_same_as(self):
        r = self.config["reseaux"]
        return [r[k] for k in ("linkedin_profil", "tiktok") if r[k]]

    def tr(self, fr, lang, where=""):
        """Traduction d'un texte isolé (titres, descriptions…)."""
        if lang == "fr":
            return fr
        e = self.i18n.get(norm(fr))
        self.used.add(norm(fr))
        if not e or not e.get(lang):
            self.missing.setdefault(norm(fr), set()).add(where)
            return fr
        return e[lang]


# ---------------------------------------------------------------------------------------------------------------
# Réécriture d'une page : traduction des textes, adresses des liens, champs de formulaire
# ---------------------------------------------------------------------------------------------------------------
SKIP = {"script", "style", "svg", "code"}          # contenus jamais traduits (comme l'ancien site)
ATTR_TR = {"placeholder", "alt", "aria-label", "title"}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class Rewriter(HTMLParser):
    def __init__(self, site, lang, page_id, where):
        super().__init__(convert_charrefs=False)
        self.s, self.lang, self.page_id, self.where = site, lang, page_id, where
        self.out, self.buf, self.skip = [], [], 0

    # --- texte
    def flush(self):
        if not self.buf:
            return
        raw = "".join(self.buf)
        self.buf = []
        if self.skip:
            self.out.append(raw)
            return
        text = html.unescape(raw)
        key = norm(text)
        if not re.search(r"[A-Za-zÀ-ÿ]", key):
            self.out.append(raw)
            return
        e = self.s.i18n.get(key)
        self.s.used.add(key)
        if e is None or not e.get("en") or not e.get("pt"):
            self.s.missing.setdefault(key, set()).add(self.where)
        if self.lang == "fr" or not e or not e.get(self.lang):
            self.out.append(raw)
            return
        m = re.match(r"^(\s*).*?(\s*)$", text, re.S)
        self.out.append(esc(m.group(1) + e[self.lang] + m.group(2)).replace("&#x27;", "'"))

    def handle_data(self, d):
        self.buf.append(d)

    def handle_entityref(self, n):
        self.buf.append("&%s;" % n)

    def handle_charref(self, n):
        self.buf.append("&#%s;" % n)

    def handle_comment(self, d):
        self.flush()
        self.out.append("<!--%s-->" % d)

    def handle_decl(self, d):
        self.flush()
        self.out.append("<!%s>" % d)

    # --- balises
    def handle_starttag(self, tag, attrs):
        self.flush()
        self.out.append(self.tag(tag, attrs, self.get_starttag_text(), False))
        if tag in SKIP:
            self.skip += 1

    def handle_startendtag(self, tag, attrs):
        self.flush()
        self.out.append(self.tag(tag, attrs, self.get_starttag_text(), True))

    def handle_endtag(self, tag):
        self.flush()
        if tag in SKIP:
            self.skip -= 1
        self.out.append("</%s>" % tag)

    def tag(self, tag, attrs, raw, selfclose):
        a = dict(attrs)
        changed = False
        # lien vers une autre langue d'« Articles » (ancien sélecteur) : adresse directe
        if "data-href-" + self.lang in a:
            a["href"] = a["data-href-" + self.lang]
            for l in LANGS:
                a.pop("data-href-" + l, None)
            changed = True
        for k in ("href", "src"):
            if a.get(k) is not None:
                v = self.link(a[k])
                if v != a[k]:
                    a[k] = v
                    changed = True
        # menu : page courante
        if tag == "a" and a.get("data-route"):
            cur = "secteurs" if self.page_id.startswith("secteur-") else self.page_id
            if a["data-route"] == cur:
                a["aria-current"] = "page"
                changed = True
        if self.lang != "fr" and not self.skip:
            for k in ATTR_TR:
                v = a.get(k)
                if v and norm(v) in self.s.i18n and self.s.i18n[norm(v)].get(self.lang):
                    self.s.used.add(norm(v))
                    a[k] = self.s.i18n[norm(v)][self.lang]
                    changed = True
        if not changed:
            return raw
        parts = [tag] + [k if v is None else '%s="%s"' % (k, esc(v).replace("&#x27;", "'")) for k, v in a.items()]
        return "<" + " ".join(parts) + (" />" if selfclose and tag not in VOID else ">")

    def link(self, v):
        """Ancienne adresse #/rubrique?param -> vraie adresse de la page dans la langue courante."""
        m = re.match(r"^(?:/(?:en|pt))?/?#/([a-z0-9-]*)(?:\?(.*))?$", v)
        if m:
            pid = m.group(1) or "home"
            q = [p for p in (m.group(2) or "").split("&") if p]
            frag = ""
            for p in list(q):
                if p.startswith("b="):
                    frag = "#" + p[2:]
                    q.remove(p)
            if pid not in self.s.pages:
                raise SystemExit("Lien vers une rubrique inconnue : %s (%s)" % (v, self.where))
            return self.s.url(pid, self.lang) + ("?" + "&".join(q) if q else "") + frag
        if re.match(r"^(images|fonts|assets)/", v):
            return "/" + v
        return v

    def result(self, source):
        self.feed(source)
        self.close()
        self.flush()
        return "".join(self.out)


def translate(site, source, lang, page_id, where):
    return Rewriter(site, lang, page_id, where).result(source)


# ---------------------------------------------------------------------------------------------------------------
# Préparation des sources françaises (avant traduction)
# ---------------------------------------------------------------------------------------------------------------
def prepare_forms(site, src):
    """Les emails reçus doivent garder des noms de champs français, quelle que soit la langue du visiteur :
    chaque champ reçoit son libellé français (data-key) et chaque option sa valeur française (data-fr), marqueurs
    {{nom}} compris (remplacés ici par leur valeur française)."""
    fr = site.tokens("fr")
    french = lambda t: re.sub(r"\{\{([a-z_]+)\}\}", lambda m: fr[m.group(1)], t)
    labels = {}
    for fid, inner in re.findall(r'<label for="([^"]+)">(.*?)</label>', src, re.S):
        labels[fid] = french(norm(html.unescape(inner.split("<")[0])))

    def add_key(m):
        t = m.group(0)
        fid = re.search(r'\bid="([^"]+)"', t)
        if fid and fid.group(1) in labels and "data-key=" not in t:
            return t[:-1] + ' data-key="%s">' % esc(labels[fid.group(1)])
        return t
    src = re.sub(r"<(?:input|select|textarea)\b[^>]*>", add_key, src)

    def add_fr(m):
        if "data-fr=" in m.group(1):
            return m.group(0)
        return '<option%s data-fr="%s">%s</option>' % (m.group(1), esc(french(norm(html.unescape(m.group(2))))), m.group(2))
    return re.sub(r"<option([^>]*)>([^<]*)</option>", add_fr, src)


def first_heading_h1(src):
    """Le titre de la rubrique (h2 dans l'en-tête de page) devient le h1 de la page."""
    i = src.find('<div class="pagehead">')
    if i < 0 or "<h1" in src:
        return src
    j = src.find("<h2", i)
    k = src.find("</h2>", j)
    return src[:j] + "<h1" + src[j + 3:k] + "</h1>" + src[k + 5:]


def fill_lists(site, src):
    d = site.data
    caps = "".join('<div class="cap"><h3>%s</h3><p>%s</p></div>' % (c["titre"], c["texte"]) for c in d["capacites"])
    src = src.replace('<div class="caps" id="capsFull"></div>', '<div class="caps" id="capsFull">%s</div>' % caps)
    sect = "".join(
        '<article class="sector-detail"><h3><a href="#/secteur-%d">%s</a></h3><dl><div><dt>Enjeux fréquents</dt><dd>%s</dd></div>'
        '<div><dt>Besoins typiques</dt><dd>%s</dd></div><div><dt>Ce que nous apportons</dt><dd>Sourcing ciblé, vérification '
        'proportionnée au risque, comparaison documentée des offres.</dd></div><div><dt>Prochaine étape</dt><dd><a href="#/devis?s=%d" '
        'style="color:var(--copper);font-weight:600">Envoyer un besoin dans ce secteur</a></dd></div></dl></article>'
        % (i, s["titre"], s["enjeux"], s["besoins"], i) for i, s in enumerate(d["secteurs"]))
    sect += ('<p style="margin-top:36px" class="lead">Votre secteur n\'apparaît pas ? <a href="#/devis" style="color:var(--copper)">'
             'Envoyez-nous votre besoin.</a></p>')
    src = src.replace('<div class="wrap" id="sectorsFull"></div>', '<div class="wrap" id="sectorsFull">%s</div>' % sect)
    opts = "".join('<option value="%d">%s</option>' % (i, s["titre"]) for i, s in enumerate(d["secteurs"])) + \
        '<option value="other">Autre / je ne sais pas</option>'
    src = re.sub(r'(<select [^>]*class="secSelect"[^>]*>)(</select>)', lambda m: m.group(1) + opts + m.group(2), src)
    track = "".join('<li class="%s"><strong>%s</strong>%s</li>' % (
        "done" if t["etat"] == 1 else "now" if t["etat"] == 2 else "", t["etape"],
        "<small>Étape en cours</small>" if t["etat"] == 2 else "") for t in d["suivi_demo"])
    return src.replace('<ol class="track" id="demoTrack"></ol>', '<ol class="track" id="demoTrack">%s</ol>' % track)


def home_photo(src):
    """Photo de l'accueil (static/images/accueil.jpg) : remplace l'illustration du globe, même emplacement."""
    p = photo("accueil")
    if not p:
        return src
    EAGER.add(p)
    fig = '<figure class="hero-photo"><img src="%s" alt="{{accueil_description}}" fetchpriority="high"></figure>' % p
    out = re.sub(r'<figure class="globe-wrap".*?</figure>', fig, src, count=1, flags=re.S)
    assert out != src
    return out


def sector_page(site, i):
    s = site.data["secteurs"][i]
    p = photo("secteurs/" + s["adresse"]["fr"])
    img = '<figure class="sector-photo"><img src="%s" alt="%s"></figure>' % (p, s["titre"]) if p else ""
    others = "".join('<li><a href="#/secteur-%d">%s</a></li>' % (j, o["titre"]) for j, o in enumerate(site.data["secteurs"]) if j != i)
    return (
        '<section class="page" data-page="secteur" aria-labelledby="h-secteur">\n'
        '  <div class="pagehead"><div class="wrap"><span class="crumb"><a href="#/secteurs">Secteurs</a></span>'
        '<h1 id="h-secteur" style="font-size:clamp(34px,5vw,60px);max-width:18ch">%s</h1></div></div>\n'
        '  <div class="band"><div class="wrap">%s<article class="sector-detail"><dl>'
        '<div><dt>Besoins typiques</dt><dd>%s</dd></div><div><dt>Enjeux fréquents</dt><dd>%s</dd></div>'
        '<div><dt>Ce que nous apportons</dt><dd>Sourcing ciblé, vérification proportionnée au risque, comparaison documentée des offres.</dd></div>'
        '<div><dt>Prochaine étape</dt><dd><a href="#/devis?s=%d" class="btn btn-primary btn-sm">Envoyer un besoin dans ce secteur</a></dd></div>'
        '</dl></article></div></div>\n'
        '  <div class="band alt"><div class="wrap"><h2>Huit secteurs, une même méthode</h2><ul class="sector-links">%s</ul></div></div>\n'
        '</section>\n') % (s["titre"], img, s["besoins"], s["enjeux"], i, others)


# ---------------------------------------------------------------------------------------------------------------
# En-tête HTML (<head>) commun : sécurité, SEO, langues
# ---------------------------------------------------------------------------------------------------------------
def head(site, lang, pid, title, desc, *, og_title=None, og_type="website", robots="index, follow", css="/assets/site.css",
         alternates=None, jsonld=None, scripts=(), extra=""):
    D = site.domain
    alternates = alternates if alternates is not None else ({l: site.url(pid, l) for l in LANGS} if pid else {})
    img = site.site["og_image"][lang]
    img_alt = site.site["og_image_alt"][lang]
    h = ['<!DOCTYPE html>', '<html lang="%s">' % lang, '<head>', '<meta charset="utf-8">',
         '<meta http-equiv="Content-Security-Policy" content="%s">' % csp(site.stats),
         '<meta name="referrer" content="strict-origin-when-cross-origin">',
         '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">',
         '<meta name="robots" content="%s">' % robots,
         '<title>%s</title>' % esc(title)]
    if desc:
        h.append('<meta name="description" content="%s">' % esc(desc))
    if alternates:
        h.append('<link rel="canonical" href="%s%s">' % (D, alternates[lang]))
        for l in LANGS:
            h.append('<link rel="alternate" hreflang="%s" href="%s%s">' % (l, D, alternates[l]))
        h.append('<link rel="alternate" hreflang="x-default" href="%s%s">' % (D, alternates["fr"]))
        og_title = og_title or title
        h += ['<meta property="og:site_name" content="CHANCELENO">',
              '<meta property="og:type" content="%s">' % og_type,
              '<meta property="og:title" content="%s">' % esc(og_title),
              '<meta property="og:description" content="%s">' % esc(desc or ""),
              '<meta property="og:url" content="%s%s">' % (D, alternates[lang]),
              '<meta property="og:locale" content="%s">' % OG_LOCALE[lang]]
        h += ['<meta property="og:locale:alternate" content="%s">' % OG_LOCALE[l] for l in LANGS if l != lang]
        h += ['<meta property="og:image" content="%s%s">' % (D, img),
              '<meta property="og:image:secure_url" content="%s%s">' % (D, img),
              '<meta property="og:image:type" content="image/jpeg">',
              '<meta property="og:image:width" content="1200">',
              '<meta property="og:image:height" content="630">',
              '<meta property="og:image:alt" content="%s">' % esc(img_alt),
              '<meta name="twitter:card" content="summary_large_image">',
              '<meta name="twitter:title" content="%s">' % esc(og_title),
              '<meta name="twitter:description" content="%s">' % esc(desc or ""),
              '<meta name="twitter:image" content="%s%s">' % (D, img),
              '<meta name="twitter:image:alt" content="%s">' % esc(img_alt)]
    h += ['<meta name="theme-color" content="#0A1622">', extra, '<link rel="icon" href="/images/logo.png">',
          '<link rel="preload" href="/fonts/Archivo.woff2" as="font" type="font/woff2" crossorigin>',
          '<link rel="preload" href="/fonts/Newsreader.woff2" as="font" type="font/woff2" crossorigin>',
          '<link rel="stylesheet" href="%s">' % css]
    if jsonld:
        h.append('<script type="application/ld+json">%s</script>' % json.dumps(jsonld, ensure_ascii=False).replace("</", "<\\/"))
    h += ['<script src="%s"></script>' % s for s in scripts]
    if site.stats:
        h.append('<script data-goatcounter="%s/count" async src="/assets/count.js"></script>' % site.stats)
    h.append('<script src="/assets/stats.js" defer></script>')
    h.append("</head>")
    return "\n".join(x for x in h if x) + "\n"


def organization(site, lang):
    """Données structurées : la marque CHANCELENO et ses deux entités (valeurs de config/site.yml)."""
    D = site.domain
    c = site.config
    a, f = c["angola"], c["france"]
    desc = site.site["pages"]["home"][lang]["description"]
    wa_eu, wa_af = "+" + re.sub(r"\D", "", c["wa_europe"]), "+" + re.sub(r"\D", "", c["wa_afrique"])
    ao = {"@type": "Organization", "name": a["denomination"], "legalName": a["denomination"]}
    if a["date_creation"]:
        ao["foundingDate"] = a["date_creation"]
    ao.update({"taxID": a["nif"], "telephone": wa_af,
               "address": {"@type": "PostalAddress", "streetAddress": a["adresse"].split(", " + a["ville"])[0],
                           "addressLocality": a["ville"], "addressCountry": "AO"}})
    fr = {"@type": "Organization", "name": f["denomination"]}
    if f["immatriculee"]:
        fr.update({"legalName": f["denomination"], "taxID": f["siren"].replace(" ", "")})
        if f["tva"]:
            fr["vatID"] = f["tva"].replace(" ", "")
        if f["date_immatriculation"]:
            fr["foundingDate"] = f["date_immatriculation"]
    else:
        statut = site.blocs[lang]["statut_attente"]
        fr["description"] = statut[0].upper() + statut[1:]
    fr["telephone"] = wa_eu
    fr["address"] = {"@type": "PostalAddress", "addressLocality": f["ville"], "addressCountry": "FR"}
    if f["immatriculee"] and f["adresse"]:
        fr["address"]["streetAddress"] = f["adresse"].split(", ")[0]
    org = {
        "@context": "https://schema.org", "@type": "Organization", "@id": D + "/#organisation",
        "name": "CHANCELENO", "url": D + "/", "logo": D + "/images/logo.png", "description": desc,
        "founder": {"@type": "Person", "name": "Chano Ndandu Chanceleno"},
        "contactPoint": [
            {"@type": "ContactPoint", "telephone": wa_eu, "contactType": "sales",
             "areaServed": ["FR", "BE", "CH", "CG", "CD"], "availableLanguage": ["fr", "en"]},
            {"@type": "ContactPoint", "telephone": wa_af, "contactType": "sales",
             "areaServed": ["AO", "MZ", "CV", "GW", "ST", "BR", "PT"], "availableLanguage": ["pt", "es"]}],
        "areaServed": ["Africa", "Europe", "Asia"], "knowsLanguage": ["fr", "pt", "en", "es"]}
    if site.founder_same_as():
        org["founder"]["sameAs"] = site.founder_same_as()
    if site.same_as():
        org["sameAs"] = site.same_as()
    org["subOrganization"] = [ao, fr]
    return org


def first_text(src, pattern):
    m = re.search(pattern, src, re.S)
    return norm(html.unescape(re.sub(r"<[^>]+>", "", m.group(1)))) if m else ""


def short(t, n=158):
    if len(t) <= n:
        return t
    return t[:n].rsplit(" ", 1)[0].rstrip(" ,;:") + "…"


# ---------------------------------------------------------------------------------------------------------------
# Pages principales
# ---------------------------------------------------------------------------------------------------------------
def lang_switch(site, pid, lang):
    links = "".join('<a href="%s" data-lang="%s" hreflang="%s" lang="%s"%s>%s</a>' % (
        site.url(pid, l), l, l, l, ' aria-current="true"' if l == lang else "", l.upper()) for l in LANGS)
    return '<div class="lang" role="group" aria-label="Langue">%s</div>' % links


def build_main(site):
    header = rd(CONTENT, "layout", "header.html")
    footer = rd(CONTENT, "layout", "footer.html")
    floating = rd(CONTENT, "layout", "floating.html")
    header = re.sub(r'<div class="lang" role="group" aria-label="Langue">.*?</div>', "<!--LANGUES-->", header, flags=re.S)
    assert "<!--LANGUES-->" in header
    sources = {}
    for pid in site.site["pages"]:
        if pid == "cgv" and not site.cgv:
            continue      # CGV pas encore rédigées : pas de page
        src = fill_lists(site, rd(CONTENT, "pages", pid + ".html"))
        sources[pid] = first_heading_h1(prepare_forms(site, home_photo(src) if pid == "home" else src))
    for i in range(len(site.data["secteurs"])):
        sources["secteur-%d" % i] = sector_page(site, i)
    for pid, src in sources.items():
        for lang in LANGS:
            where = "%s (%s)" % (pid, lang)
            body = translate(site, src, lang, pid, where)
            hdr = translate(site, header, lang, pid, "en-tête").replace("<!--LANGUES-->", lang_switch(site, pid, lang))
            ftr = translate(site, footer, lang, pid, "pied de page")
            flt = translate(site, floating, lang, pid, "assistant")
            if pid.startswith("secteur-"):
                s = site.data["secteurs"][int(pid.split("-")[1])]
                title = site.tr(s["titre"], lang, where) + " | CHANCELENO"
                desc = short(site.tr(s["besoins"], lang, where))
                og_title = None
            else:
                p = site.site["pages"][pid][lang]
                title, og_title = p["titre"], p.get("og_titre")
                filled = site.fill(body, lang)     # texte d'introduction tel qu'affiché (blocs et valeurs de config/site.yml)
                desc = p.get("description") or short(first_text(filled, r'<p class="lead"[^>]*>(.*?)</p>') or
                                                     first_text(filled, r'<div class="band">.*?<p[^>]*>(.*?)</p>'))
            extra = '<meta name="google-site-verification" content="%s">' % site.site["google_site_verification"] if pid == "home" else ""
            page = head(site, lang, pid, title, desc, og_title=og_title, jsonld=organization(site, lang) if pid == "home" else None,
                        scripts=["/assets/redirect.js"], extra=extra)
            page += ("<body>\n" + hdr + "\n" + '<main id="content" tabindex="-1">\n\n' + body + "\n</main>\n\n" + ftr + "\n" + flt +
                     '\n<script src="/assets/mail.js" defer></script>\n<script src="/assets/strings.js" defer></script>\n'
                     '<script src="/assets/site.js" defer></script>\n</body>\n</html>\n')
            wr(site.url(pid, lang), page)
            site.sitemap.append((site.url(pid, lang), {l: site.url(pid, l) for l in LANGS}, None))


# ---------------------------------------------------------------------------------------------------------------
# Mise en page légère : articles et pages de remerciement
# ---------------------------------------------------------------------------------------------------------------
LEGAL = ["mentions", "confidentialite", "cookies", "conditions"]


def light_page(site, lang, title_tag, robots, head_extra, sec_current, lang_links, main, after_main="", desc=None, alternates=None,
               og_type="website", og_title=None, jsonld=None):
    L = site.light[lang]
    home = site.url("home", lang)
    art = {"fr": "/articles/", "en": "/en/articles/", "pt": "/pt/artigos/"}[lang]
    if alternates:
        h = head(site, lang, None, title_tag, desc, og_title=og_title, og_type=og_type, robots=robots, css="/assets/articles.css",
                 alternates=alternates, jsonld=jsonld, scripts=["/assets/lang.js"])
        # articles : image de partage décrite simplement « CHANCELENO » (comme avant)
        for p in ('property="og:image:alt"', 'name="twitter:image:alt"'):
            h = h.replace('<meta %s content="%s">' % (p, esc(site.site["og_image_alt"][lang])), '<meta %s content="CHANCELENO">' % p)
    else:
        h = head(site, lang, None, title_tag, desc, robots=robots, css="/assets/articles.css", alternates={}, scripts=["/assets/lang.js"])
    nav = "".join('<a href="%s" hreflang="%s" lang="%s"%s>%s</a>' % (lang_links[l], l, l, ' aria-current="true"' if l == lang else "", l.upper())
                  for l in LANGS)
    flinks = [(home, L["pied"][0]), (art, L["pied"][1])] + [(site.url(p, lang), L["pied"][2 + i]) for i, p in enumerate(LEGAL)]
    if site.cgv:
        flinks.append((site.url("cgv", lang), site.blocs[lang]["cgv"]))
    r = site.config["reseaux"]
    social = [(r["linkedin_profil"], L["pied"][6])]   # profil du fondateur ; comptes officiels : icônes (<!--RESEAUX-->)
    fl = "".join('<li><a href="%s">%s</a></li>' % (u, esc(t)) for u, t in flinks) + \
        "".join('<li><a href="%s" target="_blank" rel="noopener">%s</a></li>' % (esc(u), esc(t)) for u, t in social if u)
    body = (
        '<body>\n<a class="skip" href="#contenu">%s</a>\n<header class="site">\n  <div class="wrap hbar">\n'
        '    <a href="%s" class="brand" aria-label="%s"><img src="/images/logo.png" alt="%s"><span class="word">CHANCELENO</span></a>\n'
        '    <div class="hnav">\n      <a class="sec" href="%s"%s>%s</a>\n'
        '      <nav class="lang" aria-label="Langue">%s</nav>\n'
        '      <a href="%s" class="btn btn-primary btn-sm hcta">%s</a>\n    </div>\n  </div>\n</header>\n'
        '<main id="contenu">\n%s\n</main>\n%s'
        '<footer class="site">\n  <div class="wrap">\n    <ul class="flinks">%s</ul>\n'
        '    <div class="entities">\n      %s\n    </div>\n    <!--RESEAUX-->\n'
        '    <div class="fbot"><span>© {{annee}} CHANCELENO</span><span><a data-mail href="%s">{{email}}</a></span></div>\n'
        '  </div>\n</footer>\n<script src="/assets/mail.js" defer></script>\n</body>\n</html>\n') % (
        esc(L["aller_au_contenu"]), home, esc(L["accueil_aria"]), esc(L["logo_alt"]), art,
        ' aria-current="page"' if sec_current else "", esc(L["articles"]), nav, site.url("devis", lang), esc(L["devis"]),
        main, after_main, fl, "<!--ENTITES-->", site.url("contact", lang))
    return h + body


def date_text(site, lang, iso):
    a, m, j = iso.split("-")
    L = site.light[lang]
    return L["format_date"].format(j=int(j), m=L["mois"][int(m) - 1], a=a)


def build_articles(site):
    base = {"fr": "/articles/", "en": "/en/articles/", "pt": "/pt/artigos/"}
    adir = os.path.join(CONTENT, "articles")
    arts = []
    for aid in sorted(os.listdir(adir)):
        if aid.startswith("_"):
            continue      # dossier modèle
        m = rjson(adir, aid, "meta.json")
        m["id"] = aid
        m["url"] = {l: base[l] + m[l]["adresse"] + "/" for l in LANGS}
        arts.append(m)
    arts.sort(key=lambda a: a["date"], reverse=True)
    for lang in LANGS:
        L = site.light[lang]
        D = site.domain
        publisher = {"@type": "Organization", "name": "CHANCELENO", "url": D + "/", "logo": {"@type": "ImageObject", "url": D + "/images/logo.png"}}
        # liste des articles
        cards = "\n".join('<a class="card" href="%s"><h2>%s</h2><p>%s</p><time datetime="%s">%s</time></a>' % (
            a["url"][lang], esc(a[lang]["titre"]), esc(a[lang]["description"]), a["date"], date_text(site, lang, a["date"])) for a in arts)
        main = ('<div class="pagehead"><div class="wrap">\n<h1>%s</h1>\n<p class="lead">%s</p>\n</div></div>\n<div class="list">\n%s\n</div>'
                % (esc(L["liste_titre"]), esc(L["liste_description"]), cards))
        ld = {"@context": "https://schema.org", "@type": "CollectionPage", "name": L["liste_jsonld_nom"], "description": L["liste_description"],
              "inLanguage": L["langue_jsonld"], "url": D + base[lang], "publisher": publisher,
              "hasPart": [{"@type": "Article", "headline": a[lang]["titre"], "url": D + a["url"][lang], "datePublished": a["date"]} for a in arts]}
        wr(base[lang], light_page(site, lang, L["liste_titre"] + " | CHANCELENO", "index, follow", "", True, base, main,
                                  desc=L["liste_description"], alternates=base, og_title=L["liste_titre"], jsonld=ld))
        site.sitemap.append((base[lang], base, arts[0]["date"] if arts else None))
        # chaque article
        for a in arts:
            t = a[lang]
            src = rd(adir, a["id"], lang + ".html").rstrip("\n")
            src = re.sub(r'href="((?:/(?:en|pt))?/?#/[^"]*)"', lambda mm: 'href="%s"' % Rewriter(site, lang, "article", a["id"]).link(mm.group(1)), src)
            b1, b2 = L["byline"].split("|")
            li = site.config["reseaux"]["linkedin_profil"]
            author = '<a href="%s" target="_blank" rel="noopener author">Chano Chanceleno</a>' % esc(li) if li else "Chano Chanceleno"
            main = ('<article>\n<div class="pagehead"><div class="wrap">\n<a class="crumb" href="%s">%s</a>\n<h1>%s</h1>\n'
                    '<p class="byline">%s%s%s<time datetime="%s">%s</time></p>\n</div></div>\n<div class="article">\n%s\n</div>\n</article>') % (
                base[lang], esc(L["articles"]), esc(t["titre"]), b1, author, b2, a["date"], date_text(site, lang, a["date"]), src)
            person = {"@type": "Person", "name": "Chano Chanceleno", "jobTitle": t["fonction_auteur"]}
            if li:
                person.update({"url": li, "sameAs": [li]})
            ld = {"@context": "https://schema.org", "@type": "Article", "headline": t["titre"], "description": t["description"],
                  "inLanguage": L["langue_jsonld"], "datePublished": a["date"], "dateModified": a.get("modifie", a["date"]),
                  "image": [D + site.site["og_image"][lang]], "mainEntityOfPage": {"@type": "WebPage", "@id": D + a["url"][lang]},
                  "author": person, "publisher": publisher}
            wr(a["url"][lang], light_page(site, lang, t["titre"] + " | CHANCELENO", "index, follow", "", False, a["url"], main,
                                          desc=t["description"], alternates=a["url"], og_type="article", og_title=t["titre"], jsonld=ld))
            site.sitemap.append((a["url"][lang], a["url"], a.get("modifie", a["date"])))


def build_thanks(site):
    urls = {"fr": "/merci/", "en": "/en/thank-you/", "pt": "/pt/obrigado/"}
    for lang in LANGS:
        main = rd(CONTENT, "thanks", lang + ".html").rstrip("\n")
        main = main.replace('href="/"', 'href="%s"' % site.url("home", lang))
        wr(urls[lang], light_page(site, lang, site.light[lang]["merci_titre"] + " | CHANCELENO", "noindex, follow", "", False, urls, main,
                                  after_main='<script src="/assets/thanks.js" defer></script>\n'))


def build_404(site):
    main = ('<div class="pagehead"><div class="wrap">\n<h1>Page introuvable</h1>\n'
            '<p class="lead">Cette page n\'existe pas ou a changé d\'adresse. <span lang="en">This page does not exist or has moved.</span> '
            '<span lang="pt">Esta página não existe ou mudou de endereço.</span></p>\n</div></div>\n<div class="article">\n'
            '<p><a href="/">Accueil</a> · <a href="/devis/">Demander un devis</a></p>\n'
            '<p lang="en"><a href="/en/">Home</a> · <a href="/en/quote/">Request a quote</a></p>\n'
            '<p lang="pt"><a href="/pt/">Início</a> · <a href="/pt/cotacao/">Pedir cotação</a></p>\n</div>')
    page = light_page(site, "fr", "Page introuvable · Page not found · Página não encontrada | CHANCELENO", "noindex, follow", "", False,
                      {"fr": "/", "en": "/en/", "pt": "/pt/"}, main)
    wr("/404.html", page.replace('<script src="/assets/lang.js"></script>\n', ""))


# ---------------------------------------------------------------------------------------------------------------
# Fichiers générés : sitemap, redirections des anciennes adresses, chaînes du JavaScript
# ---------------------------------------------------------------------------------------------------------------
def build_sitemap(site):
    D = site.domain
    rows = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for loc, alts, date in site.sitemap:
        rows.append("  <url>\n    <loc>%s%s</loc>" % (D, loc))
        for l in LANGS:
            rows.append('    <xhtml:link rel="alternate" hreflang="%s" href="%s%s"/>' % (l, D, alts[l]))
        rows.append('    <xhtml:link rel="alternate" hreflang="x-default" href="%s%s"/>' % (D, alts["fr"]))
        if date:
            rows.append("    <lastmod>%s</lastmod>" % date)
        rows.append("  </url>")
    rows.append("</urlset>")
    wr("/sitemap.xml", "\n".join(rows) + "\n")


def build_redirect(site):
    routes = {pid: v for pid, v in site.pages.items() if not pid.startswith("secteur-") and (pid != "cgv" or site.cgv)}
    js = ("/* Fichier généré par tools/build.py. Anciennes adresses #/rubrique et langue mémorisée. */\n"
          "(function(){\n"
          "var R=%s;\n"
          "var lang=document.documentElement.lang;\n"
          "function saved(){try{return localStorage.getItem(\"ch_lang\")}catch(e){return null}}\n"
          "/* Ancienne adresse #/rubrique?param : redirection vers la vraie page (dans la langue mémorisée sur une page FR).\n"
          "   Vérifiée au chargement et quand seul le #… change (lien ancien suivi depuis une page du site). */\n"
          "function legacy(){var h=location.hash;if(!/^#\\//.test(h))return false;\n"
          " var s=h.slice(2),i=s.indexOf(\"?\"),name=(i<0?s:s.slice(0,i))||\"home\",q=i<0?\"\":s.slice(i+1);\n"
          " var L=lang,sv=saved();if(lang===\"fr\"&&(sv===\"en\"||sv===\"pt\"))L=sv;\n"
          " var p=new URLSearchParams(q),b=p.get(\"b\");p.delete(\"b\");var qs=p.toString();\n"
          " location.replace((R[name]||R.home)[L]+(qs?\"?\"+qs:\"\")+(b?\"#\"+b:\"\"));return true}\n"
          "window.addEventListener(\"hashchange\",legacy);\n"
          "if(legacy())return;\n"
          "/* Page française et langue EN ou PT choisie auparavant : page équivalente dans cette langue. */\n"
          "if(lang===\"fr\"){var sv=saved();if(sv===\"en\"||sv===\"pt\"){var a=document.querySelector('link[rel=\"alternate\"][hreflang=\"'+sv+'\"]');\n"
          " if(a){var u=new URL(a.href);if(u.pathname!==location.pathname){location.replace(u.pathname+location.search+location.hash);return}}}}\n"
          "/* Animation du logo : seulement à la première page de la visite (onglet). Ensuite, la classe ch-vu affiche\n"
          "   directement le logo complet (assets/site.css) ; le survol du logo rejoue l'animation (assets/site.js). */\n"
          "try{if(sessionStorage.getItem(\"ch_vu\"))document.documentElement.classList.add(\"ch-vu\");else sessionStorage.setItem(\"ch_vu\",\"1\")}catch(e){}\n"
          "})();\n") % json.dumps(routes, ensure_ascii=False, separators=(",", ":"))
    wr("/assets/redirect.js", js)


def build_strings(site):
    """Textes produits par le JavaScript (messages d'erreur, boutons…) : seulement ceux utilisés par site.js."""
    js = rd(STATIC, "assets", "site.js")
    used = {}
    # chaînes "…" du script ; commentaires et chaînes '…' lus à part pour ne pas décaler les guillemets
    tokens = re.findall(r'/\*.*?\*/|//[^\n]*|\'(?:[^\'\\\n]|\\.)*\'|"((?:[^"\\\n]|\\.)*)"', js, re.S)
    # appels __t("…") (y compris dans les gabarits `…${…}…`)
    tokens += re.findall(r'__t\("((?:[^"\\\n]|\\.)*)"\)', js)
    for lit in tokens:
        if not lit:
            continue
        try:
            k = norm(json.loads('"%s"' % lit))
        except ValueError:
            continue
        if k in site.i18n:
            used[k] = site.i18n[k]
            site.used.add(k)
    wr("/assets/strings.js", "/* Fichier généré par tools/build.py : traductions des textes affichés par site.js. */\n"
       "window.CH_STRINGS=%s;\n" % json.dumps(used, ensure_ascii=False, separators=(",", ":")))


def copy_static():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    shutil.copytree(STATIC, OUT)


def fill_static(site):
    """Fichiers copiés tels quels (scripts, security.txt) : marqueurs {{nom}} remplacés par les valeurs de config/site.yml."""
    for d, _, files in os.walk(OUT):
        for f in files:
            full = os.path.join(d, f)
            if f.endswith((".js", ".txt", ".css")):
                t = rd(full)
                if "{{" in t:
                    with open(full, "w", encoding="utf-8") as out:
                        out.write(site.fill(t, None))


def finish_photos():
    """Emplacements photo : seule la version WebP est publiée (l'original, souvent lourd, n'est pas copié)."""
    for folder in [""] + PHOTO_DIRS:
        d = os.path.join(OUT, "images", folder)
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            stem, ext = os.path.splitext(f)
            if (folder or stem.lower() == "accueil") and ext.lower() in PHOTO_EXT and os.path.isfile(os.path.join(d, stem + ".webp")):
                os.remove(os.path.join(d, f))


def leftovers():
    """Aucun marqueur {{nom}} ne doit rester dans le site généré."""
    bad = []
    for d, _, files in os.walk(OUT):
        for f in files:
            if f.endswith((".html", ".js", ".txt", ".xml", ".css")):
                for m in set(re.findall(r"\{\{[a-z_]+\}\}", rd(os.path.join(d, f)))):
                    bad.append("%s : %s" % (os.path.relpath(os.path.join(d, f), OUT), m))
    if bad:
        raise SystemExit("Marqueurs non remplacés :\n  - " + "\n  - ".join(sorted(bad)))


def main():
    global SITE
    copy_static()
    site = SITE = Site()
    fill_static(site)
    build_main(site)
    build_articles(site)
    build_thanks(site)
    build_404(site)
    build_sitemap(site)
    build_redirect(site)
    build_strings(site)
    finish_photos()
    leftovers()
    if site.missing:
        print("ERREUR : %d texte(s) français sans traduction EN/PT dans content/i18n.json :" % len(site.missing))
        for k, w in sorted(site.missing.items()):
            print("  - %r  (%s)" % (k, ", ".join(sorted(w))))
        sys.exit(1)
    unused = sorted(k for k in site.i18n if k not in site.used)
    if unused:
        print("Remarque : %d texte(s) de content/i18n.json ne sont plus utilisés (à supprimer) :" % len(unused))
        for k in unused:
            print("  - %r" % k)
    n = sum(len(fs) for _, _, fs in os.walk(OUT))
    print("Site généré dans _site/ : %d pages, %d fichiers." % (len(site.sitemap), n))
    if "--serve" in sys.argv:
        import http.server
        import functools
        print("Aperçu : http://localhost:8000  (Ctrl+C pour arrêter)")
        http.server.ThreadingHTTPServer(("", 8000), functools.partial(http.server.SimpleHTTPRequestHandler, directory=OUT)).serve_forever()


if __name__ == "__main__":
    main()
