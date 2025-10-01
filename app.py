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
    "BDD",
    "BDR",
    "Anatomie",
    "UEDS",
    "UEDL",
    "De l'atome aux molécules",
    "Humanités en santé",
    "Environnement urbain et santé",
    "Fondements philosophiques de l'éthique médicale",
    "Droit et santé",
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

def build_uvsq_manual() -> Dict[str, Dict[str, List[Dict]]]:
    # Chaque ligne : (date_dd/mm/YYYY, titre du cours)
    rows: List[Tuple[str, str]] = []
    def add(d: str, title: str):
        rows.append((d, title))

    # -------- Septembre 2025 --------
    add("08/09/2025", "Chimie biochimie 1")
    add("08/09/2025", "Biocell histo embryo 1")

    add("09/09/2025", "Biostatistiques 1")
    add("09/09/2025", "Biocell histo embryo 2")
    add("09/09/2025", "Biocell histo embryo 3")

    add("10/09/2025", "Biostatistiques 2")
    add("10/09/2025", "Chimie biochimie 2")

    add("15/09/2025", "Biostatistiques 3")
    add("15/09/2025", "Chimie biochimie 3")
    add("15/09/2025", "Chimie biochimie 4")
    add("15/09/2025", "Bio cell histo embryo 4")

    add("16/09/2025", "Biostatistiques 4")
    add("16/09/2025", "Chimie biochimie 5")
    add("16/09/2025", "Chimie biochimie 6")
    add("16/09/2025", "Physique biophysique 1")

    add("17/09/2025", "Bio cell histo embryo 5")
    add("17/09/2025", "Chimie biochimie 7")

    add("22/09/2025", "Bio cell histo embryo 6")
    add("22/09/2025", "Bio cell histo embryo 7")
    add("22/09/2025", "Chimie biochimie 8")

    add("23/09/2025", "Biostatistiques 5")
    add("23/09/2025", "Bio cell histo embryo 8")
    add("23/09/2025", "Chimie biochimie 9")
    add("23/09/2025", "Chimie biochimie 10")

    add("24/09/2025", "Bio cell histo embryo 9")
    add("24/09/2025", "Chimie biochimie 11")

    add("29/09/2025", "Physique biophysique 2")
    add("29/09/2025", "Physique biophysique 3")
    add("29/09/2025", "Bio cell histo embryo 10")
    add("29/09/2025", "Bio cell histo embryo 11")

    # -------- Octobre 2025 --------
    add("06/10/2025", "Bio cell histo embryo 12")
    add("06/10/2025", "Chimie biochimie 12")
    add("06/10/2025", "Bio cell histo embryo 13")
    add("06/10/2025", "Bio cell histo embryo 14")

    add("07/10/2025", "Biostatistiques 6")
    add("07/10/2025", "Chimie biochimie 13")
    add("07/10/2025", "Chimie biochimie 14")
    add("07/10/2025", "Chimie biochimie 15")

    add("08/10/2025", "Bio cell histo embryo 15")
    add("08/10/2025", "Chimie biochimie 16")

    add("13/10/2025", "Bio cell histo embryo 16")
    add("13/10/2025", "Bio cell histo embryo 17")

    add("14/10/2025", "Biostatistiques 7")
    add("14/10/2025", "Chimie biochimie 17")
    add("14/10/2025", "Chimie biochimie 18")
    add("14/10/2025", "Bio cell histo embryo 18")

    add("15/10/2025", "Bio cell histo embryo 19")
    add("15/10/2025", "Bio cell histo embryo 20")

    add("27/10/2025", "Physique biophysique 4")

    add("28/10/2025", "Biostatistiques 8")
    add("28/10/2025", "Physique biophysique 5")

    # -------- Novembre 2025 --------
    add("03/11/2025", "Physique biophysique 6")

    add("04/11/2025", "Biostatistiques 9")
    add("04/11/2025", "Chimie biochimie 19")
    add("04/11/2025", "Chimie biochimie 20")

    add("10/11/2025", "Bio cell histo embryo 21")
    add("10/11/2025", "Physique biophysique 7")

    add("11/11/2025", "CM inconnu 8h 18h")

    # Tri chronologique
    rows.sort(key=lambda x: parse_fr_date(x[0]))

    out: Dict[str, Dict[str, List[Dict]]] = {}
    for dstr, title in rows:
        d = parse_fr_date(dstr)
        wlab = week_label_for(d)

        # Classification des matières
        subject = classify_subject(title)
        
        # ID stable
        safe_subj = re.sub(r'[^a-z0-9]+', '_', subject.lower())
        safe_title = re.sub(r'[^a-z0-9]+', '_', title.lower())
        item_id = f"UVSQ-{safe_subj}-{safe_title}-{d.strftime('%Y%m%d')}"

        out.setdefault(wlab, {}).setdefault(subject, []).append({
            "id": item_id,
            "title": title,
            "date": d.strftime("%d/%m/%Y"),
        })

    return out

UVSQ = build_uvsq_manual()

