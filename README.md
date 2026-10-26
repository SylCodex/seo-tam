# SEO skills pour Claude Code

## seo-tam-forecast

Projection du trafic organique et des conversions d'un groupe de mots-clés, avec la méthode du TAM (Total Addressable Market) :

1. **Volume total** des mots-clés ciblés.
2. **CTR réels du site** par tranche de positions (1-3, 4-6, 7-10), calculés depuis un export Google Search Console (sans les requêtes de marque, celles à moins de 5 clics et celles au-delà de la position 10).
3. **3 scénarios** : optimiste (1-3), neutre (4-6), pessimiste (7-10). Trafic estimé par mois = volume total × CTR.
4. **Conversions** = trafic estimé × taux de conversion organique.
5. **Saisonnalité** mois par mois (profil générique ou celle du site) et **graphique** du trafic estimé par mois.

Méthode présentée dans [ce thread](https://x.com/scharbitjrs/status/1825829744576811327).

### Installation

Dans Claude Code :

```
/plugin marketplace add SylCodex/seo-tam
/plugin install seo-tam-forecast@seo-tam
```

Ou depuis un terminal :

```bash
claude plugin marketplace add SylCodex/seo-tam
claude plugin install seo-tam-forecast@seo-tam
```

Prérequis : Python 3 (aucune librairie à installer).

### Utilisation

Demandez simplement à Claude, par exemple :

> Fais une projection de trafic pour 2027

Claude vous demandera :

- **la liste des mots-clés ciblés** avec leur volume mensuel (CSV : `Mot-clé`, `Volume`), exportée de Semrush, Ahrefs, Keyword Planner… ;
- **un export Google Search Console des 12 derniers mois** (Performances → Résultats de recherche → Exporter → CSV), le ZIP tel quel ;
- en option : votre taux de conversion organique, votre saisonnalité, votre marque, la valeur d'une conversion.

Vous obtenez le tableau des 3 scénarios (trafic et conversions par mois), le détail mois par mois avec la saisonnalité et un graphique.

### Tester avec les fichiers exemple

Le dossier `plugins/seo-tam-forecast/skills/seo-tam-forecast/examples/` contient 40 mots-clés « recettes de tarte » et un faux export GSC. Demandez à Claude : « fais un forecast TAM avec les fichiers exemple du skill ».

Résultat attendu : 8 215 / 6 095 / 3 445 visites et 186 / 138 / 78 conversions par mois.

### Mise à jour

```
/plugin marketplace update seo-tam
```
