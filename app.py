# app.py — Streamlit Cloud (sans dossier .streamlit)
import json
import re
from datetime import date, timedelta
from typing import Dict, List

import streamlit as st
from streamlit_js_eval import streamlit_js_eval

# =========================
# CONFIG PAGE
# =========================
st.set_page_config(
    page_title="Diploma Santé - Suivi de l'avancement des fiches",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =========================
# CHARTE DIPLOMA SANTÉ (dark) — pas de .streamlit/config.toml, on injecte tout en CSS
# =========================
DS_BLUE = "#59a8d8"   # bleu DS
DS_NAVY = "#0f223f"   # navy DS
DS_BG   = "#0b162b"   # fond
DS_GOLD = "#cda96a"   # accent
TEXT    = "#e6eef6"   # texte

st.markdown(
    f"""
    <style>
    .stApp {{
      background: radial-gradient(1200px 600px at 10% -10%, rgba(89,168,216,0.10), transparent 60%),
                  linear-gradient(180deg, {DS_BG} 0%, #0a1628 40%, #07121f 100%);
      color: {TEXT};
    }}
    header[data-testid="stHeader"] {{ background: transparent; }}
    .glass {{
      background: rgba(15,22,36,.55);
      border: 1px solid rgba(94,106,129,.25);
      border-radius: 16px; padding: 14px;
    }}
    .cardish {{
      background: rgba(2,6,23,.35);
      border: 1px solid rgba(148,163,184,.22);
      border-radius: 14px; padding: 12px;
    }}
    .cell {{
      border: 1px solid rgba(148,163,184,.25);
      border-radius: 12px; padding: 10px; margin-bottom: 10px;
      background: rgba(15,22,36,.55);
    }}
    .muted {{ color: rgb(168,179,194); }}
    .subject {{ color:#e2e8f0; font-weight: 700; }}
    .title-grad {{
      background: linear-gradient(90deg, {DS_BLUE} 0%, #7fc1e6 70%);
      -webkit-background-clip: text; background-clip: text; color: transparent;
      font-weight: 800; letter-spacing:.2px;
    }}
    .thin-sep {{ height:1px; background:rgba(255,255,255,.08); margin: 8px 0 14px 0; }}
    .small {{ font-size: 0.85rem; }}
    .mini  {{ font-size: 0.78rem; color: rgb(168,179,194); }}
    .fac-head {{
      display:flex; justify-content:center; align-items:center;
      background: rgba(15,22,36,.45);
      border:1px solid rgba(148,163,184,.25);
      border-radius:10px; padding:6px; font-weight:600; color:#e5e7eb;
    }}
    .table-head {{
      font-weight:600; color:#e5e7eb; letter-spacing:.3px; border-bottom:1px solid #25314a; padding:10px 8px;
    }}
    .rowline {{ border-bottom:1px solid #111827; padding:10px 8px; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================
# OUTILS: semaines, clés de stockage
# =========================
def week_ranges(start: date, end_included: date) -> List[str]:
    """Retourne des libellés 'dd/mm/yyyy - dd/mm/yyyy' (lundi→dimanche)."""
    cur = start - timedelta(days=start.weekday())  # aligne sur lundi
    out = []
    while cur <= end_included:
        fin = cur + timedelta(days=6)
        out.append(f"{cur.strftime('%d/%m/%Y')} - {fin.strftime('%d/%m/%Y')}")
        cur += timedelta(days=7)
    return out

def make_key(*parts: str) -> str:
    def slug(s: str) -> str:
        return re.sub(r'[^a-z0-9]+', '_', s.lower())
    return "ds::" + "::".join(slug(p) for p in parts if p)

# =========================
# DONNÉES UVSQ — CM uniquement (extraites de tes captures)
# =========================
COMMON_HINTS = {
    "Biologie cellulaire – Histo-Embryo",
    "Chimie – Biochimie",
    "Physique – Biophysique",
}

UVSQ: Dict[str, Dict[str, List[Dict]]] = {
    "08/09/2025 - 14/09/2025": {
        "Chimie – Biochimie": [
            {"id": "CM1", "title": "CM 1 Chimie – Biochimie", "date": "08/09/2025"},
        ],
        "Biologie cellulaire – Histo-Embryo": [
            {"id": "CM1", "title": "CM 1 Biologie cellulaire", "date": "08/09/2025"},
            {"id": "CM2", "title": "CM 2 Biologie cellulaire", "date": "09/09/2025"},
        ],
    },
    "15/09/2025 - 21/09/2025": {
        "Chimie – Biochimie": [
            {"id": "CM2", "title": "CM 2 Chimie – Biochimie", "date": "15/09/2025"},
            {"id": "CM3", "title": "CM 3 Chimie – Biochimie", "date": "16/09/2025"},
        ],
        "Biologie cellulaire – Histo-Embryo": [
            {"id": "CM3", "title": "CM 3 Biologie cellulaire", "date": "15/09/2025"},
        ],
        "Physique – Biophysique": [
            {"id": "CM1", "title": "CM 1 Physique – Biophysique", "date": "16/09/2025"},
        ],
    },
    "22/09/2025 - 28/09/2025": {
        "Chimie – Biochimie": [
            {"id": "CM4", "title": "CM 4 Chimie – Biochimie", "date": "22/09/2025"},
        ],
        "Biologie cellulaire – Histo-Embryo": [
            {"id": "CM4", "title": "CM 4 Biologie cellulaire", "date": "22/09/2025"},
            {"id": "CM5", "title": "CM 5 Biologie cellulaire", "date": "23/09/2025"},
        ],
    },
    "29/09/2025 - 05/10/2025": {
        "Physique – Biophysique": [
            {"id": "CM2", "title": "CM 2 Physique – Biophysique", "date": "30/09/2025"},
        ],
        "Biologie cellulaire – Histo-Embryo": [
            {"id": "CM6", "title": "CM 6 Biologie cellulaire", "date": "01/10/2025"},
        ],
    },
    "06/10/2025 - 12/10/2025": {
        "Chimie – Biochimie": [
            {"id": "CM5", "title": "CM 5 Chimie – Biochimie", "date": "06/10/2025"},
            {"id": "CM6", "title": "CM 6 Chimie – Biochimie", "date": "07/10/2025"},
        ],
        "Biologie cellulaire – Histo-Embryo": [
            {"id": "CM7", "title": "CM 7 Biologie cellulaire", "date": "06/10/2025"},
            {"id": "CM8", "title": "CM 8 Biologie cellulaire", "date": "08/10/2025"},
        ],
    },
    "13/10/2025 - 19/10/2025": {
        "Chimie – Biochimie": [
            {"id": "CM7", "title": "CM 7 Chimie – Biochimie", "date": "14/10/2025"},
        ],
        "Biologie cellulaire – Histo-Embryo": [
            {"id": "CM9", "title": "CM 9 Biologie cellulaire", "date": "13/10/2025"},
            {"id": "CM10", "title": "CM 10 Biologie cellulaire", "date": "15/10/2025"},
        ],
    },
    "27/10/2025 - 02/11/2025": {
        "Biologie cellulaire – Histo-Embryo": [
            {"id": "CM11", "title": "CM 11 Biologie cellulaire", "date": "29/10/2025"},
        ],
    },
    "03/11/2025 - 09/11/2025": {
        "Chimie – Biochimie": [
            {"id": "CM8", "title": "CM 8 Chimie – Biochimie", "date": "04/11/2025"},
            {"id": "CM9", "title": "CM 9 Chimie – Biochimie", "date": "04/11/2025"},
        ],
        "Physique – Biophysique": [
            {"id": "CM3", "title": "CM 3 Physique – Biophysique", "date": "04/11/2025"},
        ],
    },
    "10/11/2025 - 16/11/2025": {
        "Biologie cellulaire – Histo-Embryo": [
            {"id": "CM12", "title": "CM 12 Biologie cellulaire", "date": "10/11/2025"},
        ],
        "Physique – Biophysique": [
            {"id": "CM4", "title": "CM 4 Physique – Biophysique", "date": "10/11/2025"},
        ],
    },
}

DATA = {
    "UPC": {},   # vides pour l’instant
    "UPS": {},
    "UVSQ": UVSQ,
}
FACULTIES = ["UPC", "UPS", "UVSQ"]  # ordre demandé

def all_subjects_sorted():
    subjects = set()
    for fac in FACULTIES:
        for subj_map in DATA.get(fac, {}).values():
            subjects.update(subj_map.keys())
    return sorted(subjects, key=lambda s: (0 if s in COMMON_HINTS else 1, s.lower()))

SUBJECTS = all_subjects_sorted()

# =========================
# PERSISTENCE localStorage <-> session_state
# =========================
def k(fac, subject, week, item_id):
    return make_key(fac, subject, week, item_id)

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
# HEADER
# =========================
h1, h2 = st.columns([0.12, 0.88])
with h1:
    # place ton logo ici: streamlit/logo.png
    st.image("streamlit/logo.png", use_container_width=True)
with h2:
    st.markdown('<div class="title-grad" style="font-size:2rem;">Diploma Santé</div>', unsafe_allow_html=True)
    st.markdown('<div class="muted" style="margin-top:-6px;">Suivi de l’avancement des fiches</div>', unsafe_allow_html=True)

st.markdown('<div class="thin-sep"></div>', unsafe_allow_html=True)

# =========================
# LAYOUT PRINCIPAL 2 COLONNES (3/4 — 1/4)
# =========================
left, right = st.columns([3, 1], gap="large")

# ==== COLONNE AVANCEMENT (TABLEAU) ====
with left:
    st.markdown('<div class="glass">', unsafe_allow_html=True)

    # Semaine: 01/09/2025 - 07/09/2025 → 29/12/2025 - 04/01/2025 (étiquette)
    # NB: calcul réel va jusqu'à 04/01/2026, mais on affiche l'étiquette demandée si besoin.
    all_weeks_calc = week_ranges(date(2025, 9, 1), date(2026, 1, 4))
    # Remplace la dernière étiquette pour coller exactement à la demande
    if all_weeks_calc and all_weeks_calc[-1].endswith("04/01/2026"):
        all_weeks_calc[-1] = "29/12/2025 - 04/01/2025"

    # par défaut: 1ère semaine qui contient au moins 1 CM
    def first_week_with_data():
        for w in all_weeks_calc:
            for fac in FACULTIES:
                if w in DATA.get(fac, {}) and any(DATA[fac][w].values()):
                    return w
        return all_weeks_calc[0]

    st.caption("Choisis la semaine")
    selected_week = st.selectbox("Semaine", all_weeks_calc, index=all_weeks_calc.index(first_week_with_data()))

    st.divider()

    # Entêtes
    c0, c1, c2, c3 = st.columns([2.1, 1, 1, 1])
    c0.markdown('<div class="table-head">Matière</div>', unsafe_allow_html=True)
    for fac, c in zip(FACULTIES, [c1, c2, c3]):
        c.markdown(f'<div class="table-head fac-head">{fac}</div>', unsafe_allow_html=True)

    # Lignes
    subjects = SUBJECTS
    if not subjects:
        st.info("Aucune matière (CM) détectée pour le moment.")
    else:
        for subj in subjects:
            r0, r1, r2, r3 = st.columns([2.1, 1, 1, 1], gap="large")
            with r0:
                st.markdown(f'<div class="rowline subject">{subj}</div>', unsafe_allow_html=True)

            def render_cell(col, fac):
                items = DATA.get(fac, {}).get(selected_week, {}).get(subj, [])
                with col:
                    st.markdown('<div class="rowline">', unsafe_allow_html=True)
                    if not items:
                        st.markdown('<span class="muted small">—</span>', unsafe_allow_html=True)
                    else:
                        for it in items:
                            ck = k(fac, subj, selected_week, it.get("id") or it.get("title"))
                            checked = st.session_state.get(ck, False)
                            st.markdown('<div class="cell">', unsafe_allow_html=True)
                            st.markdown(f"**{it['title']}**")
                            st.markdown(f'<span class="mini">{it["date"]}</span>', unsafe_allow_html=True)
                            # checkbox persistante
                            new_val = st.checkbox("Fiche faite", value=checked, key=ck)
                            if new_val != checked:
                                st.session_state[ck] = new_val
                            st.markdown('</div>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)

            render_cell(r1, "UPC")
            render_cell(r2, "UPS")
            render_cell(r3, "UVSQ")

    st.markdown('</div>', unsafe_allow_html=True)  # fin glass

# ==== COLONNE BOURSIERS (1/4) ====
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
            <div class="cardish" style="margin-bottom:10px;">
              <div style="font-weight:600">{title}</div>
              <div class="mini"><a href="{url}" target="_blank">{url}</a></div>
              <div class="mini">{login}</div>
              <div class="mini">{pwd}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)

# Sauvegarde localStorage (après interactions)
flush_to_localstorage()