# =========================
# SU — Cours avec nouvelle nomenclature (sept → nov 2025)
# =========================
def build_su_manual() -> Dict[str, Dict[str, List[Dict]]]:
    # Chaque ligne : (date_dd/mm/YYYY, UE, numéro)
    rows: List[Tuple[str, str, int]] = []
    def add(d: str, ue: str, num: int):
        rows.append((d, ue, num))

    # -------- Septembre 2025 --------
    add("08/09/2025", "UE1", 1)
    add("08/09/2025", "UE2", 1)
    
    add("09/09/2025", "UE1", 2)
    add("09/09/2025", "UE2", 2)
    
    add("10/09/2025", "UE2", 3)
    add("10/09/2025", "UEDS", 1)  # C1
    add("10/09/2025", "UEDL", 1)
    
    add("11/09/2025", "UEDL", 2)
    add("11/09/2025", "UEDS", 2)  # P1
    add("11/09/2025", "UE5", 1)
    
    add("15/09/2025", "UE1", 3)
    add("15/09/2025", "UE2", 4)
    
    add("16/09/2025", "UE1", 4)
    add("16/09/2025", "UE2", 5)
    
    add("17/09/2025", "UE2", 6)
    add("17/09/2025", "UEDS", 3)  # C2
    add("17/09/2025", "UEDL", 3)
    
    add("18/09/2025", "UEDL", 4)
    add("18/09/2025", "UEDS", 4)  # P2
    add("18/09/2025", "UE5", 2)
    
    add("22/09/2025", "UE1", 5)
    add("22/09/2025", "UE2", 7)
    
    add("23/09/2025", "UE1", 6)
    add("23/09/2025", "UE2", 8)
    
    add("24/09/2025", "UE2", 9)
    add("24/09/2025", "UEDS", 5)  # C3
    add("24/09/2025", "UEDL", 5)
    
    add("25/09/2025", "UEDL", 6)
    add("25/09/2025", "UEDS", 6)  # P3
    
    add("29/09/2025", "UE1", 7)
    add("29/09/2025", "UE2", 10)
    
    add("30/09/2025", "UE1", 8)
    add("30/09/2025", "UE2", 11)
    
    # -------- Octobre 2025 --------
    add("01/10/2025", "UE2", 12)
    add("01/10/2025", "UEDS", 7)  # C4
    add("01/10/2025", "UEDL", 7)
    
    add("02/10/2025", "UEDS", 8)  # P4
    add("02/10/2025", "UEDL", 8)
    add("02/10/2025", "UE5", 3)
    
    add("06/10/2025", "UE1", 9)
    add("06/10/2025", "UE2", 13)
    
    add("07/10/2025", "UE1", 10)
    add("07/10/2025", "UE2", 14)
    
    add("08/10/2025", "UE2", 15)
    add("08/10/2025", "UEDS", 9)  # C4 (répété dans l'exemple)
    add("08/10/2025", "UEDL", 9)  # UEDL 7 → 9 pour éviter la duplication
    
    add("09/10/2025", "UEDS", 10)  # P5
    add("09/10/2025", "UEDL", 10)
    add("09/10/2025", "UE5", 4)
    
    add("13/10/2025", "UE1", 11)
    add("13/10/2025", "UE2", 16)
    
    add("14/10/2025", "UE1", 12)
    add("14/10/2025", "UE2", 17)
    
    add("15/10/2025", "UE2", 18)
    add("15/10/2025", "UEDS", 11)  # C6
    add("15/10/2025", "UEDL", 11)
    
    add("16/10/2025", "UEDL", 12)
    add("16/10/2025", "UE5", 5)
    
    add("20/10/2025", "UE1", 13)
    add("20/10/2025", "UE2", 19)
    
    add("21/10/2025", "UE1", 14)
    add("21/10/2025", "UE2", 20)
    
    add("22/10/2025", "UE2", 21)
    add("22/10/2025", "UEDS", 12)  # C7
    add("22/10/2025", "UEDL", 13)
    
    add("23/10/2025", "UEDS", 13)  # C8
    add("23/10/2025", "UEDL", 14)
    add("23/10/2025", "UE5", 6)
    
    add("27/10/2025", "UE1", 15)
    add("27/10/2025", "UE2", 22)
    
    add("28/10/2025", "UE1", 16)
    add("28/10/2025", "UE2", 23)
    
    add("29/10/2025", "UE2", 24)
    
    add("30/10/2025", "UEDS", 14)  # P6
    add("30/10/2025", "UE5", 7)
    
    # -------- Novembre 2025 --------
    add("04/11/2025", "UE2", 25)
    
    add("06/11/2025", "UE5", 8)
    add("06/11/2025", "UE5", 9)

    # Tri chronologique
    rows.sort(key=lambda x: parse_fr_date(x[0]))

    out: Dict[str, Dict[str, List[Dict]]] = {}
    for dstr, ue, num in rows:
        d = parse_fr_date(dstr)
        wlab = week_label_for(d)

        # Conversion UE vers matières
        if ue == "UE1":
            subject = "Chimie"
            title = f"Chimie, Biochimie {num}"
            all_subjects_str = "Chimie, Biochimie"
        elif ue == "UE2":
            subject = "Biologie cellulaire"
            title = f"Biologie cellulaire, Histologie, BDD, BDR {num}"
            all_subjects_str = "Biologie cellulaire, Histologie, BDD, BDR"
        elif ue == "UE5":
            subject = "Anatomie"
            title = f"Anatomie {num}"
            all_subjects_str = "Anatomie"
        elif ue == "UEDS":
            subject = "UEDS"
            title = f"UEDS {num}"
            all_subjects_str = "UEDS"
        elif ue == "UEDL":
            subject = "UEDL"
            title = f"UEDL {num}"
            all_subjects_str = "UEDL"
        else:
            subject = UNKNOWN_SUBJECT
            title = f"{ue} {num}"
            all_subjects_str = ue

        # ID stable
        safe_subj = re.sub(r'[^a-z0-9]+', '_', subject.lower())
        safe_title = re.sub(r'[^a-z0-9]+', '_', title.lower())
        item_id = f"SU-{safe_subj}-{safe_title}-{d.strftime('%Y%m%d')}"

        out.setdefault(wlab, {}).setdefault(subject, []).append({
            "id": item_id,
            "title": title,
            "date": d.strftime("%d/%m/%Y"),
            "all_subjects": all_subjects_str,
        })

    return out

SU = build_su_manual()

