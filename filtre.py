"""MODULE 2 - Filtre : garde un article seulement s'il parle d'IA ET d'architecture/BTP."""
import re

MOTS_IA = (r"artificial intelligence|\bai\b|\bia\b|intelligence artificielle|machine learning|deep learning|"
           r"\bgenerative\b|génératif|neural network|\bllms?\b|large language model|computer vision|"
           r"reinforcement learning|digital twin|jumeau num|autonomous (?:robot|excavator|machine)")
MOTS_BTP = (r"\barchitect(?:ure|ural|s)?\b|construction (?:site|industry|project|material|robot)|civil engineering|"
            r"\bbim\b|\bconcrete\b|\bbéton\b|\bbtp\b|chantier|bâtiment|\bbuildings\b|building (?:information|design|energy|industry)|"
            r"fa[cç]ade|structural (?:engineering|design|analysis)|infrastructure|génie civil")


def pertinent(article):
    texte = (article["titre"] + " " + article["resume"]).lower()
    return bool(re.search(MOTS_IA, texte)) and bool(re.search(MOTS_BTP, texte))


def diagnostic(article):
    """None si l'article passe le filtre ; sinon la raison précise du rejet (avec les termes trouvés)."""
    texte = (article["titre"] + " " + article["resume"]).lower()
    ia, btp = sorted(set(re.findall(MOTS_IA, texte))), sorted(set(re.findall(MOTS_BTP, texte)))
    if ia and btp:
        return None
    if ia:
        return f"parle d'IA ({', '.join(ia[:3])}) mais aucun terme architecture/BTP"
    if btp:
        return f"parle d'architecture/BTP ({', '.join(btp[:3])}) mais aucun terme IA"
    return "aucun terme IA ni architecture/BTP"
