"""MODULE 11 - Alertes : envoie les articles à fort score dans un salon Discord."""
import os, json, urllib.request


def discord(articles):
    adresse = os.getenv("DISCORD_WEBHOOK")
    if not adresse or not articles:
        return
    lignes = [f"• **{a['score']}/10** [{a['phase']}] {a['titre']} — {a['lien']}" for a in articles[:8]]
    message = "🔔 **Veille IA/BTP — innovations à fort score**\n" + "\n".join(lignes)
    requete = urllib.request.Request(adresse, data=json.dumps({"content": message[:1900]}).encode(),
                                     headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    try:
        urllib.request.urlopen(requete, timeout=15)
    except Exception as e:
        print("Alerte Discord échouée :", e)
