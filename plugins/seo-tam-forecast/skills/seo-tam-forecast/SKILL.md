---
name: seo-tam-forecast
description: Projection / forecast / prévision du trafic organique SEO et des conversions avec la méthode TAM (Total Addressable Market) - volume total d'un groupe de mots-clés × CTR moyen du site par tranche de positions (calculé depuis la Google Search Console) × taux de conversion organique, en 3 scénarios optimiste (1-3), neutre (4-6), pessimiste (7-10), avec saisonnalité mois par mois et graphique. À utiliser dès qu'on demande une projection ou une prévision de trafic organique (ex. « fais une projection de trafic pour 2027 », « combien de trafic SEO l'an prochain ? »), un forecast SEO, le potentiel de trafic d'un cluster ou d'une liste de mots-clés, ou les conversions attendues en se positionnant sur des requêtes.
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/forecast.py *)
---

# Projection de trafic SEO – méthode TAM

Estime le trafic organique (et les conversions) qu'un site peut obtenir en ciblant un groupe de mots-clés. **Le trafic et les conversions estimés sont toujours mensuels**, même pour une demande du type « projection pour 2027 » : ne jamais multiplier par 12 ni donner de total annuel. La saisonnalité répartit ce trafic mensuel mois par mois (janvier → décembre).

## Étape 0 – Demander les fichiers et les informations (toujours en premier)

Si l'utilisateur n'a pas fourni les deux fichiers ci-dessous, **ne pas lancer de calcul** : répondre avec ce message (reprendre l'horizon de la demande, ex. « pour 2027 »), puis attendre la réponse.

> Pour faire la projection de trafic [pour 2027], j'ai besoin de deux fichiers :
>
> **1. La liste des mots-clés ciblés, avec leur volume de recherche mensuel**
> Les requêtes sur lesquelles vous voulez vous positionner, exportées de Semrush, Ahrefs, Google Keyword Planner…
> Format CSV, deux colonnes suffisent : `Mot-clé` et `Volume`.
>
> **2. Un export Google Search Console des 12 derniers mois**
> Search Console → *Performances* → *Résultats de recherche* → période *12 derniers mois* → cochez *Clics*, *Impressions*, *CTR* et *Position moyenne* → *Exporter* → *Télécharger au format CSV*.
> Envoyez-moi le ZIP obtenu tel quel. Il me sert à calculer le taux de clic réel de votre site selon la position.
>
> **Deux questions :**
> - **Souhaitez-vous partager votre taux de conversion organique ?** (GA4 : conversions ÷ sessions organiques). Sinon, j'utiliserai 2,27 %.
> - **Avez-vous une saisonnalité propre à votre activité ?** Par exemple la tendance mensuelle de vos mots-clés (Google Trends, Keyword Planner) ou 12 coefficients de janvier à décembre. Sinon, j'appliquerai un profil de saisonnalité générique.
>
> **Facultatif :** le nom de votre marque et ses variantes (pour exclure les requêtes de marque), et la valeur d'une conversion (panier moyen, valeur d'un lead) pour estimer un chiffre d'affaires.

Règles :
- Un seul fichier fourni → accuser réception et redemander uniquement ce qui manque.
- Fichiers fournis sans réponse aux deux questions → lancer le calcul avec les valeurs par défaut (CVR 2,27 %, saisonnalité générique), le dire, et rappeler en une ligne qu'on peut relancer avec leurs propres valeurs.
- Pas d'accès à la GSC → proposer de continuer avec des CTR par défaut (31 / 23 / 13 %), en prévenant que la projection sera moins fiable.
- Pas de liste de mots-clés mais une thématique → si un outil de données SEO (ex. DataForSEO) est disponible, proposer de construire la liste et de récupérer les volumes, puis la faire valider avant de calculer.
- Ne pas redemander une information déjà donnée dans la conversation.

## La méthode

1. **Volume total (TAM)** = somme des volumes mensuels des mots-clés ciblés.
2. **Nettoyage de l'export GSC** : on retire les requêtes à moins de 5 clics, celles en position > 10 et les requêtes de **marque**.
3. **CTR moyen du site par tranche** : moyenne du CTR des requêtes restantes en position 1-3, 4-6 et 7-10.
4. **3 scénarios** : optimiste (1-3), neutre (4-6), pessimiste (7-10).
   Trafic estimé par mois = volume mensuel total × CTR de la tranche.
5. **Conversions** = trafic estimé × taux de conversion organique (CVR). *(Optionnel)* valeur = conversions × panier moyen.
6. **Saisonnalité** : trafic du mois = trafic estimé par mois × coefficient du mois (moyenne des 12 coefficients = 1, donc la moyenne mensuelle ne change pas).

Exemple (cluster « recettes de tarte », 26 500 recherches/mois, CTR 31 / 23 / 13 %, CVR 2,27 %), par mois :
optimiste 8 215 visites → 186 conversions ; neutre 6 095 → 138 ; pessimiste 3 445 → 78.

### Saisonnalité

- **Par défaut** : profil générique de la recherche web (creux l'été, pics en début et fin d'année) :
  janv. 1,08 · févr. 1,03 · mars 1,05 · avr. 1,00 · mai 0,98 · juin 0,95 · juil. 0,88 · août 0,85 · sept. 1,00 · oct. 1,05 · nov. 1,08 · déc. 1,05.
  Le signaler comme hypothèse et proposer d'intégrer celle de l'utilisateur.