# =========================
# UPEC L1 — Cours semaine 08/09-14/09 (sans anglais médical)
# =========================
def build_upec_l1_manual() -> Dict[str, Dict[str, List[Dict]]]:
    # Chaque ligne : (date_dd/mm/YYYY, UE, titre du cours, enseignant)
    rows: List[Tuple[str, str, str, str]] = []
    def add(d: str, ue: str, cours: str, enseignant: str):
        rows.append((d, ue, cours, enseignant))

    # -------- SEMAINE 1 (08/09-12/09) --------
    # De l'atome aux molécules
    add("08/09/2025", "De l'atome aux molécules", "Notions fondamentales de la structure d'un atome, définitions", "Marie Claire Gazeau")
    add("08/09/2025", "De l'atome aux molécules", "Modèle quantique de l'atome et organisation électronique de l'atome", "Marie Claire Gazeau")
    add("08/09/2025", "De l'atome aux molécules", "présentation du tableau de classification des éléments", "Marie Claire Gazeau")
    add("08/09/2025", "De l'atome aux molécules", "la liaison chimique (ionique, covalente) modèle de Lewis", "Marie Claire Gazeau")
    add("08/09/2025", "De l'atome aux molécules", "Notion d'électronégativité, liaisons polarisées et molécules polaires", "Marie Claire Gazeau")
    add("08/09/2025", "De l'atome aux molécules", "Etat de la matière", "Marie Claire Gazeau")
    add("08/09/2025", "De l'atome aux molécules", "Particules élémentaires, notion de nucléide", "Emmanuel Itti")
    add("08/09/2025", "De l'atome aux molécules", "Forces d'interaction", "Emmanuel Itti")
    add("08/09/2025", "De l'atome aux molécules", "Modèle quantique, énergie de liaison", "Emmanuel Itti")
    add("08/09/2025", "De l'atome aux molécules", "Transitions électroniques", "Emmanuel Itti")
    add("08/09/2025", "De l'atome aux molécules", "Autres modèles de l'atome", "Emmanuel Itti")
    
    # Humanités en santé
    add("08/09/2025", "Humanités en santé", "Les origines de la médecine occidentale : Hippocrate et l'hippocratisme (Ve-IVe siècle av. JC)", "Thibault Miguet")
    
    # Environnement urbain et santé
    add("08/09/2025", "Environnement urbain et santé", "Introduction à la géographie de la santé", "Léa Prost")
    
    # Fondements philosophiques de l'éthique médicale
    add("08/09/2025", "Fondements philosophiques de l'éthique médicale", "Philosophie, éthique et médecine : introduction", "Elodie Boublil")
    
    # Histoire et épistémologie de la pensée médicale et sanitaire
    add("08/09/2025", "Histoire et épistémologie de la pensée médicale et sanitaire", "Les origines de la médecine occidentale : Hippocrate et l'hippocratisme (Ve-IVe siècle av. JC)", "Thibault Miguet")
    
    # Anglais médical
    add("08/09/2025", "Anglais médical", "Health careers", "Fanny Tison-Harinte")
    add("10/09/2025", "Anglais médical", "Présentation du programme question/réponses", "Fanny Tison-Harinte")

    # -------- SEMAINE 2 (15/09-19/09) --------
    # De l'atome aux molécules
    add("15/09/2025", "De l'atome aux molécules", "Fission et fusion", "Christophe PICHON")
    add("15/09/2025", "De l'atome aux molécules", "Généralité sur le 'chimie organique'", "Christophe PICHON")
    add("15/09/2025", "De l'atome aux molécules", "Fonctions chimiques et degrés de fonctions", "Christophe PICHON")
    add("15/09/2025", "De l'atome aux molécules", "Conformations de chaines", "Christophe PICHON")
    add("15/09/2025", "De l'atome aux molécules", "Conformation de cycle", "Christophe PICHON")
    add("15/09/2025", "De l'atome aux molécules", "Isomérie optique et asymétrie", "Christophe PICHON")
    add("15/09/2025", "De l'atome aux molécules", "Isomérie géométrique et configuration", "Christophe PICHON")
    add("15/09/2025", "De l'atome aux molécules", "Effets inductifs", "Christophe PICHON")
    add("15/09/2025", "De l'atome aux molécules", "Effets mésomères", "Christophe PICHON")
    add("15/09/2025", "De l'atome aux molécules", "Influence des effets électroniques sur la géométrie et la réactivités de biomolécules", "Christophe PICHON")
    add("15/09/2025", "De l'atome aux molécules", "Modèle quantique, énergie de liaison", "Emmanuel Itti")
    add("15/09/2025", "De l'atome aux molécules", "Stabilité du noyau, transitions nucléaires", "Emmanuel Itti")
    
    # Environnement urbain et santé
    add("15/09/2025", "Environnement urbain et santé", "Les inégalités spatiales de santé, reflet des inégalités en lien avec les conditions de vie", "Léa Prost")
    
    # Fondements philosophiques de l'éthique médicale
    add("15/09/2025", "Fondements philosophiques de l'éthique médicale", "L'éthique des vertus", "Elodie Boublil")
    
    # Humanités en santé
    add("15/09/2025", "Humanités en santé", "De l'époque hellénistique à Galien : la médecine à Alexandrie et à Rome (IIIe s. av. JC - IIe s. ap. JC)", "Thibault Miguet")
    
    # Droit et santé
    add("15/09/2025", "Droit et santé", "La norme juridique et la hiérarchie des normes", "Alison Linon")

    # -------- SEMAINE 3 (22/09-26/09) --------
    # De la cellule aux tissus
    add("22/09/2025", "De la cellule aux tissus", "La membrane plasmique (composition, structure et diversité) 1", "José Cohen")
    add("22/09/2025", "De la cellule aux tissus", "La membrane plasmique (composition, structure et diversité) 2", "José Cohen")
    add("22/09/2025", "De la cellule aux tissus", "La mitochondrie", "Anaïs Pujals")
    add("22/09/2025", "De la cellule aux tissus", "Le noyau cellulaire : centre de contrôle de la vie de la cellule 1", "Anaïs Pujals")
    add("22/09/2025", "De la cellule aux tissus", "Le peroxysome", "Asma Ferchiou")
    add("22/09/2025", "De la cellule aux tissus", "Le système endo-membranaire. RE-Golgi", "Asma Ferchiou")
    add("22/09/2025", "De la cellule aux tissus", "Le système endo-membranaire. lysosomes, endosomes", "Asma Ferchiou")
    
    # Fondements philosophiques de l'éthique médicale
    add("22/09/2025", "Fondements philosophiques de l'éthique médicale", "L'approche déontologique en éthique médicale et en bioéthique", "Elodie Boublil")
    
    # Environnement urbain et santé
    add("22/09/2025", "Environnement urbain et santé", "Interactions santé-environnement", "Léa Prost")
    
    # Histoire et épistémologie de la pensée médicale et sanitaire
    add("22/09/2025", "Histoire et épistémologie de la pensée médicale et sanitaire", "La médecine à l'époque tardo-antique et médiévale (jusqu'au XIe s.) : histoire d'un transfert d'Orient vers Occident", "Thibault Miguet")
    
    # Anglais médical
    add("22/09/2025", "Anglais médical", "Anatomy - Basics", "Fanny Tison-Harinte")
    
    # Droit et santé
    add("23/09/2025", "Droit et santé", "La distinction des droits public et privé, positif et naturel, et la séparation des pouvoirs", "Alison Linon")
    
    # SHS (présentiel)
    add("23/09/2025", "SHS", "Méthodologie (inscriptions sur Cristolink, groupes 1, 2, 3)", "Elodie Boublil Thibault Miguet David Simard")
    
    # De l'atome aux molécules (ED)
    add("23/09/2025", "De l'atome aux molécules", "ED n°1 partie Atomistique", "Christophe Pichon")

    # -------- SEMAINE 4 (29/09-03/10) --------
    # De la cellule aux tissus
    add("29/09/2025", "De la cellule aux tissus", "Le cytosquelette : les microtubules", "Anaïs Pujals")
    add("29/09/2025", "De la cellule aux tissus", "Le cytosquelette : les filaments intermédiaires", "Anaïs Pujals")
    add("29/09/2025", "De la cellule aux tissus", "La cellule et son environnement : récepteurs-médiateurs", "Anaïs Pujals")
    add("29/09/2025", "De la cellule aux tissus", "Dogme de la biologie moléculaire, les acides nucléiques", "José Cohen")
    add("29/09/2025", "De la cellule aux tissus", "Réplication de l'ADN / Transcription", "Sylvain Loric")
    add("29/09/2025", "De la cellule aux tissus", "Code génétique et traduction", "Sylvain Loric")
    add("29/09/2025", "De la cellule aux tissus", "Transmission allélique mendeléienne /allèles et polymorphismes", "Sylvain Loric")
    add("29/09/2025", "De la cellule aux tissus", "Propriétés de la molécule d'ADN/ Organisation génomique de l'ADN", "Sylvain Loric")
    add("29/09/2025", "De la cellule aux tissus", "Le cytosquelette : Microfilaments d'actine", "Anaïs Pujals")
    
    # Histoire et épistémologie de la pensée médicale et sanitaire
    add("29/09/2025", "Histoire et épistémologie de la pensée médicale et sanitaire", "La médecine médiévale du XIIe s. jusqu'à la fin du Moyen Âge : l'âge d'or des universités", "Thibault Miguet")
    
    # Environnement urbain et santé
    add("29/09/2025", "Environnement urbain et santé", "Villes et santé", "Léa Prost")
    
    # Fondements philosophiques de l'éthique médicale
    add("29/09/2025", "Fondements philosophiques de l'éthique médicale", "L'approche conséquentialiste en éthique médicale et en bioéthique", "Elodie Boublil")
    
    # Droit et santé
    add("30/09/2025", "Droit et santé", "La hiérarchie des juridictions et le procès", "Alison Linon")
    
    # SHS (présentiel)
    add("30/09/2025", "SHS", "Méthodologie (inscriptions sur Cristolink, groupes 4, 5, 6)", "Elodie Boublil Thibault Miguet David Simard")
    
    # De l'atome aux molécules (ED)
    add("30/09/2025", "De l'atome aux molécules", "ED n°2 partie Chimie organique", "Christophe Pichon")

    # -------- SEMAINE 5 (06/10-10/10) --------
    # De la cellule aux tissus
    add("06/10/2025", "De la cellule aux tissus", "Structure et propriétés des AA", "Sylvain Loric")
    add("06/10/2025", "De la cellule aux tissus", "Structure primaire et liaison peptidique - Structures secondaires, tertiaire et quaternaire des protéines", "Sylvain Loric")
    add("06/10/2025", "De la cellule aux tissus", "Introduction au métabolisme énergétique (ATP...)", "Pascale Fanen")
    add("06/10/2025", "De la cellule aux tissus", "Schéma général des voies métaboliques : oses, AA, acides gras", "Pascale Fanen")
    add("06/10/2025", "De la cellule aux tissus", "Glucides : Oses simples ou monosaccharides - Oses complexes ou polysaccharide - Un exemple de voie métabolique des oses : la glycolyse", "Pascale Fanen")
    add("06/10/2025", "De la cellule aux tissus", "Le catabolisme des acides gras et cétogenèse", "Pascale Fanen")
    add("06/10/2025", "De la cellule aux tissus", "Division et prolifération cellulaire", "Anaïs Pujals")
    add("06/10/2025", "De la cellule aux tissus", "Introduction à la Biologie systémique de la cellule II", "Abdel Aïssat")
    add("06/10/2025", "De la cellule aux tissus", "Apoptose", "Anaïs Pujals")
    
    # Fondements philosophiques de l'éthique médicale
    add("06/10/2025", "Fondements philosophiques de l'éthique médicale", "Principisme, éthique de la discussion et théories de la justice en éthique médicale et en bioéthique", "Elodie Boublil")
    
    # Anglais médical
    add("06/10/2025", "Anglais médical", "Public health - Obesity", "Fanny Tison-Harinte")
    
    # Histoire et épistémologie de la pensée médicale et sanitaire (présentiel)
    add("07/10/2025", "Histoire et épistémologie de la pensée médicale et sanitaire", "Cours 1", "Roberto Poma")
    
    # Droit et santé
    add("07/10/2025", "Droit et santé", "Notion et fondement de la responsabilité juridique", "Alison Linon")

    # -------- SEMAINE 6 (13/10-17/10) --------
    # De la cellule aux tissus
    add("13/10/2025", "De la cellule aux tissus", "Néoglucogenèse et voie des pentoses", "Pascale Fanen")
    add("13/10/2025", "De la cellule aux tissus", "Cycle de Krebs et phosphorylation oxydative", "Pascale Fanen")
    add("13/10/2025", "De la cellule aux tissus", "Organisation des cellules en tissus et organes", "Piotr Topilko")
    add("13/10/2025", "De la cellule aux tissus", "Tissus conjonctifs", "François Jérôme Authier")
    add("13/10/2025", "De la cellule aux tissus", "Microenvironnement cellulaire", "Jeanne Tran Van Nhieu")
    add("13/10/2025", "De la cellule aux tissus", "Os et cartilages", "Piotr Topilko")
    add("13/10/2025", "De la cellule aux tissus", "Tissus nerveux 1 (SNP)", "François Jérôme Authier")
    add("13/10/2025", "De la cellule aux tissus", "Tissus nerveux 2 (SNC)", "François Jérôme Authier")
    add("13/10/2025", "De la cellule aux tissus", "Introduction à l'histologie et principes de l'histologie moléculaire", "François Jérôme Authier")
    add("13/10/2025", "De la cellule aux tissus", "La cellule épithéliale", "Jeanne Tran Van Nhieu")
    add("13/10/2025", "De la cellule aux tissus", "Les épithéliums", "Piotr Topilko")
    add("13/10/2025", "De la cellule aux tissus", "Tissus Musculaires", "François Jérôme Authier")
    
    # Science politique, droits humains et droit à la santé
    add("13/10/2025", "Science politique, droits humains et droit à la santé", "Notions fondamentales de théorie politique", "Thémis Andéol Lê Quan Phong")
    
    # Histoire et épistémologie de la pensée médicale et sanitaire
    add("13/10/2025", "Histoire et épistémologie de la pensée médicale et sanitaire", "Cours 2", "Roberto Poma")
    
    # Droit et santé
    add("14/10/2025", "Droit et santé", "Les conditions de la responsabilité médicale", "Alison Linon")

    # -------- SEMAINE 7 (20/10-24/10) --------
    # L'organisme face aux agents pathogènes
    add("20/10/2025", "L'organisme face aux agents pathogènes", "a. Hématopoïèse", "Ivan Sloma")
    add("20/10/2025", "L'organisme face aux agents pathogènes", "b. Régulation de l'hématopoïèse", "Ivan Sloma")
    add("20/10/2025", "L'organisme face aux agents pathogènes", "2. Globules rouges et groupes sanguins", "Violaine Tran Quang")
    add("20/10/2025", "L'organisme face aux agents pathogènes", "a. Les globules rouges", "Violaine Tran Quang")
    add("20/10/2025", "L'organisme face aux agents pathogènes", "b. les groupes sanguins", "Violaine Tran Quang / France Pirenne")
    add("20/10/2025", "L'organisme face aux agents pathogènes", "3. Plaquettes et physiologie de l' Hémostase", "Violaine Tran Quang")
    add("20/10/2025", "L'organisme face aux agents pathogènes", "a. Les plaquettes", "Violaine Tran Quang")
    add("20/10/2025", "L'organisme face aux agents pathogènes", "b. Physiologie de l'hémostase", "Violaine Tran Quang")
    add("20/10/2025", "L'organisme face aux agents pathogènes", "Présentation du système immunitaire", "Allan Thiolat")
    add("20/10/2025", "L'organisme face aux agents pathogènes", "Anatomie du système immunitaire", "Allan Thiolat")
    add("20/10/2025", "L'organisme face aux agents pathogènes", "Principe de l'hémogramme", "Béatrice Fareau- Saposnik")
    
    # Science politique, droits humains et droit à la santé
    add("20/10/2025", "Science politique, droits humains et droit à la santé", "Politiques publiques de la Santé en France", "Thémis Andéol Lê Quan Phong")
    
    # Histoire et épistémologie de la pensée médicale et sanitaire
    add("20/10/2025", "Histoire et épistémologie de la pensée médicale et sanitaire", "Introduction aux fondements de l'épistémologie", "Elodie Boublil")
    add("20/10/2025", "Histoire et épistémologie de la pensée médicale et sanitaire", "Cours 3", "Roberto Poma")
    
    # Anglais médical
    add("20/10/2025", "Anglais médical", "Drugs", "Fanny Tison-Harinte")
    
    # Droit et santé
    add("21/10/2025", "Droit et santé", "Eléments spécifiques au droit de la responsabilité médicale", "Alison Linon")

    # -------- SEMAINE 8 (27/10-31/10) --------
    # L'organisme face aux agents pathogènes
    add("27/10/2025", "L'organisme face aux agents pathogènes", "Immunité innée : les acteurs moléculaires", "Allan Thiolat")
    add("27/10/2025", "L'organisme face aux agents pathogènes", "Immunité innée : les acteurs moléculaires", "Allan Thiolat")
    add("27/10/2025", "L'organisme face aux agents pathogènes", "Présentation antigénique : le complexe majeur d'histocompatibilité", "Allan Thiolat")
    add("27/10/2025", "L'organisme face aux agents pathogènes", "Présentation antigénique : les récepteurs antigèniques", "Allan Thiolat")
    add("27/10/2025", "L'organisme face aux agents pathogènes", "Immunité adaptative : les lymphocytes", "Allan Thiolat")
    add("27/10/2025", "L'organisme face aux agents pathogènes", "les Lymphocytes T", "Allan Thiolat")
    add("27/10/2025", "L'organisme face aux agents pathogènes", "les Lymphocytes B", "Allan Thiolat")
    add("27/10/2025", "L'organisme face aux agents pathogènes", "a. Notion d'immunité anti-infectieuse", "S. Gallien")
    add("27/10/2025", "L'organisme face aux agents pathogènes", "b. L'hygiène et la vaccination", "JW. Decousser")
    add("27/10/2025", "L'organisme face aux agents pathogènes", "c. Les antiinfectieux", "PL. Woerther")
    add("27/10/2025", "L'organisme face aux agents pathogènes", "Le monde des infections bactérienne: Typhoïde", "M. Danjean")
    add("27/10/2025", "L'organisme face aux agents pathogènes", "Le monde des infections virales : Grippe", "Amandine Caillault")
    add("27/10/2025", "L'organisme face aux agents pathogènes", "Le monde des infections parasitaires: Bilharziose", "F. Botterel")
    
    # Science politique, droits humains et droit à la santé
    add("27/10/2025", "Science politique, droits humains et droit à la santé", "Mobilisations des patients et droits à la santé", "Thémis Andéol Lê Quan Phong")
    
    # Histoire et épistémologie de la pensée médicale et sanitaire
    add("27/10/2025", "Histoire et épistémologie de la pensée médicale et sanitaire", "Les concepts de normal et de pathologique", "Elodie Boublil")
    
    # Droit et santé
    add("28/10/2025", "Droit et santé", "Eléments spécifiques au droit de la responsabilité médicale (typologie des fautes médicales), distinction de la responsabilité personnelle et de la responsabilité hospitalière", "Alison Linon")
    
    # Histoire et épistémologie de la pensée médicale et sanitaire
    add("28/10/2025", "Histoire et épistémologie de la pensée médicale et sanitaire", "Cours 4", "Roberto Poma")

    # -------- SEMAINE 9 (03/11-07/11) --------
    # Reproduction et développement
    add("03/11/2025", "Reproduction et développement", "Généralités en anatomie", "Peggy lafuste")
    add("03/11/2025", "Reproduction et développement", "Urètre", "Peggy lafuste")
    add("03/11/2025", "Reproduction et développement", "Prostate", "Peggy lafuste")
    add("03/11/2025", "Reproduction et développement", "Testicule et voies spermatiques", "Peggy lafuste")
    add("03/11/2025", "Reproduction et développement", "Pénis", "Peggy lafuste")
    add("03/11/2025", "Reproduction et développement", "Utérus et annexes", "Peggy lafuste")
    add("03/11/2025", "Reproduction et développement", "Vagin et pudendum", "Peggy lafuste")
    
    # Compétences transversales
    add("03/11/2025", "Compétences transversales", "Compétences informationnelles", "Elodie Boublil")
    
    # Fondements philosophiques de l'éthique médicale
    add("03/11/2025", "Fondements philosophiques de l'éthique médicale", "Intelligence artificielle et anthropologie philosophique : enjeux éthiques contemporains", "Elodie Boublil")
    
    # Organisation du système de santé
    add("03/11/2025", "Organisation du système de santé", "Les différentes dimensions d'un système de santé, les réformes et le paysage institutionnel en France", "Céleste Fournier")
    
    # Histoire et épistémologie de la pensée médicale et sanitaire
    add("03/11/2025", "Histoire et épistémologie de la pensée médicale et sanitaire", "Les approches contemporaines des définitions de la santé", "Elodie Boublil")
    
    # Anglais médical
    add("03/11/2025", "Anglais médical", "Public Health - Pregnancy", "Fanny Tison-Harinte")

    # -------- SEMAINE 10 (10/11-14/11) --------
    # Reproduction et développement
    add("10/11/2025", "Reproduction et développement", "Physiologie de la reproduction", "Hélène Bry")
    add("10/11/2025", "Reproduction et développement", "a. Action des hormones (testicules et ovaires)", "Hélène Bry")
    add("10/11/2025", "Reproduction et développement", "b. Cycle ovarien et vie reproductive", "Hélène Bry")
    add("10/11/2025", "Reproduction et développement", "Méïose", "Peggy Lafuste")
    add("10/11/2025", "Reproduction et développement", "Gametogénèse (ovogenèse/folliculogenèse,spermatogenèse)", "Peggy Lafuste")
    add("10/11/2025", "Reproduction et développement", "Fécondation", "Peggy Lafuste")
    add("10/11/2025", "Reproduction et développement", "Cellules souches", "Piotr Topilko")
    add("10/11/2025", "Reproduction et développement", "Détermination embryonnaire", "Fred Relaix")
    
    # Fondements philosophiques de l'éthique médicale
    add("10/11/2025", "Fondements philosophiques de l'éthique médicale", "Questions bioéthiques : le don d'organes", "Elodie Boublil")
    add("10/11/2025", "Fondements philosophiques de l'éthique médicale", "Questions bioéthiques : La recherche sur les cellules souches", "Elodie Boublil")
    
    # Organisation du système de santé
    add("10/11/2025", "Organisation du système de santé", "L'analyse économique des biens soin et santé et le concept de marché des soins", "Isabelle Durand- Zaleski")
    
    # Histoire et épistémologie de la pensée médicale et sanitaire
    add("10/11/2025", "Histoire et épistémologie de la pensée médicale et sanitaire", "Les principales cultures médicales", "David Simard")
    
    # Compétences transversales
    add("10/11/2025", "Compétences transversales", "Compétences informationnelles", "Elodie Boublil")

    # -------- SEMAINE 11 (17/11-21/11) --------
    # Reproduction et développement
    add("17/11/2025", "Reproduction et développement", "Embryogénèse 1", "Fred Relaix")
    add("17/11/2025", "Reproduction et développement", "Embryogénèse 2", "Fred Relaix")
    add("17/11/2025", "Reproduction et développement", "Embryogénèse 3", "Fred Relaix")
    add("17/11/2025", "Reproduction et développement", "Embryogénèse 4", "Fred Relaix")
    add("17/11/2025", "Reproduction et développement", "Myogenèse", "Fred Relaix")
    add("17/11/2025", "Reproduction et développement", "Nidation/implantation", "François Jérôme Authier")
    add("17/11/2025", "Reproduction et développement", "Développement des villosités choriales", "François Jérôme Authier")
    add("17/11/2025", "Reproduction et développement", "Formation du cordon et des membranes", "François Jérôme Authier")
    add("17/11/2025", "Reproduction et développement", "Circulation placentaire", "François Jérôme Authier")
    
    # Organisation du système de santé
    add("17/11/2025", "Organisation du système de santé", "La couverture du risque santé", "Yann Videau")
    
    # Fondements philosophiques de l'éthique médicale
    add("17/11/2025", "Fondements philosophiques de l'éthique médicale", "La relation de soin : empathie et vulnérabilité", "Elodie Boublil")
    add("17/11/2025", "Fondements philosophiques de l'éthique médicale", "Le handicap", "Elodie Boublil")
    
    # Histoire et épistémologie de la pensée médicale et sanitaire
    add("17/11/2025", "Histoire et épistémologie de la pensée médicale et sanitaire", "Epistémologie de l'essai clinique contrôlé randomisé", "David Simard")

    # -------- SEMAINE 12 (24/11-28/11) --------
    # Organisation du système de santé
    add("24/11/2025", "Organisation du système de santé", "Les dépenses de santé et leur financement", "Mathias Béjean")
    
    # Fondements philosophiques de l'éthique médicale
    add("24/11/2025", "Fondements philosophiques de l'éthique médicale", "Le vieillissement", "Elodie Boublil")
    add("24/11/2025", "Fondements philosophiques de l'éthique médicale", "Enjeux éthiques en santé mentale", "Elodie Boublil")
    
    # Histoire et épistémologie de la pensée médicale et sanitaire
    add("24/11/2025", "Histoire et épistémologie de la pensée médicale et sanitaire", "Etude d'une controverse épistémologique et éthique contemporaine : le traitement de la COVID-19", "David Simard")

    # -------- SEMAINE 13 (01/12-05/12) --------
    # Semaine interactive de réponses aux questions
    add("01/12/2025", "Q&A", "SEMAINE INTERACTIVE DE REPONSES AUX QUESTIONS AVEC LES ENSEIGNANT∙ES", "Isabelle Durand-Zaleski")

    # -------- SEMAINE 14 (08/12-12/12) --------
    # Semaine de révision
    add("08/12/2025", "Révision", "SEMAINE DE REVISION", "Équipe pédagogique")

    # -------- SEMAINE 15 (15/12-19/12) --------
    # Examen terminal
    add("15/12/2025", "Examen", "EXAMEN TERMINAL", "Équipe pédagogique")

    # Tri chronologique
    rows.sort(key=lambda x: parse_fr_date(x[0]))

    out: Dict[str, Dict[str, List[Dict]]] = {}
    for dstr, ue, cours, enseignant in rows:
        d = parse_fr_date(dstr)
        wlab = week_label_for(d)

        # Utiliser l'UE comme matière
        subject = ue
        title = cours

        # Date : "-" pour tous sauf "Droit et santé" qui garde sa date précise
        if subject == "Droit et santé":
            display_date = d.strftime("%d/%m/%Y")
        else:
            display_date = "-"

        # ID stable
        safe_subj = re.sub(r'[^a-z0-9]+', '_', subject.lower())
        safe_title = re.sub(r'[^a-z0-9]+', '_', title.lower())
        item_id = f"UPEC-L1-{safe_subj}-{safe_title}-{d.strftime('%Y%m%d')}"

        out.setdefault(wlab, {}).setdefault(subject, []).append({
            "id": item_id,
            "title": title,
            "date": display_date,
            "all_subjects": subject,  # Pour la recherche
        })

    return out

