"""MODULE 13 - Rapport PDF : pour CHAQUE article lu, la décision (retenu / rejeté) et sa raison.

Usage : python rapport_pdf.py                         # data/analyse.json -> rapport/rapport.pdf
        python rapport_pdf.py --md data/rapport.md    # ancien rapport Markdown (moins complet : pas d'articles filtrés)
Nécessite xelatex (TeX Live / MiKTeX). Module autonome : ne modifie aucun autre fichier.
"""
import argparse, json, os, re, shutil, subprocess, sys
from collections import Counter

# (clé d'étape, titre de section, explication)
ETAPES = [("collecte", "Données incomplètes", "Titre ou lien absent dans le flux."),
          ("ancien", "Trop anciens", "Publiés avant la fenêtre de veille (paramètre jours_max)."),
          ("hors_sujet", "Hors sujet (filtre mots-clés)", "Le texte doit contenir à la fois un terme d'IA et un terme d'architecture/BTP. Le terme trouvé est indiqué."),
          ("doublon", "Doublons", "Lien déjà traité, ou information identique à un article déjà gardé."),
          ("llm", "Écartés par l'analyse (LLM)", "Passés par le filtre mais jugés non pertinents à l'analyse détaillée.")]


# ---------------------------------------------------------------- lecture
def lire_journal(chemin):
    d = json.load(open(chemin, encoding="utf-8"))
    return d["date"], d["articles"], d.get("seuil", 7.0)


def lire_markdown(chemin):
    """Secours : reconstruit un journal (partiel) depuis l'ancien rapport.md."""
    texte = open(chemin, encoding="utf-8").read()
    date = re.search(r"(\d{4}-\d{2}-\d{2})", texte).group(1)
    arts = []
    for bloc in re.split(r"^## ", texte, flags=re.M)[1:]:
        entete, _, corps = bloc.partition("\n")
        if entete.startswith("Articles écartés"):
            for l in corps.splitlines():
                if l.startswith("- "):
                    t, _, r = l[2:].rpartition(" — ")
                    etape = "llm" if "LLM" in r else "doublon"
                    arts.append({"titre": t, "source": "", "lien": "", "decision": "rejeté", "etape": etape, "raison": r})
        else:
            m = re.match(r"(?:🔔 )?\[(.+)\]\((\S+)\)$", entete.strip())
            meta = re.search(r"\*(.+?) · (.+?) · score \*\*([\d.]+)/10\*\* · TRL (\d+)/9 · analysé par : (.+?)\*", corps)
            if m and meta:
                arts.append({"titre": m.group(1), "lien": m.group(2), "decision": "retenu", "etape": "retenu", "raison": "",
                             "phase": meta.group(1), "source": meta.group(2), "score": float(meta.group(3)),
                             "trl": int(meta.group(4)), "methode": meta.group(5), "resume": corps[meta.end():].strip()})
    return date, arts, 7.0


