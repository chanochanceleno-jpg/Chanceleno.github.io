// Tests navigateur du site généré (_site/), à 360, 412, 1024, 1280 et 1440 px, en FR, EN et PT.
// Aucun formulaire n'est réellement envoyé : les requêtes vers FormSubmit sont interceptées.
//
//   python3 tools/build.py
//   cd _site && python3 -m http.server 8765 &      (dans un autre terminal)
//   cd tests && npm install && npm test             (BASE=http://localhost:8765 par défaut)
//
// Options : SHOTS=dossier pour enregistrer des captures à 360 px ; WIDTHS=360,412,1440.
const { chromium } = require(process.env.PW || "playwright");
const fs = require("fs");
const path = require("path");

const BASE = process.env.BASE || "http://localhost:8765";
const WIDTHS = (process.env.WIDTHS || "360,412,1024,1280,1440").split(",").map(Number);
const SHOTS = process.env.SHOTS || "";
const MAIL = "contact@chanceleno.com";
const SITE = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "content", "site.json"), "utf8"));
const U = (pid, lang) => SITE.pages[pid][lang].chemin;
const LANGS = ["fr", "en", "pt"];

let fails = 0, checks = 0;
const ok = (c, m) => { checks++; if (!c) { fails++; console.log("  ÉCHEC", m); } };
const field = (body, name) => { const m = body.match(new RegExp('name="' + name.replace(/[()]/g, "\\$&") + '"\\r\\n\\r\\n([\\s\\S]*?)\\r\\n--')); return m ? m[1] : null; };

async function page(b, w, lang) {
  const ctx = await b.newContext({ viewport: { width: w, height: 800 } });
  await ctx.addInitScript(() => { window.__csp = []; document.addEventListener("securitypolicyviolation", e => window.__csp.push(e.violatedDirective + " " + e.blockedURI)); });
  if (lang) await ctx.addInitScript(l => { try { if (!sessionStorage.getItem("__set")) { localStorage.setItem("ch_lang", l); sessionStorage.setItem("__set", "1"); } } catch (e) {} }, lang);
  const p = await ctx.newPage();
  p.errs = [];
  p.on("pageerror", e => p.errs.push(e.message));
  p.on("console", m => { if (m.type() === "error" && !/status of 500/.test(m.text())) p.errs.push(m.text()); });
  return p;
}
const close = p => p.context().close();

async function health(p, label) {
  const r = await p.evaluate(() => ({ csp: window.__csp, sw: document.documentElement.scrollWidth, iw: innerWidth,
    mails: [...document.querySelectorAll("a[data-mail]")].map(a => a.getAttribute("href")), masked: document.body.innerText.includes("(at)"),
    title: document.title, desc: (document.querySelector('meta[name="description"]') || {}).content, h1: document.querySelectorAll("h1").length }));
  ok(r.csp.length === 0, label + " : ressource bloquée par la CSP " + r.csp.join(" | "));
  ok(p.errs.length === 0, label + " : erreur JS " + p.errs.join(" | ")); p.errs.length = 0;
  ok(r.sw <= r.iw, label + " : débordement horizontal " + r.sw + " > " + r.iw);
  ok(r.mails.every(h => h === "mailto:" + MAIL), label + " : lien email " + r.mails.join(","));
  ok(!r.masked, label + " : adresse email non reconstituée");
  ok(r.h1 === 1, label + " : " + r.h1 + " titre(s) h1");
  return r;
}

