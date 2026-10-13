"""MODULE 12 - Chef d'orchestre : appelle tous les modules dans l'ordre.
Usage : python main.py          (vraie collecte)
        python main.py --demo   (faux articles, sans internet)"""
import json, sys, time
from datetime import datetime, timezone, timedelta
import collecte, filtre, doublons, llm, scoring, sortie, dashboard, alertes, rapport_pdf
from base_vectorielle import Base

DEMO = "--demo" in sys.argv
P = "demo_" if DEMO else ""                      # préfixe pour ne pas mélanger démo et vrais résultats
CSV, RAPPORT, PAGE = f"data/{P}veille.csv", f"data/{P}rapport.md", f"docs/{P}index.html"
VECTEURS, LIENS = f"data/{P}vecteurs.json", f"data/{P}liens_vus.txt"
JOURNAL = f"data/{P}analyse.json"


def articles_demo(config):
    """Faux articles du dossier sample_data (pour tester sans internet)."""
    fiabilite = {s["nom"]: round(sum(s["craap"].values()) / len(s["craap"]) * 2, 1) for s in config["sources"]}
    return [{"titre": d["titre"], "lien": d["lien"], "resume": d["resume"], "source": d["source"],
             "type": "arxiv" if "arXiv" in d["source"] else "rss", "fiabilite": fiabilite[d["source"]],
             "date": datetime.now(timezone.utc) - timedelta(days=d["jours"])}
            for d in json.load(open("sample_data/sample.json", encoding="utf-8"))]


def main():
    config = json.load(open("sources.json", encoding="utf-8"))
    maintenant = datetime.now(timezone.utc)

    # 1. Collecte
    erreurs, articles = [], []
    if DEMO:
        articles = articles_demo(config)
    else:
        for source in config["sources"]:
            try:
                articles += collecte.collecter(source)
            except Exception as e:
                erreurs.append(f"{source['nom']} : {e}")
            time.sleep(3) 
        if not articles:
            sys.exit("Aucune source n'a répondu : vérifier internet et les adresses des flux.")

    # 2. Filtre (récents + pertinents) ; journal = la décision prise pour chaque article
    journal = []
    def noter(a, decision, etape, raison, **plus):
        journal.append({"titre": a["titre"], "source": a["source"], "lien": a["lien"],
                        "date_pub": f"{a['date']:%Y-%m-%d}" if a["date"] else "", "decision": decision,
                        "etape": etape, "raison": raison, **plus})
    recents, pertinents = [], []
    for a in articles:
        age = (maintenant - a["date"]).days if a["date"] else 0
        if not (a["titre"] and a["lien"]):
            noter(a, "rejeté", "collecte", "titre ou lien manquant")
        elif age > config["jours_max"]:
            noter(a, "rejeté", "ancien", f"publié il y a {age} jours (limite : {config['jours_max']})")
        else:
            recents.append(a)
            raison = None if not a.get("prefiltre", True) else filtre.diagnostic(a)
            if raison:
                noter(a, "rejeté", "hors_sujet", raison)
            else:
                pertinents.append(a)

    # 3. Doublons
    base = Base(VECTEURS)
    liens = sortie.lire_liens(LIENS)
    gardes, ecartes = doublons.retirer_doublons(pertinents, base, liens)
    for a, raison in ecartes:
        noter(a, "rejeté", "doublon", raison)

    # 4. Analyse + score
    lignes = []
    for a in gardes:
        analyse = llm.analyser(a)
        if not analyse["pertinent"]:                      # 2e filtre : Gemini juge l'article hors sujet
            ecartes.append((a, "jugé hors sujet par le LLM : " + analyse["raison"]))
            noter(a, "rejeté", "llm", analyse["raison"] or "jugé hors sujet", methode=analyse["methode"])
            continue
        score, fraicheur = scoring.note_finale(a, analyse)
        noter(a, "retenu", "retenu", "article pertinent", phase=analyse["phase"], trl=analyse["trl"], score=score,
              methode=analyse["methode"], resume=analyse["resume_fr"])
        lignes.append({"date_collecte": f"{maintenant:%Y-%m-%d}", "date_pub": f"{a['date']:%Y-%m-%d}" if a["date"] else "",
                       "source": a["source"], "titre": a["titre"], "lien": a["lien"], "phase": analyse["phase"],
                       "trl": analyse["trl"], "impact": analyse["impact"], "pertinence": analyse["pertinence"],
                       "fiabilite": a["fiabilite"], "fraicheur": fraicheur, "score": score,
                       "methode": analyse["methode"], "resume_fr": analyse["resume_fr"]})
    lignes.sort(key=lambda l: -l["score"])

    # 5. Sorties
    sortie.ecrire_csv(CSV, lignes)
    sortie.ecrire_rapport(RAPPORT, lignes, ecartes, erreurs, config["seuil_alerte"], {"lus": len(articles), "pertinents": len(pertinents)})
    base.sauver()
    sortie.sauver_liens(LIENS, liens)
    dashboard.ecrire(PAGE, sortie.lire_csv(CSV)[-200:], config["seuil_alerte"])
    sortie.ecrire_journal(JOURNAL, f"{maintenant:%Y-%m-%d}", {"lus": len(articles), "retenus": len(lignes)}, config["seuil_alerte"], journal)
    try:                                                  # le PDF est un bonus : son échec ne bloque pas la veille
        print("PDF :", rapport_pdf.generer(JOURNAL, f"{P}rapport"))
    except Exception as e:
        print("  ✗ rapport PDF non généré :", e)
    alertes.discord([l for l in lignes if l["score"] >= config["seuil_alerte"]])

    print(f"Lus {len(articles)} | pertinents {len(pertinents)} | écartés {len(ecartes)} | nouvelles fiches {len(lignes)}")
    for e in erreurs:
        print("  ✗", e)


if __name__ == "__main__":
    main()
