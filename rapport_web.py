"""MODULE 13 - Rapport : pour CHAQUE article lu, la décision (retenu / rejeté) et sa raison.
Produit deux fichiers, sans aucun logiciel à installer :
  - une page web (docs/rapport.html), lisible en ligne, téléchargeable, et enregistrable en PDF avec le bouton « Imprimer / PDF » du navigateur ;
  - un fichier CSV (docs/rapport.csv), à ouvrir dans Excel.
Usage : python rapport_web.py          # data/analyse.json -> docs/rapport.html + docs/rapport.csv
        python rapport_web.py --md data/rapport.md   # ancien rapport Markdown (moins complet)
"""
import argparse, csv, html, json, os, re

# (clé d'étape, titre de section, explication)
ETAPES = [("collecte", "Données incomplètes", "Titre ou lien absent dans le flux."),
          ("ancien", "Trop anciens", "Publiés avant la fenêtre de veille (paramètre jours_max)."),
          ("hors_sujet", "Hors sujet (filtre mots-clés)", "Le texte doit contenir à la fois un terme d'IA et un terme d'architecture/BTP. Le terme trouvé est indiqué."),
          ("doublon", "Doublons", "Lien déjà traité, ou information identique à un article déjà gardé."),
          ("llm", "Écartés par l'analyse (LLM)", "Passés par le filtre mais jugés non pertinents à l'analyse détaillée.")]


# ---------------------------------------------------------------- lecture
def lire_journal(chemin):
    d = json.load(open(chemin, encoding="utf-8"))
    return d["date"], d["articles"], d.get("seuil", 7.0)


def lire_markdown(chemin):
    """Secours : reconstruit un journal (partiel) depuis l'ancien rapport.md."""
    texte = open(chemin, encoding="utf-8").read()
    date = re.search(r"(\d{4}-\d{2}-\d{2})", texte).group(1)
    arts = []
    for bloc in re.split(r"^## ", texte, flags=re.M)[1:]:
        entete, _, corps = bloc.partition("\n")
        if entete.startswith("Articles écartés"):
            for l in corps.splitlines():
                if l.startswith("- "):
                    t, _, r = l[2:].rpartition(" — ")
                    etape = "llm" if "LLM" in r else "doublon"
                    arts.append({"titre": t, "source": "", "lien": "", "decision": "rejeté", "etape": etape, "raison": r})
        else:
            m = re.match(r"(?:🔔 )?\[(.+)\]\((\S+)\)$", entete.strip())
            meta = re.search(r"\*(.+?) · (.+?) · score \*\*([\d.]+)/10\*\* · TRL (\d+)/9 · analysé par : (.+?)\*", corps)
            if m and meta:
                arts.append({"titre": m.group(1), "lien": m.group(2), "decision": "retenu", "etape": "retenu", "raison": "",
                             "phase": meta.group(1), "source": meta.group(2), "score": float(meta.group(3)),
                             "trl": int(meta.group(4)), "methode": meta.group(5), "resume": corps[meta.end():].strip()})
    return date, arts, 7.0


def date_fr(d):
    mois = "janvier février mars avril mai juin juillet août septembre octobre novembre décembre".split()
    y, m, j = d.split("-")
    return f"{int(j)} {mois[int(m) - 1]} {y}"


