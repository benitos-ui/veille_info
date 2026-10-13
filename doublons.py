"""MODULE 6 - Doublons : écarte les articles déjà vus (même lien) ou de même sens."""
import re
from embeddings import vecteurs, similarite

SEUIL_SENS = 0.93     # au-dessus : même information (réglé avec le test de la v3)
SEUIL_MOTS = 0.3      # plan B sans Gemini : part de mots en commun (le vrai doublon de la démo : 0.40 ; les autres paires : < 0.1)


def cle_url(url):
    """Rend deux liens comparables : sans http, www, paramètres de suivi (?utm=...) ni slash final."""
    return re.sub(r"^https?://(www\.)?", "", url.split("?")[0].split("#")[0]).rstrip("/")


def mots(article):
    """L'ensemble des mots (4 lettres ou plus) du titre et du résumé."""
    return set(re.findall(r"[a-zà-ÿ]{4,}", (article["titre"] + " " + article["resume"]).lower()))


def part_commune(a, b):
    """Part de mots en commun entre deux articles : 0 = aucun, 1 = identiques."""
    ma, mb = mots(a), mots(b)
    return len(ma & mb) / len(ma | mb) if ma | mb else 0


def retirer_doublons(articles, base, liens_connus):
    """Renvoie (articles gardés, doublons écartés avec la raison)."""
    doublons, nouveaux = [], []
    for a in articles:                                        # 1) même lien déjà vu ?
        cle = cle_url(a["lien"])
        if cle in liens_connus:
            doublons.append((a, "lien déjà connu"))
        else:
            liens_connus.add(cle)
            nouveaux.append(a)
    if not nouveaux:
        return [], doublons

    vecs = vecteurs([a["titre"] + " " + a["resume"][:500] for a in nouveaux])
    gardes = []
    if vecs is None:                                          # 2b) plan B : on compare les mots
        for a in nouveaux:
            if any(part_commune(a, g) >= SEUIL_MOTS for g in gardes):
                doublons.append((a, "mots très proches"))
            else:
                gardes.append(a)
        return gardes, doublons

    vecs_gardes = []                                          # 2a) on compare le sens
    for a, v in zip(nouveaux, vecs):
        proche = max(base.meilleure_similarite(v), max((similarite(v, w) for w in vecs_gardes), default=0))
        if proche >= SEUIL_SENS:
            doublons.append((a, f"même sens ({proche:.2f})"))
        else:
            gardes.append(a)
            vecs_gardes.append(v)
            base.ajouter(a["lien"], v)
    return gardes, doublons
