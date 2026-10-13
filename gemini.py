"""MODULE 3 - Appel à Gemini : une seule fonction, utilisée par les embeddings et par le LLM."""
import os, json, time, urllib.request, urllib.error

MODELE_LLM = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
MODELE_EMB = os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-001")
PAUSE = 3  # secondes entre deux appels (le palier gratuit limite le nombre de requêtes par minute)


def appeler(modele, methode, corps):
    """Envoie une requête à Gemini. Renvoie la réponse (dict), ou None s'il n'y a pas de clé / en cas d'échec."""
    cle = os.getenv("GEMINI_API_KEY")
    if not cle:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modele}:{methode}"
    for essai in range(3):
        try:
            time.sleep(PAUSE)
            requete = urllib.request.Request(url, data=json.dumps(corps).encode(),
                                             headers={"Content-Type": "application/json", "x-goog-api-key": cle})
            return json.loads(urllib.request.urlopen(requete, timeout=40).read())
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 503) and essai < 2:   # serveur occupé : on attend puis on réessaie
                time.sleep(10 * (essai + 1))
                continue
            print(f"  (Gemini HTTP {e.code} avec le modèle {modele})")
            return None
        except Exception as e:                        # délai dépassé, réseau coupé...
            if essai < 2:
                print(f"  (Gemini ne répond pas : {e} - nouvel essai)")
                time.sleep(10)
                continue
            print(f"  (Gemini indisponible : {e})")
            return None
