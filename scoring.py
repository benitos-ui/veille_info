"""MODULE 8 - Score final sur 10 : pertinence 35 % + impact 20 % + maturité 15 % + fiabilité de la source 20 % + fraîcheur 10 %."""
from datetime import datetime, timezone


def note_finale(article, analyse):
    age = (datetime.now(timezone.utc) - article["date"]).days if article["date"] else 30   # âge en jours
    fraicheur = max(0, 10 - age / 3)                       # 10 le jour même, 0 à 30 jours
    maturite = analyse["trl"] / 9 * 10                     # TRL 1-9 -> /10
    score = (0.35 * analyse["pertinence"] + 0.20 * analyse["impact"] + 0.15 * maturite
             + 0.20 * article["fiabilite"] + 0.10 * fraicheur)
    return round(score, 1), round(fraicheur, 1)
