#!/usr/bin/env python3
"""Forecast SEO par la méthode TAM : volume total x CTR par tranche x CVR."""
import argparse
import csv
import json
import os
import sys

DEFAULT_CTR = "1-3=31,4-6=23,7-10=13"
KEYWORD_ALIASES = ["mot-clé", "mot-cle", "mot clé", "mots-clés", "keyword", "keywords", "query", "requête", "requete", "kw"]
VOLUME_ALIASES = ["volume", "search volume", "volume de recherche", "avg. monthly searches", "sv", "vol"]


def parse_number(value):
    s = str(value).strip().replace(" ", "").replace("\xa0", "").replace(" ", "")
    if not s:
        return None
    # "1,900" (milliers) vs "2,5" (décimale)
    if "," in s and "." not in s:
        head, _, tail = s.rpartition(",")
        s = head.replace(",", "") + ("" if len(tail) == 3 else ".") + tail
    else:
        s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def find_column(headers, explicit, aliases, label):
    lowered = {h.strip().lower(): h for h in headers}
    if explicit:
        if explicit.strip().lower() in lowered:
            return lowered[explicit.strip().lower()]
        sys.exit(f"Colonne {label} '{explicit}' introuvable. Colonnes : {headers}")
    for alias in aliases:
        if alias in lowered:
            return lowered[alias]
    for h in headers:
        if any(alias in h.lower() for alias in aliases):
            return h
    sys.exit(f"Colonne {label} non détectée. Colonnes : {headers}. Utilise --{label}-col.")


def read_keywords(path, keyword_col, volume_col):
    with open(path, encoding="utf-8-sig") as f:
        reader = open_dict_reader(f)
        headers = reader.fieldnames or []
        kcol = find_column(headers, keyword_col, KEYWORD_ALIASES, "keyword")
        vcol = find_column(headers, volume_col, VOLUME_ALIASES, "volume")

        merged, skipped = {}, 0
        for row in reader:
            kw = " ".join((row.get(kcol) or "").split())
            vol = parse_number(row.get(vcol, ""))
            if not kw or not vol or vol <= 0:
                skipped += 1
                continue
            key = kw.lower()
            # Doublon exact : on garde le plus gros volume
            if key not in merged or vol > merged[key][1]:
                merged[key] = (kw, vol)
    keywords = sorted(merged.values(), key=lambda kv: kv[1], reverse=True)
    return keywords, skipped


def parse_ctr(spec):
    buckets = []
    for part in spec.split(","):
        label, _, pct = part.partition("=")
        buckets.append((label.strip(), float(pct.replace("%", "").strip()) / 100))
    return buckets


def open_dict_reader(f):
    # Ignore les lignes vides (ou faites seulement de séparateurs) avant l'en-tête,
    # fréquentes dans les exports Google Sheets
    lines = f.read().splitlines()
    while lines and not lines[0].strip(" \t,;"):
        lines.pop(0)
    sample = "\n".join(lines[:50])
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    return csv.DictReader(lines, dialect=dialect)


