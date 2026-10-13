# Veille IA × Architecture & BTP (version light)

Chaque module = un fichier court, un rôle. Ordre d'exécution (voir `main.py`) :

collecte → filtre → doublons (embeddings + base vectorielle) → analyse LLM → score → CSV / rapport / tableau de bord / Discord

| Fichier | Rôle |
|---|---|
| `collecte.py` | lit les flux RSS / Atom |
| `filtre.py` | garde « IA » ET « architecture/BTP » |
| `gemini.py` | appel unique à l'API Gemini (réessais si serveur occupé) |
| `embeddings.py` | texte -> vecteur (le sens en nombres) |
| `base_vectorielle.py` | mémoire des vecteurs (`data/vecteurs.json`) ; `data/liens_vus.txt` = liens déjà traités |
| `doublons.py` | écarte les articles déjà vus ou de même sens |
| `llm.py` | phase, maturité, impact, pertinence, résumé FR (plan B : mots-clés) |
| `scoring.py` | note finale /10 |
| `sortie.py`, `dashboard.py`, `alertes.py` | CSV + rapport, page web, Discord |

## Lancer
```
python -m unittest discover -s tests   # 17 tests
python main.py --demo                  # faux articles, sans internet -> docs/demo_index.html
python main.py                         # vraie collecte
```
Clé Gemini (facultative) : `$env:GEMINI_API_KEY="..."` (PowerShell). Sans clé : doublons par mots communs, analyse par mots-clés.
Si tu changes de modèle d'embeddings, supprime `data/vecteurs.json`.

## Automatiser
GitHub : envoyer le dossier, ajouter les secrets `GEMINI_API_KEY` et `DISCORD_WEBHOOK`, lancer l'Action une fois à la main, puis Settings > Pages > branche `main`, dossier `/docs`.
