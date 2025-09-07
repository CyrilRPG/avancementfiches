import base64
import json
import os
import re
from uuid import uuid4
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

import streamlit as st
from streamlit_js_eval import streamlit_js_eval
# Airtable removed
# import requests
# import urllib.parse

# =========================
# PERSISTENCE via Cookie + localStorage (JS only)
# =========================

def _encode_for_cookie(s: str) -> str:
    return s.replace("%", "%25").replace(";", "%3B")


def _load_progress_from_browser() -> Dict[str, bool]:
    raw = streamlit_js_eval(
        js_expressions=(
            "(function(){\n"
            "  try{\n"
            "    const getCookie = (name)=>{\n"
            "      const m=document.cookie.match(new RegExp('(?:^|; )'+name+'=([^;]+)'));\n"
            "      return m? decodeURIComponent(m[1]) : null;\n"
            "    };\n"
            "    const c = getCookie('ds_progress');\n"
            "    const cts = parseInt(getCookie('ds_progress_ts')||'0',10)||0;\n"
            "    const ls = localStorage.getItem('ds_progress');\n"
            "    const lts = parseInt(localStorage.getItem('ds_progress_ts')||'0',10)||0;\n"
            "    const pick = (cts>=lts? c : ls) || c || ls || '';\n"
            "    return pick;\n"
            "  }catch(e){ return ''; }\n"
            "})()"
        ),
        want_output=True,
        key="load-progress-cookie-ls",
    )
    try:
        return json.loads(raw) if raw else {}
    except Exception:
        return {}


def _save_progress_to_browser(payload: Dict[str, bool]):
    data_json = json.dumps(payload)
    ts = str(int(datetime.utcnow().timestamp()))
    # localStorage
    streamlit_js_eval(
        js_expressions=(
            "(function(){\n"
            f"  localStorage.setItem('ds_progress', '{data_json.replace('\\','\\\\').replace("'","\\'" )}');\n"
            f"  localStorage.setItem('ds_progress_ts', '{ts}');\n"
            "})();"
        ),
        key=f"save-ls-{uuid4()}",
    )
    # cookie 1 an, SameSite=Lax
    streamlit_js_eval(
        js_expressions=(
            "(function(){\n"
            f"  var v=encodeURIComponent('{data_json.replace('\\','\\\\').replace("'","\\'")}');\n"
            f"  var ts='{ts}';\n"
            "  var attrs='; path=/; max-age=31536000; SameSite=Lax';\n"
            "  if (location.protocol==='https:'){ attrs += '; Secure'; }\n"
            "  document.cookie='ds_progress='+v+attrs;\n"
            "  document.cookie='ds_progress_ts='+ts+attrs;\n"
            "})();"
        ),
        key=f"save-cookie-{uuid4()}",
    )
# =========================
# FIN persistence helpers
# =========================

# (Supprimé) Airtable; on utilise cookie + localStorage

# Charger une fois
if "progress_loaded_browser" not in st.session_state:
    browser = _load_progress_from_browser()
    for kk, vv in browser.items():
        st.session_state[kk] = vv
    st.session_state.progress_loaded_browser = True


