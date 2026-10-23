// Tests des statistiques GoatCounter. À lancer sur un site généré AVEC un code (ex. « chanceleno » dans config/site.yml) :
// les requêtes vers <code>.goatcounter.com sont interceptées, rien n'est réellement envoyé.
//   BASE=http://localhost:8765 GC=test node stats.test.js
const { chromium } = require(process.env.PW || "playwright");
const fs = require("fs");
const path = require("path");

const BASE = process.env.BASE || "http://localhost:8765";
const GC = process.env.GC || "test";
const SITE = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "content", "site.json"), "utf8"));
const U = (pid, lang) => SITE.pages[pid][lang].chemin;
let fails = 0, checks = 0;
const ok = (c, m) => { checks++; if (!c) { fails++; console.log("  ÉCHEC", m); } };

async function page(b, w) {
  const ctx = await b.newContext({ viewport: { width: w, height: 800 } });
  // count.js ignore « localhost » par défaut : on l'autorise pour le test
  await ctx.addInitScript(() => { window.goatcounter = { allow_local: true }; window.__csp = [];
    document.addEventListener("securitypolicyviolation", e => window.__csp.push(e.violatedDirective + " " + e.blockedURI)); });
  const p = await ctx.newPage();
  p.hits = [];
  await ctx.route(new RegExp("^https://" + GC + "\\.goatcounter\\.com/"), r => { p.hits.push(new URL(r.request().url())); r.fulfill({ status: 200, body: "" }); });
  await ctx.route(/formsubmit\.co/, r => r.fulfill(r.request().url().includes("/ajax/") ? { status: 200, contentType: "application/json", body: '{"success":"true"}' } : { status: 200, body: "ok" }));
  await ctx.route(/wa\.me/, r => r.fulfill({ status: 200, body: "wa" }));
  return p;
}
const events = p => p.hits.filter(u => u.searchParams.get("e") === "true").map(u => u.searchParams.get("p"));
const views = p => p.hits.filter(u => u.searchParams.get("e") !== "true").map(u => u.searchParams.get("p"));
const settle = p => p.waitForTimeout(600);