def ctr_from_gsc(path, brand_terms, min_clicks, fallback):
    """Moyenne du CTR par tranche (1-3, 4-6, 7-10) sur un export « Requêtes » de la GSC.

    On retire les requêtes de marque, celles à moins de `min_clicks` clics
    et celles en position > 10, comme dans la méthode.
    """
    with open(path, encoding="utf-8-sig") as f:
        reader = open_dict_reader(f)
        headers = reader.fieldnames or []
        qcol = find_column(headers, None, ["top queries", "requêtes les plus fréquentes", "requête", "query"] + KEYWORD_ALIASES, "gsc-query")
        ccol = find_column(headers, None, ["clicks", "clics"], "gsc-clicks")
        tcol = find_column(headers, None, ["ctr"], "gsc-ctr")
        pcol = find_column(headers, None, ["position", "pos"], "gsc-position")

        bounds = [("1-3", 0, 3.5), ("4-6", 3.5, 6.5), ("7-10", 6.5, 10.5)]
        ctrs = {label: [] for label, _, _ in bounds}
        excluded = {"marque": 0, "clics": 0, "position": 0}
        for row in reader:
            query = (row.get(qcol) or "").lower()
            clicks = parse_number(row.get(ccol, "")) or 0
            ctr = parse_number(str(row.get(tcol, "")).replace("%", ""))
            pos = parse_number(row.get(pcol, ""))
            if ctr is None or pos is None:
                continue
            if any(term in query for term in brand_terms):
                excluded["marque"] += 1
                continue
            if clicks < min_clicks:
                excluded["clics"] += 1
                continue
            if pos > 10.5:
                excluded["position"] += 1
                continue
            # La GSC exporte « 2.8% » ou 0.028 selon le format
            ctr = ctr / 100 if ctr > 1 or "%" in str(row.get(tcol, "")) else ctr
            for label, lo, hi in bounds:
                if lo < pos <= hi:
                    ctrs[label].append(ctr)
                    break

    fallback = dict(fallback)
    buckets, details = [], []
    for label, _, _ in bounds:
        values = ctrs[label]
        if values:
            buckets.append((label, sum(values) / len(values)))
            details.append(f"{label} : {len(values)} requête(s)")
        else:
            buckets.append((label, fallback[label]))
            details.append(f"{label} : aucune requête, CTR par défaut utilisé")
    return buckets, details, excluded


def fmt_int(n):
    return f"{round(n):,}".replace(",", " ")


def fmt_pct(p):
    return f"{p * 100:.2f}".rstrip("0").rstrip(".").replace(".", ",") + " %"


# Profil générique de la recherche web (moyenne = 1) : creux l'été et pics en début et fin d'année
DEFAULT_SEASONALITY = [1.08, 1.03, 1.05, 1.00, 0.98, 0.95, 0.88, 0.85, 1.00, 1.05, 1.08, 1.05]
MONTHS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]
MONTH_NAMES = {
    "jan": 1, "janv": 1, "janvier": 1, "january": 1, "feb": 2, "fev": 2, "févr": 2, "février": 2, "fevrier": 2, "february": 2,
    "mar": 3, "mars": 3, "march": 3, "apr": 4, "avr": 4, "avril": 4, "april": 4, "may": 5, "mai": 5,
    "jun": 6, "juin": 6, "june": 6, "jul": 7, "juil": 7, "juillet": 7, "july": 7, "aug": 8, "aoû": 8, "aou": 8, "août": 8, "aout": 8, "august": 8,
    "sep": 9, "sept": 9, "septembre": 9, "september": 9, "oct": 10, "octobre": 10, "october": 10,
    "nov": 11, "novembre": 11, "november": 11, "dec": 12, "déc": 12, "décembre": 12, "decembre": 12, "december": 12,
}


def parse_month(value):
    s = str(value).strip().lower().rstrip(".")
    if not s:
        return None
    if s.isdigit() and 1 <= int(s) <= 12:
        return int(s)
    # 2025-03 ou 2025-03-14
    parts = s.replace("/", "-").split("-")
    if len(parts) >= 2 and parts[0].isdigit() and len(parts[0]) == 4 and parts[1].isdigit():
        return int(parts[1]) if 1 <= int(parts[1]) <= 12 else None
    return MONTH_NAMES.get(s.split()[0])


def normalize(values):
    mean = sum(values) / len(values)
    if mean <= 0:
        sys.exit("Saisonnalité invalide : valeurs nulles.")
    return [v / mean for v in values]


