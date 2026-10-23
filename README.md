# Site chanceleno.com

Le site est **généré automatiquement** à partir d'une source unique, en français, anglais et portugais.
Vous ne modifiez jamais les pages HTML finales : vous modifiez les textes dans `content/`, et le site se
reconstruit tout seul à chaque mise en ligne.

## Où se trouve quoi

| Dossier / fichier | Contenu |
|---|---|
| `content/pages/` | Le texte **français** de chaque rubrique (un fichier par page : `devis.html`, `partenaires.html`…) |
| `content/i18n.json` | Les **traductions** : chaque phrase française avec sa version anglaise (`en`) et portugaise (`pt`) |
| `content/data.json` | Les listes : 6 capacités, 8 secteurs, **cartes de la page Marchés**, suivi DEMO |
| `content/site.json` | Adresse, titre et description Google de chaque page, dans les 3 langues |
| `content/layout/` | En-tête, pied de page, assistant « Besoin d'aide ? », WhatsApp, mise en page des articles |
| `content/articles/` | Les articles (un dossier par article) |
| `content/thanks/` | Pages de remerciement après l'envoi d'un formulaire |
| `static/` | Images, polices, styles, scripts, `robots.txt`, `.well-known/security.txt`, fichier Google |
| `tools/build.py` | Le générateur (ne pas modifier sauf évolution du site) |
| `tools/check.py` | Les contrôles automatiques (liens, sécurité, référencement) |

## Modifier un texte

1. Ouvrez la page concernée dans `content/pages/` (par exemple `fournisseurs.html`) et modifiez la phrase **en français**.
2. Ouvrez `content/i18n.json`, cherchez l'**ancienne** phrase française (Ctrl+F), remplacez-la par la nouvelle,
   et mettez à jour les traductions `en` et `pt` sur la même ligne :
   ```json
   "Inscription gratuite": {"en": "Free registration", "pt": "Registo gratuito"},
   ```
3. Si vous oubliez une traduction, la génération **s'arrête** et affiche la liste des phrases sans traduction :
   aucune page à moitié traduite ne peut être publiée.

Les titres et descriptions qui apparaissent dans Google se modifient dans `content/site.json`.

> Vous pouvez tout faire depuis github.com : ouvrez le fichier, cliquez sur le crayon, modifiez,
> puis choisissez « Create a new branch and start a pull request ». Les contrôles se lancent tout seuls.

## Mettre à jour une carte de la page Marchés

Dans `content/data.json`, rubrique `"marches"`, chaque carte a trois textes en français :

```json
{ "role": "Pays relais · partenaire local", "titre": "Kinshasa, RD Congo", "texte": "Un partenaire sur place…" }
```

Modifiez-les (ou ajoutez une carte en copiant un bloc), puis ajoutez ou mettez à jour les traductions de ces
trois textes dans `content/i18n.json`, comme pour n'importe quel texte.

## Ajouter un article

1. Copiez le dossier `content/articles/_modele` et renommez la copie (par exemple `content/articles/dedouanement-luanda`).
   Ne mettez pas de `_` au début du nom : les dossiers qui commencent par `_` sont ignorés.
2. Remplissez `meta.json` : la date de publication, puis pour chaque langue l'adresse (minuscules, tirets, sans
   accents), le titre et le résumé.
3. Écrivez l'article dans `fr.html`, `en.html` et `pt.html` (paragraphes `<p>`, intertitres `<h2>`, encadré final).
4. La liste des articles, le plan du site (`sitemap.xml`) et les liens entre langues sont mis à jour automatiquement.
   L'article sera en ligne à l'adresse `/articles/<adresse>/` (et `/en/articles/…`, `/pt/artigos/…`).

## Voir le résultat sur votre ordinateur

Il faut Python 3 (déjà installé sur Mac). Dans un terminal, à la racine du dossier :

```
python3 tools/build.py --serve
```

puis ouvrez http://localhost:8000. Pour vérifier les liens et la sécurité : `python3 tools/check.py`.

## Mise en ligne

- Chaque **pull request** lance la génération et les contrôles (onglet « Checks ») : si quelque chose est cassé,
  la PR l'indique et rien n'est publié.
- Chaque **merge sur `main`** génère le site et le publie sur chanceleno.com en environ une minute
  (fichier `.github/workflows/deploy.yml`).
- Les anciennes adresses du type `chanceleno.com/#/devis` continuent de fonctionner : elles redirigent vers
  les nouvelles (`/devis/`, `/en/quote/`, `/pt/cotacao/`…).

## Statistiques de visite (GoatCounter)

Le site mesure sa fréquentation avec **GoatCounter**, un outil gratuit **sans cookie** qui ne conserve pas les
adresses IP : aucun bandeau de consentement n'est affiché. Le script est hébergé sur le site
(`static/assets/count.js`).

**Activer le comptage** (une seule fois) :
1. Créez un compte gratuit sur https://www.goatcounter.com (« Sign up ») et choisissez un code, par exemple `chanceleno`.
2. Dans `content/site.json`, remplissez le champ : `"goatcounter": "chanceleno"`.
3. Mergez : le comptage démarre au déploiement suivant. Tant que le champ est vide, rien n'est chargé ni compté.

**Consulter les statistiques** : connectez-vous sur `https://chanceleno.goatcounter.com` (avec votre code).
Vous y voyez, jour par jour :
- les **pages les plus vues** (ex. `/devis/`, `/en/quote/`, `/pt/cotacao/`) ;
- d'où viennent les visiteurs (Google, LinkedIn, WhatsApp…), leur pays et leur appareil ;
- les **événements**, dans la même liste :
  - `envoi-devis`, `envoi-fournisseur`, `envoi-partenaire`, `envoi-contact` : un formulaire valide est parti
    (le libellé indique la langue, ex. « envoi-devis (pt) ») ;
  - `whatsapp-europe` (+33) et `whatsapp-afrique` (+244) : un clic sur un lien WhatsApp ;
- les pages `/merci/`, `/en/thank-you/`, `/pt/obrigado/` : demandes réellement reçues après le captcha.

**Réglage conseillé** dans *Settings* de GoatCounter : activez l'option qui ignore vos propres visites. Sur un
appareil donné, vous pouvez aussi cliquer sur « Ne pas compter mes visites » en bas de la page Cookies du site.

## À faire régulièrement

- **Chaque année, avant le 22 octobre** : repousser d'un an la date `Expires` de `static/.well-known/security.txt`.
- **Après l'immatriculation de CHANCELENO INTERNATIONAL** (lot Kbis) : mentions légales et informations
  contractuelles (`content/pages/mentions.html`, `conditions.html`), entités du pied de page
  (`content/layout/footer.html` et `content/layout/light.json`), carte Lyon de la page Marchés (`content/data.json`),
  données structurées (fonction `organization` dans `tools/build.py`).

## Tests navigateur (facultatif)

`tests/site.test.js` vérifie toutes les pages à 360, 412 et 1440 px, les formulaires (sans rien envoyer), les
anciennes adresses, la langue mémorisée, l'assistant et WhatsApp :

```
python3 tools/build.py && (cd _site && python3 -m http.server 8765 &)
cd tests && npm install && npx playwright install chromium && npm test
```
