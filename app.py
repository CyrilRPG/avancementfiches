# app.py — Streamlit Cloud
# UI DS élégante + import auto UVSQ + parser UPS (PDF Sem/UE)
import json
import re
from datetime import date, timedelta
from typing import Dict, List, Tuple, Optional

import streamlit as st
from streamlit_js_eval import streamlit_js_eval

# ====== CONFIG ======
st.set_page_config(
    page_title="Diploma Santé - Suivi de l'avancement des fiches",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ====== PALETTE / THEME (dark soft) ======
DS_BLUE = "#59a8d8"
DS_NAVY = "#12233f"
DS_BG   = "#0e1a30"
DS_BG_SOFT = "#12223e"
DS_CARD = "rgba(255,255,255,.05)"
TEXT    = "#ecf2f8"
MUTED   = "#aab7c8"
BORDER  = "rgba(255,255,255,.12)"
SUCCESS = "#4ade80"

st.markdown(
    f"""
    <style>
    .stApp {{
      background:
        radial-gradient(1200px 600px at 10% -10%, rgba(89,168,216,.12), transparent 60%),
        linear-gradient(180deg, {DS_BG} 0%, {DS_BG_SOFT} 50%, #0c192e 100%);
      color: {TEXT}; font-weight: 450;
    }}
    header[data-testid="stHeader"] {{ background: transparent; }}
    .ds-header {{
      display:flex; align-items:center; justify-content:center;
      gap:16px; padding:10px 16px;
      position: sticky; top: 0; z-index: 50;
      background: linear-gradient(180deg, rgba(14,26,48,.96), rgba(14,26,48,.86));
      border-bottom: 1px solid {BORDER};
      backdrop-filter: blur(8px);
    }}
    .ds-title {{ font-size: 1.9rem; font-weight: 800; letter-spacing:.2px; }}
    .title-grad {{
      background: linear-gradient(90deg, {DS_BLUE} 0%, #9ed2ef 65%);
      -webkit-background-clip: text; background-clip: text; color: transparent;
      line-height: 1.1;
    }}
    .ds-sub {{ margin-top: -6px; color: {MUTED}; }}

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

    div.stCheckbox > label > div[data-testid="stMarkdownContainer"] p {{
      color: {TEXT} !important; font-weight: 600;
    }}
    .ok-pill {{
      display:inline-block; padding:2px 8px; border-radius: 999px;
      background: rgba(74,222,128,.15); border: 1px solid rgba(74,222,128,.35); color:{SUCCESS};
      font-size: .78rem; margin-left: 6px;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ====== UTILITAIRES ======
def week_ranges(start: date, end_included: date) -> List[str]:
    cur = start - timedelta(days=start.weekday())
    out = []
    while cur <= end_included:
        fin = cur + timedelta(days=6)
        out.append(f"{cur.strftime('%d/%m/%Y')} - {fin.strftime('%d/%m/%Y')}")
        cur += timedelta(days=7)
    return out

def monday_of_iso_week(year: int, iso_week: int) -> date:
    # ISO week: Monday is day 1
    return date.fromisocalendar(year, iso_week, 1)

def make_key(*parts: str) -> str:
    slug = lambda s: re.sub(r'[^a-z0-9]+', '_', s.lower())
    return "ds::" + "::".join(slug(p) for p in parts if p)

# ====== CLASSIFICATION ======
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
    return UNKNOWN_SUBJECT

# ====== UVSQ (CM uniquement) ======
def add_item(dst: Dict[str, Dict[str, List[Dict]]], week_label: str,
             title: str, date_str: str, explicit_subject: Optional[str]=None, cid: Optional[str]=None):
    subj = explicit_subject or classify_subject(title)
    dst.setdefault(week_label, {}).setdefault(subj, []).append({
        "id": cid or title, "title": title, "date": date_str,
    })

UVSQ: Dict[str, Dict[str, List[Dict]]] = {}

# S1 — 01/09–07/09
add_item(UVSQ, "01/09/2025 - 07/09/2025", "CM (intitulé non précisé)", "03/09/2025", cid="CM-1")
add_item(UVSQ, "01/09/2025 - 07/09/2025", "CM (intitulé non précisé)", "03/09/2025", cid="CM-2")
# S2 — 08/09–14/09
add_item(UVSQ, "08/09/2025 - 14/09/2025", "CM Biologie cellulaire – Histo Embryo", "08/09/2025",
         explicit_subject="Biologie cellulaire – Histo-Embryo", cid="BIO-1")
add_item(UVSQ, "08/09/2025 - 14/09/2025", "CM Chimie – Biochimie (UE1)", "08/09/2025",
         explicit_subject="Chimie – Biochimie", cid="CHIM-1")
add_item(UVSQ, "08/09/2025 - 14/09/2025", "CM (intitulé non précisé)", "09/09/2025", cid="CM-3")
# S3 — 15/09–21/09
add_item(UVSQ, "15/09/2025 - 21/09/2025", "CM Biologie cellulaire – Histo Embryo", "17/09/2025",
         explicit_subject="Biologie cellulaire – Histo-Embryo", cid="BIO-2")
add_item(UVSQ, "15/09/2025 - 21/09/2025", "CM Chimie – Biochimie (PASS-1.1)", "15/09/2025",
         explicit_subject="Chimie – Biochimie", cid="CHIM-2")
add_item(UVSQ, "15/09/2025 - 21/09/2025", "CM Chimie – Biochimie (PASS-1.1)", "17/09/2025",
         explicit_subject="Chimie – Biochimie", cid="CHIM-3")
add_item(UVSQ, "15/09/2025 - 21/09/2025", "CM (intitulé non précisé)", "15/09/2025", cid="CM-4")
add_item(UVSQ, "15/09/2025 - 21/09/2025", "CM (intitulé non précisé)", "15/09/2025", cid="CM-5")
# S4 — 22/09–28/09
add_item(UVSQ, "22/09/2025 - 28/09/2025", "CM Biologie cellulaire – Histo Embryo", "22/09/2025",
         explicit_subject="Biologie cellulaire – Histo-Embryo", cid="BIO-3")
add_item(UVSQ, "22/09/2025 - 28/09/2025", "CM Chimie – Biochimie (PASS-1.1)", "24/09/2025",
         explicit_subject="Chimie – Biochimie", cid="CHIM-4")
add_item(UVSQ, "22/09/2025 - 28/09/2025", "CM Chimie – Biochimie (PASS-1.1)", "22/09/2025",
         explicit_subject="Chimie – Biochimie", cid="CHIM-5")
# S5 — 29/09–05/10
add_item(UVSQ, "29/09/2025 - 05/10/2025", "CM Physique – Biophysique (PASS-3.1)", "30/09/2025",
         explicit_subject="Physique – Biophysique", cid="PHYS-1")
add_item(UVSQ, "29/09/2025 - 05/10/2025", "CM Biologie cellulaire – Histo Embryo", "01/10/2025",
         explicit_subject="Biologie cellulaire – Histo-Embryo", cid="BIO-4")
# S6 — 06/10–12/10
add_item(UVSQ, "06/10/2025 - 12/10/2025", "CM Biologie cellulaire – Histo Embryo", "06/10/2025",
         explicit_subject="Biologie cellulaire – Histo-Embryo", cid="BIO-5")
add_item(UVSQ, "06/10/2025 - 12/10/2025", "CM Chimie – Biochimie (PASS-1.1)", "06/10/2025",
         explicit_subject="Chimie – Biochimie", cid="CHIM-6")
add_item(UVSQ, "06/10/2025 - 12/10/2025", "CM Biologie cellulaire – Histo Embryo", "08/10/2025",
         explicit_subject="Biologie cellulaire – Histo-Embryo", cid="BIO-6")
add_item(UVSQ, "06/10/2025 - 12/10/2025", "CM Chimie – Biochimie (PASS-1.1)", "08/10/2025",
         explicit_subject="Chimie – Biochimie", cid="CHIM-7")
# S7 — 13/10–19/10
add_item(UVSQ, "13/10/2025 - 19/10/2025", "CM Biologie cellulaire – Histo Embryo", "13/10/2025",
         explicit_subject="Biologie cellulaire – Histo-Embryo", cid="BIO-7")
add_item(UVSQ, "13/10/2025 - 19/10/2025", "CM Chimie – Biochimie (PASS-1.1)", "14/10/2025",
         explicit_subject="Chimie – Biochimie", cid="CHIM-8")
add_item(UVSQ, "13/10/2025 - 19/10/2025", "CM Biologie cellulaire – Histo Embryo", "15/10/2025",
         explicit_subject="Biologie cellulaire – Histo-Embryo", cid="BIO-8")
# S9 — 27/10–02/11
add_item(UVSQ, "27/10/2025 - 02/11/2025", "CM (intitulé non précisé)", "27/10/2025", cid="CM-6")
add_item(UVSQ, "27/10/2025 - 02/11/2025", "CM (intitulé non précisé)", "28/10/2025", cid="CM-7")
add_item(UVSQ, "27/10/2025 - 02/11/2025", "CM (intitulé non précisé)", "29/10/2025", cid="CM-8")
# S10 — 03/11–09/11
add_item(UVSQ, "03/11/2025 - 09/11/2025", "CM Chimie – Biochimie (PASS-1.1)", "04/11/2025",
         explicit_subject="Chimie – Biochimie", cid="CHIM-9")
add_item(UVSQ, "03/11/2025 - 09/11/2025", "CM Chimie – Biochimie (PASS-1.1)", "04/11/2025",
         explicit_subject="Chimie – Biochimie", cid="CHIM-10")
add_item(UVSQ, "03/11/2025 - 09/11/2025", "CM (intitulé non précisé)", "05/11/2025", cid="CM-9")
add_item(UVSQ, "03/11/2025 - 09/11/2025", "CM Physique – Biophysique (PASS-3.1)", "07/11/2025",
         explicit_subject="Physique – Biophysique", cid="PHYS-2")
# S11 — 10/11–16/11
add_item(UVSQ, "10/11/2025 - 16/11/2025", "CM Biologie cellulaire – Histo Embryo", "10/11/2025",
         explicit_subject="Biologie cellulaire – Histo-Embryo", cid="BIO-9")
add_item(UVSQ, "10/11/2025 - 16/11/2025", "CM Physique – Biophysique (PASS-3.1)", "10/11/2025",
         explicit_subject="Physique – Biophysique", cid="PHYS-3")
# S12 — 17/11–23/11 (image S12 fournie) — révision ignorée, CM non précisé conservé
add_item(UVSQ, "17/11/2025 - 23/11/2025", "CM (intitulé non précisé)", "17/11/2025", cid="CM-10")

# ====== UPS (PDF) – parsing Sem/UE ======
UE_TO_SUBJECT = {
    1: "Chimie – Biochimie",   # UE1 Biochimie → on regroupe avec Chimie–Biochimie côté tableau
    2: "Biologie cellulaire – Histo-Embryo",  # UE2 Biologie → on regroupe avec UVSQ bio cell/histo
    3: "Physique – Biophysique",
    4: "Statistiques",
    5: "Chimie – Biochimie",   # UE5 Chimie → même ligne que biochimie (commun)
}

def extract_ups_pdf_text(paths: List[str]) -> str:
    for p in paths:
        try:
            import PyPDF2
            with open(p, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                txt = ""
                for page in reader.pages:
                    t = page.extract_text() or ""
                    txt += "\n" + t
                if txt.strip():
                    return txt
        except Exception:
            continue
    return ""

def parse_ups_schedule(pdf_text: str) -> Dict[str, Dict[str, List[Dict]]]:
    """
    Cherche blocs 'Sem xx' puis les occurrences 'UE n k' suivantes.
    Assigne chaque 'UE n k' à la semaine ISO correspondante (année 2025),
    titre 'CM UE{n} {k} — {matière}', date=lundi de la semaine.
    """
    data: Dict[str, Dict[str, List[Dict]]] = {}
    if not pdf_text:
        return data

    lines = [l.strip() for l in pdf_text.splitlines() if l.strip()]
    current_sem: Optional[int] = None
    # On va collecter toutes les (sem, ue, num)
    events: List[Tuple[int, int, str]] = []

    sem_re = re.compile(r'\b[Ss]em\s*([0-9]{1,2})\b')
    ue_re  = re.compile(r'\bUE\s*([1-5])\s*([0-9]+)\b')

    for ln in lines:
        m_sem = sem_re.search(ln)
        if m_sem:
            current_sem = int(m_sem.group(1))
            continue
        for m in ue_re.finditer(ln):
            ue = int(m.group(1))
            num = m.group(2)
            if current_sem:
                events.append((current_sem, ue, num))

    # Convertit en semaines
    by_week: Dict[int, List[Tuple[int, str]]] = {}
    for sem, ue, num in events:
        by_week.setdefault(sem, []).append((ue, num))

    # Map week -> label -> subject -> items
    for sem, items in by_week.items():
        try:
            monday = monday_of_iso_week(2025, sem)
        except Exception:
            # si sem hors plage ISO, on ignore
            continue
        week_label = f"{monday.strftime('%d/%m/%Y')} - {(monday + timedelta(days=6)).strftime('%d/%m/%Y')}"
        for ue, num in items:
            subject = UE_TO_SUBJECT.get(ue, UNKNOWN_SUBJECT)
            title = f"CM UE{ue} {num} — {subject}"
            entry = {"id": f"UE{ue}-{num}", "title": title, "date": monday.strftime("%d/%m/%Y")}
            data.setdefault(week_label, {}).setdefault(subject, []).append(entry)

    return data

UPS: Dict[str, Dict[str, List[Dict]]] = {}
_pdf_txt = extract_ups_pdf_text([
    "CM 1er semestre (1).pdf",
    "streamlit/CM 1er semestre (1).pdf",
])
UPS = parse_ups_schedule(_pdf_txt)

# ====== DATA globale ======
DATA = {
    "UPC": {},           # prêt pour futurs imports
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

# ====== PERSISTENCE localStorage ======
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

# ====== HEADER ======
st.markdown(
    """
    <div class="ds-header">
      <img src="streamlit/logo.png" style="height:44px;"/>
      <div>
        <div class="ds-title title-grad">Diploma Santé</div>
        <div class="ds-sub">Suivi de l’avancement des fiches</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True
)
st.write("")

# ====== LAYOUT 3/4 – 1/4 ======
left, right = st.columns([3, 1], gap="large")

# ---------------- AVANCEMENT ----------------
with left:
    st.markdown('<div class="glass">', unsafe_allow_html=True)

    # Semaine
    all_weeks = week_ranges(date(2025, 9, 1), date(2026, 1, 4))
    if all_weeks and all_weeks[-1].endswith("04/01/2026"):
        all_weeks[-1] = "29/12/2025 - 04/01/2025"

    def first_week_with_data():
        for w in all_weeks:
            for fac in FACULTIES:
                if w in DATA.get(fac, {}) and any(DATA[fac][w].values()):
                    return w
        return all_weeks[0]

    ctop = st.columns([1, 1.8, 1.6, 1.6])
    with ctop[0]:
        st.caption("Semaine")
        week = st.selectbox("Semaine", all_weeks,
                            index=all_weeks.index(first_week_with_data()),
                            label_visibility="collapsed")
    with ctop[1]:
        st.caption("Filtrer par matière")
        query = st.text_input("Rechercher…", value="", label_visibility="collapsed").strip().lower()
    with ctop[2]:
        st.caption("Actions semaine")
        if st.button("Tout cocher", use_container_width=True):
            for fac in FACULTIES:
                for subj, items in DATA[fac].get(week, {}).items():
                    for it in items:
                        st.session_state[k(fac, subj, week, it["id"])] = True
            flush_to_localstorage()
    with ctop[3]:
        st.caption(" ")
        if st.button("Tout décocher", use_container_width=True):
            for fac in FACULTIES:
                for subj, items in DATA[fac].get(week, {}).items():
                    for it in items:
                        st.session_state[k(fac, subj, week, it["id"])] = False
            flush_to_localstorage()

    st.divider()

    # En-têtes
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

# ---------------- BOURSIERS ----------------
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
         "u32502188",
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

# Sauvegarde localStorage
flush_to_localstorage()