def save_progress():
    payload = {kk: bool(vv) for kk, vv in st.session_state.items()
               if isinstance(kk, str) and kk.startswith("ds::")}
    _save_progress_to_browser(payload)

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
    /* Couleurs par plateforme */
    .cell-upc  {{ background: rgba(255,255,255,.04); border-color: rgba(255,255,255,.18); }}
    .cell-ups  {{ background: rgba(89,168,216,.10); border-color: rgba(89,168,216,.38); }}
    .cell-uvsq {{ background: rgba(144,238,144,.12); border-color: rgba(144,238,144,.38); }}
    .cell-l1-upec {{ background: rgba(255,165,0,.10); border-color: rgba(255,165,0,.35); }}
    .cell-l2-upec {{ background: rgba(255,140,0,.10); border-color: rgba(255,140,0,.35); }}
    .cell-uspn {{ background: rgba(138,43,226,.10); border-color: rgba(138,43,226,.35); }}
    .cell-su {{ background: rgba(220,20,60,.10); border-color: rgba(220,20,60,.35); }}
    
    /* Blocs colorés pour les cours */
    .course-block {{
      background: rgba(255,255,255,.08);
      border: 1px solid rgba(255,255,255,.15);
      border-radius: 12px;
      padding: 12px;
      margin-bottom: 8px;
      box-shadow: 0 2px 8px rgba(0,0,0,.1);
    }}
    
    /* Réduire l'espace entre contrôles et tableau */
    .controls-tableau {{
      margin-bottom: 4px;
    }}
    
    /* Espacement réduit entre filtres et tableau */
    .stSelectbox, .stTextInput, .stDateInput {{
      margin-bottom: 4px;
    }}
    .subject {{ color:#f3f6fb; font-weight: 700; }}
    .subject.mini {{ font-size: 0.75rem; color: {MUTED}; font-weight: 500; }}
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
    div.stCheckbox > label {{
      color: #ffffff !important; font-weight: 700 !important;
    }}
    /* Forcer le texte des checkboxes en blanc */
    .stCheckbox label {{
      color: #ffffff !important; font-weight: 700 !important;
    }}
    .stCheckbox label span {{
      color: #ffffff !important; font-weight: 700 !important;
    }}
    /* Cibler spécifiquement le texte "Fiche déjà faite" */
    .stCheckbox > label > div:first-child {{
      color: #ffffff !important; font-weight: 700 !important;
    }}
    /* CSS plus agressif pour forcer le texte blanc */
    .stCheckbox * {{
      color: #ffffff !important;
    }}
    .stCheckbox label, .stCheckbox label * {{
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
    "Biologie cellulaire",
    "Histologie",
    "Embryologie",
    "Chimie",
    "Biochimie", 
    "Physique",
    "Biophysique",
    "Statistiques",
    "SHS",
    "Santé publique",
}
UNKNOWN_SUBJECT = "CM inconnus"

def classify_subject(raw_title: str) -> str:
    """Classification basée sur le nom exact du cours"""
    t = raw_title.upper()
    
    # Classification précise basée sur les noms réels des cours
    if re.search(r'^BIOCHIMIE\s+\d+', t): return "Biochimie"
    if re.search(r'^CHIMIE\s+\d+', t): return "Chimie"
    if re.search(r'^BIOLOGIE\s+\d+', t): return "Biologie cellulaire"
    if re.search(r'^BIOPHYSIQUE\s+\d+', t): return "Biophysique"
    if re.search(r'^STATISTIQUES\s+\d+', t): return "Statistiques"
    
    # Pour les cours UPC avec noms descriptifs
    if re.search(r'CELLULE|MEMBRANE|MITOCHONDRIE|NOYAU|CYTOSQUELETTE|CYCLE\s+CELLULAIRE|APOPTOSE|COMMUNICATION\s+INTERCELLULAIRE|TRAFIC\s+INTRACELLULAIRE|ENDO.*EXOCYTOSE|JONCTIONS|INTEGRINES|MATRICE\s+EXTRACELLULAIRE|DEVELOPPEMENT', t):
        return "Biologie cellulaire"
    
    if re.search(r'ETHIQUE|SANTE|ENVIRONNEMENT|MEDECINE|PRESCRIPTION|MEDICAMENT|RECHERCHE|COMMERCIALISATION|MALADIES\s+CHRONIQUES|GENETIQUE|IVG|SECRET\s+PROFESSIONNEL|RESPONSABILITE\s+PROFESSIONNELLE|FIN\s+DE\s+VIE|EPIDEMIES|SANTE\s+PUBLIQUE|INEQUALITES\s+SOCIALES|TRAVAIL', t):
        return "SHS"
    
    if re.search(r'^PHYSIQUE\s+\d+', t): return "Physique"
    if re.search(r'^HISTO.*EMBRYO\s+\d+', t): return "Biologie cellulaire"
    if re.search(r'^MATHS.*BIOSTATS\s+\d+', t): return "Statistiques"
    if re.search(r'^SANTE\s+PUBLIQUE\s+\d+', t): return "Santé publique"
    
    # Fallback pour les noms composés UVSQ
    if re.search(r'BIO.*CELL.*HISTO.*EMBRYO', t): return "Biologie cellulaire"
    if re.search(r'CHIMIE.*BIOCHIMIE', t): return "Chimie"
    if re.search(r'PHYSIQUE.*BIOPHYSIQUE', t): return "Physique"
    
    return UNKNOWN_SUBJECT

def normalize_from_ups(label: str) -> str:
    """Normalisation pour UPS - utilise le premier mot du label"""
    t = label.strip().lower()
    first_word = t.split()[0] if t.split() else ""
    
    if first_word == "biologie":
        return "Biologie cellulaire"
    elif first_word == "biophysique":
        return "Biophysique"
    elif first_word == "chimie":
        return "Chimie"
    elif first_word == "biochimie":
        return "Biochimie"
    elif first_word == "statistiques":
        return "Statistiques"
    elif first_word == "consignes":
        return UNKNOWN_SUBJECT
    
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

    add("03/09/2025", "Biophysique 3", "8h15", "10h15")

    add("04/09/2025", "Biophysique 4", "8h15", "10h15")
    add("04/09/2025", "Statistiques 1", "10h30", "12h30")

    add("05/09/2025", "Chimie 1", "8h15", "10h15")

    add("08/09/2025", "Biologie 2", "8h15", "10h15")
    add("08/09/2025", "Biologie 3", "10h30", "12h30")

    add("09/09/2025", "Biochimie 1", "8h15", "10h15")
    add("09/09/2025", "Biologie 4", "10h30", "12h30")

    add("10/09/2025", "Biologie 5", "8h15", "10h15")
    add("10/09/2025", "Biochimie 2", "10h30", "12h30")

    add("11/09/2025", "Biophysique 5", "8h15", "10h15")
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

    add("22/09/2025", "Biophysique 6", "10h30", "12h30")

    add("23/09/2025", "Biologie 9", "8h15", "10h15")
    add("23/09/2025", "Biochimie 4", "10h30", "12h30")

    add("24/09/2025", "Biophysique 9", "8h15", "10h15")
    add("24/09/2025", "Biologie 10", "10h30", "12h30")

    add("25/09/2025", "Chimie 4", "8h15", "10h15")
    add("25/09/2025", "Statistiques 4", "10h30", "12h30")

    add("29/09/2025", "Biophysique 10", "10h30", "12h30")

    add("30/09/2025", "Biochimie 5", "8h15", "10h15")
    add("30/09/2025", "Biologie 12", "10h30", "12h30")

    # -------- Octobre 2025 --------
    add("01/10/2025", "Statistiques 5", "8h15", "10h15")
    add("01/10/2025", "Chimie 5", "10h30", "12h30")

    add("02/10/2025", "Biophysique 11", "8h15", "10h15")

    add("03/10/2025", "Chimie 6", "8h15", "10h15")
    add("03/10/2025", "Biologie 13", "10h30", "12h30")

    add("06/10/2025", "Biophysique 12", "8h15", "10h15")
    add("06/10/2025", "Biologie 14", "10h30", "12h30")

    add("07/10/2025", "Biochimie 6", "8h15", "10h15")
    add("07/10/2025", "Biophysique 13", "10h30", "12h30")

    add("08/10/2025", "Biophysique 14", "10h30", "12h30")

    add("09/10/2025", "Statistiques 6", "8h15", "10h15")
    add("09/10/2025", "Biologie 11", "10h30", "12h30")

    add("10/10/2025", "Chimie 7", "8h15", "10h15")
    add("10/10/2025", "Biologie 15", "10h30", "12h30")

    add("13/10/2025", "Biologie 16", "8h15", "10h15")
    add("13/10/2025", "Biophysique 15", "10h30", "12h30")

    add("14/10/2025", "Biochimie 7", "8h15", "10h15")

    add("16/10/2025", "Statistiques 7", "8h15", "10h15")
    add("16/10/2025", "Biologie 17", "10h30", "12h30")

    add("17/10/2025", "Chimie 8", "8h15", "10h15")

    add("20/10/2025", "Biophysique 16", "8h15", "10h15")
    add("20/10/2025", "Biologie 18", "10h30", "12h30")

    add("21/10/2025", "Biochimie 8", "8h15", "10h15")
    add("21/10/2025", "Chimie 9", "10h30", "12h30")

    add("23/10/2025", "Biophysique 17", "8h15", "10h15")

    add("24/10/2025", "Biophysique 18", "8h15", "10h15")
    add("24/10/2025", "Biologie 19", "10h30", "12h30")

    add("27/10/2025", "Biophysique 19", "8h15", "10h15")
    add("27/10/2025", "Biologie 20", "10h30", "12h30")

    add("28/10/2025", "Biologie 21", "8h15", "10h15")
    add("28/10/2025", "Chimie 10", "10h30", "12h30")

    # -------- Novembre 2025 --------
    add("03/11/2025", "Biophysique 20", "8h15", "10h15")
    add("03/11/2025", "Biologie 22", "10h30", "12h30")

    add("04/11/2025", "Biochimie 9", "8h15", "10h15")
    add("04/11/2025", "Statistiques 8", "10h30", "12h30")

    add("05/11/2025", "Biochimie 10", "10h30", "12h30")

    add("06/11/2025", "Chimie 11", "8h15", "10h15")
    add("06/11/2025", "Biologie 23", "10h30", "12h30")

    add("07/11/2025", "Biophysique 21", "8h15", "10h15")
    add("07/11/2025", "Biochimie 11", "10h30", "12h30")

    add("10/11/2025", "Chimie 12", "10h30", "12h30")

    add("12/11/2025", "Biophysique 22", "10h30", "12h30")

    add("13/11/2025", "Biochimie 12", "8h15", "10h15")
    add("13/11/2025", "Biologie 24", "10h30", "12h30")

    add("14/11/2025", "Chimie 13", "8h15", "10h15")
    add("14/11/2025", "Biologie 25", "10h30", "12h30")

    add("17/11/2025", "Biologie 26", "8h15", "10h15")

    add("18/11/2025", "Biologie 27", "8h15", "10h15")
    add("18/11/2025", "Biochimie 13", "10h30", "12h30")

    add("19/11/2025", "Biochimie 14", "8h15", "10h15")

    add("20/11/2025", "Statistiques 9", "8h15", "10h15")
    add("20/11/2025", "Biophysique 23", "10h30", "12h30")

    add("21/11/2025", "Chimie 14", "8h15", "10h15")
    add("21/11/2025", "Biologie 28", "10h30", "12h30")

    add("24/11/2025", "Biochimie 15", "8h15", "10h15")
    add("24/11/2025", "Biologie 29", "10h30", "12h30")

    add("25/11/2025", "Biologie 30", "8h15", "10h15")
    add("25/11/2025", "Biophysique 24", "10h30", "12h30")

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
# UPC — Cours de biologie cellulaire (sept → nov 2025)
# =========================
def build_upc_manual() -> Dict[str, Dict[str, List[Dict]]]:
    # Chaque ligne : (date_dd/mm/YYYY, titre) — Biologie cellulaire
    rows_bio: List[Tuple[str, str]] = []
    def add_bio(d: str, title: str):
        rows_bio.append((d, title))

    # -------- Septembre 2025 (BIO) --------
    add_bio("04/09/2025", "Organisation de la cellule eucaryote")
    add_bio("08/09/2025", "Méthodes d'étude de la cellule 1")
    add_bio("15/09/2025", "Méthodes d'étude de la cellule 2")
    add_bio("17/09/2025", "Membrane plasmique")
    add_bio("22/09/2025", "Récepteurs / médiateurs")
    add_bio("29/09/2025", "Communication intercellulaire")

    # -------- Octobre 2025 (BIO) --------
    add_bio("01/10/2025", "Apoptose")
    add_bio("07/10/2025", "Mitochondrie et péroxysomes")
    add_bio("14/10/2025", "Système endo-membranaire - trafic intracellulaire")
    add_bio("21/10/2025", "Endo- et exocytose")
    add_bio("28/10/2025", "Noyau")

    # -------- Novembre 2025 (BIO) --------
    add_bio("04/11/2025", "Cytosquelette")
    add_bio("06/11/2025", "Jonctions - intégrines - matrice extracellulaire")
    add_bio("14/11/2025", "Bases cellulaires du développement")
    add_bio("20/11/2025", "Cycle cellulaire 1")
    add_bio("24/11/2025", "Cycle cellulaire 2")

    # -------- SHS (UPC) --------
    rows_shs: List[Tuple[str, str]] = []
    def add_shs(d: str, title: str):
        rows_shs.append((d, title))

    add_shs("04/09/2025", "Histoire et définition de l’éthique")
    add_shs("09/09/2025", "Evolution des systèmes de santé, acteurs et relations de soin")
    add_shs("15/09/2025", "Principes, courants et pratiques de l’éthique en santé")
    add_shs("17/09/2025", "Éthique de la recherche")
    add_shs("19/09/2025", "Santé et environnement")
    add_shs("25/09/2025", "Les définitions de la santé et de la maladie")
    add_shs("26/09/2025", "La construction scientifique de la médecine aux 19e et 20e siècles")
    add_shs("03/10/2025", "Prélèvements et don d’organes")
    add_shs("06/10/2025", "De la prescription aux usages des médicaments : enjeux éthiques et sociaux")
    add_shs("14/10/2025", "De la recherche à la commercialisation du médicament : enjeux éthiques et sociaux")
    add_shs("21/10/2025", "Enjeux éthiques et sociaux des maladies chroniques")
    add_shs("23/10/2025", "Histoire de la génétique")
    add_shs("30/10/2025", "Enjeux éthiques autour de l'interruption volontaire de grossesse")
    add_shs("03/11/2025", "Le secret professionnel")
    add_shs("10/11/2025", "La responsabilité professionnelle")
    add_shs("13/11/2025", "Ethique et fin de vie")
    add_shs("17/11/2025", "Epidémies et santé publique")
    add_shs("18/11/2025", "Sociologie des inégalités sociales de santé")
    add_shs("24/11/2025", "Santé et travail")

    # -------- Santé publique (UPC) --------
    # Remplacer par la nouvelle liste catégorisée (septembre 2025)
    rows_phys: List[Tuple[str, str]] = []
    rows_cb: List[Tuple[str, str]] = []  # Chimie + Biochimie
    rows_stats: List[Tuple[str, str]] = []
    rows_sp: List[Tuple[str, str]] = []   # Santé publique

    def add_phys(d: str, title: str): rows_phys.append((d, title))
    def add_cb(d: str, title: str): rows_cb.append((d, title))
    def add_stats(d: str, title: str): rows_stats.append((d, title))
    def add_sp(d: str, title: str): rows_sp.append((d, title))

    # Ajouts selon ta liste
    # Histo-Embryo (BIO)
    add_bio("04/09/2025", "Histo-Embryo 1")
    add_bio("11/09/2025", "Histo-Embryo 2")
    add_bio("17/09/2025", "Histo-Embryo 3")
    add_bio("19/09/2025", "Histo-Embryo 4")
    add_bio("24/09/2025", "Histo-Embryo 5")
    add_bio("26/09/2025", "Histo-Embryo 6")

    # Physique
    add_phys("08/09/2025", "Physique 1")
    add_phys("15/09/2025", "Physique 2")
    add_phys("22/09/2025", "Physique 3")
    add_phys("24/09/2025", "Physique 4")

    # Chimie / Biochimie (fusion sous "Chimie – Biochimie")
    add_cb("08/09/2025", "Chimie 1")
    add_cb("09/09/2025", "Biochimie 1")
    add_cb("11/09/2025", "Chimie 2")
    add_cb("16/09/2025", "Biochimie 2")
    add_cb("16/09/2025", "Chimie 3")
    add_cb("18/09/2025", "Biochimie 3")
    add_cb("19/09/2025", "Chimie 4")
    add_cb("22/09/2025", "Chimie 5")
    add_cb("23/09/2025", "Chimie 6")
    add_cb("25/09/2025", "Biochimie 4")
    add_cb("26/09/2025", "Chimie 7")

    # Statistiques
    add_stats("11/09/2025", "Maths - Biostats 1")
    add_stats("18/09/2025", "Maths - Biostats 2")

    # Santé publique
    add_sp("09/09/2025", "Santé publique 1")
    add_sp("16/09/2025", "Santé publique 2")
    add_sp("23/09/2025", "Santé publique 3")
    add_sp("25/09/2025", "Santé publique 4")
 
    # Tri chronologique
    rows_bio.sort(key=lambda x: parse_fr_date(x[0]))
    rows_shs.sort(key=lambda x: parse_fr_date(x[0]))
    rows_phys.sort(key=lambda x: parse_fr_date(x[0]))
    rows_cb.sort(key=lambda x: parse_fr_date(x[0]))
    rows_stats.sort(key=lambda x: parse_fr_date(x[0]))
    rows_sp.sort(key=lambda x: parse_fr_date(x[0]))

    out: Dict[str, Dict[str, List[Dict]]] = {}

    # BIO → sujet Biologie cellulaire
    for dstr, title in rows_bio:
        d = parse_fr_date(dstr)
        wlab = week_label_for(d)
        subject = "Biologie cellulaire"
        safe_subj = re.sub(r'[^a-z0-9]+', '_', subject.lower())
        safe_title = re.sub(r'[^a-z0-9]+', '_', title.lower())
        item_id = f"UPC-{safe_subj}-{safe_title}-{d.strftime('%Y%m%d')}"
        out.setdefault(wlab, {}).setdefault(subject, []).append({
            "id": item_id,
            "title": title,
            "date": d.strftime("%d/%m/%Y"),
        })

    # SHS → sujet SHS
    for dstr, title in rows_shs:
        d = parse_fr_date(dstr)
        wlab = week_label_for(d)
        subject = "SHS"
        safe_subj = re.sub(r'[^a-z0-9]+', '_', subject.lower())
        safe_title = re.sub(r'[^a-z0-9]+', '_', title.lower())
        item_id = f"UPC-{safe_subj}-{safe_title}-{d.strftime('%Y%m%d')}"
        out.setdefault(wlab, {}).setdefault(subject, []).append({
            "id": item_id,
            "title": title,
            "date": d.strftime("%d/%m/%Y"),
        })

    # Physique → sujet Physique
    for dstr, title in rows_phys:
        d = parse_fr_date(dstr)
        wlab = week_label_for(d)
        subject = "Physique"
        safe_subj = re.sub(r'[^a-z0-9]+', '_', subject.lower())
        safe_title = re.sub(r'[^a-z0-9]+', '_', title.lower())
        item_id = f"UPC-{safe_subj}-{safe_title}-{d.strftime('%Y%m%d')}"
        out.setdefault(wlab, {}).setdefault(subject, []).append({
            "id": item_id,
            "title": title,
            "date": d.strftime("%d/%m/%Y"),
        })

    # Chimie/Biochimie → sujet Chimie ou Biochimie selon le titre
    for dstr, title in rows_cb:
        d = parse_fr_date(dstr)
        wlab = week_label_for(d)
        subject = classify_subject(title)  # Utilise la nouvelle classification
        safe_subj = re.sub(r'[^a-z0-9]+', '_', subject.lower())
        safe_title = re.sub(r'[^a-z0-9]+', '_', title.lower())
        item_id = f"UPC-{safe_subj}-{safe_title}-{d.strftime('%Y%m%d')}"
        out.setdefault(wlab, {}).setdefault(subject, []).append({
            "id": item_id,
            "title": title,
            "date": d.strftime("%d/%m/%Y"),
        })

    # Statistiques → sujet Statistiques
    for dstr, title in rows_stats:
        d = parse_fr_date(dstr)
        wlab = week_label_for(d)
        subject = "Statistiques"
        safe_subj = re.sub(r'[^a-z0-9]+', '_', subject.lower())
        safe_title = re.sub(r'[^a-z0-9]+', '_', title.lower())
        item_id = f"UPC-{safe_subj}-{safe_title}-{d.strftime('%Y%m%d')}"
        out.setdefault(wlab, {}).setdefault(subject, []).append({
            "id": item_id,
            "title": title,
            "date": d.strftime("%d/%m/%Y"),
        })

    # Santé publique → sujet Santé publique (nouvelle liste seulement)
    for dstr, title in rows_sp:
        d = parse_fr_date(dstr)
        wlab = week_label_for(d)
        subject = "Santé publique"
        safe_subj = re.sub(r'[^a-z0-9]+', '_', subject.lower())
        safe_title = re.sub(r'[^a-z0-9]+', '_', title.lower())
        item_id = f"UPC-{safe_subj}-{safe_title}-{d.strftime('%Y%m%d')}"
        out.setdefault(wlab, {}).setdefault(subject, []).append({
            "id": item_id,
            "title": title,
            "date": d.strftime("%d/%m/%Y"),
        })

    return out

UPC = build_upc_manual()

# =========================
# UVSQ — construit à partir de la liste fournie (sept → nov 2025)
# =========================
def subject_short_name(subject: str) -> str:
    if subject == "Biologie cellulaire":
        return "Biocell - Histo - Embryo"
    if subject == "Chimie":
        return "Chimie - Biochimie"
    if subject == "Physique":
        return "Physique - Biophysique"
    return "CM inconnu"

def build_uvsq_from_list(ups_data: Dict[str, Dict[str, List[Dict]]]) -> Dict[str, Dict[str, List[Dict]]]:
    # Chaque ligne utilisateur compte pour 1 cours dans la catégorie correspondante.
    # kind in {"biohe", "chimiebioch", "phys", "unknown"}
    raw_plan: List[Tuple[str, List[Tuple[str, Optional[str]]]]] = []

    def add_day(d: str, entries: List[Tuple[str, Optional[str]]]):
        raw_plan.append((d, entries))

    # Septembre 2025
    add_day("02/09/2025", [("chimiebioch", None), ("biohe", None)])
    add_day("03/09/2025", [("biohe", None), ("chimiebioch", None)])
    add_day("08/09/2025", [("chimiebioch", None), ("biohe", None)])
    add_day("09/09/2025", [("biohe", None), ("chimiebioch", None), ("biohe", None)])
    add_day("10/09/2025", [("chimiebioch", None)])
    add_day("15/09/2025", [("chimiebioch", None), ("chimiebioch", None), ("biohe", None)])
    add_day("16/09/2025", [("chimiebioch", None), ("phys", None)])
    add_day("17/09/2025", [("biohe", None), ("chimiebioch", None)])
    add_day("22/09/2025", [("biohe", None), ("chimiebioch", None), ("biohe", None), ("chimiebioch", None), ("biohe", None)])
    add_day("23/09/2025", [("biohe", None), ("chimiebioch", None), ("chimiebioch", None)])
    add_day("24/09/2025", [("biohe", None), ("chimiebioch", None)])
    add_day("29/09/2025", [("phys", None), ("biohe", None), ("biohe", None)])
    add_day("30/09/2025", [("phys", None), ("phys", None), ("biohe", None), ("biohe", None)])
    # Octobre 2025
    add_day("01/10/2025", [("unknown", None)])
    add_day("06/10/2025", [("biohe", None), ("chimiebioch", None), ("biohe", None), ("biohe", None)])
    add_day("07/10/2025", [("chimiebioch", None), ("chimiebioch", None), ("chimiebioch", None)])
    add_day("08/10/2025", [("biohe", None), ("chimiebioch", None)])
    add_day("13/10/2025", [("biohe", None), ("biohe", None)])
    add_day("14/10/2025", [("chimiebioch", None), ("chimiebioch", None), ("biohe", None)])
    add_day("15/10/2025", [("biohe", None), ("biohe", None)])
    add_day("27/10/2025", [("unknown", "10 heures")])
    add_day("28/10/2025", [("unknown", "10 heures")])
    add_day("29/10/2025", [("unknown", "4 heures")])
    # Novembre 2025
    add_day("03/11/2025", [("phys", None)])
    add_day("04/11/2025", [("chimiebioch", None), ("chimiebioch", None)])
    add_day("05/11/2025", [("unknown", "4 heures")])
    add_day("10/11/2025", [("biohe", None), ("phys", None)])
    add_day("11/11/2025", [("unknown", "10 heures")])

    # Regroupement par catégories communes - pour UVSQ on crée plusieurs entrées
    def kind_to_subjects(k: str) -> List[str]:
        if k == "biohe":
            return ["Biologie cellulaire", "Histologie", "Embryologie"]
        if k == "chimiebioch":
            return ["Chimie", "Biochimie"]
        if k == "phys":
            return ["Physique", "Biophysique"]
        return [UNKNOWN_SUBJECT]

    # Pour UVSQ: numérotation démarre à 1 pour chaque matière (indépendante de UPS)
    out: Dict[str, Dict[str, List[Dict]]] = {}
    raw_plan.sort(key=lambda x: parse_fr_date(x[0]))
    seq: Dict[str, int] = {}

    for dstr, entries in raw_plan:
        d = parse_fr_date(dstr)
        wlab = week_label_for(d)
        for kind, detail in entries:
            subjects = kind_to_subjects(kind)
            
            for subject in subjects:
                seq.setdefault(subject, 0)
                seq[subject] += 1
                num = seq[subject]

                if subject == UNKNOWN_SUBJECT:
                    title = f"CM inconnu {num}" + (f" — durée: {detail}" if detail else "")
                else:
                    # Affichage UVSQ personnalisé selon la matière
                    if subject == "Biologie cellulaire":
                        title = f"Biocell - Histo - Embryo {num}"
                    elif subject == "Histologie":
                        title = f"Biocell - Histo - Embryo {num}"
                    elif subject == "Embryologie":
                        title = f"Biocell - Histo - Embryo {num}"
                    elif subject == "Chimie":
                        title = f"Chimie - Biochimie {num}"
                    elif subject == "Biochimie":
                        title = f"Chimie - Biochimie {num}"
                    elif subject == "Physique":
                        title = f"Physique - Biophysique {num}"
                    elif subject == "Biophysique":
                        title = f"Physique - Biophysique {num}"
                    else:
                        title = f"{subject} {num}"

                safe_subj = re.sub(r'[^a-z0-9]+', '_', subject.lower())
                safe_title = re.sub(r'[^a-z0-9]+', '_', title.lower())
                item_id = f"UVSQ-{safe_subj}-{safe_title}-{d.strftime('%Y%m%d')}"

                out.setdefault(wlab, {}).setdefault(subject, []).append({
                    "id": item_id,
                    "title": title,
                    "date": d.strftime("%d/%m/%Y"),
                })

    return out

UVSQ = build_uvsq_from_list(UPS)

# =========================
# DATA GLOBALE
# =========================
DATA = {
    "UPC": UPC,
    "UPS": UPS,
    "UVSQ": UVSQ,
    "L1 UPEC": {},
    "L2 UPEC": {},
    "USPN": {},
    "SU": {},
}
FACULTIES = ["UPC", "UPS", "UVSQ", "L1 UPEC", "L2 UPEC", "USPN", "SU"]

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
# HEADER — logo centré (base64)
# =========================
logo_b64 = load_logo_base64(["streamlit/logo.png", "logo.png"])
logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="height:56px;"/>' if logo_b64 else ""
st.markdown(
    f"""
    <div class="ds-header">
      {logo_html}
      <div class="ds-title title-grad">Diploma Santé</div>
      <div class="ds-sub">Suivi de l'avancement des fiches</div>
    </div>
    """,
    unsafe_allow_html=True
)

# =========================
# LAYOUT 4/5 – 1/5
# =========================
left, right = st.columns([4, 1], gap="large")

# ------ AVANCEMENT ------
with left:
    # Ajouter un espace entre header et filtres
    st.markdown('<div style="margin-top: 16px;"></div>', unsafe_allow_html=True)
    st.markdown('<div class="glass">', unsafe_allow_html=True)

    # Semaine et filtres
    all_weeks = week_ranges(date(2025, 9, 1), date(2026, 1, 4))
    if all_weeks and all_weeks[-1].endswith("04/01/2026"):
        all_weeks[-1] = "29/12/2025 - 04/01/2025"

    def first_week_with_data():
        for w in all_weeks:
            for fac in FACULTIES:
                if w in DATA.get(fac, {}) and any(DATA[fac][w].values()):
                    return w
        return all_weeks[0]

    # Filtres avec date précise
    ctop = st.columns([2.5, 1.5, 1.2, 1.0])
    
    with ctop[0]:
        st.caption("Semaine")
        week = st.selectbox("Semaine", all_weeks,
                            index=all_weeks.index(first_week_with_data()),
                            label_visibility="collapsed")
    
    with ctop[1]:
        st.caption("Date précise (optionnel)")
        specific_date = st.date_input("Date", value=None, label_visibility="collapsed")
    
    with ctop[2]:
        st.caption("Filtrer par matière")
        query = st.text_input("Rechercher…", value="", label_visibility="collapsed").strip().lower()
    
    with ctop[3]:
        st.caption("Actions")
        if st.button("Tout cocher", use_container_width=True):
            for fac in FACULTIES:
                for subj, items in DATA[fac].get(week, {}).items():
                    for it in items:
                        st.session_state[make_key(fac, subj, week, it["id"])] = True
            save_progress()
            st.success("Toutes les cases de la semaine sont cochées.")

    # Réduire l'espace entre filtres et tableau
    st.markdown('<div style="margin-bottom: 8px;"></div>', unsafe_allow_html=True)

    # Entêtes tableau - 7 colonnes pour les facultés avec largeurs optimisées
    c0, c1, c2, c3, c4, c5, c6 = st.columns([1.2, 1.2, 1.2, 1.1, 1.1, 1.1, 1.1])
    for fac, c in zip(FACULTIES, [c0, c1, c2, c3, c4, c5, c6]):
        c.markdown(f'<div class="table-head fac-head">{fac}</div>', unsafe_allow_html=True)

    # Lignes triées par fréquence décroissante (puis alpha), inconnus en bas
    for subj in [s for s in SUBJECTS if query in s.lower()]:
        r0, r1, r2, r3, r4, r5, r6 = st.columns([1.2, 1.2, 1.2, 1.1, 1.1, 1.1, 1.1], gap="large")
        
        def render_cell(col, fac):
            # Si une date précise est sélectionnée, filtrer par cette date
            if specific_date:
                target_date = specific_date.strftime("%d/%m/%Y")
                all_items = DATA.get(fac, {}).get(week, {}).get(subj, [])
                items = [it for it in all_items if it["date"] == target_date]
            else:
                items = DATA.get(fac, {}).get(week, {}).get(subj, [])
            
            with col:
                st.markdown('<div class="rowline">', unsafe_allow_html=True)
                if not items:
                    st.markdown('<span class="muted small">—</span>', unsafe_allow_html=True)
                else:
                    for it in items:
                        cid = it.get("id") or it["title"]
                        ck = make_key(fac, subj, week, cid)
                        checked = st.session_state.get(ck, False)
                        if fac == 'UPC':
                            cell_cls = 'cell-upc'
                        elif fac == 'UPS':
                            cell_cls = 'cell-ups'
                        elif fac == 'UVSQ':
                            cell_cls = 'cell-uvsq'
                        elif fac == 'L1 UPEC':
                            cell_cls = 'cell-l1-upec'
                        elif fac == 'L2 UPEC':
                            cell_cls = 'cell-l2-upec'
                        elif fac == 'USPN':
                            cell_cls = 'cell-uspn'
                        elif fac == 'SU':
                            cell_cls = 'cell-su'
                        else:
                            cell_cls = 'cell-upc'
                        st.markdown(f'<div class="cell {cell_cls} course-block">', unsafe_allow_html=True)
                        st.markdown(f"**{it['title']}**")
                        st.markdown(f'<span class="mini">{it["date"]}</span>', unsafe_allow_html=True)
                        st.markdown(f'<span class="mini subject">{subj}</span>', unsafe_allow_html=True)
                        new_val = st.checkbox("Fiche déjà faite", value=checked, key=ck)
                        if new_val != checked:
                            st.session_state[ck] = new_val
                            save_progress()
                        st.markdown(
                            f"<span class='ok-pill'>{'OK' if new_val else 'À faire'}</span>",
                            unsafe_allow_html=True,
                        )
                        st.markdown('</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

        render_cell(r0, "UPC")
        render_cell(r1, "UPS")
        render_cell(r2, "UVSQ")
        render_cell(r3, "L1 UPEC")
        render_cell(r4, "L2 UPEC")
        render_cell(r5, "USPN")
        render_cell(r6, "SU")

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
         "1Croy@able2025!"),
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
        ("SU (Moodle Sciences, Mayla)",
         "https://moodle-sciences-25.sorbonne-universite.fr/login/index.php",
         "21505225",
         "Mayla_MD-2008"),
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
# La sauvegarde se fait maintenant immédiatement lors des changements
