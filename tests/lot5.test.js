// Tests du lot 5 (données modifiables dans config/site.yml), à 360, 412, 1024, 1280 et 1440 px, en FR, EN et PT.
//   MODE=reel   (par défaut) : configuration réelle ; logo animé seulement à la 1re page de la visite.
//   MODE=fictif : lancé par tests/fictif.py avec des valeurs fictives (Kbis, photos, références, Instagram, CGV…).
//   BASE=http://localhost:8765 node lot5.test.js        SHOTS=dossier pour des captures à 360 px
const { chromium } = require(process.env.PW || "playwright");
const fs = require("fs");
const path = require("path");

const BASE = process.env.BASE || "http://localhost:8765";
const MODE = process.env.MODE || "reel";
const WIDTHS = (process.env.WIDTHS || "360,412,768,1024,1280,1440").split(",").map(Number);
const SHOTS = process.env.SHOTS || "";
const SITE = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "content", "site.json"), "utf8"));
const U = (pid, lang) => SITE.pages[pid][lang].chemin;
const LANGS = ["fr", "en", "pt"];
const YEAR = String(new Date().getFullYear());
let fails = 0, checks = 0;
const ok = (c, m) => { checks++; if (!c) { fails++; console.log("  ÉCHEC", m); } };

async function page(b, w) {
  const ctx = await b.newContext({ viewport: { width: w, height: 800 } });
  await ctx.addInitScript(() => { window.__csp = []; document.addEventListener("securitypolicyviolation", e => window.__csp.push(e.violatedDirective + " " + e.blockedURI)); });
  await ctx.route(/formsubmit\.co/, r => r.fulfill({ status: 200, contentType: "application/json", body: '{"success":"true"}' }));
  await ctx.route(/goatcounter\.com/, r => r.fulfill({ status: 200, body: "" }));
  const p = await ctx.newPage();
  p.errs = [];
  p.on("pageerror", e => p.errs.push(e.message));
  p.on("console", m => { if (m.type() === "error") p.errs.push(m.text()); });
  return p;
}
async function go(p, url, label) {
  const r = await p.goto(BASE + url);
  ok(r && r.status() === 200, label + " : code " + (r && r.status()));
  const h = await p.evaluate(() => ({ csp: window.__csp, sw: document.documentElement.scrollWidth, iw: innerWidth }));
  ok(h.csp.length === 0, label + " : CSP " + h.csp.join(" | "));
  ok(h.sw <= h.iw, label + " : débordement horizontal " + h.sw + " > " + h.iw);
  ok(p.errs.length === 0, label + " : erreur JS " + p.errs.join(" | ")); p.errs.length = 0;
}
const text = (p, sel) => p.$eval(sel, e => e.innerText.replace(/\s+/g, " ").trim()).catch(() => "");
// image chargée (après défilement jusqu'à elle : les images hors du premier écran sont en chargement différé)
const loaded = async (p, sel, webp = true) => {
  const el = await p.$(sel); if (!el) return false;
  await el.scrollIntoViewIfNeeded(); await p.waitForFunction(i => i.complete, el, { timeout: 5000 }).catch(() => {});
  return el.evaluate((i, w) => i.complete && i.naturalWidth > 0 && (!w || /\.webp$/.test(i.src)), webp);
};
const jsonld = p => p.$eval('script[type="application/ld+json"]', s => JSON.parse(s.textContent)).catch(() => ({}));
const shot = async (p, name) => { if (SHOTS) { fs.mkdirSync(SHOTS, { recursive: true }); await p.screenshot({ path: path.join(SHOTS, name + ".png"), fullPage: true }); } };

const PAGES = ["home", "marches", "mentions", "confidentialite", "contact", "devis", "cookies"];

