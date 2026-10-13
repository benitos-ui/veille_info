import json, time
import collecte, filtre

config = json.load(open("sources.json", encoding="utf-8"))
for s in config["sources"]:
    try:
        arts = collecte.collecter(s)
    except Exception as e:
        print("✗", s["nom"], e)
        continue
    print(f"\n=== {s['nom']} : {len(arts)} articles")
    for a in arts:
        print(("GARDÉ   " if filtre.pertinent(a) else "écarté  ") + a["titre"][:90])
    time.sleep(3)