UPEC_L1 = build_upec_l1_manual()

def build_upec_l2_manual() -> Dict[str, Dict[str, List[Dict]]]:
    # Données brutes : (date_dd/mm/YYYY, matière)
    raw_courses: List[Tuple[str, str]] = []
    
    def add_course(date_str: str, subject: str):
        raw_courses.append((date_str, subject))
    
    # -------- Cours UPEC L2 --------
    # 08/09
    add_course("08/09/2025", "Biostatistiques")
    add_course("08/09/2025", "Biochimie")
    
    # 09/09
    add_course("09/09/2025", "Biologie moléculaire")
    add_course("09/09/2025", "Bases en biophysique")
    add_course("09/09/2025", "Biochimie")
    
    # 10/09
    add_course("10/09/2025", "Neurosciences")
    add_course("10/09/2025", "Santé publique")
    
    # 12/09
    add_course("12/09/2025", "Immunologie")
    add_course("12/09/2025", "Communication cellulaire et signalisation")
    
    # 15/09
    add_course("15/09/2025", "Biostatistiques")
    add_course("15/09/2025", "Biochimie")
    
    # 16/09
    add_course("16/09/2025", "Biologie moléculaire")
    add_course("16/09/2025", "Bases en biophysique")
    add_course("16/09/2025", "Biochimie")
    
    # 17/09
    add_course("17/09/2025", "Santé publique")
    add_course("17/09/2025", "Neurosciences")
    
    # 18/09
    add_course("18/09/2025", "Présentation UE du S4 Amphis 1 et 2")
    add_course("18/09/2025", "Neurosciences")
    
    # 19/09
    add_course("19/09/2025", "Immunologie")
    add_course("19/09/2025", "Communication cellulaire et signalisation")
    
    # 22/09
    add_course("22/09/2025", "Biostatistiques")
    add_course("22/09/2025", "Biochimie")
    
    # 23/09
    add_course("23/09/2025", "Biologie moléculaire")
    add_course("23/09/2025", "Bases en biophysique")
    add_course("23/09/2025", "Biochimie")
    
    # 24/09
    add_course("24/09/2025", "Neurosciences")
    add_course("24/09/2025", "Santé publique")
    
    # 26/09
    add_course("26/09/2025", "Immunologie")
    add_course("26/09/2025", "Communication cellulaire et signalisation")
    
    # 29/09
    add_course("29/09/2025", "Biostatistiques")
    add_course("29/09/2025", "Biochimie")
    
    # 30/09
    add_course("30/09/2025", "Biologie moléculaire")
    add_course("30/09/2025", "Bases en biophysique")
    add_course("30/09/2025", "Biochimie")
    
    # 01/10
    add_course("01/10/2025", "Neurosciences")
    add_course("01/10/2025", "Santé publique")
    
    # 03/10
    add_course("03/10/2025", "Immunologie")
    add_course("03/10/2025", "Communication cellulaire et signalisation")
    
    # 06/10
    add_course("06/10/2025", "Biostatistiques")
    add_course("06/10/2025", "Biochimie")
    
    # 07/10
    add_course("07/10/2025", "Biologie moléculaire")
    add_course("07/10/2025", "Bases en biophysique")
    add_course("07/10/2025", "Biochimie")
    
    # 08/10
    add_course("08/10/2025", "Neurosciences")
    add_course("08/10/2025", "Santé publique")
    
    # 10/10
    add_course("10/10/2025", "Immunologie")
    add_course("10/10/2025", "Communication cellulaire et signalisation")
    
    # 13/10
    add_course("13/10/2025", "Biostatistiques")
    add_course("13/10/2025", "SHS")
    
    # 14/10
    add_course("14/10/2025", "Biologie moléculaire")
    add_course("14/10/2025", "Bases en biophysique")
    add_course("14/10/2025", "SHS")
    
    # 15/10
    add_course("15/10/2025", "Neurosciences")
    add_course("15/10/2025", "Santé publique")
    
    # 17/10
    add_course("17/10/2025", "Immunologie")
    add_course("17/10/2025", "Communication cellulaire et signalisation")
    
    # 20/10
    add_course("20/10/2025", "Biostatistiques")
    add_course("20/10/2025", "SHS")
    
    # 21/10
    add_course("21/10/2025", "Biologie moléculaire")
    add_course("21/10/2025", "Bases en biophysique")
    add_course("21/10/2025", "SHS")
    
    # 22/10
    add_course("22/10/2025", "Neurosciences")
    add_course("22/10/2025", "Santé publique")
    
    # 24/10
    add_course("24/10/2025", "Communication cellulaire et signalisation")
    add_course("24/10/2025", "Immunologie")
    
    # 27/10
    add_course("27/10/2025", "Biostatistiques")
    add_course("27/10/2025", "SHS")
    
    # 28/10
    add_course("28/10/2025", "Biologie moléculaire")
    add_course("28/10/2025", "Bases en biophysique")
    add_course("28/10/2025", "SHS")
    
    # 29/10
    add_course("29/10/2025", "Neurosciences")
    add_course("29/10/2025", "Santé publique")
    
    # 31/10
    add_course("31/10/2025", "Immunologie")
    add_course("31/10/2025", "Communication cellulaire et signalisation")
    
    # 03/11
    add_course("03/11/2025", "Biostatistiques")
    add_course("03/11/2025", "SHS")
    
    # 04/11
    add_course("04/11/2025", "Biologie moléculaire")
    add_course("04/11/2025", "Bases en biophysique")
    add_course("04/11/2025", "SHS")
    
    # 05/11
    add_course("05/11/2025", "Neurosciences")
    add_course("05/11/2025", "Santé publique")
    
    # 07/11
    add_course("07/11/2025", "Immunologie")
    add_course("07/11/2025", "Communication cellulaire et signalisation")
    
    # 10/11
    add_course("10/11/2025", "SHS")
    
    # 12/11
    add_course("12/11/2025", "Neurosciences")
    add_course("12/11/2025", "Santé publique")
    
    # 14/11
    add_course("14/11/2025", "Immunologie")
    add_course("14/11/2025", "Communication cellulaire et signalisation")
    
    # 17/11
    add_course("17/11/2025", "Biostatistiques")
    add_course("17/11/2025", "SHS")
    
    # 18/11
    add_course("18/11/2025", "Biologie moléculaire")
    add_course("18/11/2025", "Bases en biophysique")
    add_course("18/11/2025", "SHS")
    
    # 19/11
    add_course("19/11/2025", "Neurosciences")
    add_course("19/11/2025", "Santé publique")
    
    # 21/11
    add_course("21/11/2025", "Immunologie")
    add_course("21/11/2025", "Communication cellulaire et signalisation")
    
    # 24/11
    add_course("24/11/2025", "SHS")
    
    # 25/11
    add_course("25/11/2025", "Biologie moléculaire")
    add_course("25/11/2025", "Bases en biophysique")
    add_course("25/11/2025", "SHS")
    
    # 26/11
    add_course("26/11/2025", "Neurosciences")
    add_course("26/11/2025", "Santé publique")
    
    # 28/11
    add_course("28/11/2025", "Immunologie")
    add_course("28/11/2025", "Communication cellulaire et signalisation")
    
    # 01/12
    add_course("01/12/2025", "Bases en biophysique")
    
    # 02/12
    add_course("02/12/2025", "Biologie moléculaire")
    add_course("02/12/2025", "Santé publique")
    add_course("02/12/2025", "SHS")
    
    # 03/12
    add_course("03/12/2025", "Neurosciences")
    add_course("03/12/2025", "Santé publique")
    
    # 05/12
    add_course("05/12/2025", "Neurosciences")
    
    # 09/12
    add_course("09/12/2025", "SHS Questions-réponses")
    
    # Tri chronologique
    raw_courses.sort(key=lambda x: parse_fr_date(x[0]))
    
    # Compter les occurrences de chaque matière pour la numérotation des CM
    subject_counts: Dict[str, int] = {}
    
    out: Dict[str, Dict[str, List[Dict]]] = {}
    for date_str, subject in raw_courses:
        d = parse_fr_date(date_str)
        wlab = week_label_for(d)
        
        # Compter les occurrences de cette matière
        subject_counts[subject] = subject_counts.get(subject, 0) + 1
        cm_number = subject_counts[subject]
        
        # Créer le titre avec numérotation automatique
        title = f"{subject} CM {cm_number}"
        
        # ID stable
        safe_subj = re.sub(r'[^a-z0-9]+', '_', subject.lower())
        safe_title = re.sub(r'[^a-z0-9]+', '_', title.lower())
        item_id = f"UPEC-L2-{safe_subj}-{safe_title}-{d.strftime('%Y%m%d')}"
        
        out.setdefault(wlab, {}).setdefault(subject, []).append({
            "id": item_id,
            "title": title,
            "date": d.strftime("%d/%m/%Y"),
            "all_subjects": subject,  # Pour la recherche
        })
    
    return out

