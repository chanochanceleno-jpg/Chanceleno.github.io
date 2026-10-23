#!/usr/bin/env python3
"""Fabrique les polices légères du site (WOFF2) à partir des fichiers d'origine de sources/fonts/.

À relancer uniquement si l'on change de police ou si le site doit afficher des caractères nouveaux
(autres que ceux du français, de l'anglais et du portugais). Le résultat est enregistré dans static/fonts/.

    python3 -m pip install fonttools==4.60.1 brotli==1.1.0
    python3 tools/fonts.py
"""
import os
import subprocess
import sys
import tempfile

from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "sources", "fonts")
OUT = os.path.join(ROOT, "static", "fonts")
# Caractères latins (français, anglais, portugais), ponctuation typographique, € et flèches.
UNICODES = ("U+0020-007E,U+00A0-00FF,U+0100-017F,U+0152-0153,U+02C6,U+02DA,U+02DC,U+2000-206F,U+20AC,"
            "U+2122,U+2190-2193,U+2212,U+FEFF,U+FFFD")
# Plages réellement utilisées par les styles : graisses (wght), largeur (wdth, le logo utilise 118 %),
# taille optique (opsz) de Newsreader.
FONTS = {
    "Archivo": {"wght": (400, 700), "wdth": (100, 125)},
    "Newsreader": {"wght": 400, "opsz": (12, 72)},
}


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, axes in FONTS.items():
        font = instancer.instantiateVariableFont(TTFont(os.path.join(SRC, name + ".ttf")), axes)
        with tempfile.TemporaryDirectory() as tmp:
            reduced = os.path.join(tmp, name + ".ttf")
            font.save(reduced)
            out = os.path.join(OUT, name + ".woff2")
            subprocess.run([sys.executable, "-m", "fontTools.subset", reduced, "--unicodes=" + UNICODES,
                            "--layout-features=*", "--flavor=woff2", "--output-file=" + out], check=True)
        print("%s : %d Ko" % (os.path.relpath(out, ROOT), os.path.getsize(out) // 1024))


if __name__ == "__main__":
    main()