// Identité légale réelle (config/site.yml) : société française éditrice et structure angolaise
const FR_ID = {
  fr: "CHANCELENO INTERNATIONAL – SAS à associé unique au capital de 1 000 € – RCS Lyon 133 060 319 – Siège : 12 rue de la Part-Dieu, 69003 Lyon",
  en: "CHANCELENO INTERNATIONAL – SAS à associé unique with share capital of 1 000 € – RCS Lyon 133 060 319 – Registered office: 12 rue de la Part-Dieu, 69003 Lyon",
  pt: "CHANCELENO INTERNATIONAL – SAS à associé unique com capital social de 1 000 € – RCS Lyon 133 060 319 – Sede: 12 rue de la Part-Dieu, 69003 Lyon" };
const AO_ID = "CHANCELENO – COMÉRCIO GERAL, (SU), LDA – Kilamba, Luanda, Angola – NIF 5003018334.";
const NO_VAT = /TVA|VAT|IVA intra|immatricul|being registered|processo de registo/;

// Réseaux sociaux officiels : ordre, libellés, attributs, taille des zones cliquables (44 × 44 px)
const SOCIAL = [["https://www.linkedin.com/company/chanceleno/", "LinkedIn"], ["https://www.instagram.com/chanceleno_international/", "Instagram"],
  ["https://www.facebook.com/profile.php?id=1149213368276296", "Facebook"], ["https://www.youtube.com/@Chanceleno", "YouTube"],
  ["https://www.tiktok.com/@chano.chanceleno", "TikTok"]];
const LABEL = (lang, name) => name === "TikTok" ? { fr: "Chano Chanceleno, fondateur, sur TikTok", en: "Chano Chanceleno, founder, on TikTok", pt: "Chano Chanceleno, fundador, no TikTok" }[lang]
  : { fr: "CHANCELENO sur ", en: "CHANCELENO on ", pt: "CHANCELENO no " }[lang] + name;
async function socials(p, sel, lang, L, expected = SOCIAL) {
  const s = await p.$$eval(sel + " .socials a", a => a.map(x => { x.scrollIntoView(); const r = x.getBoundingClientRect(), svg = x.querySelector("svg");
    return { href: x.getAttribute("href"), label: x.getAttribute("aria-label"), target: x.target, rel: x.rel, w: r.width, h: r.height,
      svg: svg && svg.getAttribute("aria-hidden") === "true" && svg.getAttribute("focusable") === "false" && svg.getAttribute("fill") === "currentColor" }; }));
  ok(JSON.stringify(s.map(x => x.href)) === JSON.stringify(expected.map(x => x[0])), L + " " + sel + " : liens des réseaux dans l'ordre " + JSON.stringify(s.map(x => x.href)));
  ok(s.every((x, i) => expected[i] && x.label === LABEL(lang, expected[i][1])), L + " " + sel + " : aria-label des réseaux");
  ok(s.every(x => x.target === "_blank" && x.rel === "noopener noreferrer" && x.svg), L + " " + sel + " : target, rel et SVG des réseaux");
  ok(s.every(x => x.w >= 44 && x.h >= 44), L + " " + sel + " : zones cliquables d'au moins 44 × 44 px");
}

