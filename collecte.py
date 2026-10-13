"""MODULE 1 - Collecte : lit un flux RSS (ou Atom pour arXiv) et renvoie une liste d'articles."""
import re, html, urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone


def nettoyer(texte):
    """Enlève les balises HTML (<p>, <b>...) d'un texte."""
    sans_balises = re.sub(r"<[^>]+>", " ", texte or "")
    return re.sub(r"\s+", " ", html.unescape(sans_balises)).strip()


def lire_date(texte):
    """Transforme un texte de date en vraie date (ou None si illisible)."""
    for lecteur in (parsedate_to_datetime, lambda t: datetime.fromisoformat(t.replace("Z", "+00:00"))):
        try:
            date = lecteur(texte)
            return date if date.tzinfo else date.replace(tzinfo=timezone.utc)
        except Exception:
            pass
    return None


def balise(element, *noms):
    """Renvoie la première balise enfant dont le nom est dans `noms` (sinon None)."""
    for enfant in element:
        if enfant.tag.split("}")[-1] in noms:
            return enfant
    return None


def texte_de(element):
    return element.text if element is not None and element.text else ""


def lire_flux(contenu, source):
    """Transforme le texte XML d'un flux en liste d'articles (dictionnaires)."""
    fiabilite = round(sum(source["craap"].values()) / len(source["craap"]) * 2, 1)  # notes CRAAP 1-5 -> /10
    articles = []
    prefiltre= source.get("prefiltre", True)
    for e in ET.fromstring(contenu).iter():
        if e.tag.split("}")[-1] not in ("item", "entry"):   # item = RSS, entry = Atom (arXiv)
            continue
        lien = balise(e, "link")
        articles.append({
            "titre": nettoyer(texte_de(balise(e, "title"))),
            "lien": ((lien.get("href") or lien.text or "") if lien is not None else "").strip(),
            "date": lire_date(texte_de(balise(e, "pubDate", "published", "updated"))),
            "resume": nettoyer(texte_de(balise(e, "description", "summary"))),
            "source": source["nom"], "type": source["type"], "fiabilite": fiabilite,
        })
    return articles


def collecter(source):
    """Télécharge le flux d'une source puis le lit."""
    requete = urllib.request.Request(source["url"], headers={"User-Agent": "Mozilla/5.0 (veille-ifri-groupe6)"})
    return lire_flux(urllib.request.urlopen(requete, timeout=25).read(), source)[: source.get("max", 100)]


if __name__ == "__main__":
    import json
    source = json.load(open("sources.json", encoding="utf-8"))["sources"][0]
    for a in collecter(source)[:5]:
        print(a["date"], "|", a["titre"])
