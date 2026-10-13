import sys, os, json, tempfile, unittest
from pathlib import Path
from unittest import mock
from datetime import datetime, timezone, timedelta
sys.path.insert(0, str(Path(__file__).parent.parent))
import collecte, filtre, doublons, llm, scoring, sortie, embeddings
from base_vectorielle import Base

SRC = {"nom": "T", "type": "rss", "craap": {"a": 5, "b": 5}}
RSS = b"""<rss><channel><item><title>AI plugin</title><link>https://ex.org/a</link><pubDate>Mon, 12 Oct 2026 08:00:00 +0000</pubDate>
<description>&lt;p&gt;Generative &lt;b&gt;design&lt;/b&gt; for architects&lt;/p&gt;</description></item></channel></rss>"""
ATOM = b"""<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Deep learning on site</title><link href="http://arxiv.org/abs/1"/>
<published>2026-10-10T10:00:00Z</published><summary>Neural network for construction site safety.</summary></entry></feed>"""

def art(titre, resume="", lien=None, type_="rss"):
    return {"titre": titre, "resume": resume, "lien": lien or "https://ex.org/" + titre.replace(" ", "")[:10], "source": "T",
            "type": type_, "fiabilite": 8.0, "date": datetime.now(timezone.utc) - timedelta(days=1)}

class Collecte(unittest.TestCase):
    def test_rss(self):
        a = collecte.lire_flux(RSS, SRC)[0]
        self.assertEqual((a["resume"], a["fiabilite"]), ("Generative design for architects", 10.0)); self.assertIsNotNone(a["date"])
    def test_atom(self):
        a = collecte.lire_flux(ATOM, SRC)[0]
        self.assertEqual(a["lien"], "http://arxiv.org/abs/1"); self.assertEqual(a["date"].year, 2026)

class Filtre(unittest.TestCase):
    def test_garde(self): self.assertTrue(filtre.pertinent(art("Generative AI for architects", "BIM tool")))
    def test_bois(self): self.assertFalse(filtre.pertinent(art("Timber houses", "Wooden homes by architects")))
    def test_ia_seule(self): self.assertFalse(filtre.pertinent(art("New LLM", "chatbots")))
    def test_building_a_model(self): self.assertFalse(filtre.pertinent(art("Building a neural network", "machine learning tutorial")))

class Diagnostic(unittest.TestCase):
    def test_passe(self): self.assertIsNone(filtre.diagnostic(art("Generative AI for architects", "BIM tool")))
    def test_ia_sans_btp(self): self.assertIn("aucun terme architecture/BTP", filtre.diagnostic(art("New LLM", "chatbots")))
    def test_rien(self): self.assertIn("aucun terme IA ni", filtre.diagnostic(art("Recipe", "cooking")))

class Doublons(unittest.TestCase):
    def setUp(self): self.base = Base(os.path.join(tempfile.mkdtemp(), "v.json"))
    def test_url_connue(self):
        a = art("Same"); g, d = doublons.retirer_doublons([a], self.base, {doublons.cle_url(a["lien"] + "?utm_source=x")})
        self.assertEqual(len(g), 0)
    def test_plan_b_mots(self):
        a = art("Graphisoft launches AI plugin for Archicad that generates facade layouts", "assistant plugin facade layouts architects")
        b = art("Graphisoft releases AI facade layout plugin for Archicad", "assistant plugin facade layouts architects", lien="https://autre.org/b")
        c = art("Robots lay bricks", "autonomous excavator safety on construction site")
        with mock.patch("doublons.vecteurs", return_value=None):
            g, d = doublons.retirer_doublons([a, b, c], self.base, set())
        self.assertEqual((len(g), len(d)), (2, 1))
    def test_sens_avec_vecteurs_simules(self):
        faux = lambda textes: [[1.0, 0.0] if "archicad" in t.lower() else [0.0, 1.0] for t in textes]
        a, b, c = art("A1", "archicad"), art("B1", "archicad aussi"), art("C1", "revit")
        with mock.patch("doublons.vecteurs", side_effect=faux):
            g, d = doublons.retirer_doublons([a, b, c], self.base, set())
        self.assertEqual((len(g), len(d)), (2, 1)); self.assertEqual(len(self.base.vecteurs), 2)
    def test_base_sauvee_relue(self):
        self.base.ajouter("l", [1.0, 0.0]); self.base.sauver()
        self.assertEqual(Base(self.base.chemin).meilleure_similarite([1.0, 0.0]), 1.0)

class Embeddings(unittest.TestCase):
    def test_normalisation(self):
        with mock.patch("embeddings.appeler", return_value={"embeddings": [{"values": [3.0, 4.0]}]}):
            self.assertEqual(embeddings.vecteurs(["x"]), [[0.6, 0.8]])
    def test_sans_gemini(self):
        with mock.patch("embeddings.appeler", return_value=None): self.assertIsNone(embeddings.vecteurs(["x"]))

class Analyse(unittest.TestCase):
    def rep(self, d): return {"candidates": [{"content": {"parts": [{"text": json.dumps(d)}]}}]}
    def test_llm_borne(self):
        with mock.patch("llm.appeler", return_value=self.rep({"phase": "Chantier", "trl": 12, "impact": -3, "pertinence": "8", "resume_fr": "ok"})):
            r = llm.analyser(art("x"))
        self.assertEqual((r["trl"], r["impact"], r["pertinence"], r["methode"]), (9, 0, 8.0, "LLM"))
    def test_llm_hors_sujet(self):
        with mock.patch("llm.appeler", return_value=self.rep({"pertinent": False, "raison": "pas de BTP", "phase": "Conception", "trl": 5, "impact": 5, "pertinence": 2, "resume_fr": "x"})):
            r = llm.analyser(art("x"))
        self.assertFalse(r["pertinent"]); self.assertEqual(r["raison"], "pas de BTP")
    def test_llm_phase_invalide_repli(self):
        with mock.patch("llm.appeler", return_value=self.rep({"phase": "Autre"})):
            self.assertEqual(llm.analyser(art("x"))["methode"], "mots-clés")
    def test_sans_cle_repli(self):
        with mock.patch("llm.appeler", return_value=None): self.assertEqual(llm.analyser(art("x"))["methode"], "mots-clés")

class Score(unittest.TestCase):
    def test_bornes_et_fraicheur(self):
        an = {"trl": 9, "impact": 10, "pertinence": 10}
        s_recent, f1 = scoring.note_finale(art("a"), an)
        vieux = art("a"); vieux["date"] -= timedelta(days=25)
        s_vieux, f2 = scoring.note_finale(vieux, an)
        self.assertTrue(0 <= s_vieux < s_recent <= 10); self.assertGreater(f1, f2)

class Sortie(unittest.TestCase):
    def test_csv_aller_retour(self):
        p = os.path.join(tempfile.mkdtemp(), "v.csv")
        l = {k: "x" for k in sortie.CHAMPS}; l.update({k: 5.0 for k in sortie.NOMBRES}); l["lien"] = "https://www.ex.org/a/"
        sortie.ecrire_csv(p, [l]); sortie.ecrire_csv(p, [l])
        self.assertEqual(len(sortie.lire_csv(p)), 2); self.assertEqual(sortie.lire_csv(p)[0]["score"], 5.0)
        sortie.sauver_liens(p + ".txt", {"ex.org/a", "ex.org/b"}); self.assertEqual(sortie.lire_liens(p + ".txt"), {"ex.org/a", "ex.org/b"})

if __name__ == "__main__": unittest.main()
