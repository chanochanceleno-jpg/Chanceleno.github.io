# Site chanceleno.com

Le site est **généré automatiquement** à partir d'une source unique, en français, anglais et portugais.
Vous ne modifiez jamais les pages HTML finales :

- les **données** (identité et Kbis, coordonnées, réseaux sociaux, tarifs, cartes Marchés, références clients,
  photos) se modifient dans **un seul fichier : `config/site.yml`** ;
- les **textes** et leurs traductions restent dans `content/`.

Le site se reconstruit tout seul à chaque mise en ligne. Une donnée n'est écrite qu'à un seul endroit : modifier
un numéro WhatsApp ou un prix dans `config/site.yml` le met à jour sur toutes les pages, dans les 3 langues.

**Sommaire des cas courants** : [remplir les champs Kbis](#remplir-les-champs-kbis) ·
[ajouter une photo](#ajouter-une-photo) · [ajouter une référence client](#ajouter-une-référence-client) ·
[ajouter un article](#ajouter-un-article) · [modifier un tarif ou un délai](#modifier-un-tarif-ou-un-délai) ·
[modifier une carte Marchés](#modifier-une-carte-marchés) · [ajouter un réseau social](#ajouter-un-réseau-social) ·
[publier les CGV](#publier-les-cgv) · [indicatifs téléphoniques](#indicatifs-téléphoniques) ·
[surveillance hebdomadaire](#surveillance-hebdomadaire)

## Où se trouve quoi

| Dossier / fichier | Contenu |
|---|---|
| `config/site.yml` | Les **données que vous modifiez vous-même** : identité et Kbis, coordonnées, réseaux sociaux, tarifs et délais, cartes Marchés, références clients, description des photos, statistiques |
| `content/pages/` | Le texte **français** de chaque rubrique (un fichier par page : `devis.html`, `partenaires.html`…) |
| `content/i18n.json` | Les **traductions** : chaque phrase française avec sa version anglaise (`en`) et portugaise (`pt`) |
| `content/data.json` | Les listes : 6 capacités, 8 secteurs, suivi DEMO |
| `content/site.json` | Adresse, titre et description Google de chaque page, dans les 3 langues |
| `content/layout/` | En-tête, pied de page, assistant « Besoin d'aide ? », WhatsApp, mise en page des articles ; `blocs.json` : libellés des blocs construits depuis `config/site.yml` (mentions légales, entités, références) |
| `content/legal/` | Texte des CGV entre professionnels (`cgv.fr.html`, `cgv.en.html`, `cgv.pt.html`), vide tant qu'il n'est pas rédigé |
| `content/articles/` | Les articles (un dossier par article) |
| `content/thanks/` | Pages de remerciement après l'envoi d'un formulaire |
| `static/` | Images, polices, styles, scripts, `robots.txt`, `.well-known/security.txt`, fichier Google |
| `tools/build.py` | Le générateur (ne pas modifier sauf évolution du site) |
| `tools/config.py` | La vérification de `config/site.yml` (messages d'erreur en français) |
| `tools/check.py` | Les contrôles automatiques (liens, sécurité, référencement) |
| `tools/surveillance.py` | Le contrôle hebdomadaire du site en ligne (voir « Surveillance hebdomadaire ») |
| `tools/requirements.txt` | Les modules Python nécessaires (PyYAML, Pillow), installés automatiquement par GitHub Actions |
| `sources/fonts/` | Polices d'origine (non publiées) ; `tools/fonts.py` en tire les versions légères de `static/fonts/` |
| `sources/images/` | Photos conservées mais **non publiées** (voir « Photos mises de côté ») |

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

## Modifier `config/site.yml` : les règles

- Le fichier se modifie depuis github.com (crayon, puis « Create a new branch and start a pull request »).
- Gardez les **espaces au début des lignes** : ils indiquent à quelle rubrique appartient un champ.
- Écrivez les textes **entre guillemets** `"…"`. Un champ vide s'écrit `""` : l'information n'est alors pas affichée.
- Les textes en trois langues s'écrivent `fr:`, `en:`, `pt:`.
- Si une valeur est mal écrite (SIREN incomplet, adresse sans `https://`, prix avec « € »…), la pull request
  l'indique en rouge avec un message en français, par exemple :
  ```
  ERREUR dans config/site.yml (1 point(s) à corriger) :
    - identite.france.siren : 9 chiffres attendus, ex. "123 456 789" (valeur actuelle : '12345')
  ```
  Rien n'est publié tant que l'erreur n'est pas corrigée. Pour vérifier sur votre ordinateur : `python3 tools/config.py`.

**Valeurs réutilisables dans les textes.** Dans les pages de `content/`, dans `content/i18n.json` et dans les textes
de `config/site.yml` (cartes Marchés, références), un marqueur entre doubles accolades est remplacé par la valeur
de la configuration :

| Marqueur | Devient (aujourd'hui) |
|---|---|
| `{{prix_audit}}` | 250 € HT · €250 excl. VAT · 250 € sem IVA (selon la langue) |
| `{{delai_rapport}}`, `{{delai_reponse}}` | 48 |
| `{{email}}` | l'adresse email, masquée contre les robots |
| `{{wa_europe}}`, `{{wa_afrique}}` | +33 6 41 80 84 99, +244 928 424 849 |
| `{{wa_europe_num}}`, `{{wa_afrique_num}}` | 33641808499, 244928424849 (pour les liens `https://wa.me/…`) |
| `{{linkedin_profil}}`, `{{linkedin_page}}`, `{{instagram}}`, `{{facebook}}`, `{{youtube}}`, `{{tiktok}}` | adresse du réseau social |
| `{{france_nom}}`, `{{france_statut}}`, `{{angola_nom}}` | dénomination, « société en cours d'immatriculation » ou « SASU, SIREN … » |
| `{{annee}}` | l'année en cours (copyright) |

Un lien vers un réseau social porte en plus `data-si="instagram"` (par exemple) : il disparaît tout seul quand
l'adresse est vide. Le copyright se met à jour seul : le site est régénéré chaque 1er janvier.

## Remplir les champs Kbis

Quand CHANCELENO INTERNATIONAL est immatriculée, recopiez le Kbis dans `config/site.yml`, rubrique
`identite` → `france` :

```yaml
  france:
    denomination: "CHANCELENO INTERNATIONAL"
    forme: "SASU"
    adresse: "10 rue Exemple, 69002 Lyon, France"
    ville: "Lyon"
    siren: "123 456 789"
    rcs: "Lyon 123 456 789"
    tva: "FR12123456789"
    capital: "1 000 €"
    president: "Chano Ndandu CHANCELENO"
    date_immatriculation: "2026-11-05"
```

Tant que `siren` est vide, le site indique « société en cours d'immatriculation ». Dès qu'il est rempli, sans
rien d'autre à faire : les **mentions légales**, le **pied de page** (toutes les pages et les articles), la
**carte Lyon** de la page Marchés et les **données lues par Google** affichent les identifiants, en FR, EN et PT.
Forme, adresse, RCS, capital et président deviennent alors obligatoires (le TVA est facultatif).

Pour que la société française devienne l'**éditeur du site**, changez aussi `editeur: angola` en `editeur: france` :
elle passe en tête des mentions légales, et la société angolaise devient « Structure angolaise ».
Le texte de l'hébergeur (GitHub) reste dans `content/pages/mentions.html`.

## Ajouter une photo

Déposez le fichier (JPG ou PNG, la taille d'origine convient) à l'un de ces emplacements, avec ce nom exact :

| Emplacement | Fichier | Où il s'affiche |
|---|---|---|
| Accueil | `static/images/accueil.jpg` | en haut de l'accueil, à la place de l'illustration du globe |
| Secteur | `static/images/secteurs/<secteur>.jpg` | en haut de la page du secteur |
| Ville (Marchés) | `static/images/marches/<id>.jpg` : `lyon`, `luanda`, `pointe-noire`, `kinshasa` | en tête de la carte |
| Fondateur | `static/images/fondateur.jpg` (remplace l'actuelle) | accueil et À propos |
| Référence | `static/images/references/<fichier>` | à côté du témoignage (voir ci-dessous) |

Noms des secteurs : `automobile-poids-lourds-flottes`, `petrole-gaz-securite-hse`, `industrie-maintenance-mro`,
`mines-ressources`, `sante-laboratoire`, `electricite-eau-energie-solaire`, `agroalimentaire-equipement-agricole`,
`informatique-telecoms-technologie`.

Exemple : une photo du port de Luanda → `static/images/marches/luanda.jpg`. Sur github.com : dossier
`static/images`, « Add file » → « Upload files », puis tapez `marches/` devant le nom du fichier pour créer le
dossier.

À la génération, chaque photo est **convertie en WebP et redimensionnée** (seule la version légère est publiée),
reçoit ses dimensions et se charge seulement quand elle devient visible (sauf la photo d'accueil, affichée tout
de suite). **Sans photo, l'affichage reste exactement celui d'aujourd'hui.** Pour la photo d'accueil, écrivez sa
description dans `config/site.yml` (rubrique `photos` → `accueil_description`, en fr, en, pt) : elle est lue par
les lecteurs d'écran et par Google. Les autres photos reprennent le nom du secteur, de la ville ou du client.

Pour retirer une photo, supprimez simplement le fichier.

## Ajouter une référence client

Seulement un **vrai client** qui a donné son **accord écrit** pour être cité. Dans `config/site.yml`, remplacez
`references: []` par :

```yaml
references:
  - nom: "Société Exemple SARL"
    secteur: {fr: "Santé et laboratoire", en: "Health and laboratory", pt: "Saúde e laboratório"}
    pays: "Angola"
    temoignage:
      fr: "Le texte exact du témoignage, tel que validé par le client."
      en: "The exact testimonial, as approved by the client."
      pt: "O texto exato do testemunho, tal como validado pelo cliente."
    photo: "societe-exemple.png"
    autorisation: oui
```

- La section « Ils nous font confiance » apparaît sur l'accueil **dès qu'une référence a `autorisation: oui`**.
  Avec `autorisation: non`, la référence reste dans le fichier mais n'est affichée nulle part.
- Sans traduction `en` ou `pt`, la référence n'apparaît que dans les langues où le témoignage existe.
- `photo` est facultatif : déposez le logo ou la photo dans `static/images/references/`, sinon supprimez la ligne.
- Pour une deuxième référence, recopiez le bloc à partir de `- nom:` juste en dessous.

## Ajouter un article

1. Copiez le dossier `content/articles/_modele` et renommez la copie (par exemple `content/articles/dedouanement-luanda`).
   Ne mettez pas de `_` au début du nom : les dossiers qui commencent par `_` sont ignorés.
2. Remplissez `meta.json` : la date de publication, puis pour chaque langue l'adresse (minuscules, tirets, sans
   accents), le titre et le résumé.
3. Écrivez l'article dans `fr.html`, `en.html` et `pt.html` (paragraphes `<p>`, intertitres `<h2>`, encadré final).
4. La liste des articles, le plan du site (`sitemap.xml`) et les liens entre langues sont mis à jour automatiquement.
   L'article sera en ligne à l'adresse `/articles/<adresse>/` (et `/en/articles/…`, `/pt/artigos/…`).

## Modifier un tarif ou un délai

Dans `config/site.yml`, rubrique `tarifs`, écrivez le nombre seul :

```yaml
tarifs:
  prix_audit_ht: 300        # devient « 300 € HT », « €300 excl. VAT », « 300 € sem IVA »
  delai_rapport_h: 48       # rapport d'audit sous 48 h ouvrées
  delai_reponse_h: 24       # réponse aux demandes sous 24 h ouvrées
```

Le prix et les délais changent partout : accueil, formulaire de devis (y compris la valeur reçue par email),
pages de remerciement et accusés de réception envoyés aux visiteurs.

## Modifier une carte Marchés

Dans `config/site.yml`, rubrique `marches`, chaque carte a un `id`, un état `affiche` et trois textes, chacun en
fr, en et pt :

```yaml
  - id: kinshasa
    affiche: oui
    role:
      fr: "Pays relais · partenaire local"
      en: "Relay country · local partner"
      pt: "País de apoio · parceiro local"
    titre:
      fr: "Kinshasa, RD Congo"
      en: "Kinshasa, DR Congo"
      pt: "Kinshasa, RD Congo"
    texte:
      fr: "Un partenaire sur place pour la prospection et le suivi des opérations."
      en: "A partner on the ground for prospecting and following up operations."
      pt: "Um parceiro no terreno para a prospeção e o acompanhamento das operações."
```

- Pour **masquer** une carte sans l'effacer : `affiche: non`.
- Pour **ajouter** une carte : recopiez un bloc à partir de `- id:`, avec un nouvel `id` (minuscules et tirets).
- Les cartes s'affichent dans l'ordre du fichier. La carte Lyon utilise `{{france_nom}}, {{france_statut}}` :
  son statut se met à jour tout seul avec le Kbis.

## Ajouter un réseau social

Dans `config/site.yml`, rubrique `reseaux`, collez l'adresse complète :

```yaml
reseaux:
  linkedin_profil: "https://www.linkedin.com/in/chanceleno"
  linkedin_page: "https://www.linkedin.com/company/chanceleno/"
  instagram: "https://www.instagram.com/chanceleno_international/"
  facebook: "https://www.facebook.com/profile.php?id=1149213368276296"
  youtube: "https://www.youtube.com/@Chanceleno"
  tiktok: "https://www.tiktok.com/@chano.chanceleno"
```

- Les comptes `linkedin_page`, `instagram`, `facebook`, `youtube` et `tiktok` s'affichent en **icônes** dans le pied
  de page (toutes les pages et les articles) et sur la page Contact (« Suivez-nous »), dans cet ordre, TikTok en
  dernier. Les icônes sont dans `tools/icones.py`, les libellés lus par les lecteurs d'écran dans
  `content/layout/blocs.json`.
- Les données lues par Google (schema.org) reprennent les 4 comptes de l'entreprise ; le profil LinkedIn et le
  TikTok, comptes du fondateur, y sont rattachés au fondateur.
- `linkedin_profil` est le profil du fondateur, utilisé par les liens texte « LinkedIn » (accueil, À propos,
  Contact, pied de page, signature des articles).
- Un champ vide (`""`) n'est affiché nulle part.

Les numéros WhatsApp et l'email se modifient de la même façon, rubrique `coordonnees`. **Attention à l'email** : les
formulaires arrivent à l'adresse enregistrée chez FormSubmit. Avant de changer d'adresse, envoyez un premier
formulaire vers la nouvelle adresse sur formsubmit.co, confirmez-la, puis remplacez `email` et `formsubmit` (le
nouvel identifiant chiffré).

## Indicatifs téléphoniques

Les formulaires **Devis** et **Partenaires** demandent un téléphone (facultatif) en deux parties : l'indicatif pays,
choisi dans une liste (drapeau, pays, indicatif), puis le numéro. La liste se modifie dans `config/site.yml`,
rubrique `telephone` :

```yaml
telephone:
  par_defaut: {fr: FR, en: "", pt: AO}     # pays présélectionné selon la langue ("" = aucun)
  indicatifs:
    - {pays: AO, indicatif: "244", nom: "Angola"}
    - {pays: CD, indicatif: "243", nom: {fr: "RD Congo", en: "DR Congo", pt: "RD Congo"}}
```

- `pays` : code du pays en 2 lettres majuscules (il donne le drapeau) ; `indicatif` : chiffres seuls, sans `+`.
- Les pays s'affichent dans l'ordre du fichier ; « Autre » (saisie libre de l'indicatif) est ajouté en dernier.
- Le visiteur peut aussi taper directement `+244…` ou `00244…` : l'indicatif est reconnu et le sélecteur se met à jour.
  Espaces, points, tirets, parenthèses et le 0 initial sont retirés (sauf pour l'Italie, où le 0 fait partie du
  numéro). Il faut 6 à 14 chiffres après l'indicatif, sinon un message s'affiche ; un champ vide est accepté.
- L'email reçu contient `Téléphone` au format international (ex. `+244923456789`, vide si non renseigné) et
  `Joignable sur WhatsApp` (oui / non).
- La normalisation et le contrôle sont dans `static/assets/tel.js`, testés par `tests/tel.test.js`.

## Publier les CGV

Les conditions générales de vente entre professionnels se rédigent dans `content/legal/cgv.fr.html`,
`cgv.en.html` et `cgv.pt.html`, sous le commentaire d'explication :

```html
<h3>Article 1 — Objet</h3>
<p>Les présentes conditions générales s'appliquent à …</p>
```

Tant que ces fichiers sont vides, **aucune page CGV n'existe** (ni lien, ni plan du site). Dès que les trois
contiennent leur texte, la page est publiée à `/cgv/`, `/en/terms-of-sale/` et `/pt/condicoes-gerais-de-venda/`,
avec un lien dans le pied de page. Si une seule langue est remplie, la génération s'arrête et l'indique.

## Voir le résultat sur votre ordinateur

Il faut Python 3 (déjà installé sur Mac). Dans un terminal, à la racine du dossier, la première fois :

```
python3 -m pip install -r tools/requirements.txt
```

puis, à chaque fois :

```
python3 tools/build.py --serve
```

puis ouvrez http://localhost:8000. Pour vérifier les liens et la sécurité : `python3 tools/check.py`.

## Référencement (SEO)

Tout est produit automatiquement par `tools/build.py` ; `tools/check.py` le vérifie avant chaque mise en ligne.

- **Traductions pour les lecteurs d'écran** : les textes des attributs `aria-label`, `alt`, `title`, `placeholder`
  et le titre des dessins SVG se traduisent dans `content/i18n.json`, comme le texte visible. Une traduction
  manquante arrête la génération ; un texte français resté sur une page EN ou PT bloque les contrôles.
- **Données structurées (schema.org)** :
  - sur l'accueil : l'organisation, le fondateur, le site et la FAQ, construite à partir des questions affichées
    (`<details class="faq">` de `content/pages/home.html`) ;
  - dans les articles : l'article, avec le fondateur comme auteur ;
  - sur les pages secteurs et les articles : le fil d'Ariane (« Accueil > Secteurs > … »).

  Le nom, l'autre nom et la fonction du fondateur sont dans `FONDATEUR` (`tools/build.py`) ; ses réseaux sont
  dans `config/site.yml`.
- **Plan du site** : chaque page porte la date de dernière modification de son fichier source (historique git ;
  date de l'article pour les articles). Le portail DEMO (données fictives) est exclu des moteurs (`noindex`) et du
  plan du site (`NOINDEX` dans `tools/build.py`).
- **Icônes** : `favicon.ico`, `images/icon-192.png` et `apple-touch-icon.png` sont fabriquées à chaque génération
  à partir de `static/images/logo.png` : remplacer ce fichier suffit.
- **robots.txt** : moteurs de recherche et robots des IA (GPTBot, ClaudeBot, Google-Extended…) autorisés ; seuls
  CCBot, Bytespider et anthropic-ai sont refusés.
- **Avertissements** (non bloquants) affichés par `tools/check.py` : titre de plus de 60 caractères, description de
  moins de 70 ou de plus de 160 caractères, titre ou description en double dans une même langue.

## Mise en ligne

- Chaque **pull request** lance la génération et les contrôles (onglet « Checks ») : si quelque chose est cassé,
  la PR l'indique et rien n'est publié.
- Chaque **merge sur `main`** génère le site et le publie sur chanceleno.com en environ une minute
  (fichier `.github/workflows/deploy.yml`).
- Les anciennes adresses du type `chanceleno.com/#/devis` continuent de fonctionner : elles redirigent vers
  les nouvelles (`/devis/`, `/en/quote/`, `/pt/cotacao/`…).

## Statistiques de visite (GoatCounter)

Le site mesure sa fréquentation avec **GoatCounter**, un outil gratuit **sans cookie** qui ne conserve pas les
adresses IP : aucun bandeau de consentement n'est affiché.

- **Script** : `static/assets/count.js` (publié à l'adresse `/assets/count.js`), copie non modifiée du fichier
  officiel de **GoatCounter v2.7.0** (https://github.com/arp242/goatcounter/blob/v2.7.0/public/count.js,
  SHA-256 `030ad75a7c80a04107a9b91f79e4b1572da0a583a80a9b67e111b310da11cbe9`). Il n'est pas chargé depuis
  gc.zgo.at : aucun script externe n'est autorisé.
- **Sécurité** : la politique de sécurité du contenu n'autorise l'envoi des statistiques que vers
  `https://chanceleno.goatcounter.com` (en plus de FormSubmit pour les formulaires). `tools/check.py` refuse
  toute page qui autoriserait un autre domaine.
- **Réglage** : dans `config/site.yml`, rubrique `statistiques` :
  ```yaml
  statistiques:
    goatcounter: chanceleno
  ```
  Mettez `goatcounter: ""` pour arrêter complètement le comptage (le script n'est alors plus chargé).
- **Mise à jour du script** (rarement utile) : remplacer `static/assets/count.js` par le fichier d'une nouvelle
  version officielle, en gardant l'en-tête qui indique sa version, et mettre à jour ce paragraphe.

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

## Images et polices (rapidité du site)

- **Images** : chaque image affichée dans une page est **convertie en WebP et redimensionnée** automatiquement (au
  double de sa taille d'affichage), reçoit ses dimensions et se charge seulement quand elle devient visible. Les
  tailles se règlent dans `IMAGE_SIZES` et `PHOTO_SIZES` (`tools/build.py`). Les images de partage
  (`og-image*.jpg`) restent en JPG. Emplacements des photos : voir « Ajouter une photo ».
- **Polices** : le site publie des versions légères (WOFF2, 141 Ko au lieu de 1,1 Mo) des polices Archivo et
  Newsreader, limitées aux caractères du français, de l'anglais et du portugais. Si un jour une autre langue ou une
  autre police est nécessaire : `python3 -m pip install fonttools==4.60.1 brotli==1.1.0` puis `python3 tools/fonts.py`.
- **Mesurer** : `python3 tests/pages_server.py 8766` sert le site comme GitHub Pages (compression, cache), puis
  lancez Lighthouse (onglet « Lighthouse » de Chrome, mode mobile) sur `http://localhost:8766/`.

## Surveillance hebdomadaire

Chaque **lundi matin**, GitHub contrôle le site (`.github/workflows/surveillance.yml`) :

- `config/site.yml` est valide ;
- le site se génère et tous ses liens internes fonctionnent ;
- les liens vers d'autres sites répondent (LinkedIn, WhatsApp…) ;
- chaque page en ligne répond, en FR, EN et PT ;
- le plan du site en ligne (`sitemap.xml`) correspond au site.

**En cas de problème**, une **issue GitHub** intitulée « Surveillance du site : problème détecté », étiquetée
`surveillance`, est ouverte, et GitHub vous l'envoie **par email**. Elle liste chaque problème, par exemple :

```
- Page en ligne :
  https://chanceleno.com/en/quote/ : code 404
```

Que faire :
- **Lien vers un autre site** : le site visé a changé d'adresse ou ne répond plus. Corrigez ou retirez le lien
  (dans `config/site.yml` pour un réseau social, sinon dans le texte de la page).
- **Page en ligne** ou **plan du site** : la dernière publication a probablement échoué. Onglet « Actions »,
  ouvrez le dernier « Générer et publier le site » et relancez-le (« Re-run all jobs »).
- **Configuration** ou **tools/check.py** : le message indique le champ ou la page à corriger.
- Un site qui refuse les contrôles automatiques (LinkedIn le fait souvent) est seulement **signalé pour
  information**, sans ouvrir d'issue.

Si le problème persiste la semaine suivante, l'issue est complétée par un commentaire (pas de doublon). Elle se
**ferme toute seule** au premier contrôle sans problème. Vous pouvez lancer le contrôle à tout moment : onglet
« Actions », « Surveillance hebdomadaire du site », « Run workflow ». Pour recevoir les emails, gardez la
notification des issues activée (bouton « Watch » du dépôt, sur « All Activity » ou « Custom » → « Issues »).

## Photos mises de côté

`sources/images/` contient quatre photos de réalisations **MACAIART** (aménagement intérieur et second œuvre),
retirées du site publié parce qu'elles n'étaient utilisées nulle part :

| Fichier | Contenu |
|---|---|
| `macaiart-equipe.jpg` | une membre de l'équipe MACAIART devant un meuble TV décoratif réalisé dans un salon |
| `macaiart-piscine.jpg` | une piscine en mosaïque bleue dans la cour d'une villa |
| `macaiart-plafond.jpg` | un faux plafond géométrique avec éclairage LED |
| `macaiart-salle-bain.jpg` | une salle de bain en marbre noir et blanc avec baignoire îlot |

Usage possible : illustrer une **référence client MACAIART** (secteur aménagement et second œuvre), ou un article
sur l'approvisionnement en matériaux de finition, **uniquement avec l'accord écrit de MACAIART**. Pour en utiliser
une, copiez-la dans `static/images/` (par exemple `static/images/references/macaiart.jpg`).

## À faire régulièrement

- **Chaque année, avant le 22 octobre** : repousser d'un an la date `Expires` de `static/.well-known/security.txt`.
- **Après l'immatriculation de CHANCELENO INTERNATIONAL** : remplir les champs Kbis (voir plus haut). Seul le texte
  des informations contractuelles (`content/pages/conditions.html`) reste à relire à la main.

## Tests navigateur (facultatif)

`tests/site.test.js` vérifie toutes les pages à 360, 412, 1024, 1280 et 1440 px, les formulaires (sans rien envoyer), les
anciennes adresses, la langue mémorisée, l'assistant et WhatsApp :

```
python3 tools/build.py && (cd _site && python3 -m http.server 8765 &)
cd tests && npm install && npx playwright install chromium && npm test
```

`tests/tel.test.js` vérifie, sans navigateur, la normalisation et le contrôle des numéros de téléphone :
`node tel.test.js` (lancé aussi par `npm test`).

`tests/stats.test.js` vérifie les statistiques (pages vues, événements, « Ne pas compter mes visites ») sans rien
envoyer : `GC=chanceleno node stats.test.js`.

`tests/lot5.test.js` vérifie les données de `config/site.yml` (statut de la société, prix, liens, copyright,
logo animé seulement à la première page de la visite) : `node lot5.test.js`. `python3 tests/fictif.py` refait ces
contrôles avec des **valeurs fictives** (Kbis, photos, références autorisée et non autorisée, Instagram, CGV, carte
masquée) et des erreurs volontaires, puis remet la configuration réelle en place.