def read_seasonality(spec):
    """12 coefficients « 1.1,1,... » ou un CSV (mois + valeur, ou export GSC « Graphique.csv » jour par jour)."""
    if not spec:
        return DEFAULT_SEASONALITY, "profil par défaut (recherche web générique)"
    if not os.path.isfile(spec):
        values = [parse_number(v) for v in spec.replace(";", ",").split(",") if v.strip()]
        if len(values) != 12 or any(v is None for v in values):
            sys.exit("--seasonality attend 12 valeurs (janvier → décembre) ou un fichier CSV.")
        return normalize(values), "coefficients fournis"

    with open(spec, encoding="utf-8-sig") as f:
        reader = open_dict_reader(f)
        headers = reader.fieldnames or []
        lowered = [h.strip().lower() for h in headers]
        mcol = headers[0]
        for name in ("date", "mois", "month"):
            if name in lowered:
                mcol = headers[lowered.index(name)]
                break
        vcol = None
        for name in ("impressions", "volume", "clics", "clicks", "coef", "coefficient", "indice"):
            if name in lowered:
                vcol = headers[lowered.index(name)]
                break
        vcol = vcol or next(h for h in headers if h != mcol)
        sums, counts = [0.0] * 12, [0] * 12
        for row in reader:
            month = parse_month(row.get(mcol, ""))
            value = parse_number(row.get(vcol, ""))
            if month and value is not None:
                sums[month - 1] += value
                counts[month - 1] += 1
    missing = [MONTHS[i] for i in range(12) if not counts[i]]
    if missing:
        sys.exit(f"Saisonnalité incomplète, mois manquants : {', '.join(missing)}")
    # Moyenne par ligne : neutralise les mois de 28/31 jours dans un export quotidien
    return normalize([s / c for s, c in zip(sums, counts)]), f"{os.path.basename(spec)} (colonne « {vcol} »)"