# ---------------------------------------------------------------- LaTeX
def tex(s):
    s = str(s).replace("\\", r"\textbackslash{}")
    for a, b in {"&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
                 "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}.items():
        s = s.replace(a, b)
    return s.replace(" ", "~").replace(" ", "\\,")


def lien(a, n=120):
    t = a["titre"] if len(a["titre"]) <= n else a["titre"][:n - 1].rstrip() + "…"
    u = a["lien"].replace("%", r"\%").replace("#", r"\#").replace("&", r"\&").replace("_", r"\_")
    return f"\\href{{{u}}}{{{tex(t)}}}" if u else tex(t)


def date_fr(d):
    mois = "janvier février mars avril mai juin juillet août septembre octobre novembre décembre".split()
    y, m, j = d.split("-")
    return f"{int(j)} {mois[int(m) - 1]} {y}"


def document(date, arts, seuil):
    retenus = sorted([a for a in arts if a["decision"] == "retenu"], key=lambda a: -a.get("score", 0))
    rejetes = [a for a in arts if a["decision"] != "retenu"]
    par_etape = Counter(a["etape"] for a in rejetes)
    P = [r"""\documentclass[10pt,a4paper]{article}
\usepackage{fontspec}\setmainfont{Latin Modern Roman}\setsansfont{Latin Modern Sans}
\usepackage{polyglossia}\setmainlanguage{french}
\usepackage[a4paper,margin=2cm]{geometry}
\usepackage{xcolor,booktabs,longtable,array,titlesec,fancyhdr,microtype}
\usepackage[hidelinks]{hyperref}\usepackage{xurl}
\definecolor{navy}{HTML}{14284B}\definecolor{ok}{HTML}{2E7D4F}\definecolor{ko}{HTML}{B3402F}
\titleformat{\section}{\sffamily\large\bfseries\color{navy}}{}{0pt}{}[\color{navy!40}\titlerule]
\titlespacing*{\section}{0pt}{1.4em}{0.6em}
\setlength{\parindent}{0pt}\setlength{\parskip}{0.4em}
\renewcommand{\arraystretch}{1.2}
\pagestyle{fancy}\fancyhf{}\renewcommand{\headrulewidth}{0pt}
\fancyfoot[C]{\sffamily\small\thepage}
\newcolumntype{L}[1]{>{\raggedright\arraybackslash}p{#1}}
\begin{document}
"""]
    P.append(f"{{\\sffamily\\LARGE\\bfseries\\color{{navy}} Veille IA $\\times$ Architecture \\& BTP}}\\\\[2pt]\n"
             f"{{\\sffamily\\large Analyse article par article --- {tex(date_fr(date))}}}\n")
    # bilan
    P.append(r"\section{Bilan}" "\n" f"{len(arts)} articles examinés : \\textbf{{\\color{{ok}}{len(retenus)} retenus}}, "
             f"\\textbf{{\\color{{ko}}{len(rejetes)} rejetés}}.\n\n"
             r"\begin{tabular}{@{}l r@{}}\toprule \textbf{Étape} & \textbf{Articles}\\ \midrule" "\n"
             f"Articles lus & {len(arts)}\\\\\n"
             + "".join(f"\\quad rejetés : {tex(t.lower())} & $-${par_etape[k]}\\\\\n" for k, t, _ in ETAPES if par_etape[k])
             + f"\\midrule \\textbf{{Retenus}} & \\textbf{{{len(retenus)}}}\\\\\n\\bottomrule\\end{{tabular}}\n")
    # retenus
    P.append(r"\section{Articles retenus}" "\n")
    if retenus:
        mots = sum(a.get("methode") == "mots-clés" for a in retenus)
        if mots:
            P.append(f"\\small {mots} article(s) sur {len(retenus)} analysés par mots-clés (pas de clé Gemini) : phase, TRL et score sont alors des estimations.\\par\\normalsize\n")
        P.append(r"\begin{longtable}{@{}r L{8.6cm} l c c l@{}}" "\n"
                 r"\toprule \textbf{\#} & \textbf{Titre} & \textbf{Phase} & \textbf{TRL} & \textbf{Score} & \textbf{Analyse}\\ \midrule \endhead" "\n"
                 + "\n".join(f"{i} & {lien(a)} & {tex(a.get('phase', ''))} & {a.get('trl', '')}/9 & \\textbf{{{a.get('score', 0):.1f}}}{'~(alerte)' if a.get('score', 0) >= seuil else ''} & {tex(a.get('methode', ''))}\\\\"
                           for i, a in enumerate(retenus, 1))
                 + "\n\\bottomrule\\end{longtable}\n")
    else:
        P.append("Aucun article retenu.\n")
    # rejetés
    P.append(r"\section{Articles rejetés et pourquoi}" "\n")
    for cle, titre, expl in ETAPES:
        groupe = [a for a in rejetes if a["etape"] == cle]
        if not groupe:
            continue
        P.append(f"\\subsection*{{\\sffamily\\normalsize\\bfseries {tex(titre)} ({len(groupe)})}}\n{{\\small\\color{{black!65}}{tex(expl)}}}\\par\n"
                 r"{\small\begin{longtable}{@{}L{9cm} L{6.8cm}@{}}" "\n"
                 r"\toprule \textbf{Article (source)} & \textbf{Raison}\\ \midrule \endhead" "\n"
                 + "\n".join(f"{lien(a, 110)}{' (' + tex(a['source']) + ')' if a.get('source') else ''} & {tex(a['raison'])}\\\\" for a in groupe)
                 + "\n\\bottomrule\\end{longtable}}\n")
    P.append(r"\end{document}")
    return "\n".join(P)


# ---------------------------------------------------------------- compilation
def compiler(tex_chemin):
    dossier, nom = os.path.split(tex_chemin)
    r = subprocess.run(["latexmk", "-xelatex", "-interaction=nonstopmode", "-halt-on-error", nom] if shutil.which("latexmk")
                       else ["xelatex", "-interaction=nonstopmode", "-halt-on-error", nom], cwd=dossier, capture_output=True, text=True)
    if r.returncode:
        print(r.stdout[-3000:], file=sys.stderr)
        raise RuntimeError("Échec de la compilation LaTeX (voir ci-dessus).")


def generer(source="data/analyse.json", sortie="rapport"):
    """source : analyse.json (complet) ou rapport.md (partiel). Renvoie le chemin du PDF."""
    if not shutil.which("xelatex"):
        raise RuntimeError("xelatex introuvable : installer TeX Live (ou MiKTeX).")
    date, arts, seuil = lire_markdown(source) if source.endswith(".md") else lire_journal(source)
    os.makedirs(sortie, exist_ok=True)
    chemin = os.path.join(sortie, "rapport.tex")
    open(chemin, "w", encoding="utf-8").write(document(date, arts, seuil))
    compiler(chemin)
    for ext in ("aux", "fdb_latexmk", "fls", "xdv", "out", "toc", "log"):
        try:
            os.remove(os.path.join(sortie, f"rapport.{ext}"))
        except OSError:
            pass
    return os.path.join(sortie, "rapport.pdf")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--md")
    ap.add_argument("--journal", default="data/analyse.json")
    ap.add_argument("--sortie", default="rapport")
    a = ap.parse_args()
    try:
        print("PDF :", generer(a.md or a.journal, a.sortie))
    except RuntimeError as e:
        sys.exit(str(e))
