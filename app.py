# app.py — Streamlit Cloud
# Diploma Santé - Suivi de l'avancement des fiches
# Thème sombre élégant, logo centré, tableau 3/4 + boursiers 1/4
# Persistance des coches via localStorage
# UVSQ (CM uniquement) + UPS (CM listés manuellement, fusion des matières)

import base64
import json
import os
import re
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

import streamlit as st
from streamlit_js_eval import streamlit_js_eval

# =========================
# CONFIG
# =========================
st.set_page_config(
    page_title="Diploma Santé - Suivi de l'avancement des fiches",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =========================
# THEME (dark soft)
# =========================
DS_BLUE = "#59a8d8"
DS_BG = "#0e1a30"
DS_BG_SOFT = "#12223e"
DS_CARD = "rgba(255,255,255,.05)"
TEXT = "#ecf2f8"
MUTED = "#aab7c8"
BORDER = "rgba(255,255,255,.12)"
SUCCESS = "#4ade80"

st.markdown(
    f"""
    <style>
    .stApp {{
      background:
        radial-gradient(1200px 600px at 10% -10%, rgba(89,168,216,.12), transparent 60%),
        linear-gradient(180deg, {DS_BG} 0%, {DS_BG_SOFT} 50%, #0c192e 100%);
      color: {TEXT};
    }}
    header[data-testid="stHeader"] {{ background: transparent; }}

    /* Header centré et collant */
    .ds-header {{
      position: sticky; top: 0; z-index: 50;
      display:flex; flex-direction:column; align-items:center; justify-content:center;
      gap:8px; padding:14px 12px;
      background: linear-gradient(180deg, rgba(14,26,48,.96), rgba(14,26,48,.86));
      border-bottom: 1px solid {BORDER};
      backdrop-filter: blur(8px);
      text-align:center;
    }}
    .ds-title {{ font-size: 1.9rem; font-weight: 800; letter-spacing:.2px; }}
    .title-grad {{
      background: linear-gradient(90deg, {DS_BLUE} 0%, #9ed2ef 65%);
      -webkit-background-clip: text; background-clip: text; color: transparent;
      line-height: 1.1;
    }}
    .ds-sub {{ margin-top: -4px; color: {MUTED}; }}

    .glass {{
      background: {DS_CARD}; border: 1px solid {BORDER};
      border-radius: 16px; padding: 16px;
    }}
    .cell {{
      border: 1px solid {BORDER};
      border-radius: 12px; padding: 10px; margin-bottom: 10px;
      background: rgba(255,255,255,.03);
    }}
    .subject {{ color:#f3f6fb; font-weight: 700; }}
    .muted {{ color: {MUTED}; }}
    .mini  {{ font-size: 0.82rem; color:{MUTED}; }}
    .small {{ font-size: 0.92rem; }}
    .table-head {{
      font-weight:700; color:#f2f6fb; letter-spacing:.25px;
      border-bottom:1px solid {BORDER}; padding:10px 8px;
      background: rgba(255,255,255,.03); border-radius: 10px;
    }}
    .rowline {{ border-bottom:1px dashed {BORDER}; padding:10px 8px; }}
    .fac-head {{
      display:flex; justify-content:center; align-items:center;
      background: rgba(255,255,255,.03);
      border:1px solid {BORDER}; border-radius:10px; padding:6px;
      font-weight:700; color:#eaf2fb;
    }}

    /* Checkboxes lisibles */
    div.stCheckbox > label > div[data-testid="stMarkdownContainer"] p {{
      color: {TEXT} !important; font-weight: 600;
    }}
    .ok-pill {{
      display:inline-block; padding:2px 8px; border-radius: 999px;
      background: rgba(74,222,128,.15); border: 1px solid rgba(74,222,128,.35); color:{SUCCESS};
      font-size: .78rem; margin-left: 6px;
    }}

    /* Boutons lisibles avant hover (texte noir) */
    .stButton>button {{
      color: #0b1220 !important;
      background: rgba(255,255,255,.92) !important;
      border: 1px solid {BORDER} !important;
      border-radius: 10px !important;
      font-weight: 600 !important;
    }}
    .stButton>button:hover {{
      background: #ffffff !important;
      color: #0b1220 !important;
      border-color: rgba(255,255,255,.35) !important;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================
# UTILS
# =========================
def week_ranges(start: date, end_included: date) -> List[str]:
    cur = start - timedelta(days=start.weekday())
    out = []
    while cur <= end_included:
        fin = cur + timedelta(days=6)
        out.append(f"{cur.strftime('%d/%m/%Y')} - {fin.strftime('%d/%m/%Y')}")
        cur += timedelta(days=7)
    return out

def monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())

def week_label_for(d: date) -> str:
    m = monday_of(d)
    s = m.strftime("%d/%m/%Y")
    e = (m + timedelta(days=6)).strftime("%d/%m/%Y")
    return f"{s} - {e}"

def make_key(*parts: str) -> str:
    slug = lambda s: re.sub(r'[^a-z0-9]+', '_', s.lower())
    return "ds::" + "::".join(slug(p) for p in parts if p)

def load_logo_base64(paths: List[str]) -> Optional[str]:
    for p in paths:
        if os.path.exists(p):
            with open(p, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
    return None

def parse_fr_date(dstr: str) -> date:
    """ '1/09/2025' or '01/10/2025' → date """
    return datetime.strptime(dstr, "%d/%m/%Y").date()

# =========================
# CLASSIFICATION MATIÈRES
# =========================
COMMON_HINTS = {
    "Biologie cellulaire – Histo-Embryo",
    "Chimie – Biochimie",
    "Physique – Biophysique",
}
UNKNOWN_SUBJECT = "CM inconnus"

def classify_subject(raw_title: str) -> str:
    t = raw_title.upper()
    if re.search(r'BIO\s*CELL|HISTO|EMBRYO', t): return "Biologie cellulaire – Histo-Embryo"
    if re.search(r'CHIMIE|BIOCHIMIE', t):         return "Chimie – Biochimie"
    if re.search(r'PHYSIQUE|BIOPHYSIQUE', t):     return "Physique – Biophysique"
    if re.search(r'STAT', t):                     return "Statistiques"
    return UNKNOWN_SUBJECT

def normalize_from_ups(label: str) -> str:
    """Mappe les libellés UPS vers les matières UVSQ quand c'est similaire."""
    t = label.strip().lower()
    if t.startswith("biologie"):
        return "Biologie cellulaire – Histo-Embryo"
    if t.startswith("biophysique"):
        return "Physique – Biophysique"
    if t.startswith("chimie") or t.startswith("biochimie"):
        return "Chimie – Biochimie"
    if t.startswith("stat"):
        return "Statistiques"
    return UNKNOWN_SUBJECT

# =========================
# UVSQ (CM only) + S12 ajoutée
# =========================
def add_item(dst: Dict[str, Dict[str, List[Dict]]], week_label: str,
             title: str, date_str: str, explicit_subject: Optional[str]=None, cid: Optional[str]=None):
    subj = explicit_subject or classify_subject(title)
    dst.setdefault(week_label, {}).setdefault(subj, []).append({
        "id": cid or f"{title}@{date_str}", "title": title, "date": date_str,
    })

UVSQ: Dict[str, Dict[str, List[Dict]]] = {}
# (bloc résumé des CM UVSQ déjà extraits + S12)
add_item(UVSQ, "01/09/2025 - 07/09/2025", "CM (intitulé non précisé)", "03/09/2025", cid="UVSQ-CM-1")
add_item(UVSQ, "01/09/2025 - 07/09/2025", "CM (intitulé non précisé)", "03/09/2025", cid="UVSQ-CM-2")

add_item(UVSQ, "08/09/2025 - 14/09/2025", "CM Biologie cellulaire – Histo Embryo", "08/09/2025",
         explicit_subject="Biologie cellulaire – Histo-Embryo", cid="UVSQ-BIO-1")
add_item(UVSQ, "08/09/2025 - 14/09/2025", "CM Chimie – Biochimie", "08/09/2025",
         explicit_subject="Chimie – Biochimie", cid="UVSQ-CHIM-1")
add_item(UVSQ, "08/09/2025 - 14/09/2025", "CM (intitulé non précisé)", "09/09/2025", cid="UVSQ-CM-3")

add_item(UVSQ, "15/09/2025 - 21/09/2025", "CM Biologie cellulaire – Histo Embryo", "17/09/2025",
         explicit_subject="Biologie cellulaire – Histo-Embryo", cid="UVSQ-BIO-2")
add_item(UVSQ, "15/09/2025 - 21/09/2025", "CM Chimie – Biochimie", "15/09/2025",
         explicit_subject="Chimie – Biochimie", cid="UVSQ-CHIM-2")
add_item(UVSQ, "15/09/2025 - 21/09/2025", "CM Chimie – Biochimie", "17/09/2025",
         explicit_subject="Chimie – Biochimie", cid="UVSQ-CHIM-3")
add_item(UVSQ, "15/09/2025 - 21/09/2025", "CM (intitulé non précisé)", "15/09/2025", cid="UVSQ-CM-4")
add_item(UVSQ, "15/09/2025 - 21/09/2025", "CM (intitulé non précisé)", "15/09/2025", cid="UVSQ-CM-5")

add_item(UVSQ, "22/09/2025 - 28/09/2025", "CM Biologie cellulaire – Histo Embryo", "22/09/2025",
         explicit_subject="Biologie cellulaire – Histo-Embryo", cid="UVSQ-BIO-3")
add_item(UVSQ, "22/09/2025 - 28/09/2025", "CM Chimie – Biochimie", "24/09/2025",
         explicit_subject="Chimie – Biochimie", cid="UVSQ-CHIM-4")
add_item(UVSQ, "22/09/2025 - 28/09/2025", "CM Chimie – Biochimie", "22/09/2025",
         explicit_subject="Chimie – Biochimie", cid="UVSQ-CHIM-5")

add_item(UVSQ, "29/09/2025 - 05/10/2025", "CM Physique – Biophysique", "30/09/2025",
         explicit_subject="Physique – Biophysique", cid="UVSQ-PHYS-1")
add_item(UVSQ, "29/09/2025 - 05/10/2025", "CM Biologie cellulaire – Histo Embryo", "01/10/2025",
         explicit_subject="Biologie cellulaire – Histo-Embryo", cid="UVSQ-BIO-4")

add_item(UVSQ, "06/10/2025 - 12/10/2025", "CM Biologie cellulaire – Histo Embryo", "06/10/2025",
         explicit_subject="Biologie cellulaire – Histo-Embryo", cid="UVSQ-BIO-5")
add_item(UVSQ, "06/10/2025 - 12/10/2025", "CM Chimie – Biochimie", "06/10/2025",
         explicit_subject="Chimie – Biochimie", cid="UVSQ-CHIM-6")
add_item(UVSQ, "06/10/2025 - 12/10/2025", "CM Biologie cellulaire – Histo Embryo", "08/10/2025",
         explicit_subject="Biologie cellulaire – Histo-Embryo", cid="UVSQ-BIO-6")
add_item(UVSQ, "06/10/2025 - 12/10/2025", "CM Chimie – Biochimie", "08/10/2025",
         explicit_subject="Chimie – Biochimie", cid="UVSQ-CHIM-7")

add_item(UVSQ, "13/10/2025 - 19/10/2025", "CM Biologie cellulaire – Histo Embryo", "13/10/2025",
         explicit_subject="Biologie cellulaire – Histo-Embryo", cid="UVSQ-BIO-7")
add_item(UVSQ, "13/10/2025 - 19/10/2025", "CM Chimie – Biochimie", "14/10/2025",
         explicit_subject="Chimie – Biochimie", cid="UVSQ-CHIM-8")
add_item(UVSQ, "13/10/2025 - 19/10/2025", "CM Biologie cellulaire – Histo Embryo", "15/10/2025",
         explicit_subject="Biologie cellulaire – Histo-Embryo", cid="UVSQ-BIO-8")

add_item(UVSQ, "27/10/2025 - 02/11/2025", "CM (intitulé non précisé)", "27/10/2025", cid="UVSQ-CM-6")
add_item(UVSQ, "27/10/2025 - 02/11/2025", "CM (intitulé non précisé)", "28/10/2025", cid="UVSQ-CM-7")
add_item(UVSQ, "27/10/2025 - 02/11/2025", "CM (intitulé non précisé)", "29/10/2025", cid="UVSQ-CM-8")

add_item(UVSQ, "03/11/2025 - 09/11/2025", "CM Chimie – Biochimie", "04/11/2025",
         explicit_subject="Chimie – Biochimie", cid="UVSQ-CHIM-9")
add_item(UVSQ, "03/11/2025 - 09/11/2025", "CM Chimie – Biochimie", "04/11/2025",
         explicit_subject="Chimie – Biochimie", cid="UVSQ-CHIM-10")
add_item(UVSQ, "03/11/2025 - 09/11/2025", "CM (intitulé non précisé)", "05/11/2025", cid="UVSQ-CM-9")
add_item(UVSQ, "03/11/2025 - 09/11/2025", "CM Physique – Biophysique", "07/11/2025",
         explicit_subject="Physique – Biophysique", cid="UVSQ-PHYS-2")

add_item(UVSQ, "10/11/2025 - 16/11/2025", "CM Biologie cellulaire – Histo Embryo", "10/11/2025",
         explicit_subject="Biologie cellulaire – Histo-Embryo", cid="UVSQ-BIO-9")
add_item(UVSQ, "10/11/2025 - 16/11/2025", "CM Physique – Biophysique", "10/11/2025",
         explicit_subject="Physique – Biophysique", cid="UVSQ-PHYS-3")

add_item(UVSQ, "17/11/2025 - 23/11/2025", "CM (intitulé non précisé)", "17/11/2025", cid="UVSQ-CM-10")

# =========================
# UPS — tous les CM listés (sept -> déc 2025)
# =========================
def build_ups_manual() -> Dict[str, Dict[str, List[Dict]]]:
    """
    Construit le mapping semaine -> matière -> [cours] pour UPS à partir
    de la liste fournie par l'utilisateur (septembre à décembre 2025).
    Biologie = Biologie cellulaire – Histo-Embryo (fusion UVSQ),
    Biophysique = Physique – Biophysique,
    Chimie = Chimie – Biochimie,
    Statistiques = Statistiques,
    autres -> CM inconnus.
    """
    rows: List[Tuple[str, str, str]] = []  # (dd/mm/yyyy, label, title)

    def add(d: str, matiere: str, title: Optional[str] = None):
        rows.append((d, matiere, title or f"CM {matiere}"))

    # -------- Septembre 2025 --------
    # Semaine 1-5 sept
    add("01/09/2025", "CM inconnus", "Amphi de rentrée + Méthodologie")
    add("02/09/2025", "Biologie")
    add("02/09/2025", "Statistiques")
    add("03/09/2025", "Biophysique")
    add("03/09/2025", "CM inconnus", "Prépa rédactionnel")
    add("04/09/2025", "Biophysique")
    add("04/09/2025", "Biologie")
    add("05/09/2025", "Chimie")

    # Semaine 8-12 sept
    add("08/09/2025", "Biologie")
    add("08/09/2025", "Biologie")
    add("09/09/2025", "Biologie")
    add("09/09/2025", "Biologie")
    add("11/09/2025", "Biologie")
    add("11/09/2025", "Biologie")
    add("12/09/2025", "Chimie")
    add("12/09/2025", "Biologie")

    # Semaine 15-19 sept
    add("15/09/2025", "Biologie")
    add("15/09/2025", "Biologie")
    add("16/09/2025", "Biophysique")
    add("16/09/2025", "Statistiques")
    add("17/09/2025", "Biophysique")
    add("17/09/2025", "Biologie")
    add("18/09/2025", "Biophysique")
    add("18/09/2025", "Biologie")
    add("19/09/2025", "Biologie")

    # Semaine 22-26 sept
    add("22/09/2025", "Biologie")
    add("22/09/2025", "Statistiques")
    add("23/09/2025", "Biophysique")
    add("23/09/2025", "Biophysique")
    add("24/09/2025", "Biophysique")
    add("24/09/2025", "Biophysique")
    add("25/09/2025", "Chimie")
    add("25/09/2025", "Biologie")
    add("26/09/2025", "Chimie")
    add("26/09/2025", "Biologie")

    # Semaine 29 sept - 3 oct
    add("29/09/2025", "Biophysique")
    add("29/09/2025", "Biophysique")
    add("30/09/2025", "Chimie")
    add("30/09/2025", "Biologie")
    add("01/10/2025", "Biophysique")
    add("01/10/2025", "Statistiques")
    add("02/10/2025", "Chimie")
    add("02/10/2025", "Biologie")
    add("03/10/2025", "Biophysique")
    add("03/10/2025", "Statistiques")

    # -------- Octobre 2025 --------
    # Semaine 6-10 oct
    add("06/10/2025", "Biophysique")
    add("06/10/2025", "Biologie")
    add("07/10/2025", "Statistiques")
    add("07/10/2025", "Biophysique")
    add("08/10/2025", "Biophysique")
    add("08/10/2025", "Biologie")
    add("09/10/2025", "Biophysique")
    add("09/10/2025", "Biologie")
    add("10/10/2025", "Chimie")
    add("10/10/2025", "Biologie")

    # Semaine 13-17 oct
    add("13/10/2025", "Chimie")
    add("13/10/2025", "Statistiques")
    add("14/10/2025", "Chimie")
    add("14/10/2025", "Biologie")
    add("15/10/2025", "Chimie")
    add("15/10/2025", "Biophysique")
    add("16/10/2025", "Chimie")
    add("16/10/2025", "Biologie")
    add("17/10/2025", "Biophysique")
    add("17/10/2025", "Biologie")

    # Semaine 20-24 oct
    add("20/10/2025", "Chimie")
    add("20/10/2025", "Biophysique")
    add("21/10/2025", "Biologie")
    add("21/10/2025", "Biophysique")
    add("22/10/2025", "Chimie")
    add("22/10/2025", "Biophysique")
    add("23/10/2025", "Chimie")
    add("23/10/2025", "Biologie")
    add("24/10/2025", "Chimie")
    add("24/10/2025", "Statistiques")

    # Semaine 27-31 oct
    add("27/10/2025", "Biophysique")
    add("27/10/2025", "Biophysique")
    add("28/10/2025", "Biologie")
    add("28/10/2025", "Statistiques")
    add("29/10/2025", "Chimie")
    add("29/10/2025", "Biophysique")
    add("30/10/2025", "Chimie")
    add("30/10/2025", "Biophysique")
    add("31/10/2025", "Chimie")
    add("31/10/2025", "Biologie")

    # -------- Novembre 2025 --------
    # Semaine 3-7 nov
    add("03/11/2025", "Biophysique")
    add("03/11/2025", "Biophysique")
    add("04/11/2025", "Biophysique")
    add("04/11/2025", "Biologie")
    add("05/11/2025", "Chimie")
    add("05/11/2025", "Biologie")
    add("06/11/2025", "Biologie")
    add("06/11/2025", "Chimie")
    add("07/11/2025", "Chimie")
    add("07/11/2025", "Statistiques")

    # Semaine 10-14 nov
    add("10/11/2025", "Chimie")
    add("10/11/2025", "Chimie")
    # 11/11 : férié
    add("12/11/2025", "Biologie")
    add("12/11/2025", "Biophysique")
    add("13/11/2025", "Chimie")
    add("13/11/2025", "Biologie")
    add("14/11/2025", "Chimie")
    add("14/11/2025", "Biologie")

    # Semaine 17-21 nov
    add("17/11/2025", "Chimie")
    add("17/11/2025", "Chimie")
    add("18/11/2025", "Biologie")
    add("18/11/2025", "Biologie")
    add("19/11/2025", "Biologie")
    add("19/11/2025", "Biophysique")
    add("20/11/2025", "Chimie")
    add("20/11/2025", "Biologie")
    add("21/11/2025", "Chimie")
    add("21/11/2025", "Biologie")

    # Semaine 24-28 nov
    add("24/11/2025", "Biologie")
    add("24/11/2025", "Biophysique")
    add("25/11/2025", "Chimie")
    add("25/11/2025", "Biophysique")
    add("26/11/2025", "Biologie")
    add("26/11/2025", "Biologie")
    add("27/11/2025", "Chimie")
    add("27/11/2025", "Statistiques")
    add("28/11/2025", "Chimie")
    add("28/11/2025", "CM inconnus", "Consignes concours")

    # -------- Décembre 2025 --------
    # Semaine 1-5 déc
    add("01/12/2025", "Biophysique")
    add("01/12/2025", "Biologie")
    add("02/12/2025", "Chimie")
    add("02/12/2025", "Biophysique")
    add("03/12/2025", "Chimie")
    add("03/12/2025", "Biophysique")
    add("04/12/2025", "Chimie")
    add("04/12/2025", "Biologie")
    add("05/12/2025", "Chimie")
    add("05/12/2025", "Statistiques")

    # Semaine 8-12 déc
    add("08/12/2025", "Biophysique")
    add("08/12/2025", "Statistiques")
    add("09/12/2025", "Chimie")
    add("09/12/2025", "Biologie")
    add("10/12/2025", "Biologie")
    add("10/12/2025", "Biophysique")
    add("11/12/2025", "Biophysique")
    add("11/12/2025", "Biologie")
    add("12/12/2025", "Biophysique")
    add("12/12/2025", "Biologie")

    # Semaine 15-19 déc
    add("15/12/2025", "Biophysique")
    add("15/12/2025", "Biophysique")
    add("16/12/2025", "Chimie")
    add("16/12/2025", "Biologie")
    add("17/12/2025", "Chimie")
    add("17/12/2025", "Biologie")
    add("18/12/2025", "Chimie")
    add("18/12/2025", "Biophysique")
    add("19/12/2025", "Chimie")
    add("19/12/2025", "Biophysique")

    # Construction de la structure
    out: Dict[str, Dict[str, List[Dict]]] = {}
    counters: Dict[Tuple[str, str, str], int] = {}
    for dstr, raw_subject, opt_title in rows:
        d = parse_fr_date(dstr)
        wlab = week_label_for(d)
        subject = normalize_from_ups(raw_subject)

        # numérotation CM par sujet et semaine pour des titres propres
        key = (wlab, subject, dstr)
        counters[key] = counters.get(key, 0) + 1
        idx = counters[key]

        title = opt_title if opt_title != f"CM {raw_subject}" else f"CM {raw_subject} {idx}"
        # si on a mappé vers matière UVSQ, on renomme le titre pour cohérence visuelle
        if subject != UNKNOWN_SUBJECT and raw_subject != subject:
            base = subject.split(" – ")[0] if " – " in subject else subject
            title = f"CM {base} {idx}"

        out.setdefault(wlab, {}).setdefault(subject, []).append({
            "id": f"UPS-{dstr}-{subject}-{idx}",
            "title": title,
            "date": d.strftime("%d/%m/%Y"),
        })
    return out

UPS = build_ups_manual()

# =========================
# DATA GLOBALE
# =========================
DATA = {
    "UPC": {},      # vide pour l’instant
    "UPS": UPS,
    "UVSQ": UVSQ,
}
FACULTIES = ["UPC", "UPS", "UVSQ"]

def all_subjects_sorted() -> List[str]:
    subjects = set()
    for fac in FACULTIES:
        for subj_map in DATA.get(fac, {}).values():
            subjects.update(subj_map.keys())
    return sorted(
        subjects,
        key=lambda s: (0 if s in COMMON_HINTS else (2 if s == UNKNOWN_SUBJECT else 1), s.lower())
    )

SUBJECTS = all_subjects_sorted()

# =========================
# PERSISTENCE localStorage
# =========================
def k(fac, subject, week, item_id): return make_key(fac, subject, week, item_id)

if "loaded_from_localstorage" not in st.session_state:
    raw = streamlit_js_eval(
        js_expressions="localStorage.getItem('ds_progress')",
        want_output=True,
        key="load-store"
    )
    try:
        if raw:
            saved = json.loads(raw)
            for kk, vv in saved.items():
                st.session_state[kk] = vv
    except Exception:
        pass
    st.session_state.loaded_from_localstorage = True

def flush_to_localstorage():
    payload = {kk: bool(vv) for kk, vv in st.session_state.items()
               if isinstance(kk, str) and kk.startswith("ds::")}
    streamlit_js_eval(
        js_expressions=f"localStorage.setItem('ds_progress', '{json.dumps(payload)}')",
        key="save-store"
    )

# =========================
# HEADER — logo centré (base64)
# =========================
logo_b64 = load_logo_base64(["streamlit/logo.png", "logo.png"])
logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="height:56px;"/>' if logo_b64 else ""
st.markdown(
    f"""
    <div class="ds-header">
      {logo_html}
      <div class="ds-title title-grad">Diploma Santé</div>
      <div class="ds-sub">Suivi de l’avancement des fiches</div>
    </div>
    """,
    unsafe_allow_html=True
)
st.write("")

# =========================
# LAYOUT 3/4 – 1/4
# =========================
left, right = st.columns([3, 1], gap="large")

# ------ AVANCEMENT ------
with left:
    st.markdown('<div class="glass">', unsafe_allow_html=True)

    # Semaine (élargi) — pas de "Tout décocher"
    all_weeks = week_ranges(date(2025, 9, 1), date(2026, 1, 4))
    if all_weeks and all_weeks[-1].endswith("04/01/2026"):
        all_weeks[-1] = "29/12/2025 - 04/01/2025"

    def first_week_with_data():
        for w in all_weeks:
            for fac in FACULTIES:
                if w in DATA.get(fac, {}) and any(DATA[fac][w].values()):
                    return w
        return all_weeks[0]

    # Colonnes: Semaine (large) | Filtre | Tout cocher
    ctop = st.columns([3.4, 2.0, 1.2])
    with ctop[0]:
        st.caption("Semaine")
        week = st.selectbox("Semaine", all_weeks,
                            index=all_weeks.index(first_week_with_data()),
                            label_visibility="collapsed")
    with ctop[1]:
        st.caption("Filtrer par matière")
        query = st.text_input("Rechercher…", value="", label_visibility="collapsed").strip().lower()
    with ctop[2]:
        st.caption("Actions")
        if st.button("Tout cocher", use_container_width=True):
            for fac in FACULTIES:
                for subj, items in DATA[fac].get(week, {}).items():
                    for it in items:
                        st.session_state[k(fac, subj, week, it["id"])] = True
            flush_to_localstorage()

    st.divider()

    # Entêtes tableau
    c0, c1, c2, c3 = st.columns([2.1, 1, 1, 1])
    c0.markdown('<div class="table-head">Matière</div>', unsafe_allow_html=True)
    for fac, c in zip(FACULTIES, [c1, c2, c3]):
        c.markdown(f'<div class="table-head fac-head">{fac}</div>', unsafe_allow_html=True)

    # Lignes
    for subj in [s for s in SUBJECTS if query in s.lower()]:
        r0, r1, r2, r3 = st.columns([2.1, 1, 1, 1], gap="large")
        with r0:
            st.markdown(f'<div class="rowline subject">{subj}</div>', unsafe_allow_html=True)

        def render_cell(col, fac):
            items = DATA.get(fac, {}).get(week, {}).get(subj, [])
            with col:
                st.markdown('<div class="rowline">', unsafe_allow_html=True)
                if not items:
                    st.markdown('<span class="muted small">—</span>', unsafe_allow_html=True)
                else:
                    for it in items:
                        cid = it.get("id") or it["title"]
                        ck = k(fac, subj, week, cid)
                        checked = st.session_state.get(ck, False)
                        st.markdown('<div class="cell">', unsafe_allow_html=True)
                        st.markdown(f"**{it['title']}**")
                        st.markdown(f'<span class="mini">{it["date"]}</span>', unsafe_allow_html=True)
                        new_val = st.checkbox("Fiche déjà faite", value=checked, key=ck)
                        if new_val != checked:
                            st.session_state[ck] = new_val
                        st.markdown(f"<span class='ok-pill'>{'OK' if new_val else 'À faire'}</span>", unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

        render_cell(r1, "UPC")
        render_cell(r2, "UPS")
        render_cell(r3, "UVSQ")

    st.markdown('</div>', unsafe_allow_html=True)

# ------ BOURSIERS ------
with right:
    st.markdown('<div class="glass">', unsafe_allow_html=True)
    st.markdown("### Boursiers")
    blocks = [
        ("UPS (e campus, Doranne)",
         "https://ecampus.paris-saclay.fr/",
         "doranne.ngoufi-moussa@universite-paris-saclay.fr",
         "D073125300604d"),
        ("UPEC L2 (crystolink, Keyssy)",
         "https://cristolink.medecine.u-pec.fr/login/index.php",
         "keyssy.bilingi@etu.u-pec.fr",
         "#Keyssy!Upec@2006"),
        ("UVSQ (e campus, Zineb)",
         "https://www.uvsq.fr/ufr-des-sciences-de-la-sante-simone-veil",
         "22506082",
         "1Croyable2025!"),
        ("UPEC L1 (Crystolink, Ahuna)",
         "https://cristolink.medecine.u-pec.fr/login/index.php",
         "ahuna.somon@etu.u-pec.fr",  # maj demandée
         "!ObantiAlif20092019!"),
        ("USPN (Moodle, Wiam)",
         "https://ent.univ-paris13.fr",
         "12501658",
         "100670595HK"),
        ("UPC (Moodle, Lina)",
         "https://moodle.u-paris.fr/",
         "lina.atea",
         "Monamalek93#"),
    ]
    for title, url, login, pwd in blocks:
        st.markdown(
            f"""
            <div class="cell" style="margin-bottom:10px;">
              <div style="font-weight:700">{title}</div>
              <div class="mini"><a href="{url}" target="_blank">{url}</a></div>
              <div class="mini">{login}</div>
              <div class="mini">{pwd}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)

# Sauvegarde localStorage (fin de script)
def _save():
    payload = {kk: bool(vv) for kk, vv in st.session_state.items()
               if isinstance(kk, str) and kk.startswith("ds::")}
    streamlit_js_eval(
        js_expressions=f"localStorage.setItem('ds_progress', '{json.dumps(payload)}')",
        key="save-store"
    )
_save()