def write_chart(path, title, subtitle, rows):
    template = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chart_template.html")
    with open(template, encoding="utf-8") as f:
        html = f.read()
    data = {
        "title": title,
        "subtitle": subtitle,
        "months": MONTHS,
        "series": [{"name": f"{r['scenario'].capitalize()} (pos. {r['position']})", "values": r["mensuel"]} for r in rows],
    }
    html = html.replace("__TITLE__", title).replace("__DATA__", json.dumps(data, ensure_ascii=False))
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", help="CSV avec une colonne mot-clé et une colonne volume")
    ap.add_argument("--keyword-col")
    ap.add_argument("--volume-col")
    ap.add_argument("--ctr", default=DEFAULT_CTR, help=f"CTR par tranche en %% (défaut {DEFAULT_CTR})")
    ap.add_argument("--gsc", help="Export CSV « Requêtes » de la Search Console pour calculer les CTR du site")
    ap.add_argument("--brand", default="", help="Termes de marque à exclure de la GSC, séparés par des virgules")
    ap.add_argument("--min-clicks", type=float, default=5, help="Clics minimum d'une requête GSC (défaut 5)")
    ap.add_argument("--cvr", type=float, default=2.27, help="Taux de conversion en %% (défaut 2.27)")
    ap.add_argument("--aov", type=float, help="Valeur d'une conversion (panier moyen)")
    ap.add_argument("--seasonality", help="Saisonnalité : 12 coefficients janv.→déc. séparés par des virgules, ou un CSV (mois + valeur, ou Graphique.csv de la GSC). Défaut : profil générique")
    ap.add_argument("--chart", help="Graphique HTML du trafic estimé par mois")
    ap.add_argument("--title", default="Projection de trafic organique", help="Titre du graphique")
    ap.add_argument("--out", help="Export CSV des résultats")
    ap.add_argument("--json", action="store_true", help="Sortie JSON")
    args = ap.parse_args()

    season, season_source = read_seasonality(args.seasonality)

    for label, path in (("mots-clés", args.input), ("Search Console", args.gsc)):
        if path and not os.path.isfile(path):
            sys.exit(f"Fichier {label} introuvable : {os.path.abspath(path)}\n"
                     "Astuce : tape la commande jusqu'à l'argument, puis glisse le fichier "
                     "depuis le Finder dans le Terminal pour coller son chemin complet.")

    keywords, skipped = read_keywords(args.input, args.keyword_col, args.volume_col)
    if not keywords:
        sys.exit("Aucun mot-clé avec un volume valide.")
    total = sum(v for _, v in keywords)
    cvr = args.cvr / 100

    if args.gsc:
        brand_terms = [t.strip().lower() for t in args.brand.split(",") if t.strip()]
        buckets, ctr_details, excluded = ctr_from_gsc(args.gsc, brand_terms, args.min_clicks, parse_ctr(args.ctr))
        ctr_source = "Search Console (" + " ; ".join(ctr_details) + f") – exclues : {excluded['marque']} marque, {excluded['clics']} < {args.min_clicks:g} clics, {excluded['position']} position > 10"
    else:
        buckets = parse_ctr(args.ctr)
        ctr_source = "valeurs fournies" if args.ctr != DEFAULT_CTR else "valeurs par défaut (pas d'export GSC)"

    scenarios = {"1-3": "optimiste", "4-6": "neutre", "7-10": "pessimiste"}
    rows = []
    for label, ctr in buckets:
        traffic = total * ctr
        conversions = traffic * cvr
        row = {"position": label, "scenario": scenarios.get(label, ""), "ctr": ctr, "trafic": round(traffic), "cvr": cvr, "conversions": round(conversions)}
        if args.aov is not None:
            row["valeur"] = round(conversions * args.aov, 2)
        row["mensuel"] = [round(traffic * coef) for coef in season]
        rows.append(row)

    if args.chart:
        write_chart(args.chart, args.title,
                    f"Trafic organique estimé par mois · {len(keywords)} mots-clés, {fmt_int(total)} recherches/mois · saisonnalité : {season_source}",
                    rows)

    if args.json:
        print(json.dumps({
            "volume_total": total,
            "mots_cles": [{"mot_cle": k, "volume": v} for k, v in keywords],
            "lignes_ignorees": skipped,
            "source_ctr": ctr_source,
            "saisonnalite": {"source": season_source, "coefficients": [round(c, 3) for c in season]},
            "forecast": rows,
        }, ensure_ascii=False, indent=2))
    else:
        print(f"Mots-clés : {len(keywords)}  |  Volume total (TAM) : {fmt_int(total)} / mois"
              + (f"  |  {skipped} ligne(s) ignorée(s)" if skipped else ""))
        print()
        print("| Mot-clé | Volume |\n|---|---:|")
        for k, v in keywords:
            print(f"| {k} | {fmt_int(v)} |")
        print(f"| **Total** | **{fmt_int(total)}** |")
        print()
        print(f"CTR : {ctr_source}")
        print()
        head = "| Scénario | Position | CTR | Trafic estimé / mois | CVR | Conversions estimées / mois |"
        sep = "|---|---|---:|---:|---:|---:|"
        if args.aov is not None:
            head += " Valeur estimée / mois |"
            sep += "---:|"
        print(head + "\n" + sep)
        for r in rows:
            line = f"| {r['scenario']} | {r['position']} | {fmt_pct(r['ctr'])} | {fmt_int(r['trafic'])} | {fmt_pct(r['cvr'])} | {fmt_int(r['conversions'])} |"
            if args.aov is not None:
                line += f" {fmt_int(r['valeur'])} |"
            print(line)
        print()
        print(f"Trafic estimé mois par mois – saisonnalité : {season_source}")
        print()
        print("| Mois | Coef. | " + " | ".join(r["scenario"].capitalize() for r in rows) + " |")
        print("|---|---:|" + "---:|" * len(rows))
        for i, month in enumerate(MONTHS):
            print(f"| {month} | " + f"{season[i]:.2f}".replace(".", ",") + " | " + " | ".join(fmt_int(r["mensuel"][i]) for r in rows) + " |")

    if args.out:
        with open(args.out, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["Mot-clé", "Volume"])
            for k, v in keywords:
                w.writerow([k, round(v)])
            w.writerow(["Volume total", round(total)])
            w.writerow([])
            header = ["Scénario", "Position", "CTR", "Trafic estimé / mois", "CVR", "Conversions estimées / mois"]
            if args.aov is not None:
                header.append("Valeur estimée / mois")
            w.writerow(header)
            for r in rows:
                line = [r["scenario"], r["position"], fmt_pct(r["ctr"]), r["trafic"], fmt_pct(r["cvr"]), r["conversions"]]
                if args.aov is not None:
                    line.append(r["valeur"])
                w.writerow(line)
            w.writerow([])
            w.writerow(["Mois", "Coef. saisonnalité"] + [f"Trafic {r['scenario']}" for r in rows])
            for i, month in enumerate(MONTHS):
                w.writerow([month, f"{season[i]:.2f}".replace(".", ",")] + [r["mensuel"][i] for r in rows])
        print(f"\nExport : {args.out}", file=sys.stderr)
    if args.chart:
        print(f"Graphique : {args.chart}", file=sys.stderr)


if __name__ == "__main__":
    main()
