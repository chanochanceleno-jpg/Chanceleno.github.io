// Tests de la normalisation et du contrôle du numéro de téléphone (static/assets/tel.js), sans navigateur :
//   node tel.test.js
const assert = require("assert");
const fs = require("fs");
const path = require("path");
const { telNorm, telCheck } = require("../static/assets/tel.js");

// indicatifs de config/site.yml (rubrique telephone)
const yml = fs.readFileSync(path.join(__dirname, "..", "config", "site.yml"), "utf8");
const CODES = [...yml.matchAll(/indicatif: "(\d+)"/g)].map(m => m[1]);
let checks = 0, fails = 0;
function t(label, got, want) {
  checks++;
  const sub = Object.fromEntries(Object.keys(want).map(k => [k, got[k]]));
  try { assert.deepStrictEqual(sub, want); } catch (e) { fails++; console.log("  ÉCHEC", label, "\n    obtenu  :", JSON.stringify(sub), "\n    attendu :", JSON.stringify(want)); }
}

assert.ok(CODES.length >= 25 && CODES.includes("244") && CODES.includes("971"), "liste des indicatifs lue dans config/site.yml");

// --- telNorm : nettoyage, 0 initial, format international
t("vide", telNorm("", "33", CODES), { ok: true, empty: true, full: "" });
t("espaces seuls", telNorm("   ", "", CODES), { ok: true, empty: true });
t("France, 0 initial et espaces", telNorm("06 12 34 56 78", "33", CODES), { ok: true, cc: "33", num: "612345678", full: "+33612345678" });
t("points", telNorm("06.12.34.56.78", "33", CODES), { ok: true, full: "+33612345678" });
t("tirets et parenthèses", telNorm("(06)-12-34-56-78", "33", CODES), { ok: true, full: "+33612345678" });
t("Angola sans 0", telNorm("923 456 789", "244", CODES), { ok: true, full: "+244923456789" });
t("espace insécable", telNorm("923 456 789", "244", CODES), { ok: true, full: "+244923456789" });
t("Italie : le 0 est conservé", telNorm("06 1234 5678", "39", CODES), { ok: true, full: "+390612345678" });

// --- +xxx et 00xxx : indicatif reconnu (remplace celui du sélecteur)
t("+244 reconnu", telNorm("+244 923 456 789", "33", CODES), { ok: true, intl: true, cc: "244", num: "923456789", full: "+244923456789" });
t("00244 reconnu", telNorm("00244923456789", "", CODES), { ok: true, intl: true, cc: "244", full: "+244923456789" });
t("+33 (0)6 …", telNorm("+33 (0)6 12 34 56 78", "", CODES), { ok: true, cc: "33", full: "+33612345678" });
t("+351 Portugal", telNorm("+351 912 345 678", "", CODES), { ok: true, cc: "351", full: "+351912345678" });
t("+971 Émirats", telNorm("+971 50 123 4567", "", CODES), { ok: true, cc: "971", full: "+971501234567" });
t("+55 Brésil", telNorm("+55 11 91234 5678", "", CODES), { ok: true, cc: "55", full: "+5511912345678" });
t("+243 RD Congo, pas +24", telNorm("+243 81 234 5678", "", CODES), { ok: true, cc: "243" });
t("+7 inconnu", telNorm("+7 912 345 67 89", "33", CODES), { ok: false, error: "inconnu" });

// --- contrôle : 6 à 14 chiffres après l'indicatif
t("5 chiffres : trop court", telNorm("12345", "33", CODES), { ok: false, error: "longueur" });
t("6 chiffres : accepté", telNorm("123456", "33", CODES), { ok: true, full: "+33123456" });
t("14 chiffres : accepté", telNorm("12345678901234", "33", CODES), { ok: true });
t("15 chiffres : trop long", telNorm("123456789012345", "33", CODES), { ok: false, error: "longueur" });
t("0 + 6 chiffres : 6 après retrait du 0", telNorm("0123456", "33", CODES), { ok: true, num: "123456" });
t("0 + 5 chiffres : trop court", telNorm("012345", "33", CODES), { ok: false, error: "longueur" });
t("+244 trop court", telNorm("+244 12345", "", CODES), { ok: false, error: "longueur", cc: "244" });
t("lettres", telNorm("06 12 AB 56 78", "33", CODES), { ok: false, error: "chiffres" });
t("+ au milieu", telNorm("06+12345678", "33", CODES), { ok: false, error: "chiffres" });
t("sans indicatif", telNorm("612345678", "", CODES), { ok: false, error: "indicatif" });

// --- telCheck : sélecteur (« », indicatif, « autre ») et indicatif libre
t("sélecteur France", telCheck("0612345678", "33", "", CODES), { ok: true, full: "+33612345678" });
t("aucun choix, numéro vide", telCheck("", "", "", CODES), { ok: true, empty: true, full: "" });
t("aucun choix, numéro national", telCheck("612345678", "", "", CODES), { ok: false, error: "indicatif" });
t("aucun choix, +244", telCheck("+244923456789", "", "", CODES), { ok: true, cc: "244" });
t("Autre +7", telCheck("912 345 67 89", "autre", "+7", CODES), { ok: true, cc: "7", full: "+79123456789" });
t("Autre 007", telCheck("9123456789", "autre", "007", CODES), { ok: true, full: "+79123456789" });
t("Autre 1 et +1 …", telCheck("+1 212 555 0100", "autre", "1", CODES), { ok: true, cc: "1", full: "+12125550100" });
t("Autre vide", telCheck("9123456789", "autre", "", CODES), { ok: false, error: "autre" });
t("Autre invalide", telCheck("9123456789", "autre", "+12345", CODES), { ok: false, error: "autre" });
t("Autre vide, +244 connu", telCheck("+244923456789", "autre", "", CODES), { ok: true, cc: "244" });
t("Autre vide, numéro vide", telCheck("", "autre", "", CODES), { ok: true, empty: true });

console.log(fails ? "ÉCHECS : " + fails + " sur " + checks + " contrôles" : "TOUT OK : " + checks + " contrôles (telNorm, telCheck)");
process.exit(fails ? 1 : 0);
