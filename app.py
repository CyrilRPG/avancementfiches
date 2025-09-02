# app.py — Streamlit Cloud
# Diploma Santé - Suivi de l'avancement des fiches
# Thème sombre élégant, logo centré, tableau 3/4 + boursiers 1/4
# Persistance des coches via localStorage
# UVSQ (CM seulement) + UPS (CM listés manuellement, fusion des matières)
# Tri des matières par fréquence décroissante (UVSQ + UPS), "CM inconnus" en bas
# Numérotation CM continue par matière (pas par semaine)

import base64
import json
import os
import re
from uuid import uuid4
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

    /* Checkboxes : label blanc + fort contraste */
    div.stCheckbox > label > div[data-testid="stMarkdownContainer"] p {{
      color: #ffffff !important; font-weight: 700 !important;
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
# UVSQ (CM only) + S12 ajoutée (résumé à partir de tes captures)
# =========================
def add_item(dst: Dict[str, Dict[str, List[Dict]]], week_label: str,
             title: str, date_str: str, explicit_subject: Optional[str]=None, cid: Optional[str]=None):
    subj = explicit_subject or classify_subject(title)
    dst.setdefault(week_label, {}).setdefault(subj, []).append({
        "id": cid or f"{title}@{date_str}", "title": title, "date": date_str,
    })

UVSQ: Dict[str, Dict[str, List[Dict]]] = {}
# (Extraits CM uniquement pour illustrer — tu pourras compléter si besoin)
add_item(UVSQ, "01/09/2025 - 07/09/2025", "CM (intitulé non précisé)", "03/09/2025", cid="UVSQ-CM-1")
add_item(UVSQ, "08/09/2025 - 14/09/2025", "CM Biologie cellulaire – Histo Embryo", "08/09/2025",
         explicit_subject="Biologie cellulaire – Histo-Embryo", cid="UVSQ-BIO-1")
add_item(UVSQ, "15/09/2025 - 21/09/2025", "CM Biologie cellulaire – Histo Embryo", "17/09/2025",
         explicit_subject="Biologie cellulaire – Histo-Embryo", cid="UVSQ-BIO-2")
add_item(UVSQ, "22/09/2025 - 28/09/2025", "CM Biologie cellulaire – Histo Embryo", "22/09/2025",
         explicit_subject="Biologie cellulaire – Histo-Embryo", cid="UVSQ-BIO-3")
add_item(UVSQ, "29/09/2025 - 05/10/2025", "CM Physique – Biophysique", "30/09/2025",
         explicit_subject="Physique – Biophysique", cid="UVSQ-PHYS-1")
add_item(UVSQ, "06/10/2025 - 12/10/2025", "CM Biologie cellulaire – Histo Embryo", "06/10/2025",
         explicit_subject="Biologie cellulaire – Histo-Embryo", cid="UVSQ-BIO-5")
add_item(UVSQ, "13/10/2025 - 19/10/2025", "CM Biologie cellulaire – Histo Embryo", "13/10/2025",
         explicit_subject="Biologie cellulaire – Histo-Embryo", cid="UVSQ-BIO-7")
add_item(UVSQ, "27/10/2025 - 02/11/2025", "CM (intitulé non précisé)", "27/10/2025", cid="UVSQ-CM-6")
add_item(UVSQ, "03/11/2025 - 09/11/2025", "CM Physique – Biophysique", "07/11/2025",
         explicit_subject="Physique – Biophysique", cid="UVSQ-PHYS-2")
add_item(UVSQ, "10/11/2025 - 16/11/2025", "CM Biologie cellulaire – Histo Embryo", "10/11/2025",
         explicit_subject="Biologie cellulaire – Histo-Embryo", cid="UVSQ-BIO-9")
add_item(UVSQ, "17/11/2025 - 23/11/2025", "CM (intitulé non précisé)", "17/11/2025", cid="UVSQ-CM-10")

# =========================
# UPS — REMPLACÉ par la NOUVELLE LISTE fournie (sept → nov 2025)
# =========================
def build_ups_manual() -> Dict[str, Dict[str, List[Dict]]]:
    # Chaque ligne : (date_dd/mm/YYYY, libellé tel que fourni, heure début, heure fin)
    rows: List[Tuple[str, str, Optional[str], Optional[str]]] = []
    def add(d: str, label: str, h1: Optional[str], h2: Optional[str]):
        rows.append((d, label, h1, h2))

    # -------- Septembre 2025 --------
    add("02/09/2025", "Biologie 1", "8h15", "10h15")
    add("02/09/2025", "Biophysique 2", "10h30", "12h30")

    add("03/09/2025", "Biophysique 2", "8h15", "10h15")

    add("04/09/2025", "Biophysique 3", "8h15", "10h15")
    add("04/09/2025", "Statistiques 1", "10h30", "12h30")

    add("05/09/2025", "Chimie 1", "8h15", "10h15")

    add("08/09/2025", "Biologie 2", "8h15", "10h15")
    add("08/09/2025", "Biologie 3", "10h30", "12h30")

    add("09/09/2025", "Biochimie 1", "8h15", "10h15")
    add("09/09/2025", "Biologie 4", "10h30", "12h30")

    add("10/09/2025", "Biologie 5", "8h15", "10h15")
    add("10/09/2025", "Biochimie 2", "10h30", "12h30")

    add("11/09/2025", "Biophysique 4", "8h15", "10h15")
    add("11/09/2025", "Statistiques 2", "10h30", "12h30")

    add("12/09/2025", "Chimie 2", "8h15", "10h15")
    add("12/09/2025", "Biologie 6", "10h30", "12h30")

    add("15/09/2025", "Biologie 7", "8h15", "10h15")

    add("16/09/2025", "Biologie 8", "8h15", "10h15")
    add("16/09/2025", "Biochimie 3", "10h30", "12h30")

    add("18/09/2025", "Biophysique 6", "8h15", "10h15")
    add("18/09/2025", "Statistiques 3", "10h30", "12h30")

    add("19/09/2025", "Chimie 3", "8h15", "10h15")
    add("19/09/2025", "Biophysique 7", "10h30", "12h30")

    add("22/09/2025", "Biophysique 5", "10h30", "12h30")

    add("23/09/2025", "Biologie 9", "8h15", "10h15")
    add("23/09/2025", "Biochimie 4", "10h30", "12h30")

    add("24/09/2025", "Biophysique 8", "8h15", "10h15")
    add("24/09/2025", "Biologie 10", "10h30", "12h30")

    add("25/09/2025", "Chimie 4", "8h15", "10h15")
    add("25/09/2025", "Statistiques 4", "10h30", "12h30")

    add("29/09/2025", "Biophysique 9", "10h30", "12h30")

    add("30/09/2025", "Biochimie 5", "8h15", "10h15")
    add("30/09/2025", "Biologie 12", "10h30", "12h30")

    # -------- Octobre 2025 --------
    add("01/10/2025", "Statistiques 5", "8h15", "10h15")
    add("01/10/2025", "Chimie 5", "10h30", "12h30")

    add("02/10/2025", "Biophysique 10", "8h15", "10h15")

    add("03/10/2025", "Chimie 6", "8h15", "10h15")
    add("03/10/2025", "Biologie 13", "10h30", "12h30")

    add("06/10/2025", "Biophysique 11", "8h15", "10h15")
    add("06/10/2025", "Biologie 14", "10h30", "12h30")

    add("07/10/2025", "Biochimie 6", "8h15", "10h15")
    add("07/10/2025", "Biophysique 12", "10h30", "12h30")

    add("08/10/2025", "Biophysique 13", "10h30", "12h30")

    add("09/10/2025", "Statistiques 6", "8h15", "10h15")
    add("09/10/2025", "Biologie 11", "10h30", "12h30")

    add("10/10/2025", "Chimie 7", "8h15", "10h15")
    add("10/10/2025", "Biologie 15", "10h30", "12h30")

    add("13/10/2025", "Biologie 16", "8h15", "10h15")
    add("13/10/2025", "Biophysique 14", "10h30", "12h30")

    add("14/10/2025", "Biochimie 7", "8h15", "10h15")

    add("16/10/2025", "Statistiques 7", "8h15", "10h15")
    add("16/10/2025", "Biologie 17", "10h30", "12h30")

    add("17/10/2025", "Chimie 8", "8h15", "10h15")

    add("20/10/2025", "Biophysique 15", "8h15", "10h15")
    add("20/10/2025", "Biologie 18", "10h30", "12h30")

    add("21/10/2025", "Biochimie 8", "8h15", "10h15")
    add("21/10/2025", "Chimie 9", "10h30", "12h30")

    add("23/10/2025", "Biophysique 16", "8h15", "10h15")

    add("24/10/2025", "Biophysique 17", "8h15", "10h15")
    add("24/10/2025", "Biologie 19", "10h30", "12h30")

    add("27/10/2025", "Biophysique 18", "8h15", "10h15")
    add("27/10/2025", "Biologie 20", "10h30", "12h30")

    add("28/10/2025", "Biologie 21", "8h15", "10h15")
    add("28/10/2025", "Chimie 10", "10h30", "12h30")

    # -------- Novembre 2025 --------
    add("03/11/2025", "Biophysique 19", "8h15", "10h15")
    add("03/11/2025", "Biologie 22", "10h30", "12h30")

    add("04/11/2025", "Biochimie 9", "8h15", "10h15")
    add("04/11/2025", "Statistiques 8", "10h30", "12h30")

    add("05/11/2025", "Biochimie 10", "10h30", "12h30")

    add("06/11/2025", "Chimie 11", "8h15", "10h15")
    add("06/11/2025", "Biologie 23", "10h30", "12h30")

    add("07/11/2025", "Biophysique 20", "8h15", "10h15")
    add("07/11/2025", "Biochimie 11", "10h30", "12h30")

    add("10/11/2025", "Chimie 12", "10h30", "12h30")

    add("12/11/2025", "Biophysique 21", "10h30", "12h30")

    add("13/11/2025", "Biochimie 12", "8h15", "10h15")
    add("13/11/2025", "Biologie 24", "10h30", "12h30")

    add("14/11/2025", "Chimie 13", "8h15", "10h15")
    add("14/11/2025", "Biologie 25", "10h30", "12h30")

    add("17/11/2025", "Biologie 26", "8h15", "10h15")

    add("18/11/2025", "Biologie 27", "8h15", "10h15")
    add("18/11/2025", "Biochimie 13", "10h30", "12h30")

    add("19/11/2025", "Biochimie 14", "8h15", "10h15")

    add("20/11/2025", "Statistiques 9", "8h15", "10h15")
    add("20/11/2025", "Biophysique 22", "10h30", "12h30")

    add("21/11/2025", "Chimie 14", "8h15", "10h15")
    add("21/11/2025", "Biologie 28", "10h30", "12h30")

    add("24/11/2025", "Biochimie 15", "8h15", "10h15")
    add("24/11/2025", "Biologie 29", "10h30", "12h30")

    add("25/11/2025", "Biologie 30", "8h15", "10h15")
    add("25/11/2025", "Biophysique 23", "10h30", "12h30")

    add("26/11/2025", "Biologie 31", "8h15", "10h15")
    add("26/11/2025", "Biochimie 16", "10h30", "12h30")

    add("27/11/2025", "Biologie 32", "8h15", "10h15")
    add("27/11/2025", "Statistiques 10", "10h30", "12h30")

    add("28/11/2025", "Chimie 15", "8h15", "10h15")
    add("28/11/2025", "Consignes concours", "10h30", "12h30")

    # Tri chronologique
    rows.sort(key=lambda x: parse_fr_date(x[0]))

    out: Dict[str, Dict[str, List[Dict]]] = {}
    for dstr, label, h1, h2 in rows:
        d = parse_fr_date(dstr)
        wlab = week_label_for(d)

        # Sujet normalisé (fusion avec UVSQ)
        subject = normalize_from_ups(label.split()[0])  # "Biologie", "Biochimie", "Chimie", "Biophysique", "Statistiques", etc.
        if label.lower().startswith("consignes concours"):
            subject = UNKNOWN_SUBJECT

        # Titre affiché avec horaires
        time_suffix = f" — {h1}–{h2}" if (h1 and h2) else ""
        title = f"{label}{time_suffix}"

        # ID stable
        safe_subj = re.sub(r'[^a-z0-9]+', '_', subject.lower())
        safe_label = re.sub(r'[^a-z0-9]+', '_', label.lower())
        item_id = f"UPS-{safe_subj}-{safe_label}-{d.strftime('%Y%m%d')}"

        out.setdefault(wlab, {}).setdefault(subject, []).append({
            "id": item_id,
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

# =========================
# TRI des matières par fréquence (desc), "CM inconnus" en bas
# =========================
def subjects_sorted_by_frequency() -> List[str]:
    counts: Dict[str, int] = {}
    for fac in FACULTIES:
        fac_weeks = DATA.get(fac, {})
        for week_map in fac_weeks.values():
            for subj, items in week_map.items():
                counts[subj] = counts.get(subj, 0) + len(items)

    # garantir présence si vide au départ
    for subj in list(COMMON_HINTS) + [UNKNOWN_SUBJECT]:
        counts.setdefault(subj, 0)

    # tri : inconnus tout en bas, sinon par fréquence décroissante puis alpha
    def sort_key(s: str):
        if s == UNKNOWN_SUBJECT: return (1, 0, s.lower())
        return (0, -counts.get(s, 0), s.lower())

    return sorted(counts.keys(), key=sort_key)

SUBJECTS = subjects_sorted_by_frequency()

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

def save_to_localstorage_once():
    payload = {kk: bool(vv) for kk, vv in st.session_state.items()
               if isinstance(kk, str) and kk.startswith("ds::")}
    streamlit_js_eval(
        js_expressions=f"localStorage.setItem('ds_progress', '{json.dumps(payload)}')",
        key=f"save-store-{uuid4()}",
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

    # Semaine (élargi) — sans "Tout décocher"
    all_weeks = week_ranges(date(2025, 9, 1), date(2026, 1, 4))
    if all_weeks and all_weeks[-1].endswith("04/01/2026"):
        all_weeks[-1] = "29/12/2025 - 04/01/2025"

    def first_week_with_data():
        for w in all_weeks:
            for fac in FACULTIES:
                if w in DATA.get(fac, {}) and any(DATA[fac][w].values()):
                    return w
        return all_weeks[0]

    ctop = st.columns([3.6, 2.0, 1.0])
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
            st.success("Toutes les cases de la semaine sont cochées.")

    st.divider()

    # Entêtes tableau
    c0, c1, c2, c3 = st.columns([2.1, 1, 1, 1])
    c0.markdown('<div class="table-head">Matière</div>', unsafe_allow_html=True)
    for fac, c in zip(FACULTIES, [c1, c2, c3]):
        c.markdown(f'<div class="table-head fac-head">{fac}</div>', unsafe_allow_html=True)

    # Lignes triées par fréquence décroissante (puis alpha), inconnus en bas
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
                        st.markdown(
                            f"<span class='ok-pill'>{'OK' if new_val else 'À faire'}</span>",
                            unsafe_allow_html=True,
                        )
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
         "ahuna.somon@etu.u-pec.fr",
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

# =========================
# Sauvegarde localStorage (une seule fois)
# =========================
save_to_localstorage_once()