async function main() {
  const b = await chromium.launch(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {});
  const sitemap = fs.readFileSync(path.join(__dirname, "..", "_site", "sitemap.xml"), "utf8");
  const urls = [...sitemap.matchAll(/<loc>https:\/\/chanceleno\.com([^<]*)<\/loc>/g)].map(m => m[1]);
  const langOf = u => (u.startsWith("/en/") ? "en" : u.startsWith("/pt/") ? "pt" : "fr");

  // 1. Toutes les pages, toutes les largeurs
  for (const w of WIDTHS) {
    const p = await page(b, w);
    for (const u of urls.concat(["/merci/?ref=CH-RFQ-20261023-1432", "/en/thank-you/?ref=CH-SUP-20261023-1432", "/pt/obrigado/?ref=CH-PAR-20261023-1432"])) {
      const r = await p.goto(BASE + u);
      ok(r.status() === 200, u + " : HTTP " + r.status());
      ok(new URL(p.url()).pathname === u.split("?")[0], u + " : redirigé vers " + p.url());
      const h = await health(p, w + "px " + u);
      ok(await p.evaluate(() => document.documentElement.lang) === langOf(u), u + " : langue de la page");
      ok(h.title && (u.includes("/merci") || u.includes("thank-you") || u.includes("obrigado") || (h.desc && h.desc.length > 40)), u + " : titre ou description manquants");
    }
    // GitHub Pages sert 404.html pour toute adresse inconnue
    await p.goto(BASE + "/404.html"); const c404 = await p.content(); await health(p, w + "px /404.html");
    ok(c404.includes("Page introuvable") && c404.includes("Page not found") && c404.includes("Página não encontrada") && c404.includes("noindex"), "page 404 trilingue");
    await close(p);
  }
  console.log("1. pages : terminé");

  // 2. Anciennes adresses #/… (liens existants, favoris, Google)
  const legacy = { "#/": "home", "#/a-propos": "a-propos", "#/conditions": "conditions", "#/confidentialite": "confidentialite", "#/contact": "contact",
    "#/cookies": "cookies", "#/devis": "devis", "#/fournisseurs": "fournisseurs", "#/marches": "marches", "#/mentions": "mentions", "#/methode": "methode",
    "#/partenaires": "partenaires", "#/portail": "portail", "#/secteurs": "secteurs", "#/solutions": "solutions" };
  const p2 = await page(b, 412);
  for (const [from, lang, start] of [["fr", "fr", "/"], ["en", "en", "/"], ["pt", "pt", "/"], [null, "pt", "/pt/"]].map(x => [x[0], x[1], x[2]])) {
    await p2.goto(BASE + "/"); await p2.evaluate(l => { localStorage.clear(); if (l) localStorage.setItem("ch_lang", l); }, from === "fr" ? null : from);
    for (const [h, pid] of Object.entries(legacy)) {
      await p2.goto(BASE + start + h); await p2.waitForURL(u => !u.hash.startsWith("#/")); await p2.waitForLoadState();
      ok(new URL(p2.url()).pathname === U(pid, lang), start + h + " (langue mémorisée " + from + ") → " + p2.url() + " au lieu de " + U(pid, lang));
    }
    for (const [h, pid, q] of [["#/devis?t=afrique", "devis", "?t=afrique"], ["#/devis?t=audit1", "devis", "?t=audit1"], ["#/partenaires?a=1", "partenaires", "?a=1"],
      ["#/partenaires?e=1", "partenaires", "?e=1"], ["#/portail?t=sup", "portail", "?t=sup"], ["#/?b=audit", "home", "#audit"], ["#/fournisseurs?b=supForm", "fournisseurs", "#supForm"]]) {
      await p2.goto(BASE + start + h); await p2.waitForURL(u => !u.hash.startsWith("#/")); await p2.waitForLoadState();
      const u = new URL(p2.url());
      ok(u.pathname + u.search + u.hash === U(pid, lang) + q, start + h + " → " + u.pathname + u.search + u.hash);
    }
  }
  await close(p2);
  console.log("2. anciennes adresses : terminé");

  // 3. Langue mémorisée
  {
    const p = await page(b, 360);
    await p.goto(BASE + U("devis", "fr")); await p.click('.lang a[data-lang="en"]'); await p.waitForLoadState();
    ok(new URL(p.url()).pathname === U("devis", "en") && await p.evaluate(() => localStorage.getItem("ch_lang")) === "en", "sélecteur EN → page équivalente + mémorisation");
    await p.goto(BASE + U("secteurs", "fr")); await p.waitForLoadState();
    ok(new URL(p.url()).pathname === U("secteurs", "en"), "page FR avec EN mémorisé → page EN " + p.url());
    await p.goto(BASE + "/pt/"); await p.waitForTimeout(200);
    ok(new URL(p.url()).pathname === "/pt/" && await p.evaluate(() => localStorage.getItem("ch_lang")) === "en", "/pt/ ne redirige pas et n'écrase pas la langue");
    await p.goto(BASE + "/en/"); await p.click('.lang a[data-lang="fr"]'); await p.waitForLoadState();
    await p.goto(BASE + U("secteurs", "fr")); await p.waitForTimeout(200);
    ok(new URL(p.url()).pathname === U("secteurs", "fr"), "retour au FR mémorisé");
    await p.goto(BASE + "/pt/artigos/"); ok(await p.evaluate(() => localStorage.getItem("ch_lang")) === "pt", "article : langue mémorisée");
    await close(p);
  }
  console.log("3. langue mémorisée : terminé");

  // 4. Formulaires, préselections, assistant, WhatsApp, menu — dans chaque langue et chaque largeur
  const T = { fr: { btn: "Besoin d’aide ?", wa: "Bonjour CHANCELENO", num: "33641808499", thanks: "https://chanceleno.com/merci/", ack: "Bonjour,",
    menu: ["Solutions", "Secteurs", "Fournisseurs", "Partenaires", "À propos", "Contact"], cta: "Demander un devis" },
  en: { btn: "Need help?", wa: "Hello CHANCELENO", num: "33641808499", thanks: "https://chanceleno.com/en/thank-you/", ack: "Hello,",
    menu: ["Solutions", "Industries", "Suppliers", "Partners", "About", "Contact"], cta: "Request a quote" },
  pt: { btn: "Precisa de ajuda?", wa: "Olá CHANCELENO", num: "244928424849", thanks: "https://chanceleno.com/pt/obrigado/", ack: "Olá,",
    menu: ["Soluções", "Setores", "Fornecedores", "Parceiros", "Sobre nós", "Contacto"], cta: "Pedir cotação" } };
  for (const w of WIDTHS) for (const lang of LANGS) {
    const L = w + "px " + lang, t = T[lang];
    const p = await page(b, w);
    const posts = [];
    await p.route(/formsubmit\.co/, async r => { const q = r.request(); posts.push({ url: q.url(), body: q.postDataBuffer() ? q.postDataBuffer().toString("utf8") : "" });
      await r.fulfill(q.url().includes("/ajax/") ? { status: 200, contentType: "application/json", body: '{"success":"true"}' } : { status: 200, contentType: "text/html", body: "ok" }); });
    const submit = async (form, kind) => {
      const n = posts.length; await p.click("#" + form + " button[type=submit]"); await p.waitForTimeout(700); const q = posts[n];
      ok(q && /formsubmit\.co\/(ajax\/)?dd4826d916be1ff8585a8daf1f96ea91$/.test(q.url), L + " " + kind + " : envoi vers FormSubmit");
      if (!q) return "";
      const ref = field(q.body, "Référence") || "";
      ok(new RegExp("^CH-" + (kind === "CT" ? "MSG" : kind) + "-\\d{8}-\\d{4}$").test(ref) && (field(q.body, "_subject") || "").endsWith(" " + ref), L + " " + kind + " : référence " + ref);
      ok(field(q.body, "_honey") === "", L + " " + kind + " : champ piège _honey");
      ok((field(q.body, "_autoresponse") || "").startsWith(t.ack) && field(q.body, "_autoresponse").includes(ref) && field(q.body, "_autoresponse").includes(MAIL), L + " " + kind + " : accusé de réception");
      if (kind !== "CT") ok((field(q.body, "_next") || "").startsWith(t.thanks), L + " " + kind + " : page de remerciement");
      return q.body;
    };
    // devis + pièce jointe + préselections
    await p.goto(BASE + U("devis", lang) + "?t=afrique"); ok(await p.$eval("#r-type", s => s.value) === "afrique", L + " ?t=afrique");
    await p.goto(BASE + U("devis", lang) + "?s=3"); ok(await p.$eval("#r-sec", s => s.value) === "3", L + " ?s=3");
    await p.goto(BASE + U("devis", lang) + "?t=audit1"); ok(await p.$eval("#r-type", s => s.value) === "audit1", L + " ?t=audit1");
    await p.click("#rfqForm button[type=submit]"); ok((await p.$$("#rfqForm .err.show")).length >= 4, L + " devis : validation");
    await p.fill("#r-req", "Test"); await p.fill("#r-dest", "Luanda"); await p.fill("#r-name", "T"); await p.fill("#r-mail", "a@b.co");
    await p.setInputFiles("#r-files", { name: "liste.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF-1.4") });
    let body = await submit("rfqForm", "RFQ");
    ok(/filename="liste\.pdf"/.test(body) && field(body, "Pays et ville de destination") === "Luanda" && field(body, "Type de demande") !== null, L + " devis : pièce jointe et noms de champs en français");
    // fournisseur
    await p.goto(BASE + U("fournisseurs", lang));
    ok((await p.$$('section.page .caps .cap')).length === 5, L + " bloc « Pourquoi rejoindre »");
    await p.fill("#s-co", "A"); await p.fill("#s-ct", "France"); await p.fill("#s-name", "T"); await p.fill("#s-mail", "a@b.co");
    await p.setInputFiles("#s-doc", { name: "kbis.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF-1.4") });
    body = await submit("supForm", "SUP"); ok(/filename="kbis\.pdf"/.test(body) && field(body, "Raison sociale") === "A", L + " fournisseur : pièce jointe et champs");
    // partenaire (PR n° 9)
    await p.goto(BASE + U("partenaires", lang) + "?a=1"); ok((await p.$eval("#p-type", s => s.options[s.selectedIndex].dataset.fr)).startsWith("Apporteur"), L + " ?a=1");
    await p.goto(BASE + U("partenaires", lang) + "?e=1"); ok((await p.$eval("#p-type", s => s.options[s.selectedIndex].dataset.fr)).startsWith("Export"), L + " ?e=1");
    await p.click("#parForm button[type=submit]"); ok(await p.$eval("#e-p-country", e => e.classList.contains("show")), L + " partenaire : erreur pays");
    await p.fill("#p-co", "TEST"); await p.fill("#p-country", "France"); await p.fill("#p-tel", "+33 6 00 00 00 00"); await p.fill("#p-web", "www.linkedin.com/in/chanceleno");
    await p.selectOption("#p-type", { index: 5 }); await p.fill("#p-msg", "T"); await p.fill("#p-name", "T"); await p.fill("#p-mail", "a@b.co");
    body = await submit("parForm", "PAR");
    ok(field(body, "Pays d'établissement") === "France" && field(body, "Téléphone ou WhatsApp") === "+33 6 00 00 00 00" && field(body, "Site web ou profil LinkedIn") === "www.linkedin.com/in/chanceleno"
      && field(body, "Nature de la demande") === "Partenaire logistique / transit / douane", L + " partenaire : champs de la PR n° 9 en français");
    // contact (AJAX), succès puis échec
    await p.goto(BASE + U("contact", lang)); await p.fill("#c-name", "T"); await p.fill("#c-mail", "a@b.co"); await p.fill("#c-msg", "T");
    await submit("ctForm", "CT"); ok(await p.$eval("#ctForm .status", s => s.classList.contains("ok")), L + " contact : confirmation");
    await p.unroute(/formsubmit\.co/); await p.route(/formsubmit\.co/, r => r.fulfill({ status: 500, body: "{}" }));
    await p.fill("#c-name", "T"); await p.fill("#c-mail", "a@b.co"); await p.fill("#c-msg", "T"); await p.click("#ctForm button[type=submit]"); await p.waitForTimeout(600);
    ok((await p.$eval("#ctForm .status a[data-mail]", a => a.href).catch(() => "")) === "mailto:" + MAIL, L + " contact : message d'erreur avec lien email");
    // portails DEMO
    await p.goto(BASE + U("portail", lang) + "?t=sup"); ok(await p.$eval("#tab-sup", t => t.getAttribute("aria-selected")) === "true", L + " portail ?t=sup");
    // accueil : menu, assistant, WhatsApp, globe, logo
    await p.goto(BASE + U("home", lang)); await p.waitForTimeout(300);
    ok(JSON.stringify(await p.$$eval("nav.main li:not(.nav-cta) a", a => a.map(x => x.textContent.trim()))) === JSON.stringify(t.menu), L + " menu");
    const navHrefs = await p.$$eval("nav.main li:not(.nav-cta) a", a => a.map(x => x.getAttribute("href")));
    ok(JSON.stringify(navHrefs) === JSON.stringify(["solutions", "secteurs", "fournisseurs", "partenaires", "a-propos", "contact"].map(x => U(x, lang))), L + " liens du menu");
    const foot = await p.$$eval("footer.site a", a => a.map(x => x.getAttribute("href")));
    ok([U("methode", lang), U("marches", lang)].every(h => foot.includes(h)) && foot.some(h => /articles|artigos/.test(h)), L + " pied de page : Méthode, Marchés, Articles");
    // en-tête : menu complet sur une ligne dès 1024 px, menu replié (☰) en dessous
    const hd = await p.evaluate(() => { const vis = s => getComputedStyle(document.querySelector(s)).display !== "none";
      const r = s => document.querySelector(s).getBoundingClientRect();
      return { btn: vis("#menuBtn"), nav: vis("nav.main"), cta: vis(".hcta"), h: Math.round(r(".hbar").height),
        right: Math.round(Math.max(r(".hcta").right, r(".lang").right)), navTop: Math.round(r("nav.main ul").top), ctaTop: Math.round(r(".hcta").top) }; });
    if (w >= 1024) ok(!hd.btn && hd.nav && hd.cta && hd.h <= 70 && hd.right <= w && Math.abs(hd.navTop - hd.ctaTop) < 20, L + " en-tête ordinateur sur une ligne " + JSON.stringify(hd));
    else ok(hd.btn && !hd.nav, L + " menu replié " + JSON.stringify(hd));
    if (w < 1024) { await p.click("#menuBtn"); ok((await p.$eval("nav.main .nav-cta a", a => a.textContent.trim())) === t.cta, L + " bouton devis du menu mobile"); await p.click("#menuBtn"); }
    else { const h = await p.$eval(".hcta", a => [a.textContent.trim(), getComputedStyle(a).display, a.getBoundingClientRect().width]);
      ok(h[0] === t.cta && h[1] !== "none" && h[2] > 0 && (await p.$eval(".nav-cta", e => getComputedStyle(e).display)) === "none", L + " bouton devis de l'en-tête " + h); }
    ok(await p.$eval(".brand", e => e.classList.contains("has-logo")), L + " logo");
    ok(await p.$eval("#globe", g => g.querySelectorAll("path").length > 5), L + " globe");
    ok((await p.textContent("#cbBtn")).trim() === t.btn, L + " assistant : libellé");
    await p.click("#cbBtn"); ok(await p.$eval("#cbPanel", e => !e.hidden), L + " assistant : ouverture");
    const cb = await p.$$eval("#cbPanel a.cbx-link:not(.cbx-wa):not([data-mail])", a => a.map(x => x.getAttribute("href")));
    ok(JSON.stringify(cb) === JSON.stringify([U("devis", lang), U("fournisseurs", lang), U("partenaires", lang) + "?a=1", U("secteurs", lang), U("methode", lang)]), L + " assistant : liens " + cb);
    const wa = await p.$eval("#cbWa", a => { a.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true })); return decodeURIComponent(a.href); });
    ok(wa.includes("wa.me/" + t.num) && wa.includes(t.wa), L + " assistant : WhatsApp " + wa);
    ok((await p.$eval("#cbPanel a[data-mail]", a => a.href)) === "mailto:" + MAIL, L + " assistant : email");
    await p.keyboard.press("Escape"); ok(await p.$eval("#cbPanel", e => e.hidden), L + " assistant : fermeture");
    await p.click("#waBtn"); const wl = await p.$$eval("#waMenu a", a => a.map(x => x.href).join(" "));
    ok(/33641808499/.test(wl) && /244928424849/.test(wl), L + " menu WhatsApp");
    // liens internes : bloc Audit depuis Solutions, formulaire fournisseur
    await p.goto(BASE + U("solutions", lang)); ok(!(await p.$("section.page .audit")), L + " Solutions sans doublon Audit");
    await p.click('a[href="' + U("home", lang) + '#audit"]'); await p.waitForTimeout(500);
    const ay = await p.$eval("#audit", e => Math.round(e.getBoundingClientRect().top)); ok(ay >= 0 && ay < 200, L + " lien vers le bloc Audit (top=" + ay + ")");
    ok(p.errs.length === 0 && (await p.evaluate(() => window.__csp)).length === 0, L + " erreurs/CSP " + p.errs.join("|"));
    // en-tête (PR n° 10) : aucune largeur dépassée pendant l'animation du logo
    if (w === 360) { const sws = []; for (let i = 0; i < 8; i++) { await p.waitForTimeout(400); sws.push(await p.evaluate(() => document.documentElement.scrollWidth)); } ok(sws.every(x => x <= 360), L + " en-tête : largeur " + sws); }
    // photo de repli
    await p.route(/fondateur\.jpg/, r => r.abort()); await p.goto(BASE + U("a-propos", lang)); await p.waitForTimeout(500);
    ok(await p.$eval("section.page figure", f => f.classList.contains("noimg")), L + " photo de repli");
    if (SHOTS && w === 360) {
      fs.mkdirSync(SHOTS, { recursive: true });
      await p.unroute(/fondateur\.jpg/);
      for (const pid of ["home", "secteurs", "devis", "partenaires"]) { await p.goto(BASE + U(pid, lang)); await p.waitForTimeout(600); await p.screenshot({ path: path.join(SHOTS, lang + "-" + pid + ".png") }); }
      await p.goto(BASE + SITE.secteurs_base[lang]); await p.click("#sectorsFull h3 a"); await p.waitForTimeout(400); await p.screenshot({ path: path.join(SHOTS, lang + "-secteur.png") });
    }
    await close(p);
  }
  console.log("4. formulaires, assistant, menu : terminé");
  await b.close();
  console.log(fails ? "ÉCHECS : " + fails + " sur " + checks + " contrôles" : "TOUT OK : " + checks + " contrôles");
  process.exit(fails ? 1 : 0);
}
main().catch(e => { console.error(e); process.exit(1); });
