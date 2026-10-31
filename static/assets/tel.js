/* Numéro de téléphone avec indicatif pays (formulaires Devis et Partenaires).
   Fonctions pures, sans accès à la page : utilisées par assets/site.js et testées sous Node (tests/tel.test.js).
   telNorm(saisie, indicatif, indicatifsConnus) -> {ok, empty, intl, cc, num, full, error}
     - retire espaces, points, tirets et parenthèses, puis le 0 initial (sauf Italie, +39, où il fait partie du numéro) ;
     - « +xxx… » ou « 00xxx… » : l'indicatif est reconnu parmi les indicatifs connus (il remplace celui du sélecteur) ;
     - 6 à 14 chiffres attendus après l'indicatif ; full = numéro international, ex. +244923456789 ;
     - champ vide : ok (le numéro est facultatif).
   error : "indicatif" (aucun indicatif choisi), "inconnu" (+xxx non reconnu), "chiffres" (autre chose que des
   chiffres), "longueur" (moins de 6 ou plus de 14 chiffres) ; telCheck ajoute "autre" (indicatif libre invalide). */
(function (root) {
  "use strict";
  var MIN = 6, MAX = 14;
  function clean(s) { return String(s == null ? "" : s).trim().replace(/[\s.()\-‐-―]/g, ""); }
  function validCode(c) { return /^[1-9]\d{0,3}$/.test(c); }

  function telNorm(raw, cc, codes) {
    var s = clean(raw), intl = false;
    cc = cc ? String(cc) : "";
    var r = { ok: false, empty: false, intl: false, cc: cc, num: "", full: "", error: null };
    if (!s) { r.ok = true; r.empty = true; return r; }
    if (s.charAt(0) === "+") { intl = true; s = s.slice(1); }
    else if (s.slice(0, 2) === "00") { intl = true; s = s.slice(2); }
    r.intl = intl;
    if (!/^\d+$/.test(s)) { r.error = "chiffres"; return r; }
    if (intl) {
      var list = (codes || []).filter(validCode).sort(function (a, b) { return b.length - a.length; }), k = null;
      for (var i = 0; i < list.length; i++) if (s.indexOf(list[i]) === 0) { k = list[i]; break; }
      if (!k) { r.error = "inconnu"; return r; }
      cc = r.cc = k; s = s.slice(k.length);
    }
    if (!validCode(cc)) { r.error = "indicatif"; return r; }
    if (cc !== "39") s = s.replace(/^0/, "");
    r.num = s; r.full = "+" + cc + s;
    if (s.length < MIN || s.length > MAX) { r.error = "longueur"; return r; }
    r.ok = true;
    return r;
  }

  /* Contrôle du champ complet : choix du sélecteur ("" | indicatif | "autre") et indicatif saisi librement pour « Autre ». */
  function telCheck(raw, choice, custom, codes) {
    var list = (codes || []).slice(), cc = choice === "autre" ? "" : (choice || "");
    if (choice === "autre") {
      var x = clean(custom).replace(/^(\+|00)/, "");
      if (validCode(x)) { cc = x; list.push(x); }
    }
    var r = telNorm(raw, cc, list);
    if (!r.ok && choice === "autre" && !cc && (r.error === "indicatif" || r.error === "inconnu")) r.error = "autre";
    return r;
  }

  var api = { telNorm: telNorm, telCheck: telCheck, MIN: MIN, MAX: MAX };
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.chTel = api;
})(this);
