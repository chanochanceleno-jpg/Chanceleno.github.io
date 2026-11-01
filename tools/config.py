"""Lecture et vérification de config/site.yml (données modifiables du site).

Utilisé par tools/build.py, tools/check.py et tools/surveillance.py. Toute erreur arrête la génération avec un
message en français qui indique la rubrique et le champ à corriger.

    python3 tools/config.py       # vérifie seulement le fichier
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "config", "site.yml")
LANGS = ["fr", "en", "pt"]


def oui(v, champ, errors):
    """oui / non (ou true / false) -> booléen."""
    if isinstance(v, bool):
        return v
    if str(v).strip().lower() in ("oui", "non"):
        return str(v).strip().lower() == "oui"
    errors.append("%s : écrire oui ou non (valeur actuelle : %r)" % (champ, v))
    return False


def text(v, champ, errors, obligatoire=False):
    if v is None:
        v = ""
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        v = str(v)
    if not isinstance(v, str):
        errors.append("%s : texte attendu entre guillemets (valeur actuelle : %r)" % (champ, v))
        return ""
    v = v.strip()
    if obligatoire and not v:
        errors.append("%s : champ obligatoire, actuellement vide" % champ)
    return v


def per_lang(v, champ, errors, obligatoire=True, langues=LANGS):
    """Texte en fr / en / pt. Un texte unique (sans fr/en/pt) vaut pour les trois langues."""
    if isinstance(v, str) or v is None:
        v = {l: v for l in LANGS}
    if not isinstance(v, dict):
        errors.append("%s : écrire {fr: \"…\", en: \"…\", pt: \"…\"}" % champ)
        return {l: "" for l in LANGS}
    extra = set(v) - set(LANGS)
    if extra:
        errors.append("%s : langue inconnue %s (seules fr, en et pt sont possibles)" % (champ, ", ".join(sorted(map(str, extra)))))
    return {l: text(v.get(l), "%s.%s" % (champ, l), errors, obligatoire and l in langues) for l in LANGS}


def date(v, champ, errors):
    v = text(v, champ, errors)
    if v and not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
        errors.append("%s : date au format AAAA-MM-JJ attendue, ex. 2026-11-05 (valeur actuelle : %r)" % (champ, v))
    return v


def url(v, champ, errors):
    v = text(v, champ, errors)
    if v and not re.match(r"^https://[^\s\"'<>]+\.[^\s\"'<>]+$", v):
        errors.append("%s : adresse complète commençant par https:// attendue (valeur actuelle : %r)" % (champ, v))
    return v


def phone(v, champ, errors):
    v = text(v, champ, errors, True)
    if v and not re.match(r"^\+[1-9][\d ]{6,18}\d$", v):
        errors.append("%s : numéro avec indicatif attendu, ex. \"+33 6 12 34 56 78\" (valeur actuelle : %r)" % (champ, v))
    return v


def number(v, champ, errors, entier=False):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v <= 0 or (entier and v != int(v)):
        errors.append("%s : nombre %spositif attendu, sans unité (valeur actuelle : %r)" % (champ, "entier " if entier else "", v))
        return 0
    return int(v) if v == int(v) else v


def section(cfg, name, errors, kind=dict):
    v = cfg.get(name)
    if v is None:
        return kind()
    if not isinstance(v, kind):
        errors.append("%s : rubrique mal écrite (voir l'exemple dans README.md)" % name)
        return kind()
    return v


def load(path=CONFIG):
    """Renvoie la configuration vérifiée et complétée, ou arrête avec la liste des erreurs."""
    try:
        import yaml
    except ImportError:
        raise SystemExit("Le module PyYAML est nécessaire : python3 -m pip install -r tools/requirements.txt")
    try:
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise SystemExit("config/site.yml n'est pas un fichier YAML valide (souvent : guillemet ou espace manquant) :\n%s" % e)
    if not isinstance(raw, dict):
        raise SystemExit("config/site.yml doit contenir des rubriques (clé: valeur)")
    errors = []
    cfg = {}

    # identité
    ident = section(raw, "identite", errors)
    ao, fr = section(ident, "angola", errors), section(ident, "france", errors)
    cfg["editeur"] = text(ident.get("editeur"), "identite.editeur", errors, True)
    if cfg["editeur"] not in ("angola", "france"):
        errors.append("identite.editeur : écrire angola ou france (valeur actuelle : %r)" % cfg["editeur"])
    cfg["directeur"] = text(ident.get("directeur_publication"), "identite.directeur_publication", errors, True)
    cfg["angola"] = {k: text(ao.get(k), "identite.angola." + k, errors, True) for k in ("denomination", "adresse", "ville", "nif")}
    cfg["angola"]["date_creation"] = date(ao.get("date_creation"), "identite.angola.date_creation", errors)
    f = {k: text(fr.get(k), "identite.france." + k, errors, k in ("denomination", "ville"))
         for k in ("denomination", "forme", "adresse", "ville", "siren", "rcs", "tva", "capital", "president")}
    f["date_immatriculation"] = date(fr.get("date_immatriculation"), "identite.france.date_immatriculation", errors)
    f["immatriculee"] = bool(f["siren"])
    if f["siren"]:
        if not re.match(r"^\d{9}$", f["siren"].replace(" ", "")):
            errors.append("identite.france.siren : 9 chiffres attendus, ex. \"123 456 789\" (valeur actuelle : %r)" % f["siren"])
        for k in ("forme", "adresse", "rcs", "capital", "president"):
            if not f[k]:
                errors.append("identite.france.%s : obligatoire dès que le SIREN est rempli (voir le Kbis)" % k)
    if f["tva"] and not re.match(r"^FR[0-9A-Z]{2}\d{9}$", f["tva"].replace(" ", "")):
        errors.append("identite.france.tva : numéro de TVA français attendu, ex. \"FR12123456789\" (valeur actuelle : %r)" % f["tva"])
    if cfg["editeur"] == "france" and not f["immatriculee"]:
        errors.append("identite.editeur : « france » n'est possible qu'une fois le SIREN de la société française rempli")
    cfg["france"] = f

    # coordonnées
    co = section(raw, "coordonnees", errors)
    cfg["email"] = text(co.get("email"), "coordonnees.email", errors, True)
    if cfg["email"] and not re.match(r"^[a-z0-9._+-]+@[a-z0-9-]+(\.[a-z0-9-]+)+$", cfg["email"]):
        errors.append("coordonnees.email : adresse email attendue, en minuscules (valeur actuelle : %r)" % cfg["email"])
    cfg["formsubmit"] = text(co.get("formsubmit"), "coordonnees.formsubmit", errors, True)
    if cfg["formsubmit"] and not re.match(r"^[a-f0-9]{32}$", cfg["formsubmit"]):
        errors.append("coordonnees.formsubmit : identifiant de 32 caractères (chiffres et lettres a à f) attendu")
    cfg["wa_europe"] = phone(co.get("whatsapp_europe"), "coordonnees.whatsapp_europe", errors)
    cfg["wa_afrique"] = phone(co.get("whatsapp_afrique"), "coordonnees.whatsapp_afrique", errors)

    # réseaux sociaux (vide = non affiché)
    rs = section(raw, "reseaux", errors)
    cfg["reseaux"] = {k: url(rs.get(k), "reseaux." + k, errors) for k in ("linkedin_profil", "linkedin_page", "instagram", "facebook",
                                                                                "youtube", "tiktok")}
    for k in set(rs) - set(cfg["reseaux"]):
        errors.append("reseaux.%s : réseau inconnu (possibles : %s)" % (k, ", ".join(cfg["reseaux"])))

    # tarifs
    ta = section(raw, "tarifs", errors)
    cfg["prix_audit"] = number(ta.get("prix_audit_ht"), "tarifs.prix_audit_ht", errors)
    cfg["delai_rapport"] = number(ta.get("delai_rapport_h"), "tarifs.delai_rapport_h", errors, True)
    cfg["delai_reponse"] = number(ta.get("delai_reponse_h"), "tarifs.delai_reponse_h", errors, True)

    # cartes Marchés
    cards, seen = [], set()
    for i, c in enumerate(section(raw, "marches", errors, list)):
        where = "marches, carte %d" % (i + 1)
        if not isinstance(c, dict):
            errors.append("%s : carte mal écrite (voir l'exemple dans README.md)" % where)
            continue
        cid = text(c.get("id"), where + " : id", errors, True)
        if cid and not re.match(r"^[a-z0-9-]+$", cid):
            errors.append("%s : id en minuscules, chiffres et tirets seulement (valeur actuelle : %r)" % (where, cid))
        if cid in seen:
            errors.append("%s : id %r déjà utilisé par une autre carte" % (where, cid))
        seen.add(cid)
        liens = c.get("liens") or []
        if not isinstance(liens, list) or not all(isinstance(x, str) and re.match(r"^(article|secteur|page):[a-z0-9-]+$", x) for x in liens):
            errors.append("%s : liens attendus sous la forme [article:<dossier>, secteur:<adresse>, page:<page>] (valeur actuelle : %r)"
                          % (where, c.get("liens")))
            liens = []
        cards.append({"id": cid, "affiche": oui(c.get("affiche", "oui"), where + " : affiche", errors), "liens": liens,
                      **{k: per_lang(c.get(k), "%s : %s" % (where, k), errors) for k in ("role", "titre", "texte")}})
    cfg["marches"] = cards

    # références clients
    refs = []
    for i, r in enumerate(section(raw, "references", errors, list)):
        where = "references, référence %d" % (i + 1)
        if not isinstance(r, dict):
            errors.append("%s : référence mal écrite (voir l'exemple dans README.md)" % where)
            continue
        ref = {"nom": text(r.get("nom"), where + " : nom", errors, True),
               "secteur": per_lang(r.get("secteur"), where + " : secteur", errors, False),
               "pays": per_lang(r.get("pays"), where + " : pays", errors, False),
               "temoignage": per_lang(r.get("temoignage"), where + " : temoignage", errors, True, ["fr"]),
               "photo": text(r.get("photo"), where + " : photo", errors),
               "autorisation": oui(r.get("autorisation", "non"), where + " : autorisation", errors)}
        if ref["photo"]:
            if not re.match(r"^[A-Za-z0-9._-]+\.(jpe?g|png)$", ref["photo"], re.I):
                errors.append("%s : photo = nom de fichier JPG ou PNG, sans dossier ni espace (ex. \"client-x.jpg\")" % where)
            elif not os.path.isfile(os.path.join(ROOT, "static", "images", "references", ref["photo"])):
                errors.append("%s : photo introuvable : static/images/references/%s" % (where, ref["photo"]))
        refs.append(ref)
    cfg["references"] = refs

    # photos
    ph = section(raw, "photos", errors)
    cfg["accueil_description"] = per_lang(ph.get("accueil_description"), "photos.accueil_description", errors, False)

    # statistiques
    code = text(section(raw, "statistiques", errors).get("goatcounter"), "statistiques.goatcounter", errors)
    if code and not re.match(r"^[a-z0-9-]+$", code):
        errors.append("statistiques.goatcounter : code en minuscules, chiffres et tirets (valeur actuelle : %r)" % code)
    cfg["goatcounter"] = code

    # indicatifs téléphoniques des formulaires Devis et Partenaires
    tel = section(raw, "telephone", errors)
    codes, seen = [], set()
    for i, c in enumerate(tel.get("indicatifs") or []):
        where = "telephone.indicatifs, ligne %d" % (i + 1)
        if not isinstance(c, dict):
            errors.append("%s : écrire {pays: AO, indicatif: \"244\", nom: \"Angola\"}" % where)
            continue
        pays = text(c.get("pays"), where + " : pays", errors, True)
        if pays and not re.match(r"^[A-Z]{2}$", pays):
            errors.append("%s : pays = code de 2 lettres majuscules, ex. AO (valeur actuelle : %r)" % (where, pays))
        if pays in seen:
            errors.append("%s : pays %r déjà dans la liste" % (where, pays))
        seen.add(pays)
        ind = text(c.get("indicatif"), where + " : indicatif", errors, True).lstrip("+")
        if ind and not re.match(r"^[1-9]\d{0,3}$", ind):
            errors.append("%s : indicatif = 1 à 4 chiffres, sans + ni 00, ex. \"244\" (valeur actuelle : %r)" % (where, ind))
        codes.append({"pays": pays, "indicatif": ind, "nom": per_lang(c.get("nom"), where + " : nom", errors)})
    if not codes:
        errors.append("telephone.indicatifs : la liste des indicatifs est vide")
    defaut = tel.get("par_defaut") or {}
    if not isinstance(defaut, dict):
        errors.append("telephone.par_defaut : écrire {fr: FR, en: \"\", pt: AO}")
        defaut = {}
    cfg["tel_defaut"] = {l: text(defaut.get(l), "telephone.par_defaut." + l, errors) for l in LANGS}
    for l, v in cfg["tel_defaut"].items():
        if v and v not in seen:
            errors.append("telephone.par_defaut.%s : %r n'est pas dans la liste des indicatifs" % (l, v))
    cfg["indicatifs"] = codes

    known = {"identite", "coordonnees", "reseaux", "tarifs", "marches", "references", "photos", "statistiques", "telephone"}
    for k in set(raw) - known:
        errors.append("%s : rubrique inconnue (vérifier l'orthographe)" % k)
    if errors:
        raise SystemExit("ERREUR dans config/site.yml (%d point(s) à corriger) :\n  - %s" % (len(errors), "\n  - ".join(errors)))
    return cfg


if __name__ == "__main__":
    load(sys.argv[1] if len(sys.argv) > 1 else CONFIG)
    print("config/site.yml : OK")
