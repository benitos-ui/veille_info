"""MODULE 10 - Tableau de bord : une page web (HTML) avec recherche, filtres (phase, source, score), tri et lien vers chaque article original."""
import json
from datetime import datetime

PAGE = r"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Veille IA × Architecture & BTP</title><style>
:root{--bg:#fbfaf7;--encre:#1a1a1a;--doux:#6b6b6b;--trait:#dcd9d0;--accent:#b4531a}
@media(prefers-color-scheme:dark){:root{--bg:#161616;--encre:#e9e7e2;--doux:#9a978f;--trait:#333;--accent:#f0a068}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--encre);font:16px/1.55 Georgia,"Times New Roman",serif}
main{max-width:820px;margin:0 auto;padding:36px 20px 60px}
h1{margin:0 0 4px;font-size:1.5rem;font-weight:700}.sous{margin:0 0 22px;color:var(--doux);font:.85rem system-ui,sans-serif}
.filtres{display:flex;flex-wrap:wrap;gap:8px;padding:12px 0;border-top:1px solid var(--trait);border-bottom:1px solid var(--trait);font:.85rem system-ui,sans-serif}
.filtres input,.filtres select{font:inherit;color:var(--encre);background:transparent;border:1px solid var(--trait);border-radius:3px;padding:5px 8px}
.filtres input[type=search]{flex:1 1 200px;min-width:0}.filtres label{display:flex;align-items:center;gap:6px;color:var(--doux)}
#nb{margin:10px 0 0;color:var(--doux);font:.8rem system-ui,sans-serif}
ol{list-style:none;margin:0;padding:0}
li{display:grid;grid-template-columns:3.2rem 1fr;gap:0 14px;padding:16px 0;border-bottom:1px solid var(--trait)}
.note{font:600 1.15rem/1.4 ui-monospace,Menlo,Consolas,monospace;text-align:right}.chaud .note{color:var(--accent)}
h2{margin:0;font-size:1.08rem;line-height:1.35;font-weight:600}h2 a{color:inherit;text-decoration:none}h2 a:hover{text-decoration:underline}
.meta{margin:2px 0 0;color:var(--doux);font:.78rem/1.5 system-ui,sans-serif}.resume{margin:6px 0 0;font-size:.95rem}.resume.vide{color:var(--doux);font-style:italic}
.orig{display:inline-block;margin-top:6px;font:.82rem system-ui,sans-serif;color:var(--accent)}
a:focus-visible,input:focus-visible,select:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.vide-liste{color:var(--doux);padding:30px 0;font-family:system-ui,sans-serif}
@media(max-width:520px){li{grid-template-columns:2.6rem 1fr;gap:0 10px}}
</style></head><body><main>
<h1>Veille IA × Architecture &amp; BTP</h1>
<p class="sous" id="sous"></p>__PDF__
<div class="filtres">
 <input type="search" id="q" placeholder="Rechercher" aria-label="Rechercher">
 <select id="phase" aria-label="Phase"></select>
 <select id="source" aria-label="Source"></select>
 <select id="tri" aria-label="Tri"><option value="score">Meilleur score</option><option value="pub">Plus récents</option><option value="titre">Titre A–Z</option></select>
 <label>Score min <input id="min" type="range" min="0" max="10" step="0.5" value="0"><b id="val">0</b></label>
</div>
<p id="nb"></p>
<ol id="liste"></ol>
</main>
<script>
const DONNEES = __DATA__;
const SEUIL = __SEUIL__;
const etat = {phase: "", source: "", tri: "score", min: 0, q: ""};
const $ = id => document.getElementById(id);
const h = t => String(t == null ? "" : t).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const sûr = u => /^https?:\/\//i.test(u) ? u : "#";
const norm = t => String(t).toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]+/g, " ").trim();
const fmt = x => Number(x).toFixed(1);
const coupe = r => /[.!?»")]$/.test(r.trim()) ? r.trim() : r.trim().replace(/\s+\S*$/, "") + "…";

const lignes = DONNEES.map(d => {
  const google = /Google/i.test(d.source) && / - /.test(d.titre), morceaux = d.titre.split(" - ");
  const titre = google ? morceaux.slice(0, -1).join(" - ") : d.titre, editeur = google ? morceaux.pop() : "";
  const r = norm(d.resume_fr), utile = r && !r.startsWith(norm(titre).slice(0, 40));
  return {...d, titre, editeur, score: +d.score, trl: +d.trl, resume: utile ? coupe(d.resume_fr) : "",
          texte: norm([titre, d.source, editeur, d.resume_fr, d.phase].join(" "))};
});

function controles() {
  const liste = (cle, vide) => `<option value="">${vide}</option>` + [...new Set(lignes.map(d => d[cle]))].sort().map(v => `<option>${h(v)}</option>`).join("");
  $("phase").innerHTML = liste("phase", "Toutes les phases");
  $("source").innerHTML = liste("source", "Toutes les sources");
  $("sous").textContent = lignes.length + " fiches · mis à jour le __DATE__ · alerte à partir de " + SEUIL + "/10";
}

function afficher() {
  $("val").textContent = etat.min;
  const mots = norm(etat.q).split(" ").filter(Boolean);
  const tri = {score: (a, b) => b.score - a.score, pub: (a, b) => (b.date_pub || "").localeCompare(a.date_pub || ""), titre: (a, b) => a.titre.localeCompare(b.titre)}[etat.tri];
  const choisis = lignes.filter(d => (!etat.phase || d.phase == etat.phase) && (!etat.source || d.source == etat.source)
      && d.score >= etat.min && mots.every(m => d.texte.includes(m))).sort(tri);
  $("nb").textContent = choisis.length + " sur " + lignes.length;
  $("liste").innerHTML = choisis.length ? choisis.map(ligne).join("") : '<p class="vide-liste">Aucune fiche ne correspond.</p>';
}

function ligne(d) {
  const llm = d.methode == "LLM";      // sans LLM, TRL / pertinence / impact sont des valeurs par défaut : on ne les montre pas
  const meta = [d.phase, d.editeur || d.source, d.date_pub, llm ? "TRL " + d.trl + "/9" : "", llm ? "pertinence " + fmt(d.pertinence) : "", llm ? "impact " + fmt(d.impact) : "",
                "fiabilité de la source " + fmt(d.fiabilite), llm ? "" : "score estimé (analyse par mots-clés)", d.score >= SEUIL ? "alerte" : ""].filter(Boolean).join(" · ");
  return `<li class="${d.score >= SEUIL ? "chaud" : ""}"><div class="note" title="Score /10">${fmt(d.score)}</div><div>
    <h2><a href="${h(sûr(d.lien))}" target="_blank" rel="noopener noreferrer">${h(d.titre)}</a></h2>
    <p class="meta">${h(meta)}</p>${d.resume ? `<p class="resume">${h(d.resume)}</p>` : ""}
    <a class="orig" href="${h(sûr(d.lien))}" target="_blank" rel="noopener noreferrer">Lire l'article original →</a></div></li>`;
}

$("q").oninput = e => { etat.q = e.target.value; afficher(); };
$("phase").onchange = e => { etat.phase = e.target.value; afficher(); };
$("source").onchange = e => { etat.source = e.target.value; afficher(); };
$("tri").onchange = e => { etat.tri = e.target.value; afficher(); };
$("min").oninput = e => { etat.min = +e.target.value; afficher(); };
controles(); afficher();
</script></body></html>"""


def liens_rapport(html, csv):
    """Ligne de liens vers le rapport du jour : page web, version téléchargeable, tableur."""
    if not html:
        return ""
    jour = f"{datetime.now():%Y-%m-%d}"
    liens = [f'<a class="orig" href="{html}">Lire le rapport du jour</a>',
             f'<a class="orig" href="{html}" download="rapport-veille-{jour}.html">Télécharger (HTML) ↓</a>']
    if csv:
        liens.append(f'<a class="orig" href="{csv}" download="rapport-veille-{jour}.csv">Télécharger (Excel/CSV) ↓</a>')
    return '<p class="sous">' + " · ".join(liens) + ' <span style="color:var(--doux)">articles retenus et rejetés, avec les raisons</span></p>'


def ecrire(chemin, lignes, seuil, html=None, csv=None):
    donnees = json.dumps(lignes, ensure_ascii=False).replace("</", "<\\/")
    page = PAGE.replace("__DATA__", donnees).replace("__SEUIL__", str(seuil)).replace("__PDF__", liens_rapport(html, csv)).replace("__DATE__", f"{datetime.now():%d/%m/%Y}")
    open(chemin, "w", encoding="utf-8").write(page)