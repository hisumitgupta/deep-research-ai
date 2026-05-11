import streamlit as st
import time
import re
import markdown
from datetime import datetime
from core.env_check import check_env_keys, format_missing_env_message
from core.rate_limiter import (
    init_rate_limit_db,
    check_rate_limit,
    get_or_create_visitor_id,
    get_user_stats
)
from core.feedback import save_user_feedback
from core.research_jobs import (
    cancel_research_job,
    get_research_job,
    start_research_job,
)
from agents.intent import classify_intent


st.set_page_config(
    page_title="Deep Research AI",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

user = None


# ── SESSION STATE ─────────────────────────────────────────────────
for k, v in {
    "result": None, "running": False,
    "query": "", "progress": [],
    "start_time": None, "error": None,
    "current_job_id": "", "loading_message": "",
    "query_prefill": "",
    "top_notice": "",
    "feedback_notice": "",
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

if st.session_state.query_prefill:
    st.session_state.query_input = st.session_state.query_prefill
    st.session_state.query = st.session_state.query_prefill
    st.session_state.query_prefill = ""
elif "query_input" not in st.session_state:
    st.session_state.query_input = st.session_state.query

init_rate_limit_db()

user_id = get_or_create_visitor_id()

active_job = get_research_job(st.session_state.get("current_job_id"))
if active_job:
    job_status = active_job.get("status")
    st.session_state.progress = active_job.get("progress", [])

    if job_status in {"running", "cancel_requested"}:
        elapsed = time.time() - active_job.get("created_at", time.time())
        st.session_state.running = True
        st.session_state.loading_message = (
            "Stopping after the current step..."
            if job_status == "cancel_requested"
            else (
                "This is taking longer than usual. Try a more specific question if it does not finish soon."
                if elapsed > 90
                else "Research agents are working..."
            )
        )

    elif job_status == "completed":
        st.session_state.result = active_job.get("result")
        st.session_state.running = False
        st.session_state.loading_message = ""
        st.session_state.current_job_id = ""
        st.session_state.progress = active_job.get("progress", [])

    elif job_status in {"failed", "cancelled"}:
        st.session_state.running = False
        st.session_state.error = active_job.get("error")
        st.session_state.loading_message = ""
        st.session_state.current_job_id = ""

elif st.session_state.get("running") and st.session_state.get("current_job_id"):
    st.session_state.running = False
    st.session_state.current_job_id = ""
    st.session_state.loading_message = ""
    st.session_state.error = (
        "The previous research run was interrupted. Please try again with a fresh search."
    )



# ── CSS ──────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&family=JetBrains+Mono:wght@400;500&family=Lora:ital,wght@0,400;0,600;1,400&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, [data-testid="stAppViewContainer"] {
    background:
        radial-gradient(circle at 18% 0%, rgba(14,165,233,0.08), transparent 28%),
        linear-gradient(180deg, #090b10 0%, #0d1117 42%, #0a0d12 100%);
    color: #e2e8f0;
    font-family: 'Inter', sans-serif;
}

#MainMenu, footer, header,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"] { display: none !important; }

.block-container { padding: 1.25rem 2rem 2rem !important; max-width: 1420px !important; }

/* ── NAV ── */
.topnav {
    display: flex; align-items: center; justify-content: space-between;
    padding: 0.35rem 0 0.85rem; border-bottom: 1px solid rgba(148,163,184,0.12);
    margin-bottom: 1rem; gap: 1rem;
}
.nav-logo { font-size: 1rem; font-weight: 700; color: #fff; letter-spacing: -0.02em; }
.nav-logo span { color: #38bdf8; }
.nav-tag {
    font-family: 'JetBrains Mono', monospace; font-size: 0.6rem;
    color: #a7f3d0; border: 1px solid rgba(52,211,153,0.22);
    border-radius: 999px; padding: 0.2rem 0.65rem; letter-spacing: 0.06em;
    background: rgba(16,185,129,0.06);
    text-align: right;
}

.hero-shell {
    display: grid;
    grid-template-columns: minmax(0, 1.35fr) minmax(280px, 0.65fr);
    gap: 1.25rem;
    align-items: stretch;
    margin: 0.25rem 0 1rem;
}
.hero-main, .hero-side {
    border: 1px solid rgba(148,163,184,0.13);
    background: rgba(15,23,42,0.72);
    border-radius: 12px;
    padding: 1.15rem;
    box-shadow: 0 18px 48px rgba(0,0,0,0.2);
}
.hero-main { display: flex; flex-direction: column; justify-content: space-between; min-height: 190px; }
.hero-eyebrow {
    font-family:'JetBrains Mono',monospace; font-size:0.62rem;
    letter-spacing:0.12em; text-transform:uppercase; color:#22d3ee; margin-bottom:0.55rem;
}
.hero-title {
    font-size: clamp(1.8rem, 3vw, 3rem);
    line-height: 1.05; font-weight: 750; letter-spacing: 0; color: #f8fafc; max-width: 780px;
}
.hero-copy {
    color:#94a3b8; font-size:0.95rem; line-height:1.65; max-width: 760px; margin-top:0.8rem;
}
.hero-stats { display:grid; grid-template-columns:repeat(3, minmax(0,1fr)); gap:0.55rem; margin-top:1rem; }
.hero-stat {
    border:1px solid rgba(148,163,184,0.12); background:rgba(2,6,23,0.35);
    border-radius:8px; padding:0.7rem;
}
.hero-stat strong { display:block; color:#f8fafc; font-size:1rem; }
.hero-stat span { display:block; color:#64748b; font-size:0.72rem; margin-top:0.15rem; }
.hero-side { display:flex; flex-direction:column; justify-content:space-between; }
.status-line { color:#cbd5e1; font-size:0.86rem; line-height:1.55; }
.status-chip {
    display:inline-flex; margin-top:0.7rem; font-family:'JetBrains Mono',monospace; font-size:0.62rem;
    color:#fbbf24; border:1px solid rgba(251,191,36,0.2); background:rgba(251,191,36,0.06);
    border-radius:999px; padding:0.25rem 0.55rem;
}

/* ── SEARCH PANEL ── */
.search-panel {
    background: rgba(15,23,42,0.8); border: 1px solid rgba(148,163,184,0.14);
    border-radius: 12px; padding: 1.1rem; margin-bottom: 0.875rem;
    box-shadow: 0 18px 48px rgba(0,0,0,0.18);
}
.workspace-label {
    font-family:'JetBrains Mono',monospace; font-size:0.6rem; letter-spacing:0.12em;
    text-transform:uppercase; color:#38bdf8; margin-bottom:0.35rem;
}
.search-title { color:#f8fafc; font-size:1rem; font-weight:700; margin-bottom:0.25rem; }
.search-hint { color:#64748b; font-size:0.78rem; line-height:1.55; margin-bottom:0.8rem; }
.search-input-label {
    display:flex; align-items:center; justify-content:space-between; gap:0.75rem;
    margin:0.75rem 0 0.35rem;
}
.search-input-label strong { color:#e2e8f0; font-size:0.86rem; }
.search-input-label span {
    color:#64748b; font-family:'JetBrains Mono',monospace; font-size:0.58rem;
    letter-spacing:0.08em; text-transform:uppercase;
}
.search-action-note { color:#94a3b8; font-size:0.74rem; line-height:1.5; margin:0.45rem 0 0.7rem; }
[data-testid="stTextArea"] textarea {
    background: linear-gradient(180deg,#f8fafc,#e2e8f0) !important;
    border: 2px solid rgba(34,211,238,0.55) !important;
    border-radius: 12px !important; color: #0f172a !important;
    font-family: 'Inter', sans-serif !important; font-size: 0.95rem !important;
    padding: 0.9rem !important; transition: border-color 0.15s, box-shadow 0.15s !important;
    resize: none !important; line-height: 1.6 !important;
    box-shadow: 0 12px 34px rgba(14,165,233,0.16) !important;
    caret-color: #0f766e !important;
    cursor: text !important;
}
[data-testid="stTextArea"] textarea::placeholder { color:#64748b !important; opacity:1 !important; }
[data-testid="stTextArea"] textarea:focus {
    border-color: rgba(20,184,166,0.95) !important;
    background: #ffffff !important;
    box-shadow: 0 0 0 4px rgba(45,212,191,0.22), 0 18px 46px rgba(14,165,233,0.28) !important;
    outline: none !important;
}
[data-testid="stTextArea"] label { display: none !important; }

/* ── BUTTONS ── */
[data-testid="stButton"] > button {
    border-radius: 8px !important; font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important; font-size: 0.82rem !important;
    padding: 0.55rem 1rem !important; transition: all 0.15s !important;
    width: 100% !important; border: none !important;
}
[data-testid="stButton"]:first-child > button {
    background: linear-gradient(135deg,#0284c7,#0f766e) !important; color:#fff !important;
}
[data-testid="stButton"]:first-child > button:hover {
    box-shadow: 0 4px 18px rgba(14,165,233,0.3) !important;
    transform: translateY(-1px) !important;
}
[data-testid="stButton"]:not(:first-child) > button {
    background: rgba(255,255,255,0.04) !important; color: #64748b !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
}
[data-testid="stButton"]:not(:first-child) > button:hover {
    background: rgba(255,255,255,0.07) !important; color: #e2e8f0 !important;
}

/* ── STEPS ── */
.steps-card {
    background: #13131a; border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px; padding: 0.875rem 1rem; margin-bottom: 0.875rem;
}
.steps-head {
    font-family: 'JetBrains Mono', monospace; font-size: 0.6rem;
    letter-spacing: 0.12em; text-transform: uppercase; color: #334155;
    margin-bottom: 0.6rem;
}
.step-row { display:flex; align-items:center; gap:0.6rem; padding:0.3rem 0; }
.step-dot { width:6px; height:6px; border-radius:50%; flex-shrink:0; }
.s-done   { background:#34d399; }
.s-run    { background:#818cf8; animation:pulse 1s infinite; }
.s-wait   { background:#1e2535; border:1px solid #2a3547; }
@keyframes pulse { 0%,100%{opacity:1}50%{opacity:0.3} }
.step-name { font-size:0.78rem; font-weight:500; }
.step-info { font-size:0.7rem; color:#334155; margin-left:auto; }

/* ── PILLS ── */
.pill {
    display:inline-block; font-family:'JetBrains Mono',monospace;
    font-size:0.6rem; font-weight:500; padding:0.15rem 0.5rem;
    border-radius:100px; border:1px solid; text-transform:uppercase; letter-spacing:0.05em;
}
.p-web  {color:#60a5fa;border-color:rgba(96,165,250,.25);background:rgba(96,165,250,.06);}
.p-news {color:#fbbf24;border-color:rgba(251,191,36,.25);background:rgba(251,191,36,.06);}
.p-paper{color:#34d399;border-color:rgba(52,211,153,.25);background:rgba(52,211,153,.06);}
.p-yt   {color:#f87171;border-color:rgba(248,113,113,.25);background:rgba(248,113,113,.06);}
.p-gh   {color:#a78bfa;border-color:rgba(167,139,250,.25);background:rgba(167,139,250,.06);}

/* ── METRIC CARDS ── */
.metric-row { display:grid; grid-template-columns:repeat(4,1fr); gap:0.6rem; margin-bottom:1rem; }
.metric-card {
    background:#13131a; border:1px solid rgba(255,255,255,0.06);
    border-radius:10px; padding:0.75rem; text-align:center;
}
.metric-val { font-size:1.5rem; font-weight:700; color:#818cf8; line-height:1; }
.metric-lbl {
    font-family:'JetBrains Mono',monospace; font-size:0.55rem;
    letter-spacing:0.1em; text-transform:uppercase; color:#334155; margin-top:0.25rem;
}

/* ── TABS ── */
[data-testid="stTabs"] button[role="tab"] {
    font-family:'JetBrains Mono',monospace !important; font-size:0.65rem !important;
    letter-spacing:0.08em !important; text-transform:uppercase !important;
    color:#334155 !important; padding:0.5rem 1rem !important;
}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
    color:#818cf8 !important; border-bottom:2px solid #5d5fef !important;
}

/* ══════════════════════════════════════════════
   REPORT RENDERER — The main upgrade
   ══════════════════════════════════════════════ */
.report-wrap {
    background: #13131a;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px;
    padding: 2rem 2.25rem;
    max-height: 70vh;
    overflow-y: auto;
    scroll-behavior: smooth;
}

/* Scrollbar */
.report-wrap::-webkit-scrollbar { width: 5px; }
.report-wrap::-webkit-scrollbar-track { background: transparent; }
.report-wrap::-webkit-scrollbar-thumb { background: rgba(129,140,248,0.25); border-radius:3px; }

/* H1 — Main report title */
.report-wrap h1 {
    font-family: 'Lora', Georgia, serif;
    font-size: 1.6rem;
    font-weight: 600;
    color: #f1f5f9;
    line-height: 1.3;
    margin: 0 0 0.5rem 0;
    padding-bottom: 0.75rem;
    border-bottom: 1px solid rgba(255,255,255,0.07);
    letter-spacing: -0.01em;
}

/* H2 — Section headings */
.report-wrap h2 {
    font-family: 'Inter', sans-serif;
    font-size: 1.05rem;
    font-weight: 700;
    color: #e2e8f0;
    margin: 2rem 0 0.6rem 0;
    padding-left: 0.75rem;
    border-left: 3px solid #5d5fef;
    letter-spacing: -0.01em;
}

/* H3 — Sub-section headings */
.report-wrap h3 {
    font-family: 'Inter', sans-serif;
    font-size: 0.92rem;
    font-weight: 600;
    color: #94a3b8;
    margin: 1.25rem 0 0.4rem 0;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-size: 0.78rem;
}

/* H4 */
.report-wrap h4 {
    font-family: 'Inter', sans-serif;
    font-size: 0.875rem;
    font-weight: 600;
    color: #cbd5e1;
    margin: 1rem 0 0.3rem 0;
}

/* Paragraphs */
.report-wrap p {
    font-family: 'Inter', sans-serif;
    font-size: 0.9rem;
    line-height: 1.85;
    color: #94a3b8;
    margin-bottom: 0.875rem;
}

/* Bold text inside paragraphs */
.report-wrap strong {
    color: #cbd5e1;
    font-weight: 600;
}

/* Italic */
.report-wrap em {
    font-family: 'Lora', Georgia, serif;
    font-style: italic;
    color: #a78bfa;
}

/* ── BULLET LISTS ── */
.report-wrap ul {
    margin: 0.5rem 0 1rem 0;
    padding-left: 0;
    list-style: none;
}
.report-wrap ul li {
    font-size: 0.875rem;
    line-height: 1.75;
    color: #94a3b8;
    padding: 0.2rem 0 0.2rem 1.25rem;
    position: relative;
}
.report-wrap ul li::before {
    content: '';
    position: absolute;
    left: 0.35rem;
    top: 0.65rem;
    width: 5px; height: 5px;
    border-radius: 50%;
    background: #5d5fef;
}

/* ── NUMBERED LISTS ── */
.report-wrap ol {
    margin: 0.5rem 0 1rem 0;
    padding-left: 1.5rem;
    counter-reset: list-counter;
    list-style: none;
}
.report-wrap ol li {
    font-size: 0.875rem;
    line-height: 1.75;
    color: #94a3b8;
    padding: 0.15rem 0 0.15rem 0.5rem;
    counter-increment: list-counter;
    position: relative;
}
.report-wrap ol li::before {
    content: counter(list-counter);
    position: absolute;
    left: -1.5rem;
    top: 0.18rem;
    width: 1.1rem; height: 1.1rem;
    background: rgba(93,95,239,0.15);
    border: 1px solid rgba(93,95,239,0.3);
    border-radius: 50%;
    color: #818cf8;
    font-size: 0.62rem;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
    display: flex; align-items: center; justify-content: center;
}

/* ── TABLES ── */
.report-wrap table {
    width: 100%;
    border-collapse: collapse;
    margin: 1.25rem 0;
    font-size: 0.82rem;
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid rgba(255,255,255,0.06);
}
.report-wrap thead {
    background: rgba(93,95,239,0.12);
    border-bottom: 1px solid rgba(93,95,239,0.25);
}
.report-wrap thead th {
    padding: 0.7rem 1rem;
    text-align: left;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    font-weight: 500;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #818cf8;
    white-space: nowrap;
}
.report-wrap tbody tr {
    border-bottom: 1px solid rgba(255,255,255,0.04);
    transition: background 0.1s;
}
.report-wrap tbody tr:hover { background: rgba(255,255,255,0.025); }
.report-wrap tbody tr:last-child { border-bottom: none; }
.report-wrap tbody td {
    padding: 0.6rem 1rem;
    color: #94a3b8;
    line-height: 1.5;
    vertical-align: top;
}
.report-wrap tbody td:first-child { color: #cbd5e1; font-weight: 500; }

/* ── BLOCKQUOTES ── */
.report-wrap blockquote {
    margin: 1rem 0;
    padding: 0.875rem 1.25rem;
    border-left: 3px solid #a78bfa;
    background: rgba(167,139,250,0.06);
    border-radius: 0 8px 8px 0;
    font-family: 'Lora', Georgia, serif;
    font-style: italic;
    color: #c4b5fd;
    font-size: 0.9rem;
    line-height: 1.7;
}

/* ── CODE ── */
.report-wrap code {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 4px;
    padding: 0.1rem 0.4rem;
    color: #34d399;
}
.report-wrap pre {
    background: #0c0c10;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 8px;
    padding: 1rem;
    overflow-x: auto;
    margin: 1rem 0;
}
.report-wrap pre code {
    background: transparent;
    border: none;
    padding: 0;
    font-size: 0.8rem;
    color: #e2e8f0;
}

/* ── HORIZONTAL RULE ── */
.report-wrap hr {
    border: none;
    height: 1px;
    background: linear-gradient(90deg,transparent,rgba(255,255,255,0.08),transparent);
    margin: 1.5rem 0;
}

/* ── LINKS ── */
.report-wrap a {
    color: #818cf8;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    background: rgba(129,140,248,0.08);
    border: 1px solid rgba(129,140,248,0.2);
    border-radius: 4px;
    padding: 0.08rem 0.4rem;
    text-decoration: none;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 200px;
    display: inline-block;
    vertical-align: middle;
    transition: background 0.15s;
}
.report-wrap a:hover { background: rgba(129,140,248,0.15); color: #a5b4fc; }

/* ── SOURCE ITEMS ── */
.src-item {
    display:flex; align-items:flex-start; gap:0.65rem;
    padding:0.6rem 0.875rem; border-radius:8px;
    border:1px solid rgba(255,255,255,0.05); background:#13131a;
    margin-bottom:0.35rem; transition:border-color 0.15s;
}
.src-item:hover { border-color:rgba(129,140,248,0.2); }
.src-title { font-size:0.8rem; color:#c7d2fe; margin-bottom:0.1rem; font-weight:500; }
.src-url   { font-size:0.67rem; color:#1e2d3d; font-family:'JetBrains Mono',monospace; }

/* ── FEEDBACK ── */
.feedback-box {
    background:rgba(251,191,36,0.04);
    border:1px solid rgba(251,191,36,0.1);
    border-radius:12px; padding:1.25rem;
    font-size:0.85rem; color:#94a3b8; line-height:1.8;
}
.feedback-box strong { color:#fbbf24; }

.user-feedback-callout {
    margin: 0.85rem 0 1rem 0;
    padding: 1rem 1.15rem;
    border: 1px solid rgba(34,211,238,0.18);
    border-radius: 12px;
    background:
        linear-gradient(135deg, rgba(34,211,238,0.08), rgba(20,184,166,0.04)),
        rgba(15,23,42,0.72);
}
.user-feedback-title {
    font-size: 1rem;
    font-weight: 800;
    color: #f8fafc;
    margin-bottom: 0.25rem;
}
.user-feedback-copy {
    font-size: 0.82rem;
    line-height: 1.6;
    color: #94a3b8;
}
.user-feedback-copy a {
    color: #67e8f9;
    text-decoration: none;
    font-weight: 700;
}
.user-feedback-copy a:hover { text-decoration: underline; }
.mobile-feedback-callout { display:none; }
.feedback-label {
    color: #e2e8f0;
    font-size: 0.82rem;
    font-weight: 700;
    margin: 0.8rem 0 0.3rem;
}
.feedback-helper {
    color: #64748b;
    font-size: 0.74rem;
    margin-top: -0.2rem;
    margin-bottom: 0.3rem;
}
.feedback-stars {
    color: #fbbf24;
    font-size: 1.35rem;
    letter-spacing: 0.08rem;
    margin: 0.15rem 0 0.55rem;
}
.feedback-stars span {
    color: #94a3b8;
    font-size: 0.8rem;
    letter-spacing: 0;
    margin-left: 0.5rem;
}

/* ── SUBQ ── */
.subq {
    padding:0.4rem 0.75rem;
    border-left:2px solid rgba(129,140,248,0.3);
    background:rgba(93,95,239,0.04);
    border-radius:0 6px 6px 0; margin-bottom:0.35rem;
    font-size:0.8rem; color:#64748b;
}

/* ── SAVE BANNER ── */
.save-banner {
    display:flex; align-items:center; gap:0.5rem;
    background:rgba(52,211,153,0.05); border:1px solid rgba(52,211,153,0.15);
    border-radius:8px; padding:0.5rem 0.875rem;
    font-family:'JetBrains Mono',monospace; font-size:0.68rem;
    color:#34d399; margin-top:0.75rem;
}

/* ── EMPTY STATE ── */
.empty-state { text-align:center; padding:4rem 1rem; color:#1e2d3d; }
.empty-icon  { font-size:2.5rem; margin-bottom:0.75rem; filter:grayscale(0.3); }
.empty-text  { font-size:0.875rem; line-height:1.8; }

/* ── DOWNLOAD BUTTON ── */
[data-testid="stDownloadButton"] button {
    background: rgba(129,140,248,0.1) !important;
    color: #818cf8 !important;
    border: 1px solid rgba(129,140,248,0.2) !important;
    border-radius: 8px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.72rem !important;
    font-weight: 500 !important;
    padding: 0.4rem 0.875rem !important;
    width: auto !important;
    transition: all 0.15s !important;
}
[data-testid="stDownloadButton"] button:hover {
    background: rgba(129,140,248,0.18) !important;
    border-color: rgba(129,140,248,0.4) !important;
}

/* ── EXPANDER ── */
[data-testid="stExpander"] {
    background: #13131a !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 10px !important;
}
[data-testid="stExpander"] summary {
    font-size: 0.8rem !important;
    color: #64748b !important;
    font-family: 'Inter', sans-serif !important;
}

.steps-card, .metric-card, [data-testid="stExpander"] {
    background: rgba(15,23,42,0.76) !important;
    border-color: rgba(148,163,184,0.12) !important;
}
.metric-val { color:#38bdf8; }
.report-wrap {
    background: rgba(15,23,42,0.82);
    border-color: rgba(148,163,184,0.14);
    border-radius: 12px;
}
.src-item {
    border-color: rgba(148,163,184,0.1);
    background: rgba(15,23,42,0.76);
}
.empty-state {
    text-align:left;
    padding:2rem;
    color:#64748b;
    border:1px solid rgba(148,163,184,0.12);
    background:rgba(15,23,42,0.72);
    border-radius:12px;
    min-height:360px;
    display:flex;
    flex-direction:column;
    justify-content:center;
}
.empty-icon  {
    font-family:'JetBrains Mono',monospace;
    color:#38bdf8;
    font-size:0.72rem;
    letter-spacing:0.12em;
    text-transform:uppercase;
    margin-bottom:0.75rem;
    filter:none;
}
.empty-text  { font-size:0.95rem; line-height:1.8; color:#94a3b8; max-width:620px; }
.empty-title { color:#f8fafc; font-size:1.55rem; line-height:1.2; font-weight:750; margin-bottom:0.6rem; }
.empty-grid {
    display:grid;
    grid-template-columns:repeat(2,minmax(0,1fr));
    gap:0.6rem;
    margin-top:1.2rem;
}
.empty-tile {
    border:1px solid rgba(148,163,184,0.11);
    background:rgba(2,6,23,0.28);
    border-radius:8px;
    padding:0.75rem;
}
.empty-tile strong { display:block; color:#cbd5e1; font-size:0.84rem; margin-bottom:0.2rem; }
.empty-tile span { display:block; color:#64748b; font-size:0.73rem; line-height:1.45; }
.loading-strip {
    border:1px solid rgba(56,189,248,0.16);
    background:rgba(8,47,73,0.2);
    border-radius:10px;
    padding:0.85rem;
    margin:0.75rem 0;
}
.loading-row { display:flex; align-items:center; gap:0.7rem; color:#cbd5e1; font-size:0.82rem; }
.loader-dot {
    width:10px; height:10px; border-radius:999px;
    background:#22d3ee;
    box-shadow:0 0 0 0 rgba(34,211,238,0.45);
    animation:loadingPulse 1.2s infinite;
    flex-shrink:0;
}
.loading-bar {
    height:5px;
    border-radius:999px;
    background:rgba(148,163,184,0.12);
    overflow:hidden;
    margin-top:0.7rem;
}
.loading-bar span {
    display:block;
    width:45%;
    height:100%;
    border-radius:999px;
    background:linear-gradient(90deg,#22d3ee,#34d399);
    animation:loadingSlide 1.35s infinite ease-in-out;
}
@keyframes loadingPulse {
    0%,100% { box-shadow:0 0 0 0 rgba(34,211,238,0.35); opacity:1; }
    50% { box-shadow:0 0 0 7px rgba(34,211,238,0); opacity:0.65; }
}
@keyframes loadingSlide {
    0% { transform:translateX(-100%); }
    100% { transform:translateX(230%); }
}
.source-grid {
    display:grid;
    grid-template-columns:repeat(2,minmax(0,1fr));
    gap:0.45rem;
    margin-top:0.45rem;
}
.source-card {
    border:1px solid rgba(148,163,184,0.1);
    background:rgba(15,23,42,0.55);
    border-radius:8px;
    padding:0.6rem;
    color:#64748b;
    font-size:0.72rem;
    line-height:1.45;
}
.source-card .pill { margin-bottom:0.35rem; }

@media (max-width: 920px) {
    .block-container { padding: 0.75rem !important; }
    .topnav { align-items:flex-start; flex-direction:column; }
    .nav-tag { text-align:left; }
    .hero-shell { grid-template-columns:1fr; margin-bottom:0.65rem; }
    .hero-stats, .metric-row, .empty-grid { grid-template-columns:1fr; }
    .source-section { display:none; }
    .hero-main { min-height:auto; padding:0.9rem; }
    .hero-title { font-size:1.45rem; line-height:1.15; }
    .hero-copy, .hero-side, .user-feedback-callout { display:none; }
    .mobile-feedback-callout {
        display:block;
        margin:0.65rem 0 0.75rem;
        padding:0.75rem 0.85rem;
        border:1px solid rgba(34,211,238,0.18);
        border-radius:10px;
        background:rgba(15,23,42,0.72);
    }
    .mobile-feedback-callout .user-feedback-title { font-size:0.86rem; }
    .mobile-feedback-callout .user-feedback-copy { font-size:0.74rem; line-height:1.45; }
    div[data-testid="stExpander"] { display:none; }
    .example-section { display:none; }
    .search-panel { padding:0.95rem; margin-bottom:0.75rem; }
    .report-wrap { max-height:none; padding:1.25rem; }
    .empty-state { min-height:auto; padding:1.25rem; }
}
</style>
""", unsafe_allow_html=True)


# ── MARKDOWN → HTML CONVERTER ─────────────────────────────────────
def _prepare_report_links(md_text: str) -> str:
    md_text = re.sub(
        r"\[Source:\s*(https?://[^\]\s]+)\]",
        r"[Source](\1)",
        md_text,
        flags=re.IGNORECASE,
    )

    def linkify_bare_url(match):
        url = match.group(0)
        trailing = ""

        while url and url[-1] in ".,;)":
            trailing = url[-1] + trailing
            url = url[:-1]

        return f"[{url}]({url}){trailing}"

    return re.sub(
        r"(?<!\()(?<!href=\")https?://[^\s<>\"]+",
        linkify_bare_url,
        md_text,
    )


def render_report(md_text: str) -> str:
    """
    Convert markdown report to styled HTML.
    Handles: headings, paragraphs, bold, italic, lists,
             tables, blockquotes, code, links, horizontal rules.
    """
    md_text = _prepare_report_links(md_text)

    try:
        import markdown as md_lib
        html = md_lib.markdown(
            md_text,
            extensions=["tables", "fenced_code", "nl2br", "sane_lists"]
        )
    except ImportError:
        # Fallback: basic manual conversion
        html = md_text

        # H1-H4
        html = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)
        html = re.sub(r'^### (.+)$',  r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$',   r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$',    r'<h1>\1</h1>', html, flags=re.MULTILINE)

        # Bold & italic
        html = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', html)
        html = re.sub(r'\*\*(.+?)\*\*',     r'<strong>\1</strong>', html)
        html = re.sub(r'\*(.+?)\*',         r'<em>\1</em>', html)

        # Links
        html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank">\1</a>', html)

        # Bullet lists
        html = re.sub(r'^\s*[-*] (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        html = re.sub(r'(<li>.*</li>\n?)+', r'<ul>\g<0></ul>', html)

        # Horizontal rule
        html = re.sub(r'^---+$', '<hr>', html, flags=re.MULTILINE)

        # Paragraphs — wrap orphan lines
        lines = html.split('\n')
        result_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith('<'):
                result_lines.append(f'<p>{stripped}</p>')
            else:
                result_lines.append(line)
        html = '\n'.join(result_lines)

    # Shorten links: replace long URLs with domain names
    def shorten_link(m):
        href = m.group(1)
        text = m.group(2)
        try:
            from urllib.parse import urlparse
            parsed = urlparse(href)
            domain = parsed.netloc.replace('www.', '')
            parts  = [p for p in parsed.path.split('/') if p]
            short  = f"{domain}/{parts[0]}" if parts else domain
            display = short if len(text) > 40 or text == href else text
        except Exception:
            display = text[:35] + '…' if len(text) > 35 else text
        return f'<a href="{href}" target="_blank" title="{href}">{display}</a>'

    html = re.sub(r'<a href="([^"]+)"[^>]*>([^<]+)</a>', shorten_link, html)

    return html




# ── NAV ───────────────────────────────────────────────────────────
def render_user_feedback_form(user: dict | None, user_id: str | None) -> None:
    if st.session_state.feedback_notice:
        st.success(st.session_state.feedback_notice)
        st.session_state.feedback_notice = ""

    st.markdown("""
    <div class="user-feedback-callout">
        <div class="user-feedback-title">Help shape this research product</div>
        <div class="user-feedback-copy">
            Share what you liked, what felt confusing, and what would make this more useful for your startup research workflow.
            You can also email feedback directly at
            <a href="mailto:sumitgupta00716@gmail.com">sumitgupta00716@gmail.com</a>.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="mobile-feedback-callout">
        <div class="user-feedback-title">Feedback</div>
        <div class="user-feedback-copy">
            Help improve this product. Send feedback directly at
            <a href="mailto:sumitgupta00716@gmail.com">sumitgupta00716@gmail.com</a>.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="feedback-form-wrap">', unsafe_allow_html=True)
    with st.expander("Open quick feedback form", expanded=False):
        st.markdown('<div class="feedback-label">Overall experience</div>', unsafe_allow_html=True)
        rating_options = ["★", "★★", "★★★", "★★★★", "★★★★★"]
        rating_choice = st.radio(
            "Overall experience",
            rating_options,
            index=3,
            horizontal=True,
            key="fb_rating_stars",
            label_visibility="collapsed",
        )
        rating = len(rating_choice)
        st.markdown(
            f'<div class="feedback-stars">{"★" * rating}{"☆" * (5 - rating)}<span>{rating}/5</span></div>',
            unsafe_allow_html=True,
        )

        st.markdown('<div class="feedback-label">What did you like?</div>', unsafe_allow_html=True)
        st.markdown('<div class="feedback-helper">Example: source quality, report format, speed, UI, or startup usefulness.</div>', unsafe_allow_html=True)
        liked = st.text_area(
            "What did you like?",
            key="fb_liked",
            height=80,
            placeholder="The report was easy to scan and the sources felt useful...",
            label_visibility="collapsed",
        )

        st.markdown('<div class="feedback-label">What did not work well?</div>', unsafe_allow_html=True)
        st.markdown('<div class="feedback-helper">Tell us where the product felt slow, confusing, shallow, or wrong.</div>', unsafe_allow_html=True)
        disliked = st.text_area(
            "What did not work well?",
            key="fb_disliked",
            height=80,
            placeholder="The answer missed competitor details, or the UI was hard to understand...",
            label_visibility="collapsed",
        )

        st.markdown('<div class="feedback-label">What should we improve or add?</div>', unsafe_allow_html=True)
        improvement = st.text_area(
            "What should we improve or add?",
            key="fb_improvement",
            height=90,
            placeholder="Add report history, export options, better source filters, team workspace...",
            label_visibility="collapsed",
        )

        contact_ok = st.checkbox("You can contact me about this feedback", key="fb_contact_ok")
        st.markdown('<div class="feedback-label">Email</div>', unsafe_allow_html=True)
        feedback_email = st.text_input(
            "Email",
            value=user.get("email", "") if user else "",
            key="fb_email",
            placeholder="you@example.com",
            label_visibility="collapsed",
        )

        if st.button("Send feedback", key="send_feedback_btn", disabled=st.session_state.running):
            if not any([liked.strip(), disliked.strip(), improvement.strip()]):
                st.warning("Please write at least one feedback detail.")
            else:
                feedback_result = save_user_feedback(
                    user_id if user else None,
                    feedback_email,
                    rating,
                    liked,
                    disliked,
                    improvement,
                    contact_ok,
                )
                if feedback_result["success"]:
                    st.session_state.feedback_notice = "Thanks. Your feedback was saved."
                    st.rerun()
                else:
                    st.error(feedback_result["error"])
    st.markdown('</div>', unsafe_allow_html=True)


user_stats = get_user_stats(user_id) if user_id else {"runs_remaining": "Free"}
runs_left = user_stats["runs_remaining"]

nav_status = f"{runs_left} reports left in this 5-hour window"
hero_status = (
    "No account needed. You can generate up to 5 research reports every 5 hours from this browser."
)
hero_chip = f"Runs left: {runs_left}/5"

st.markdown(f"""
<div class="topnav">
    <div class="nav-logo">Deep<span>Research</span> AI</div>
    <div class="nav-tag">{nav_status}</div>
</div>
""", unsafe_allow_html=True)

if st.session_state.top_notice:
    st.warning(st.session_state.top_notice)



# ── TWO COLUMN LAYOUT ─────────────────────────────────────────────
st.markdown(f"""
<section class="hero-shell">
    <div class="hero-main">
        <div>
            <div class="hero-eyebrow">Multi-source intelligence workspace</div>
            <div class="hero-title">Ask one hard question. Get a sourced research brief.</div>
            <div class="hero-copy">
                Deep Research AI plans sub-questions, searches across web, news, papers,
                YouTube, and GitHub, then writes a structured report with source tracking.
            </div>
        </div>
        <div class="hero-stats">
            <div class="hero-stat"><strong>5</strong><span>research reports per 5 hours</span></div>
            <div class="hero-stat"><strong>11</strong><span>agent pipeline steps</span></div>
            <div class="hero-stat"><strong>5</strong><span>source families checked</span></div>
        </div>
    </div>
    <div class="hero-side">
        <div>
            <div class="hero-eyebrow">Current session</div>
            <div class="status-line">{hero_status}</div>
            <div class="status-chip">{hero_chip}</div>
        </div>
        <div class="status-line" style="font-size:0.78rem;color:#64748b;margin-top:1rem">
            Best for startup research, market maps, technical comparisons, policy scans,
            and product strategy questions.
        </div>
    </div>
</section>
""", unsafe_allow_html=True)

render_user_feedback_form(user, user_id)

left, right = st.columns([1, 2], gap="large")
stop_btn = False


# ════════════════════════════════════════
# LEFT — Search + Progress
# ════════════════════════════════════════
with left:

    st.markdown("""
    <div class="search-panel">
    <div class="workspace-label">Research brief</div>
    <div class="search-title">Ask a question that deserves sources.</div>
    <div class="search-hint">
        Use a specific market, product, technology, competitor, or policy question.
        Short greetings will be answered as chat without using your research limit.
    </div>
    <div class="search-input-label">
        <strong>Research question</strong>
        <span>Required</span>
    </div>
    """, unsafe_allow_html=True)

    query = st.text_area(
        "q",
        placeholder="Type your research question here. Example: Compare Dhan vs Zerodha for beginner investors in India.",
        height=130, key="query_input", label_visibility="collapsed"
    )

    st.markdown("""
    <div class="search-action-note">
        Write a clear research topic, then click Run research. Use Stop only when a report is already running.
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        run_btn   = st.button(
            "Run research" if not st.session_state.running else "Running...",
            disabled=st.session_state.running, key="run_btn",
            help="Enter a research question first."
        )
    with c2:
        clear_btn = st.button("Clear", key="clear_btn", disabled=st.session_state.running, help="Clear the current question and result.")
    with c3:
        stop_btn = st.button("Stop", key="stop_btn", disabled=not st.session_state.running, help="Stop the current research run.")

    st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.running:
        st.markdown(f"""
        <div class="loading-strip">
            <div class="loading-row">
                <span class="loader-dot"></span>
                <span>{st.session_state.get("loading_message") or "Research is running..."}</span>
            </div>
            <div class="loading-bar"><span></span></div>
        </div>
        """, unsafe_allow_html=True)

    # Example queries
    with st.expander("Try examples", expanded=False):
        examples = [
            "AI research agents market map for startups",
            "Best free stack for an AI SaaS MVP",
            "LangGraph vs CrewAI for production agents",
        ]
        for i, ex in enumerate(examples):
            if st.button(ex, key=f"ex_{i}", disabled=st.session_state.running):
                st.session_state.query = ex
                st.session_state.query_prefill = ex
                st.rerun()

    # Progress tracker
    if st.session_state.running:
        st.markdown('<div style="height:0.75rem"></div>', unsafe_allow_html=True)
        steps = [
            ("Planner",         "Sub-questions"),
            ("Research agents", "Web + news + papers + video + code"),
            ("Quality gate",    "Source check"),
            ("Synthesizer",     "Writing"),
            ("Critic",          "Scoring"),
            ("Publisher",       "Saving"),
        ]
        done = len(st.session_state.progress)
        is_running = st.session_state.running
        rows = ""
        for i, (name, info) in enumerate(steps):
            if i < done:
                dc, nc = "s-done", "#34d399"
            elif i == done and is_running:
                dc, nc = "s-run", "#818cf8"
            else:
                dc, nc = "s-wait", "#1e2535"
            rows += f"""<div class="step-row">
                <div class="step-dot {dc}"></div>
                <span class="step-name" style="color:{nc}">{name}</span>
                <span class="step-info">{info}</span>
            </div>"""

        st.markdown(f"""
        <div class="steps-card">
            <div class="steps-head">Pipeline Progress</div>
            {rows}
        </div>""", unsafe_allow_html=True)

    # Source legend
    st.markdown("""
    <div class="source-section" style="margin-top:0.25rem">
    <div style="font-family:'JetBrains Mono',monospace;font-size:0.58rem;letter-spacing:0.12em;text-transform:uppercase;color:#64748b;margin-bottom:0.4rem;">Sources searched</div>
    <div class="source-grid">
        <div class="source-card"><span class="pill p-web">Web</span><br>Tavily plus Exa search</div>
        <div class="source-card"><span class="pill p-news">News</span><br>Current news coverage</div>
        <div class="source-card"><span class="pill p-paper">Papers</span><br>ArXiv research papers</div>
        <div class="source-card"><span class="pill p-yt">YouTube</span><br>Video transcripts</div>
        <div class="source-card"><span class="pill p-gh">GitHub</span><br>Repos and READMEs</div>
    </div>
    </div>""", unsafe_allow_html=True)

# ════════════════════════════════════════
# RIGHT — Results
# ════════════════════════════════════════
with right:
    # ── EMPTY ─────────────────────────────────────────────────────
    if not st.session_state.result and not st.session_state.running:
        if st.session_state.error:
            st.error(f"❌ {st.session_state.error}")
            st.info("Check your .env API keys and make sure all pipeline files exist.")
        else:
            st.markdown("""
            <div class="empty-state">
                <div class="empty-icon">Research canvas</div>
                <div class="empty-title">Your evidence brief will appear here.</div>
                <div class="empty-text">
                    Start with a clear question. The pipeline will break it into sub-questions,
                    gather evidence, merge duplicate sources, write the report, and score the result.
                </div>
                <div class="empty-grid">
                    <div class="empty-tile"><strong>Plan</strong><span>Turns your query into focused research angles.</span></div>
                    <div class="empty-tile"><strong>Search</strong><span>Runs web, news, papers, YouTube, and GitHub in parallel.</span></div>
                    <div class="empty-tile"><strong>Synthesize</strong><span>Writes a readable brief instead of a raw link dump.</span></div>
                    <div class="empty-tile"><strong>Review</strong><span>Scores quality and explains weak spots.</span></div>
                </div>
            </div>""", unsafe_allow_html=True)

    # ── RUNNING ───────────────────────────────────────────────────
    elif st.session_state.running:
        running_message = st.session_state.get("loading_message") or "The agents are collecting sources and preparing your report."
        st.markdown(f"""
        <div class="empty-state">
            <div class="empty-icon">Pipeline running</div>
            <div class="empty-title">Building your research brief...</div>
            <div class="empty-text">
                {running_message}
                This can take a little time for broad questions.
                <div class="loading-strip">
                    <div class="loading-row">
                        <span class="loader-dot"></span>
                        <span>Use Stop to cancel after the current research step finishes.</span>
                    </div>
                    <div class="loading-bar"><span></span></div>
                </div>
                <div class="empty-grid">
                    <div class="empty-tile"><strong>Searching</strong><span>Web, news, papers, YouTube, GitHub.</span></div>
                    <div class="empty-tile"><strong>Checking</strong><span>Deduplication, quality score, critic feedback.</span></div>
                </div>
            </div>
        </div>""", unsafe_allow_html=True)

    # ── RESULTS ───────────────────────────────────────────────────
    elif st.session_state.result:
        result   = st.session_state.result
        elapsed  = round(time.time() - st.session_state.start_time, 1) if st.session_state.start_time else 0
        src_cnt  = result.get("source_count", 0)
        score    = result.get("score", 0)
        words    = len(result.get("report", "").split())
        sub_qs   = result.get("sub_questions", [])

        # Metrics
        st.markdown(f"""
        <div class="metric-row">
            <div class="metric-card">
                <div class="metric-val">{src_cnt}</div>
                <div class="metric-lbl">Sources</div>
            </div>
            <div class="metric-card">
                <div class="metric-val">{score}<span style="font-size:0.9rem;color:#334155">/10</span></div>
                <div class="metric-lbl">Quality</div>
            </div>
            <div class="metric-card">
                <div class="metric-val">{words}</div>
                <div class="metric-lbl">Words</div>
            </div>
            <div class="metric-card">
                <div class="metric-val">{elapsed}<span style="font-size:0.9rem;color:#334155">s</span></div>
                <div class="metric-lbl">Time</div>
            </div>
        </div>""", unsafe_allow_html=True)

        # Sub-questions
        if sub_qs:
            with st.expander(f"📋 Sub-questions investigated ({len(sub_qs)})", expanded=False):
                for q in sub_qs:
                    st.markdown(f'<div class="subq">↳ {q}</div>', unsafe_allow_html=True)

        # Tabs
        tab1, tab2, tab3 = st.tabs(["📄  Report", "🔗  Sources", "💬  Critic"])

        # ── REPORT TAB ────────────────────────────────────────────
        with tab1:
            report_md = result.get("report", "")
            if report_md:
                # Download row
                dc, _ = st.columns([1, 4])
                with dc:
                    safe = st.session_state.query[:20].replace(" ", "_")
                    st.download_button(
                        "⬇ Download .md", data=report_md,
                        file_name=f"research_{safe}_{datetime.now().strftime('%Y%m%d')}.md",
                        mime="text/markdown", key="dl_btn"
                    )

                # Render markdown to styled HTML
                report_html = render_report(report_md)
                st.markdown(
                    f'<div class="report-wrap">{report_html}</div>',
                    unsafe_allow_html=True
                )

            else:
                st.warning("No report was generated.")

        # ── SOURCES TAB ───────────────────────────────────────────
        with tab2:
            sources = result.get("all_sources", [])
            if sources:
                pill_map = {
                    "web":"p-web","news":"p-news",
                    "paper":"p-paper","youtube":"p-yt","github":"p-gh"
                }
                # Breakdown pills
                counts = {}
                for s in sources:
                    t = s.get("source_type","web")
                    counts[t] = counts.get(t,0) + 1
                pills = '<div style="display:flex;flex-wrap:wrap;gap:0.35rem;margin-bottom:0.75rem">'
                for stype, cnt in counts.items():
                    cls = pill_map.get(stype,"p-web")
                    pills += f'<span class="pill {cls}">{stype} &nbsp;{cnt}</span>'
                pills += '</div>'
                st.markdown(pills, unsafe_allow_html=True)

                for s in sources:
                    stype = s.get("source_type","web")
                    cls   = pill_map.get(stype,"p-web")
                    title = (s.get("title") or "Untitled")[:72]
                    url   = s.get("url","")
                    try:
                        from urllib.parse import urlparse
                        domain = urlparse(url).netloc.replace("www.","")
                    except Exception:
                        domain = url[:40]
                    st.markdown(f"""
                    <div class="src-item">
                        <span class="pill {cls}" style="margin-top:2px;flex-shrink:0">{stype}</span>
                        <div>
                            <div class="src-title">{title}</div>
                            <div class="src-url">{domain}</div>
                        </div>
                    </div>""", unsafe_allow_html=True)
            else:
                st.markdown('<p style="color:#334155;font-size:0.8rem;padding:0.75rem 0">No sources recorded.</p>', unsafe_allow_html=True)

        # ── CRITIC TAB ────────────────────────────────────────────
        with tab3:
            feedback = result.get("feedback","")
            if feedback:
                score_color = "#34d399" if score >= 8 else "#fbbf24" if score >= 6 else "#f87171"
                st.markdown(f"""
                <div style="display:inline-flex;align-items:center;gap:0.4rem;
                border:1px solid {score_color}30;border-radius:100px;
                padding:0.3rem 0.875rem;margin-bottom:0.75rem;
                background:{score_color}0d">
                    <span style="width:7px;height:7px;border-radius:50%;
                    background:{score_color};display:inline-block"></span>
                    <span style="font-family:'JetBrains Mono',monospace;
                    font-weight:600;color:{score_color};font-size:0.82rem">
                    Score: {score}/10</span>
                </div>""", unsafe_allow_html=True)

                # Render feedback with markdown too
                feedback_html = render_report(feedback)
                st.markdown(f'<div class="feedback-box">{feedback_html}</div>', unsafe_allow_html=True)
            else:
                st.markdown('<p style="color:#334155;font-size:0.8rem;padding:0.75rem 0">No critic feedback available.</p>', unsafe_allow_html=True)


# ── ACTIONS ───────────────────────────────────────────────────────
if stop_btn:
    current_job_id = st.session_state.get("current_job_id")
    if current_job_id and get_research_job(current_job_id):
        cancel_research_job(current_job_id)
        st.session_state.loading_message = "Stopping after the current step..."
        st.session_state.error = "Stop requested. Waiting for the current step to finish."
    else:
        st.session_state.running = False
        st.session_state.current_job_id = ""
        st.session_state.loading_message = ""
        st.session_state.error = "Research was already stopped. You can start a fresh search."
    st.rerun()

if clear_btn:
    cancel_research_job(st.session_state.get("current_job_id"))
    for k in ["result","running","query","query_input","query_prefill","progress","error","start_time","current_job_id","loading_message","top_notice"]:
        st.session_state[k] = None if k in ["result","error","start_time"] else ([] if k == "progress" else (False if k == "running" else ""))
    st.rerun()

if run_btn and not query.strip():
    st.session_state.top_notice = "Please type a research question first."
    st.rerun()

if run_btn and query.strip():
    st.session_state.result = None
    st.session_state.error = None
    st.session_state.top_notice = ""
    st.session_state.progress = []
    st.session_state.query = query.strip()
    st.session_state.loading_message = "Starting..."

    env_status = check_env_keys()

    if not env_status["ok"]:
        st.session_state.loading_message = "Checking configuration..."
        st.session_state.error = format_missing_env_message(env_status)
        st.rerun()

    st.session_state.loading_message = "Understanding your query..."
    intent = classify_intent(query.strip())

    if intent["intent"] == "chat":
        st.session_state.result = {
            "report": intent["reply"],
            "source_count": 0,
            "score": 0,
            "feedback": "",
            "all_sources": [],
            "sub_questions": [],
            "output_path": "",
        }
        st.session_state.running = False
        st.session_state.error = None
        st.session_state.query = query.strip()
        st.session_state.loading_message = ""
        st.rerun()

    limit_check = check_rate_limit(user_id)

    if not limit_check["allowed"]:
        st.session_state.top_notice = f"⏳ {limit_check['reason']}"
        st.rerun()
    else:
        st.session_state.current_job_id = start_research_job(query.strip(), user_id)
        st.session_state.running    = True
        st.session_state.result     = None
        st.session_state.error      = None
        st.session_state.progress   = []
        st.session_state.query      = query.strip()
        st.session_state.loading_message = "Research agents are starting..."
        st.session_state.start_time = time.time()
        st.rerun()



# ── PIPELINE EXECUTION ────────────────────────────────────────────
if st.session_state.running and st.session_state.get("current_job_id"):
    time.sleep(1)
    st.rerun()