- **Celle de l'utilisateur**, au choix :
  - 12 coefficients ou 12 volumes mensuels (janvier → décembre) : `--seasonality "1.2,1.1,…"` (normalisés automatiquement) ;
  - un CSV avec une colonne mois (`1`-`12`, `janvier`, `2025-03`…) et une colonne valeur (volume, indice Google Trends, coefficient) : `--seasonality fichier.csv` ;
  - le `Graphique.csv` du ZIP GSC (impressions jour par jour) : `--seasonality Graphique.csv`. À proposer seulement si le site cible déjà la même thématique, et prévenir que la croissance ou la baisse du site sur l'année se mélange à la saisonnalité.
  - un export Google Trends ou Keyword Planner : le convertir en 12 valeurs mensuelles (moyenne par mois) puis utiliser `--seasonality`.

## Calcul

1. **Préparer les fichiers** : extraire le ZIP GSC avec Python (`zipfile`) dans un dossier temporaire, en renommant sans accent : `unzip` sur macOS bloque sur le « ê » de `Requêtes.csv`. Utiliser `Requêtes.csv` (ou `Queries.csv`) pour les CTR. Les lignes vides avant l'en-tête (exports Google Sheets) sont ignorées par le script. Si la GSC n'a aucune requête à 5 clics ou plus dans une tranche, le script prend les CTR par défaut : le dire clairement dans la restitution (site trop jeune ou trop peu de trafic pour mesurer ses propres CTR). Si c'est un XLSX, le convertir en CSV. Nettoyer la liste de mots-clés : doublons, volumes vides, mots-clés hors sujet ; signaler les variantes qui visent la même page (« recette de tarte tatin » / « recette de la tarte tatin »).
2. **Période** : « pour 2027 » sert au titre (« Projection de trafic 2027 ») ; les chiffres restent mensuels.
3. **Lancer le script** (avec `--json` pour récupérer les valeurs mois par mois du graphique) :

   ```bash
   python3 ${CLAUDE_SKILL_DIR}/scripts/forecast.py mots-cles.csv \
     --gsc Requetes.csv --brand "marque,ma marque" --cvr 2.27
   ```

   Options :
   - `--gsc fichier.csv` : export « Requêtes » de la GSC (colonnes FR ou EN détectées) ;
   - `--brand "a,b"` : termes de marque à exclure de la GSC ;
   - `--min-clicks 5` : seuil de clics GSC (défaut 5) ;
   - `--ctr "1-3=31,4-6=23,7-10=13"` : CTR imposés (en %), utilisés aussi si une tranche GSC est vide ;
   - `--cvr 2.27` : taux de conversion en % ;
   - `--seasonality …` : saisonnalité (voir ci-dessus ; défaut : profil générique) ;
   - `--chart fichier.html` + `--title "…"` : graphique en fichier HTML autonome (solution de repli, voir « Graphique ») ;
   - `--aov 45` : valeur d'une conversion (ajoute une colonne valeur) ;
   - `--keyword-col` / `--volume-col` : noms de colonnes si non détectés ;
   - `--out fichier.csv` : export des tableaux ; `--json` : sortie JSON.

## Restitution

- Titre avec le cluster et la période (ex. « Projection de trafic 2027 – cluster recettes de tarte »).
- Nombre de mots-clés et volume total ; tableau des 10 plus gros mots-clés + une ligne pour le reste.
- Tableau des scénarios : Scénario / Position / CTR / Trafic estimé / mois / CVR / Conversions estimées / mois (/ Valeur / mois).
- Tableau mois par mois (Mois / Coef. / Optimiste / Neutre / Pessimiste) et **le graphique du trafic estimé par mois** (voir « Graphique »).
- Hypothèses : provenance des CTR (nombre de requêtes GSC par tranche, exclusions), CVR réel ou par défaut, saisonnalité réelle ou par défaut.
- Limites en deux ou trois lignes :
  - c'est un potentiel (positionné sur **tous** les mots-clés), pas une prévision de montée progressive ;
  - une tranche GSC avec peu de requêtes donne un CTR fragile ;
  - la saisonnalité par défaut est générique : elle ne reflète pas forcément la thématique.
- Proposer l'export CSV si l'utilisateur veut reprendre les chiffres dans un tableur.

## Graphique

**Afficher le graphique directement dans la conversation**, sans créer de fichier, dès qu'un outil de visualisation en ligne est disponible (ex. `show_widget`) :
- courbes sur 12 mois (janv. → déc.), une par scénario, avec les valeurs `mensuel` de la sortie `--json` ;
- couleurs fixes : optimiste bleu `#2a78d6` (sombre `#3987e5`), neutre orange `#eb6834` (`#d95926`), pessimiste vert d'eau `#1baf7a` (`#199e70`) ;
- trait plein / tirets / pointillés en plus de la couleur ; légende au-dessus avec la moyenne mensuelle de chaque scénario ;
- axe Y à partir de 0, nombres au format français, infobulle avec les trois valeurs du mois.

Ne générer le fichier HTML (`--chart`) que si aucun outil d'affichage en ligne n'est disponible (ex. Claude Code en terminal) ou si l'utilisateur veut un fichier à partager ou à ouvrir dans un navigateur.

## Fichiers exemple

`examples/` contient un cluster de 40 mots-clés « recettes de tarte » (26 500 recherches/mois) et un faux export GSC du site « Les Papilles » (marque : « papilles »), qui donnent 31 / 23 / 13 % de CTR. Test :

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/forecast.py ${CLAUDE_SKILL_DIR}/examples/keywords-exemple.csv --gsc ${CLAUDE_SKILL_DIR}/examples/gsc-requetes-exemple.csv --brand "papilles" --cvr 2.27
```

Résultat attendu (mensuel) : 8 215 / 6 095 / 3 445 visites et 186 / 138 / 78 conversions.