# ---------------------------------------------------------------- page web
def ecrire_html(source, chemin):
    """Page web du rapport (lisible en ligne, téléchargeable, imprimable en PDF par le navigateur)."""
    date, arts, seuil = lire_markdown(source) if source.endswith(".md") else lire_journal(source)
    e = lambda t: html.escape(str(t))
    lien_a = lambda a: f'<a href="{e(a["lien"])}" target="_blank" rel="noopener noreferrer">{e(a["titre"])}</a>' if a.get("lien", "").startswith("http") else e(a["titre"])
    retenus = sorted([a for a in arts if a["decision"] == "retenu"], key=lambda a: -a.get("score", 0))
    rejetes = [a for a in arts if a["decision"] != "retenu"]
    corps = [f"<h1>Rapport du {e(date_fr(date))}</h1><p class='doux noprint'><a href='./'>← Tableau de bord</a> · <button onclick='window.print()'>Imprimer / enregistrer en PDF</button></p>",
             f"<p>{len(arts)} articles examinés : <b>{len(retenus)} retenus</b>, <b>{len(rejetes)} rejetés</b>.</p>",
             "<h2>Articles retenus</h2>"]
    corps.append("<table><tr><th>Titre</th><th>Phase</th><th>Score</th><th>Analyse</th></tr>" + "".join(
        f"<tr><td>{lien_a(a)}</td><td>{e(a.get('phase', ''))}</td><td><b>{a.get('score', 0):.1f}</b></td><td>{e(a.get('methode', ''))}</td></tr>" for a in retenus) + "</table>" if retenus else "<p>Aucun article retenu.</p>")
    corps.append("<h2>Articles rejetés et pourquoi</h2>")
    for cle, titre, expl in ETAPES:
        groupe = [a for a in rejetes if a["etape"] == cle]
        if groupe:
            corps.append(f"<h3>{e(titre)} ({len(groupe)})</h3><p class='doux'>{e(expl)}</p><table><tr><th>Article</th><th>Raison</th></tr>" + "".join(
                f"<tr><td>{lien_a(a)}{' <span class=doux>(' + e(a['source']) + ')</span>' if a.get('source') else ''}</td><td>{e(a['raison'])}</td></tr>" for a in groupe) + "</table>")
    page = ("<!doctype html><html lang='fr'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>Rapport de veille</title><style>:root{--bg:#fbfaf7;--t:#1a1a1a;--d:#6b6b6b;--l:#dcd9d0;--a:#b4531a}"
            "@media(prefers-color-scheme:dark){:root{--bg:#161616;--t:#e9e7e2;--d:#9a978f;--l:#333;--a:#f0a068}}"
            "body{margin:0;background:var(--bg);color:var(--t);font:16px/1.5 Georgia,serif}main{max-width:900px;margin:0 auto;padding:30px 20px 60px}"
            "h1{font-size:1.5rem}h2{margin-top:2rem;border-bottom:1px solid var(--l);padding-bottom:4px}h3{margin-bottom:0}a{color:var(--a)}"
            ".doux{color:var(--d);font:.85rem system-ui,sans-serif}table{width:100%;border-collapse:collapse;font:.9rem system-ui,sans-serif;margin-top:8px}"
            "button{font:inherit;font-size:.85rem;cursor:pointer;border:1px solid var(--l);background:transparent;color:var(--t);border-radius:4px;padding:3px 10px}@media print{.noprint{display:none}a{color:inherit;text-decoration:none}body{background:#fff;color:#000}}th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--l);vertical-align:top}th{color:var(--d);font-weight:600}</style></head><body><main>"
            + "".join(corps) + "</main></body></html>")
    open(chemin, "w", encoding="utf-8").write(page)


def ecrire_csv(source, chemin):
    """Une ligne par article lu : décision, étape, raison, puis les détails (ouvrable dans Excel)."""
    date, arts, seuil = lire_markdown(source) if source.endswith(".md") else lire_journal(source)
    champs = ["decision", "etape", "raison", "titre", "source", "lien", "date_pub", "phase", "score", "methode"]
    with open(chemin, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=champs, extrasaction="ignore")
        w.writeheader()
        w.writerows(arts)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--md")
    ap.add_argument("--journal", default="data/analyse.json")
    ap.add_argument("--sortie", default="docs")
    a = ap.parse_args()
    source = a.md or a.journal
    os.makedirs(a.sortie, exist_ok=True)
    ecrire_html(source, os.path.join(a.sortie, "rapport.html"))
    ecrire_csv(source, os.path.join(a.sortie, "rapport.csv"))
    print("Rapport :", os.path.join(a.sortie, "rapport.html"), "et rapport.csv")