// Contraste des icônes réseaux (WCAG 1.4.11, éléments non textuels : au moins 3:1) : couleur calculée et opacité de
// chaque lien, fondues sur la couleur de fond réelle (premier parent au fond non transparent).
async function contrast(p, sel) {
  return p.$$eval(sel + " .socials a", links => links.map(a => {
    const rgb = c => (c.match(/[\d.]+/g) || []).map(Number);
    const lum = ([r, g, b]) => { const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
    let el = a, bg = null;
    while (el && !bg) { const c = rgb(getComputedStyle(el).backgroundColor); if (c.length && (c.length < 4 || c[3] > 0)) bg = c.slice(0, 3); el = el.parentElement; }
    bg = bg || [255, 255, 255];
    const st = getComputedStyle(a), fg = rgb(st.color), op = parseFloat(st.opacity) * (fg.length > 3 ? fg[3] : 1);
    const mix = fg.slice(0, 3).map((v, i) => v * op + bg[i] * (1 - op));
    const L1 = lum(mix), L2 = lum(bg);
    return { color: st.color, opacity: st.opacity, ratio: (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05) };
  }));
}

async function iconContrast(b) {
  const pages = { home: ["footer.site"], contact: [".follow", "footer.site"] };
  const art = { fr: "/articles/importer-pieces-camions-europe-angola/", en: "/en/articles/importing-truck-parts-europe-angola/", pt: "/pt/artigos/importar-pecas-camioes-europa-angola/" };
  for (const scheme of ["light", "dark"]) {
    const ctx = await b.newContext({ viewport: { width: 360, height: 800 }, colorScheme: scheme });
    const p = await ctx.newPage();
    for (const lang of LANGS) {
      const targets = Object.entries(pages).map(([pid, sels]) => [U(pid, lang), sels]).concat([[art[lang], ["footer.site"]]]);
      for (const [url, sels] of targets) {
        await p.goto(BASE + url);
        for (const sel of sels) {
          const L = "360 " + scheme + " " + url + " " + sel;
          const c = await contrast(p, sel);
          ok(c.length === 5 && c.every(x => x.ratio >= 3), L + " : contraste des icônes ≥ 3:1 " + c.map(x => x.ratio.toFixed(1) + " (" + x.color + ", " + x.opacity + ")").join(" | "));
          if (sel === "footer.site") ok(c.every(x => x.color === "rgb(239, 231, 216)"), L + " : icônes en ivoire --cream (#EFE7D8) " + c.map(x => x.color).join(" | "));
          const first = (await p.$$(sel + " .socials a"))[0];
          await first.focus(); await p.keyboard.press("Shift+Tab"); await p.keyboard.press("Tab"); await p.waitForTimeout(250);   // focus au clavier, fin de la transition
          ok(await first.evaluate(a => getComputedStyle(a).opacity === "1" && getComputedStyle(a).outlineStyle !== "none"), L + " : opacité 100 % et contour visible au focus clavier");
          await first.hover(); await p.waitForTimeout(250);
          ok(await first.evaluate(a => getComputedStyle(a).opacity === "1"), L + " : opacité 100 % au survol");
          await p.mouse.move(0, 0);
        }
      }
    }
    await ctx.close();
  }
}

// Contraste d'éléments de texte (WCAG 1.4.3 : 4,5:1), même calcul que pour les icônes
const textContrast = (p, sel) => p.$$eval(sel, els => els.map(a => {
  const rgb = c => (c.match(/[\d.]+/g) || []).map(Number);
  const lum = ([r, g, b]) => { const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
  let el = a, bg = null;
  while (el && !bg) { const c = rgb(getComputedStyle(el).backgroundColor); if (c.length && (c.length < 4 || c[3] > 0)) bg = c.slice(0, 3); el = el.parentElement; }
  bg = bg || [255, 255, 255];
  const fg = rgb(getComputedStyle(a).color).slice(0, 3), L1 = lum(fg), L2 = lum(bg);
  return { text: a.textContent.trim(), color: getComputedStyle(a).color, ratio: (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05) };
}));

async function demoAndWhatsappContrast(b) {
  for (const scheme of ["light", "dark"]) {
    const ctx = await b.newContext({ viewport: { width: 360, height: 800 }, colorScheme: scheme });
    const p = await ctx.newPage();
    for (const lang of LANGS) {
      const L = "360 " + scheme + " " + lang;
      // Portails DEMO : étiquettes d'état (Offre, Livré, Sourcing)
      await p.goto(BASE + U("portail", lang));
      const pills = await textContrast(p, ".pill");
      ok(pills.length >= 3 && pills.every(x => x.ratio >= 4.5), L + " : étiquettes DEMO ≥ 4,5:1 " + pills.map(x => x.text + " " + x.ratio.toFixed(1)).join(" | "));
      if (scheme === "light") {
        ok(await p.$eval(".pill.ok", e => getComputedStyle(e).color) === "rgb(47, 107, 79)" && await p.$eval(".pill.w", e => getComputedStyle(e).color) === "rgb(138, 90, 18)", L + " : couleurs des étiquettes DEMO inchangées en mode clair");
      }
      // Assistant : bouton « Écrire sur WhatsApp », au repos puis au survol
      await p.goto(BASE + U("home", lang)); await p.click("#cbBtn"); await p.waitForTimeout(150);
      let wa = await textContrast(p, "#cbWa");
      ok(wa[0].ratio >= 4.5, L + " : bouton WhatsApp de l'assistant ≥ 4,5:1 (" + wa[0].ratio.toFixed(1) + ")");
      await p.hover("#cbWa"); wa = await textContrast(p, "#cbWa");
      ok(wa[0].ratio >= 4.5, L + " : bouton WhatsApp de l'assistant au survol ≥ 4,5:1 (" + wa[0].ratio.toFixed(1) + ")");
      ok(await p.$eval("#waBtn", e => getComputedStyle(e).backgroundColor) === "rgb(31, 122, 77)", L + " : bouton flottant WhatsApp inchangé");
    }
    await ctx.close();
  }
}

async function reel(b) {
  await iconContrast(b);
  await demoAndWhatsappContrast(b);
  // logo : animé à la 1re page de la visite seulement ; le survol le rejoue
  const p = await page(b, 1440);
  await go(p, "/", "logo 1re page");
  ok(!(await p.evaluate(() => document.documentElement.classList.contains("ch-vu"))), "logo : animation jouée à la 1re page");
  ok(await p.$eval(".word span", e => getComputedStyle(e).animationName) === "fade", "logo : animation d'entrée active à la 1re page");
  await go(p, U("solutions", "fr"), "logo 2e page");
  ok(await p.evaluate(() => document.documentElement.classList.contains("ch-vu")), "logo : classe ch-vu à la 2e page");
  const st = await p.$eval(".word span", e => ({ a: getComputedStyle(e).animationName, o: getComputedStyle(e).opacity }));
  ok(st.a === "none" && st.o === "1", "logo : affiché directement à la 2e page " + JSON.stringify(st));
  ok(await p.$eval(".brand img", i => getComputedStyle(i).animationName) === "none", "logo : image sans animation d'entrée à la 2e page");
  await p.hover(".brand"); await p.waitForTimeout(100);
  ok(!(await p.evaluate(() => document.documentElement.classList.contains("ch-vu"))), "logo : le survol rejoue l'animation");
  await p.context().close();
  const p2 = await page(b, 1440);   // nouvelle visite (nouvel onglet) : animation rejouée
  await go(p2, U("solutions", "fr"), "logo nouvelle visite");
  ok(!(await p2.evaluate(() => document.documentElement.classList.contains("ch-vu"))), "logo : animation rejouée à une nouvelle visite");
  await p2.context().close();

  for (const w of WIDTHS) {
    const p = await page(b, w);
    for (const lang of LANGS) {
      const L = w + " " + lang;
      for (const pid of PAGES) await go(p, U(pid, lang), L + " " + pid);
      await p.goto(BASE + U("home", lang));
      ok(!(await p.$("#references")), L + " : pas de section références (aucune référence saisie)");
      ok(!!(await p.$("#globe")) && !(await p.$(".hero-photo")), L + " : globe affiché (pas de photo d'accueil)");
      ok((await text(p, "#audit .price")) === { fr: "250 € HT", en: "€250 excl. VAT", pt: "250 € sem IVA" }[lang], L + " : prix de l'audit");
      const foot = await p.$$eval("footer.site a", a => a.map(x => x.textContent.trim() + " " + x.getAttribute("href")));
      ok(foot.some(x => x === "LinkedIn https://www.linkedin.com/in/chanceleno"), L + " : LinkedIn dans le pied de page");
      ok(!foot.some(x => /cgv|terms-of-sale|condicoes-gerais/.test(x)), L + " : CGV absentes du pied de page");
      await socials(p, "footer.site", lang, L);
      ok((await text(p, ".stats")).includes({ fr: "5 langues de travail : FR · PT · EN · ES · LN", en: "5 working languages: FR · PT · EN · ES · LN", pt: "5 línguas de trabalho: FR · PT · EN · ES · LN" }[lang]), L + " : 5 langues de travail");
      ok((await text(p, ".founder")).includes({ fr: "en français, en portugais, en anglais, en espagnol et en lingala.", en: "French, Portuguese, English, Spanish and Lingala.", pt: "francês, português, inglês, espanhol e lingala." }[lang]), L + " : lingala dans le bloc fondateur");
      ok((await text(p, ".fbot")).includes("© " + YEAR + " CHANCELENO"), L + " : copyright " + YEAR);
      const ent = await text(p, ".entities");
      ok(ent.includes({ fr: "SAS à associé unique au capital de 1 000 € RCS Lyon 133 060 319 Siège : 12 rue de la Part-Dieu, 69003 Lyon",
        en: "SAS à associé unique with share capital of 1 000 € RCS Lyon 133 060 319 Registered office: 12 rue de la Part-Dieu, 69003 Lyon",
        pt: "SAS à associé unique com capital social de 1 000 € RCS Lyon 133 060 319 Sede: 12 rue de la Part-Dieu, 69003 Lyon" }[lang]) && !NO_VAT.test(ent), L + " : pied de page, identité de la société française, sans TVA");
      const ld = lang === "fr" ? await jsonld(p) : null;
      if (ld) {
        const sfr = ld.subOrganization[1];
        ok(sfr.taxID === "133060319" && !sfr.vatID && sfr.foundingDate === "2026-11-20" && sfr.address.streetAddress === "12 rue de la Part-Dieu" && !sfr.description, "JSON-LD : identifiants de la société française, sans TVA");
        ok(JSON.stringify(ld.sameAs) === JSON.stringify(SOCIAL.slice(0, 4).map(x => x[0])), "JSON-LD : sameAs = 4 comptes de l'entreprise");
        ok(ld.founder.name === "Chano Chanceleno" && JSON.stringify(ld.founder.sameAs) === '["https://www.linkedin.com/in/chanceleno","https://www.tiktok.com/@chano.chanceleno"]', "JSON-LD : fondateur « Chano Chanceleno », profil LinkedIn et TikTok");
        ok(JSON.stringify(ld.knowsLanguage) === '["fr","pt","en","es","ln"]' && !("email" in ld), "JSON-LD : knowsLanguage avec ln, sans email");
      }
      // mentions légales : éditeur, directeur de la publication, structure angolaise, hébergeur, pas de TVA
      await p.goto(BASE + U("mentions", lang));
      const m = await text(p, ".legal .band");
      ok(m.includes({ fr: "Éditeur du site ", en: "Site publisher ", pt: "Editor do site " }[lang] + FR_ID[lang] +
        { fr: " – Email : ceo@chanceleno.com – Tél. : +33 6 41 80 84 99.", en: " – Email: ceo@chanceleno.com – Tel.: +33 6 41 80 84 99.", pt: " – Email: ceo@chanceleno.com – Tel.: +33 6 41 80 84 99." }[lang]), L + " : mentions légales, éditeur français");
      ok(m.includes({ fr: "Directeur de la publication : Chano Chanceleno, Président.", en: "Publication director: Chano Chanceleno, President.", pt: "Diretor da publicação: Chano Chanceleno, Presidente." }[lang]), L + " : mentions légales, directeur de la publication");
      ok(m.includes({ fr: "Structure angolaise ", en: "Angolan company ", pt: "Estrutura angolana " }[lang] + AO_ID), L + " : mentions légales, structure angolaise");
      ok(m.includes("GitHub Inc., 88 Colin P. Kelly Jr Street, San Francisco, CA 94107, " + { fr: "États-Unis.", en: "United States.", pt: "Estados Unidos." }[lang]), L + " : mentions légales, hébergeur");
      ok(!NO_VAT.test(m) && !m.includes("(at)"), L + " : mentions légales sans TVA, email reconstitué");
      // confidentialité : responsable du traitement = société française, droits exercés auprès de ceo@
      await p.goto(BASE + U("confidentialite", lang));
      const c = await text(p, ".legal .band");
      ok(c.includes({ fr: "Responsable du traitement ", en: "Data controller ", pt: "Responsável pelo tratamento " }[lang] + FR_ID[lang] + ". " +
        { fr: "Contact pour l'exercice de vos droits : ceo@chanceleno.com.", en: "Contact for exercising your rights: ceo@chanceleno.com.", pt: "Contacto para o exercício dos seus direitos: ceo@chanceleno.com." }[lang]), L + " : confidentialité, responsable du traitement");
      ok(!c.includes("COMÉRCIO GERAL") && (c.match(/ceo@chanceleno\.com/g) || []).length === 2 && !c.includes("(at)"), L + " : confidentialité, droits exercés auprès de ceo@");
      // carte Lyon (Marchés) ; cartes Pointe-Noire et Kinshasa inchangées
      await p.goto(BASE + U("marches", lang));
      const cards = await p.$$eval(".nodes > div", d => d.map(x => x.innerText.replace(/\s+/g, " ")));
      ok(cards[0].includes(FR_ID[lang] + ". "), L + " : carte Lyon avec l'identité légale");
      ok(cards.some(x => x.includes("Pointe-Noire")) && cards.some(x => x.includes("Kinshasa")), L + " : cartes Pointe-Noire et Kinshasa");
      // message de confirmation du formulaire de contact, traduit
      await p.goto(BASE + U("contact", lang));
      ok((await text(p, ".follow p")) === { fr: "Suivez-nous", en: "Follow us", pt: "Siga-nos" }[lang], L + " : Contact, « Suivez-nous »");
      await socials(p, ".follow", lang, L);
      await p.goto(BASE + U("a-propos", lang));
      ok((await text(p, "main")).includes({ fr: "en français, en portugais, en anglais, en espagnol et en lingala, et négocie", en: "French, Portuguese, English, Spanish and Lingala, and negotiates", pt: "francês, português, inglês, espanhol e lingala, e negoceia" }[lang]), L + " : lingala dans À propos");
      await p.goto(BASE + U("contact", lang)); await p.fill("#c-name", "T"); await p.fill("#c-mail", "a@b.co"); await p.fill("#c-msg", "T");
      await p.click("#ctForm button[type=submit]"); await p.waitForSelector("#ctForm .status.ok");
      ok((await text(p, "#ctForm .status")).startsWith({ fr: "Votre message est bien envoyé", en: "Your message has been sent", pt: "A sua mensagem foi enviada" }[lang]), L + " : confirmation du contact traduite");
      ok(!(await text(p, "#ctForm .status")).includes("{{"), L + " : pas de marqueur dans la confirmation");
    }
    const r = await p.goto(BASE + "/cgv/"); ok(r.status() === 404, w + " : pas de page CGV tant que le texte n'existe pas");
    await p.context().close();
  }
}

async function fictif(b) {
  for (const w of WIDTHS) {
    const p = await page(b, w);
    for (const lang of LANGS) {
      const L = w + " " + lang;
      for (const pid of PAGES.concat(["cgv"])) await go(p, U(pid, lang), L + " " + pid);
      await go(p, "/" + (lang === "fr" ? "" : lang + "/") + { fr: "secteurs", en: "industries", pt: "setores" }[lang] + "/" +
        { fr: "sante-laboratoire", en: "healthcare-laboratory", pt: "saude-laboratorio" }[lang] + "/", L + " secteur santé");
      ok(await loaded(p, ".sector-photo img"), L + " : photo du secteur santé");
      ok(await p.$eval(".sector-photo img", i => i.alt.length > 5 && i.loading === "lazy"), L + " : photo du secteur, texte alternatif et chargement différé");
      // accueil
      await p.goto(BASE + U("home", lang)); await p.waitForTimeout(200);
      ok(await loaded(p, ".hero-photo img") && !(await p.$("#globe")), L + " : photo d'accueil à la place du globe");
      ok(await p.$eval(".hero-photo img", (i, l) => i.alt === { fr: "Photo de test de l'accueil", en: "Home test photo", pt: "Foto de teste da página inicial" }[l] && i.loading !== "lazy", lang), L + " : photo d'accueil, texte alternatif, chargement immédiat");
      ok((await text(p, "#audit .price")) === { fr: "300 € HT", en: "€300 excl. VAT", pt: "300 € sem IVA" }[lang], L + " : prix de l'audit modifié");
      const refs = await text(p, "#references");
      if (lang === "pt") ok(refs === "", L + " : pas de références sans traduction portugaise");
      else {
        ok(refs.includes("Client Fictif Autorisé SA") && !refs.includes("Non Autorisé") && !refs.includes("jamais"), L + " : seule la référence autorisée s'affiche");
        ok(refs.includes({ fr: "Santé et laboratoire · Angola", en: "Health and laboratory · Angola" }[lang]), L + " : secteur et pays de la référence");
        ok(await loaded(p, "#references img"), L + " : logo de la référence");
      }
      const foot = await p.$$eval("footer.site a", a => a.map(x => x.textContent.trim() + " " + x.getAttribute("href")));
      await socials(p, "footer.site", lang, L, SOCIAL.filter(x => x[1] !== "YouTube"));   // lien YouTube vidé : icône absente
      ok(foot.some(x => x.endsWith(" " + U("cgv", lang))), L + " : lien CGV dans le pied de page");
      const ent = await text(p, ".entities");
      ok(ent.includes("RCS Lyon 123 456 789") && ent.includes("FR12123456789") && !/immatricul|registered|registo/.test(ent), L + " : pied de page, identifiants de la société française");
      if (lang === "fr") {
        const ld = await jsonld(p), fr = ld.subOrganization[1];
        ok(fr.taxID === "123456789" && fr.vatID === "FR12123456789" && fr.foundingDate === "2026-11-02" && !fr.description, "JSON-LD : identifiants de la société française");
        ok(ld.sameAs.length === 3 && !ld.sameAs.some(u => /youtube|tiktok/.test(u)), "JSON-LD : lien vide absent de sameAs");
      }
      await shot(p, "fictif-accueil-" + lang + "-" + w);
      // marchés
      await p.goto(BASE + U("marches", lang));
      const cards = await p.$$eval(".nodes > div", d => d.map(x => x.innerText.replace(/\s+/g, " ")));
      ok(cards.length === 6 && !cards.some(c => c.includes("XAF")), L + " : carte « Devises » masquée");
      ok(cards[0].includes({ fr: "CHANCELENO INTERNATIONAL – SASU au capital de 1 000 € – RCS Lyon 123 456 789 – Siège : 1 rue de l'Exemple, 69001 Lyon, France.",
        en: "CHANCELENO INTERNATIONAL – SASU with share capital of 1 000 € – RCS Lyon 123 456 789", pt: "CHANCELENO INTERNATIONAL – SASU com capital social de 1 000 € – RCS Lyon 123 456 789" }[lang]), L + " : carte Lyon avec le RCS");
      ok(cards.some(c => c.includes("Pointe-Noire")) && cards.some(c => c.includes("Kinshasa")), L + " : cartes Pointe-Noire et Kinshasa");
      ok(await loaded(p, ".nodes > div:nth-child(2) img.node-photo"), L + " : photo de Luanda");
      if (w === 360) await shot(p, "fictif-marches-" + lang);
      // mentions légales
      await p.goto(BASE + U("mentions", lang));
      const m = await text(p, ".legal .band");
      ok(m.includes({ fr: "Éditeur du site CHANCELENO INTERNATIONAL – SASU au capital de 1 000 € – RCS Lyon 123 456 789 – Siège : 1 rue de l'Exemple, 69001 Lyon, France – TVA intracommunautaire FR12123456789 – Email : fictif@chanceleno.com – Tél. : +33 6 41 80 84 99. Directeur de la publication : Chano Chanceleno.",
        en: "Site publisher CHANCELENO INTERNATIONAL – SASU with share capital of 1 000 €", pt: "Editor do site CHANCELENO INTERNATIONAL – SASU com capital social de 1 000 €" }[lang]), L + " : mentions légales, éditeur français (directeur ≠ président : sans qualité)");
      ok(m.includes({ fr: "Structure angolaise CHANCELENO – COMÉRCIO GERAL, (SU), LDA – Kilamba, Luanda, Angola – NIF 5003018334", en: "Angolan company CHANCELENO", pt: "Estrutura angolana CHANCELENO" }[lang]), L + " : mentions légales, société angolaise");
      ok(m.includes("fictif@chanceleno.com") && !m.includes("(at)"), L + " : mentions légales, email reconstitué");
      if (w === 360) await shot(p, "fictif-mentions-" + lang);
      // CGV, devis, remerciement
      await p.goto(BASE + U("cgv", lang));
      ok((await text(p, "main")).includes({ fr: "TEXTE DE TEST", en: "TEST TEXT", pt: "TEXTO DE TESTE" }[lang]), L + " : page CGV");
      await p.goto(BASE + U("devis", lang));
      ok((await text(p, "#rfqForm")).includes({ fr: "sous 24 h ouvrées", en: "within 24 business hours", pt: "em 24 horas úteis" }[lang]), L + " : délai de réponse modifié");
      ok(await p.$eval('#r-type option[value="audit1"]', o => o.dataset.fr) === "Audit documentaire fournisseur (300 € HT, sous 48 h)", L + " : option audit, valeur française envoyée");
      await p.goto(BASE + { fr: "/merci/", en: "/en/thank-you/", pt: "/pt/obrigado/" }[lang] + "?ref=CH-RFQ-20261102-1000");
      ok((await text(p, "#keep")).includes("24"), L + " : délai sur la page de remerciement");
    }
    // article (mise en page légère) : pied de page et auteur
    await p.goto(BASE + "/articles/");
    const art = await text(p, "footer.site");
    ok(art.includes("RCS Lyon 123 456 789") && (await p.$$("footer.site .socials a")).length === 4 && art.includes("Conditions générales de vente"), w + " : pied de page des articles");
    await p.context().close();
  }
  const sm = fs.readFileSync(path.join(__dirname, "..", "_site", "sitemap.xml"), "utf8");
  ok(["/cgv/", "/en/terms-of-sale/", "/pt/condicoes-gerais-de-venda/"].every(u => sm.includes("https://chanceleno.com" + u + "<")), "sitemap : pages CGV");
}

(async () => {
  const b = await chromium.launch(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {});
  await (MODE === "fictif" ? fictif(b) : reel(b));
  await b.close();
  console.log(fails ? "ÉCHECS : " + fails + " sur " + checks + " contrôles (" + MODE + ")" : "TOUT OK : " + checks + " contrôles (" + MODE + ")");
  process.exit(fails ? 1 : 0);
})();