(async () => {
  const b = await chromium.launch();
  // 1. une page vue par page, aucune violation CSP
  {
    const p = await page(b, 412);
    const sitemap = fs.readFileSync(path.join(__dirname, "..", "_site", "sitemap.xml"), "utf8");
    const urls = [...sitemap.matchAll(/<loc>https:\/\/chanceleno\.com([^<]*)<\/loc>/g)].map(m => m[1]).concat(["/merci/", "/en/thank-you/", "/pt/obrigado/"]);
    for (const u of urls) {
      p.hits.length = 0;
      await p.goto(BASE + u); await settle(p);
      ok(views(p).filter(v => v === u).length === 1, u + " : page vue comptée " + JSON.stringify(views(p)));
      ok((await p.evaluate(() => window.__csp)).length === 0, u + " : CSP " + (await p.evaluate(() => window.__csp)));
    }
    await p.context().close();
  }
  console.log("1. pages vues : terminé");
  // 2. formulaires et WhatsApp, 3 langues × 3 largeurs
  for (const w of [360, 412, 1440]) for (const lang of ["fr", "en", "pt"]) {
    const L = w + "px " + lang, p = await page(b, w);
    await p.goto(BASE + U("devis", lang)); await settle(p);
    p.hits.length = 0; await p.click("#rfqForm button[type=submit]"); await settle(p);
    ok(events(p).length === 0, L + " formulaire invalide : aucun événement");
    await p.fill("#r-req", "T"); await p.fill("#r-dest", "Luanda"); await p.fill("#r-name", "T"); await p.fill("#r-mail", "a@b.co");
    await p.click("#rfqForm button[type=submit]"); await settle(p);
    ok(events(p).includes("envoi-devis"), L + " envoi-devis " + events(p));
    for (const [pid, form, fill, ev] of [
      ["fournisseurs", "supForm", async () => { await p.fill("#s-co", "A"); await p.fill("#s-ct", "FR"); await p.fill("#s-name", "T"); await p.fill("#s-mail", "a@b.co"); }, "envoi-fournisseur"],
      ["partenaires", "parForm", async () => { await p.fill("#p-co", "A"); await p.fill("#p-country", "FR"); await p.fill("#p-msg", "T"); await p.fill("#p-name", "T"); await p.fill("#p-mail", "a@b.co"); }, "envoi-partenaire"],
      ["contact", "ctForm", async () => { await p.fill("#c-name", "T"); await p.fill("#c-mail", "a@b.co"); await p.fill("#c-msg", "T"); }, "envoi-contact"]]) {
      await p.goto(BASE + U(pid, lang)); await settle(p); p.hits.length = 0;
      await fill(); await p.click("#" + form + " button[type=submit]"); await settle(p);
      ok(events(p).includes(ev), L + " " + ev + " " + events(p));
    }
    // WhatsApp : menu flottant (Europe, Afrique), assistant (numéro selon la langue)
    await p.goto(BASE + U("home", lang)); await settle(p);
    for (const [i, ev] of [[0, "whatsapp-europe"], [1, "whatsapp-afrique"]]) {
      p.hits.length = 0; if (!(await p.$eval("#waMenu", m => m.classList.contains("open")))) await p.click("#waBtn");
      const [pop] = await Promise.all([p.waitForEvent("popup"), p.click("#waMenu a >> nth=" + i)]); await pop.close(); await settle(p);
      ok(events(p).includes(ev), L + " menu WhatsApp " + ev + " " + events(p));
    }
    await p.evaluate(() => document.body.click()); // ferme le menu WhatsApp resté ouvert
    p.hits.length = 0; await p.click("#cbBtn");
    const [pop] = await Promise.all([p.waitForEvent("popup"), p.click("#cbWa")]); await pop.close(); await settle(p);
    const want = lang === "pt" ? "whatsapp-afrique" : "whatsapp-europe";
    ok(events(p).includes(want), L + " assistant WhatsApp " + want + " " + events(p));
    ok((await p.evaluate(() => window.__csp)).length === 0, L + " CSP");
    await p.context().close();
  }
  console.log("2. formulaires et WhatsApp : terminé");
  // 3. article (mise en page légère) : WhatsApp du pied de page
  {
    const p = await page(b, 360);
    await p.goto(BASE + "/articles/"); await settle(p); p.hits.length = 0;
    const [pop] = await Promise.all([p.waitForEvent("popup").catch(() => null), p.click('footer a[href*="wa.me/244"]', { modifiers: ["Control"] })]);
    if (pop) await pop.close(); await settle(p);
    ok(events(p).includes("whatsapp-afrique"), "article : WhatsApp du pied de page " + events(p));
    await p.context().close();
  }
  // 4. « Ne pas compter mes visites »
  for (const lang of ["fr", "en", "pt"]) {
    const p = await page(b, 360);
    await p.goto(BASE + U("cookies", lang)); await settle(p);
    ok(await p.isVisible("#gcOptout") && await p.isVisible("#gcState"), lang + " bouton visible");
    const t1 = await p.textContent("#gcOptout");
    await p.click("#gcOptout"); ok(await p.evaluate(() => localStorage.getItem("skipgc")) === "t" && (await p.textContent("#gcOptout")) !== t1, lang + " désactivation");
    p.hits.length = 0; await p.goto(BASE + U("home", lang)); await settle(p);
    ok(p.hits.length === 0, lang + " aucun envoi après désactivation " + p.hits.length);
    await p.goto(BASE + U("cookies", lang)); await p.click("#gcOptout");
    p.hits.length = 0; await p.goto(BASE + U("home", lang)); await settle(p);
    ok(views(p).length === 1, lang + " comptage rétabli");
    await p.context().close();
  }
  console.log("4. désactivation : terminé");
  await b.close();
  console.log(fails ? "ÉCHECS : " + fails + " sur " + checks + " contrôles" : "TOUT OK : " + checks + " contrôles");
  process.exit(fails ? 1 : 0);
})().catch(e => { console.error(e); process.exit(1); });
