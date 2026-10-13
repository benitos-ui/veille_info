"""MODULE 9 - Sorties : fichier CSV cumulatif + rapport Markdown du jour."""
import csv, json, os
from datetime import datetime

CHAMPS = ["date_collecte", "date_pub", "source", "titre", "lien", "phase", "trl", "impact",
          "pertinence", "fiabilite", "fraicheur", "score", "methode", "resume_fr"]
NOMBRES = ["trl", "impact", "pertinence", "fiabilite", "fraicheur", "score"]


def ecrire_csv(chemin, lignes):
    nouveau = not os.path.exists(chemin)
    with open(chemin, "a", newline="", encoding="utf-8-sig") as f:
        ecrivain = csv.DictWriter(f, fieldnames=CHAMPS)
        if nouveau:
            ecrivain.writeheader()
        ecrivain.writerows(lignes)


def lire_csv(chemin):
    if not os.path.exists(chemin):
        return []
    lignes = list(csv.DictReader(open(chemin, encoding="utf-8-sig")))
    for l in lignes:
        for k in NOMBRES:
            l[k] = float(l[k])
    return lignes


def lire_liens(chemin):
    """Tous les liens déjà traités (gardés OU écartés comme doublons), un par ligne."""
    return set(open(chemin, encoding="utf-8").read().split()) if os.path.exists(chemin) else set()


def sauver_liens(chemin, liens):
    open(chemin, "w", encoding="utf-8").write("\n".join(sorted(liens)))


def ecrire_rapport(chemin, lignes, doublons, erreurs, seuil, stats):
    L = [f"# Veille IA × Architecture & BTP — {datetime.now():%Y-%m-%d}", "",
         f"- Articles lus : {stats['lus']} · pertinents : {stats['pertinents']} · écartés : {len(doublons)} · nouvelles fiches : {len(lignes)}", ""]
    for phase in ("Conception", "Chantier", "Exploitation"):
        for l in [x for x in lignes if x["phase"] == phase]:      # déjà triées par score
            cloche = "🔔 " if l["score"] >= seuil else ""
            L += [f"## {cloche}[{l['titre']}]({l['lien']})",
                  f"*{phase} · {l['source']} · score **{l['score']}/10** · TRL {l['trl']}/9 · analysé par : {l['methode']}*", "", l["resume_fr"], ""]
    if doublons:
        L += ["## Articles écartés (doublons ou hors sujet)", ""] + [f"- {a['titre']} — {raison}" for a, raison in doublons] + [""]
    if erreurs:
        L += ["## Sources en erreur", ""] + [f"- {e}" for e in erreurs]
    open(chemin, "w", encoding="utf-8").write("\n".join(L))


def ecrire_journal(chemin, date, stats, seuil, journal):
    """Décision pour CHAQUE article lu (retenu ou rejeté, et pourquoi) -> data/analyse.json."""
    json.dump({"date": date, "stats": stats, "seuil": seuil, "articles": journal},
              open(chemin, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
