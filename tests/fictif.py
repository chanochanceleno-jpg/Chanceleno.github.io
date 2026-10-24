#!/usr/bin/env python3
"""Test des données modifiables avec des valeurs FICTIVES (Kbis, photos, références, réseau social vidé, CGV, tarifs).

Remplace temporairement config/site.yml, ajoute des photos et des CGV de test, génère et contrôle le site, lance
tests/lot5.test.js (MODE=fictif), puis remet TOUT en l'état, même en cas d'échec. Rien n'est publié.

    python3 tests/fictif.py            # nécessite Playwright (voir tests/package.json)

Teste aussi que des erreurs volontaires dans config/site.yml bloquent la génération avec un message clair.
"""
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "config", "site.yml")
IMAGES = os.path.join(ROOT, "static", "images")
LEGAL = os.path.join(ROOT, "content", "legal")
PORT = 8768

PHOTOS = {"accueil.jpg": (1600, 1200), "secteurs/sante-laboratoire.jpg": (2400, 1200), "marches/luanda.jpg": (1800, 1200),
          "references/client-test.png": (400, 200)}
CGV = {"fr": "<h3>Article 1 — Objet (TEXTE DE TEST)</h3><p>Texte fictif de test, à ne pas publier.</p>",
       "en": "<h3>Article 1 — Purpose (TEST TEXT)</h3><p>Fictitious test text, not to be published.</p>",
       "pt": "<h3>Artigo 1 — Objeto (TEXTO DE TESTE)</h3><p>Texto fictício de teste, não publicar.</p>"}


def fictitious(text):
    """Valeurs fictives, clairement marquées comme telles."""
    rep = [
        ('  editeur: angola', '  editeur: france'),
        ('    forme: ""', '    forme: "SASU"'),
        ('    adresse: ""                        # adresse du siège', '    adresse: "1 rue de l\'Exemple, 69001 Lyon, France"  #'),
        ('    siren: ""', '    siren: "123 456 789"'),
        ('    rcs: ""', '    rcs: "Lyon 123 456 789"'),
        ('    tva: ""', '    tva: "FR12123456789"'),
        ('    capital: ""', '    capital: "1 000 €"'),
        ('    president: ""', '    president: "Président Fictif"'),
        ('    date_immatriculation: ""', '    date_immatriculation: "2026-11-02"'),
        ('  youtube: "https://www.youtube.com/@Chanceleno"', '  youtube: ""'),
        ('  prix_audit_ht: 250', '  prix_audit_ht: 300'),
        ('  delai_reponse_h: 48', '  delai_reponse_h: 24'),
        ('''  - id: devises
    affiche: oui''', '''  - id: devises
    affiche: non'''),
        ('references: []', '''references:
  - nom: "Client Fictif Autorisé SA"
    secteur: {fr: "Santé et laboratoire", en: "Health and laboratory", pt: "Saúde e laboratório"}
    pays: "Angola"
    temoignage:
      fr: "Témoignage fictif de test, autorisé."
      en: "Fictitious test testimonial, authorised."
    photo: "client-test.png"
    autorisation: oui
  - nom: "Client Fictif Non Autorisé"
    secteur: "Mines"
    pays: "RDC"
    temoignage: {fr: "Ce témoignage ne doit jamais apparaître.", en: "Must never appear.", pt: "Nunca deve aparecer."}
    autorisation: non'''),
        ('''  accueil_description:
    fr: ""
    en: ""
    pt: ""''', '''  accueil_description:
    fr: "Photo de test de l'accueil"
    en: "Home test photo"
    pt: "Foto de teste da página inicial"'''),
    ]
    for a, b in rep:
        assert text.count(a) == 1, a
        text = text.replace(a, b)
    return text


def build():
    return subprocess.run([sys.executable, os.path.join(ROOT, "tools", "build.py")], capture_output=True, text=True)


def main():
    from PIL import Image, ImageDraw
    original = open(CONFIG, encoding="utf-8").read()
    cgv_orig = {l: open(os.path.join(LEGAL, "cgv.%s.html" % l), encoding="utf-8").read() for l in CGV}
    created = []
    server = None
    fails = 0
    try:
        # 1. erreurs volontaires : la génération doit s'arrêter avec un message clair
        for bad, expected in [(('    siren: ""', '    siren: "12345"'), "identite.france.siren : 9 chiffres attendus"),
                              (('  youtube: "https://www.youtube.com/@Chanceleno"', '  youtube: "youtube.com/@x"'), "reseaux.youtube : adresse complète commençant par https://"),
                              (('  prix_audit_ht: 250', '  prix_audit_ht: "250 €"'), "tarifs.prix_audit_ht : nombre positif attendu"),
                              (('  editeur: angola', '  editeur: france'), "« france » n'est possible qu'une fois le SIREN")]:
            open(CONFIG, "w", encoding="utf-8").write(original.replace(*bad))
            r = build()
            ok = r.returncode != 0 and expected in (r.stdout + r.stderr)
            fails += not ok
            print("  %s erreur volontaire : %s" % ("OK" if ok else "ÉCHEC", expected))
        # 2. valeurs fictives
        open(CONFIG, "w", encoding="utf-8").write(fictitious(original))
        for name, (w, h) in PHOTOS.items():
            p = os.path.join(IMAGES, name)
            if os.path.dirname(name) and not os.path.isdir(os.path.dirname(p)):
                os.makedirs(os.path.dirname(p))
                created.append(os.path.dirname(p))
            im = Image.new("RGB", (w, h), (34, 70, 96))
            ImageDraw.Draw(im).rectangle([w // 8, h // 8, w * 7 // 8, h * 7 // 8], outline=(217, 137, 79), width=max(4, w // 80))
            im.save(p)
            created.insert(0, p)
        for l, t in CGV.items():
            open(os.path.join(LEGAL, "cgv.%s.html" % l), "w", encoding="utf-8").write(cgv_orig[l] + t + "\n")
        r = build()
        print(r.stdout[-400:] + r.stderr[-2000:])
        if r.returncode:
            raise SystemExit("ÉCHEC : génération avec les valeurs fictives")
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "check.py")], capture_output=True, text=True)
        print(r.stdout + r.stderr)
        fails += r.returncode != 0
        server = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--directory", os.path.join(ROOT, "_site")],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1)
        env = dict(os.environ, MODE="fictif", BASE="http://localhost:%d" % PORT)
        r = subprocess.run(["node", os.path.join(ROOT, "tests", "lot5.test.js")], env=env)
        fails += r.returncode != 0
    finally:
        if server:
            server.terminate()
        open(CONFIG, "w", encoding="utf-8").write(original)
        for l, t in cgv_orig.items():
            open(os.path.join(LEGAL, "cgv.%s.html" % l), "w", encoding="utf-8").write(t)
        for p in created:
            if os.path.isdir(p):
                shutil.rmtree(p)
            elif os.path.exists(p):
                os.remove(p)
        r = build()
        print("Configuration réelle remise en place ; site régénéré :", (r.stdout or r.stderr).strip().splitlines()[-1])
    print("TOUT OK" if not fails else "ÉCHECS : %d" % fails)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
