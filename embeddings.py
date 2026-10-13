"""MODULE 4 - Embeddings : transforme un texte en liste de nombres qui représentent son SENS."""
import math
from gemini import appeler, MODELE_EMB

DIMENSION = 256


def vecteurs(textes):
    """Renvoie un vecteur par texte, ou None si Gemini n'est pas disponible."""
    resultat = []
    for i in range(0, len(textes), 50):                      # Gemini accepte les textes par paquets
        paquet = textes[i:i + 50]
        corps = {"requests": [{"model": f"models/{MODELE_EMB}", "content": {"parts": [{"text": t[:2000]}]},
                               "taskType": "SEMANTIC_SIMILARITY", "outputDimensionality": DIMENSION} for t in paquet]}
        reponse = appeler(MODELE_EMB, "batchEmbedContents", corps)
        if not reponse:
            return None
        for e in reponse["embeddings"]:
            v = e["values"]
            longueur = math.sqrt(sum(x * x for x in v)) or 1
            resultat.append([x / longueur for x in v])       # on ramène la longueur à 1
    return resultat


def similarite(a, b):
    """Proximité de sens entre deux vecteurs : 1 = identiques, 0 = rien en commun."""
    return sum(x * y for x, y in zip(a, b))