UPEC_L2 = build_upec_l2_manual()

# =========================
# DATA GLOBALE
# =========================
DATA = {
    "UPC": UPC,
    "UPS": UPS,
    "UVSQ": UVSQ,
    "L1 UPEC": UPEC_L1,
    "L2 UPEC": UPEC_L2,
    "USPN": {},
    "SU": SU,
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
# LAYOUT 5/6 – 1/6 (plus d'espace pour le tableau principal)
# =========================
left, right = st.columns([5, 1], gap="large")

# ------ AVANCEMENT ------
with left:
    # Ajouter un espace entre header et filtres
    st.markdown('<div style="margin-top: 16px;"></div>', unsafe_allow_html=True)
    
    # Ajouter un espace avant le glass du tableau
    st.markdown('<div style="margin-bottom: 12px;"></div>', unsafe_allow_html=True)
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

    # Filtres avec sélecteur de faculté
    ctop = st.columns([1.5, 1.5, 1.2, 1.0, 1.0])
    
    with ctop[0]:
        st.caption("Semaine")
        week = st.selectbox("Semaine", all_weeks,
                            index=all_weeks.index(first_week_with_data()),
                            label_visibility="collapsed")
    
    with ctop[1]:
        st.caption("Faculté")
        selected_faculty = st.selectbox("Faculté", ["Toutes"] + FACULTIES,
                                       index=0, label_visibility="collapsed")
    
    with ctop[2]:
        st.caption("Date précise (optionnel)")
        specific_date = st.date_input("Date", value=None, label_visibility="collapsed")
    
    with ctop[3]:
        st.caption("Filtrer par matière")
        query = st.text_input("Rechercher…", value="", label_visibility="collapsed").strip().lower()
    
    with ctop[4]:
        st.caption("Actions")
        if st.button("Tout cocher", use_container_width=True):
            faculties_to_check = [selected_faculty] if selected_faculty != "Toutes" else FACULTIES
            for fac in faculties_to_check:
                for subj, items in DATA[fac].get(week, {}).items():
                    for it in items:
                        st.session_state[make_key(fac, subj, week, it["id"])] = True
            save_progress()
            st.success("Toutes les cases de la semaine sont cochées.")

    # Espacement entre filtres et tableau - agrandir le rectangle orange
    st.markdown('<div style="margin-bottom: 20px;"></div>', unsafe_allow_html=True)

    # Déterminer quelles facultés afficher
    if selected_faculty == "Toutes":
        faculties_to_display = FACULTIES
        # Entêtes tableau - 7 colonnes pour les facultés avec largeurs équilibrées
        c0, c1, c2, c3, c4, c5, c6 = st.columns([1.3, 1.3, 1.3, 1.2, 1.2, 1.2, 1.2])
        for fac, c in zip(FACULTIES, [c0, c1, c2, c3, c4, c5, c6]):
            c.markdown(f'<div class="table-head fac-head">{fac}</div>', unsafe_allow_html=True)
        
        # Organiser par faculté pour éviter les trous - affichage continu par colonne
        c0, c1, c2, c3, c4, c5, c6 = st.columns([1.3, 1.3, 1.3, 1.2, 1.2, 1.2, 1.2], gap="large")
        columns = [c0, c1, c2, c3, c4, c5, c6]
    else:
        faculties_to_display = [selected_faculty]
        # Une seule colonne en grand
        c0, = st.columns([1])
        c0.markdown(f'<div class="table-head fac-head">{selected_faculty}</div>', unsafe_allow_html=True)
        c0, = st.columns([1], gap="large")
        columns = [c0]
    
    def render_faculty_column(col, fac):
        """Affiche tous les cours d'une faculté de manière continue"""
        with col:
            st.markdown('<div class="rowline">', unsafe_allow_html=True)
            
            # Collecter tous les cours de cette faculté après filtrage
            all_courses = []
            for subj in SUBJECTS:
                # Récupérer les items de base
                if specific_date:
                    target_date = specific_date.strftime("%d/%m/%Y")
                    items = DATA.get(fac, {}).get(week, {}).get(subj, [])
                    items = [it for it in items if it["date"] == target_date]
                else:
                    items = DATA.get(fac, {}).get(week, {}).get(subj, [])
                
                # Appliquer le filtre de matière si nécessaire
                if query:
                    filtered_items = []
                    for it in items:
                        # Vérifier la matière principale
                        if query in subj.lower():
                            filtered_items.append((it, subj))
                        # Vérifier les matières étendues si disponibles
                        elif it.get("all_subjects") and query in it["all_subjects"].lower():
                            filtered_items.append((it, subj))
                    items_with_subj = filtered_items
                else:
                    items_with_subj = [(it, subj) for it in items]
                
                all_courses.extend(items_with_subj)
            
            # Trier les cours par date
            all_courses.sort(key=lambda x: x[0]["date"])
            
            if not all_courses:
                st.markdown('<span class="muted small">—</span>', unsafe_allow_html=True)
            else:
                for it, subj in all_courses:
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
                    # Afficher toutes les matières si disponibles, sinon la matière principale
                    subjects_to_show = it.get("all_subjects", subj)
                    st.markdown(f'<span class="mini subject">{subjects_to_show}</span>', unsafe_allow_html=True)
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
    
    # Afficher les facultés sélectionnées
    for i, fac in enumerate(faculties_to_display):
        render_faculty_column(columns[i], fac)

    st.markdown('</div>', unsafe_allow_html=True)

# ------ BOURSIERS ------
with right:
    # Ajouter un espace pour aligner avec le tableau principal
    st.markdown('<div style="margin-top: 28px;"></div>', unsafe_allow_html=True)
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
        ("SU (Moodle Sciences, Mayla)",
         "https://moodlepass.sorbonne-universite.fr/moodle/?redirect=0",
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
