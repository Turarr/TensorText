import io
import json
import os
import zipfile
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

import pandas as pd
import streamlit as st

from sources import (
    search_openalex,
    get_paper_bibtex,
    analyze_citation_network,
    expand_academic_queries,
    parse_pdf_bytes,
    parse_bibtex_content,
    import_dois_list,
    extract_doi_from_text
)
from sessions import (
    list_saved_sessions,
    load_session_data,
    save_session_data,
    create_new_session_data,
    delete_session_data
)
from ai import (
    get_client,
    rerank,
    extract_card,
    chat_with_papers,
    generate_method_dataset_matrix,
    synthesize_connections
)
from export import (
    export_bibtex,
    export_csv,
    export_latex_document,
    export_gost,
    export_markdown_table,
    export_docx
)
from feedback import log_feedback, get_feedback_summary

# --- Streamlit Page Setup ---
st.set_page_config(
    page_title="TensorText — Исследовательское рабочее пространство",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Modern, High-End Academic Styling ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&family=Manrope:wght@600;700;800&display=swap');

html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
    font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
    background: #080c16;
    color: #edf3fc;
}

h1, h2, h3, h4 {
    font-family: 'Manrope', sans-serif;
    letter-spacing: -0.035em;
    color: #f8fbff;
}

code, pre, .mono {
    font-family: 'JetBrains Mono', monospace;
}

[data-testid="stSidebar"] {
    background: #0c1220;
    border-right: 1px solid #1a253a;
}

[data-testid="stAppViewContainer"] .main .block-container {
    max-width: 1260px;
    padding-top: 1.5rem;
    padding-bottom: 4rem;
}

/* Hero card with modern gradient and border glow */
.hero-box {
    background: linear-gradient(135deg, rgba(20, 26, 54, 0.85) 0%, rgba(16, 33, 53, 0.85) 50%, rgba(13, 38, 48, 0.85) 100%);
    border: 1px solid rgba(139, 122, 255, 0.25);
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.1);
    border-radius: 20px;
    padding: 26px 32px;
    margin-bottom: 24px;
    backdrop-filter: blur(12px);
}

/* Polished Card Surface */
.custom-card {
    background: #0e1628;
    border: 1px solid #1c2a44;
    border-radius: 14px;
    padding: 16px 20px;
    margin-bottom: 14px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
    transition: all 0.2s ease;
}
.custom-card:hover {
    border-color: rgba(139, 122, 255, 0.35);
    box-shadow: 0 6px 20px rgba(99, 102, 241, 0.15);
}

/* Badges */
.badge-doi {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 3px 9px;
    border-radius: 6px;
    font-size: 0.78rem;
    font-weight: 600;
    background: rgba(16, 185, 129, 0.12);
    color: #34d399;
    border: 1px solid rgba(52, 211, 153, 0.3);
    text-decoration: none;
}
.badge-doi:hover {
    background: rgba(16, 185, 129, 0.22);
    color: #6ee7b7;
}

.badge-citekey {
    display: inline-flex;
    align-items: center;
    padding: 3px 9px;
    border-radius: 6px;
    font-size: 0.78rem;
    font-weight: 600;
    font-family: 'JetBrains Mono', monospace;
    background: rgba(139, 92, 246, 0.15);
    color: #c084fc;
    border: 1px solid rgba(168, 85, 247, 0.3);
}

.badge-cited {
    display: inline-flex;
    align-items: center;
    padding: 3px 9px;
    border-radius: 6px;
    font-size: 0.78rem;
    font-weight: 600;
    background: rgba(249, 115, 22, 0.12);
    color: #fb923c;
    border: 1px solid rgba(249, 115, 22, 0.3);
}

.badge-source {
    display: inline-flex;
    align-items: center;
    padding: 3px 9px;
    border-radius: 6px;
    font-size: 0.78rem;
    font-weight: 500;
    background: #192338;
    color: #93a4c3;
    border: 1px solid #23314d;
}

/* Connection card */
.conn-card {
    background: #111a2f;
    border-left: 4px solid #8b5cf6;
    border-top: 1px solid #1c2742;
    border-right: 1px solid #1c2742;
    border-bottom: 1px solid #1c2742;
    padding: 14px 18px;
    border-radius: 0 12px 12px 0;
    margin-bottom: 10px;
}

/* Buttons */
.stButton>button {
    border-radius: 10px;
    font-weight: 600;
    letter-spacing: -0.01em;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}
.stButton>button[kind="primary"] {
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
    border: none;
    box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35);
}
.stButton>button[kind="primary"]:hover {
    box-shadow: 0 6px 20px rgba(99, 102, 241, 0.55);
    transform: translateY(-1px);
}
.stButton>button[kind="secondary"] {
    background: #131d33;
    border: 1px solid #243557;
    color: #e2e8f0;
}
.stButton>button[kind="secondary"]:hover {
    border-color: #8b5cf6;
    color: #c084fc;
}
.stDownloadButton>button {
    border-radius: 10px;
    font-weight: 600;
    background: #121c33;
    border: 1px solid #283a5e;
    transition: all 0.2s ease;
}
.stDownloadButton>button:hover {
    border-color: #8b7aff;
    color: #c8c0ff;
    box-shadow: 0 4px 14px rgba(139, 92, 246, 0.25);
}

/* Chat styles */
[data-testid="stChatMessage"] {
    border-radius: 16px;
    padding: 1rem 1.3rem;
    margin-bottom: 0.85rem;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}
[data-testid="stChatMessage"][data-testid="stChatMessageUser"] {
    background: #151d33;
    border: 1px solid #27375a;
}
[data-testid="stChatMessage"][data-testid="stChatMessageAssistant"] {
    background: #0f1628;
    border: 1px solid #253354;
    border-left: 3px solid #8b5cf6;
}

/* Inputs */
[data-testid="stTextInput"] input, [data-testid="stSelectbox"] select, [data-testid="stTextArea"] textarea, [data-testid="stChatInput"] textarea {
    border-radius: 10px;
    background-color: #0e1628;
    border: 1px solid #223252;
}
[data-testid="stTextInput"] input:focus, [data-testid="stChatInput"] textarea:focus {
    border-color: #8b5cf6;
    box-shadow: 0 0 0 2px rgba(139, 92, 246, 0.25);
}

/* Tabs */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    gap: 8px;
    background-color: transparent;
    border-bottom: 1px solid #1a2740;
    padding-bottom: 4px;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 600;
    color: #94a3b8;
    background-color: #0e1628;
    border: 1px solid #1c2a44;
}
[data-testid="stTabs"] [aria-selected="true"] {
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.25) 0%, rgba(139, 92, 246, 0.25) 100%) !important;
    border: 1px solid #8b5cf6 !important;
    color: #f1f5f9 !important;
}

/* Bordered container cards (Structure & Grid) */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: #0d1527;
    border: 1px solid #1c2a44 !important;
    border-radius: 14px !important;
    padding: 14px 18px !important;
    margin-bottom: 12px !important;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.22);
    transition: all 0.2s ease;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
    border-color: rgba(99, 102, 241, 0.35) !important;
}

/* 6-Field Grid cells inside PaperCards */
.grid-field-cell {
    background: #080d19;
    border: 1px solid #16233b;
    border-radius: 10px;
    padding: 10px 13px;
    margin-bottom: 8px;
    min-height: 100px;
    display: flex;
    flex-direction: column;
    box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.25);
    transition: all 0.2s ease;
}
.grid-field-cell:hover {
    border-color: rgba(99, 102, 241, 0.4);
    background: #0a1120;
}
.grid-field-title {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #818cf8;
    margin-bottom: 5px;
}
.grid-field-value {
    font-size: 0.88rem;
    line-height: 1.45;
}
.field-val-empty {
    color: #556885;
    font-style: italic;
}
.field-val-filled {
    color: #e2e8f0;
}

/* Abstract quote block */
.abstract-box {
    background: #080d1a;
    border-left: 3px solid #6366f1;
    border-radius: 0 8px 8px 0;
    padding: 10px 14px;
    font-size: 0.86rem;
    color: #cbd5e1;
    line-height: 1.5;
    margin-top: 6px;
}
</style>
""", unsafe_allow_html=True)


def render_field_cell(icon, title, value):
    val_str = str(value or "").strip()
    is_empty = not val_str or val_str.lower() in ("не указано", "none", "null", "none.")
    val_class = "field-val-empty" if is_empty else "field-val-filled"
    display_val = "не указано" if is_empty else val_str
    return f"""
    <div class="grid-field-cell">
        <div class="grid-field-title">{icon} {title}</div>
        <div class="grid-field-value {val_class}">{display_val}</div>
    </div>
    """


# --- Session State & Disk Persistence ---
def sync_current_session_to_disk():
    """Persists current working state to tensortext_data/sessions/<id>.json."""
    sid = st.session_state.get("current_session_id")
    if not sid:
        new_s = create_new_session_data()
        sid = new_s["id"]
        st.session_state.current_session_id = sid

    cur_title = st.session_state.get("current_session_title")
    if not cur_title or cur_title in ("Новое исследование", "Импортированное исследование", "Исследование"):
        if st.session_state.get("last_query"):
            cur_title = st.session_state.last_query[:50]
        else:
            cur_title = "Новое исследование"
        st.session_state.current_session_title = cur_title

    selected_ids = [
        p["id"] for p in st.session_state.get("papers", [])
        if st.session_state.get(f"check_{p['id']}", False)
    ]

    session_payload = {
        "id": sid,
        "title": cur_title,
        "search_query": st.session_state.get("last_query", ""),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "papers": st.session_state.get("papers", []),
        "selected_paper_ids": selected_ids,
        "cards": st.session_state.get("cards", {}),
        "card_ratings": st.session_state.get("card_ratings", {}),
        "chat_history": st.session_state.get("chat_history", []),
        "connections_summary": st.session_state.get("connections_summary", ""),
        "matrix_result": st.session_state.get("matrix_result", ""),
        "author_profile": st.session_state.get("author_profile", {})
    }
    save_session_data(session_payload)


if "api_key" not in st.session_state:
    st.session_state.api_key = os.getenv("GEMINI_API_KEY", "")

if "openalex_key" not in st.session_state:
    st.session_state.openalex_key = os.getenv("OPENALEX_API_KEY", "")

if "selected_model" not in st.session_state:
    st.session_state.selected_model = os.getenv("GEMINI_LLM_MODEL", "gemini-3.5-flash")

if any(str(st.session_state.selected_model).startswith(dep) for dep in ("gemini-2.5", "gemini-2.0", "gemini-1.5", "gemini-1.0")):
    st.session_state.selected_model = "gemini-3.5-flash"

# Initialize or load latest session from disk
if "current_session_id" not in st.session_state:
    saved = list_saved_sessions()
    if saved:
        first_session = load_session_data(saved[0]["id"])
        if first_session:
            st.session_state.current_session_id = first_session["id"]
            st.session_state.current_session_title = first_session["title"]
            st.session_state.last_query = first_session["search_query"]
            st.session_state.papers = first_session["papers"]
            st.session_state.cards = first_session["cards"]
            st.session_state.card_ratings = first_session["card_ratings"]
            st.session_state.chat_history = first_session["chat_history"]
            st.session_state.connections_summary = first_session["connections_summary"]
            st.session_state.matrix_result = first_session.get("matrix_result", "")
            st.session_state.author_profile = first_session.get("author_profile", {"name": "", "university": "", "field": ""})
            for p in first_session["papers"]:
                st.session_state[f"check_{p['id']}"] = p["id"] in first_session.get("selected_paper_ids", [])
    if "current_session_id" not in st.session_state:
        new_s = create_new_session_data()
        st.session_state.current_session_id = new_s["id"]
        st.session_state.current_session_title = new_s["title"]
        st.session_state.last_query = ""
        st.session_state.papers = []
        st.session_state.cards = {}
        st.session_state.card_ratings = {}
        st.session_state.chat_history = []
        st.session_state.connections_summary = ""
        st.session_state.matrix_result = ""
        st.session_state.author_profile = {"name": "", "university": "", "field": ""}

if "expanded_info" not in st.session_state:
    st.session_state.expanded_info = {}


# --- Sidebar ---
st.sidebar.markdown("<h2 style='text-align:center;color:#b9adff;margin-bottom:2px;'>🔬 TensorText</h2>", unsafe_allow_html=True)
st.sidebar.caption("<div style='text-align:center;color:#8095b8;margin-bottom:12px;'>Сравнительный синтез и научный диалог по проверенным DOI</div>", unsafe_allow_html=True)

# 1. СЕССИИ ИССЛЕДОВАНИЙ (Персистентность и переключение)
with st.sidebar.expander("🗂️ Сессии исследований", expanded=True):
    saved_sessions = list_saved_sessions()
    session_map = {}
    for s in saved_sessions:
        cnt_str = f"{s['papers_count']} ст." if s['papers_count'] else "пустая"
        chat_indicator = f" | 💬 {s['chat_count']}" if s.get("chat_count") else ""
        label = f"{s['title'][:24]} ({cnt_str}{chat_indicator})"
        session_map[s["id"]] = label

    cur_sid = st.session_state.get("current_session_id")
    if cur_sid and cur_sid not in session_map:
        cur_chat_cnt = len(st.session_state.get("chat_history", []))
        cur_chat_ind = f" | 💬 {cur_chat_cnt}" if cur_chat_cnt else ""
        session_map[cur_sid] = f"{st.session_state.get('current_session_title', 'Текущая')} ({len(st.session_state.get('papers', []))} ст.{cur_chat_ind})"

    session_keys = list(session_map.keys())
    if cur_sid in session_keys:
        def_idx = session_keys.index(cur_sid)
    else:
        def_idx = 0

    def handle_session_selection():
        chosen_sid = st.session_state.get("session_selector_key")
        if chosen_sid and chosen_sid != st.session_state.get("current_session_id"):
            sync_current_session_to_disk()
            loaded = load_session_data(chosen_sid)
            if loaded:
                st.session_state.current_session_id = loaded["id"]
                st.session_state.current_session_title = loaded["title"]
                st.session_state.last_query = loaded["search_query"]
                st.session_state.papers = loaded["papers"]
                st.session_state.cards = loaded["cards"]
                st.session_state.card_ratings = loaded["card_ratings"]
                st.session_state.chat_history = loaded["chat_history"]
                st.session_state.connections_summary = loaded["connections_summary"]
                st.session_state.matrix_result = loaded.get("matrix_result", "")
                if loaded.get("author_profile"):
                    st.session_state.author_profile = loaded["author_profile"]
                for p in loaded["papers"]:
                    st.session_state[f"check_{p['id']}"] = p["id"] in loaded.get("selected_paper_ids", [])

    st.selectbox(
        "Сохранённые темы:",
        options=session_keys,
        index=def_idx,
        format_func=lambda k: session_map.get(k, k),
        key="session_selector_key",
        on_change=handle_session_selection,
        help="Переключайтесь между разными исследованиями без потери данных"
    )

    s_col1, s_col2 = st.columns(2)
    if s_col1.button("➕ Новая", use_container_width=True, help="Создать чистое исследование"):
        sync_current_session_to_disk()
        new_s = create_new_session_data()
        save_session_data(new_s)
        st.session_state.current_session_id = new_s["id"]
        st.session_state.current_session_title = new_s["title"]
        st.session_state.last_query = ""
        st.session_state.papers = []
        st.session_state.cards = {}
        st.session_state.card_ratings = {}
        st.session_state.chat_history = []
        st.session_state.connections_summary = ""
        st.session_state.matrix_result = ""
        st.rerun()

    if s_col2.button("💾 Сохранить", use_container_width=True, help="Сохранить текущую сессию на диск"):
        sync_current_session_to_disk()
        st.toast("Сессия успешно сохранена на диск!", icon="💾")

    with st.expander("⚙️ Управление темой", expanded=False):
        new_name_val = st.text_input("Название исследования:", value=st.session_state.get("current_session_title", ""))
        if st.button("Применить переименование", use_container_width=True):
            if new_name_val.strip():
                st.session_state.current_session_title = new_name_val.strip()
                sync_current_session_to_disk()
                st.toast("Название обновлено!", icon="✏️")
                st.rerun()

        if len(session_keys) > 1:
            if st.button("🗑️ Удалить эту сессию", use_container_width=True, type="secondary"):
                del_id = st.session_state.get("current_session_id")
                delete_session_data(del_id)
                st.session_state.current_session_id = None
                st.toast("Сессия удалена!", icon="🗑️")
                st.rerun()

st.session_state.api_key = st.sidebar.text_input(
    "🔑 Gemini API key",
    type="password",
    value=st.session_state.api_key,
    placeholder="AIzaSy…",
    help="Используется для эмбеддингов, извлечения PaperCard и диалога в чате."
)

AVAILABLE_MODELS = {
    "gemini-3.5-flash": "⚡ Gemini 3.5 Flash (Рекомендуемая, 1M токенов)",
    "gemini-3.8-flash": "🚀 Gemini 3.8 Flash (Новейшая архитектура)",
    "gemini-3.5-flash-lite": "⚡ Gemini 3.5 Flash-Lite (Сверхбыстрая)",
    "gemini-4-argon": "🧠 Gemini 4 Argon (Глубокие научные рассуждения)",
}

cur_model_keys = list(AVAILABLE_MODELS.keys())
cur_idx = cur_model_keys.index(st.session_state.selected_model) if st.session_state.selected_model in cur_model_keys else 0

st.session_state.selected_model = st.sidebar.selectbox(
    "🤖 Модель Gemini",
    options=cur_model_keys,
    index=cur_idx,
    format_func=lambda k: AVAILABLE_MODELS[k],
    help="Используйте актуальную модель gemini-3.8-flash для быстрой и точной генерации без 404 ошибок."
)

st.session_state.openalex_key = st.sidebar.text_input(
    "🌐 OpenAlex API key (опционально)",
    type="password",
    value=st.session_state.openalex_key,
    placeholder="Бесплатный ключ OpenAlex",
    help="Рекомендуется для максимальной скорости и обхода лимитов OpenAlex."
)

with st.sidebar.expander("👤 Профиль автора (для LaTeX и ГОСТ)", expanded=False):
    p_name = st.text_input("Имя и фамилия", value=st.session_state.author_profile.get("name", ""))
    p_univ = st.text_input("Организация / ВУЗ", value=st.session_state.author_profile.get("university", ""))
    p_field = st.text_input("Направление / Кафедра", value=st.session_state.author_profile.get("field", ""))
    if st.button("Сохранить профиль", use_container_width=True):
        st.session_state.author_profile = {"name": p_name, "university": p_univ, "field": p_field}
        st.toast("Профиль автора сохранён!")

with st.sidebar.expander("📸 Автоматизация скриншотов (Playwright)", expanded=False):
    st.caption("Автоматический снимок всех экранов и аналитических вкладок для академического отчёта Assignment 5.")
    if st.button("📷 Сделать скриншоты всех вкладок", use_container_width=True):
        with st.spinner("Запуск Playwright Chromium и сохранение снимков..."):
            try:
                import subprocess
                subprocess.run(["python", "capture_all_screenshots.py"], check=True, timeout=45)
                st.success("Все 9 скриншотов успешно сохранены в папку screenshots/!")
            except Exception as e:
                st.info(f"Скриншоты также можно сделать одной командой в терминале: python capture_all_screenshots.py ({e})")

# Sidebar stats & feedback summary
fb_summary = get_feedback_summary()
if fb_summary["total"] > 0:
    st.sidebar.markdown("---")
    st.sidebar.markdown("**📈 Метрики доверия MVP**")
    st.sidebar.caption(
        f"Отзывов собрано: **{fb_summary['total']}** · Ср. доверие: **{fb_summary['avg_trust']}/5** · 👍 {fb_summary['thumbs_up']} / 👎 {fb_summary['thumbs_down']}"
    )


# ==============================================================================
# HERO HEADER & SEARCH SECTION
# ==============================================================================

st.markdown("""
<div class="hero-box">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
        <span style="font-size:1.8rem;">🔬</span>
        <h1 style="margin:0;font-size:2.2rem;font-weight:800;background:linear-gradient(135deg,#ffffff 0%,#c4b5fd 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">
            TensorText
        </h1>
        <span style="background:rgba(99,102,241,0.2);color:#a5b4fc;border:1px solid rgba(99,102,241,0.4);border-radius:6px;font-size:0.75rem;padding:2px 8px;font-weight:600;margin-left:8px;">
            AI Research Workspace
        </span>
    </div>
    <p style="margin:0;color:#c0d2ef;font-size:1.02rem;max-width:920px;line-height:1.5;">
        Интеллектуальное пространство для глубокого сравнительного анализа научных публикаций. Поиск по мировым академическим каталогам с автоматическим переводом в предметную терминологию, связями между авторами, диалогом в чате и компилируемым экспортом <b>LaTeX + BibTeX</b>.
    </p>
</div>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------------------
# 1. ФОРМИРОВАНИЕ КОРПУСА (Поиск / Загрузка PDF / BibTeX / Импорт DOI)
# ------------------------------------------------------------------------------
st.markdown("### 1️⃣ Источники корпуса публикаций")

tab_search, tab_upload, tab_dois = st.tabs([
    "🔍 Поиск в OpenAlex (по теме)",
    "📂 Загрузить свои PDF / BibTeX (.bib)",
    "🔗 Импорт по списку DOI"
])

with tab_search:
    with st.container(border=True):
        search_col1, search_col2, search_col3 = st.columns([4.2, 1.4, 1.2])

        query_input = search_col1.text_input(
            "Тема исследования (RU / KZ / EN)",
            value=st.session_state.last_query,
            placeholder="Например: data centers pollutes the nature / влияние ИИ на оценивание студентов..."
        )

        lang_choice = search_col2.selectbox(
            "Язык источников",
            [None, "ru", "en", "kk"],
            format_func=lambda x: "Все языки" if x is None else ("Русский (RU)" if x == "ru" else ("English (EN)" if x == "en" else "Қазақша (KZ)"))
        )

        count_choice = search_col3.selectbox("Количество", [15, 20, 30, 40], index=2)

        btn_search = st.button("🔍 Найти и сопоставить публикации", type="primary", use_container_width=True)

    if btn_search:
        if not query_input.strip():
            st.warning("Пожалуйста, введите тему исследования.")
        else:
            st.session_state.last_query = query_input.strip()
            client = get_client(st.session_state.api_key)

            with st.spinner("Академическая нормализация темы и поиск релевантных публикаций…"):
                try:
                    exp_queries, domain_kws = expand_academic_queries(query_input.strip(), client=client)
                    st.session_state.expanded_info = {
                        "queries": exp_queries,
                        "domain_keywords": domain_kws
                    }

                    raw_papers = search_openalex(
                        query=query_input.strip(),
                        n=count_choice,
                        lang=lang_choice,
                        api_key=st.session_state.openalex_key,
                        client=client
                    )

                    if not raw_papers:
                        st.info("По данному запросу статей с открытыми аннотациями не найдено. Попробуйте скорректировать тему.")
                    else:
                        ranked_papers = rerank(client, query_input.strip(), raw_papers, k=min(25, len(raw_papers)))
                        st.session_state.papers = ranked_papers
                        st.session_state.cards = {}
                        st.session_state.card_ratings = {}
                        st.session_state.connections_summary = ""
                        st.session_state.chat_history = []
                        st.session_state.current_session_title = query_input.strip()[:50]
                        sync_current_session_to_disk()
                        st.success(f"Успешно найдено и ранжировано: {len(ranked_papers)} профильных статей!")
                        st.rerun()
                except Exception as exc:
                    st.error(f"Ошибка при поиске публикаций: {exc}")

with tab_upload:
    with st.container(border=True):
        st.markdown(
            "##### 📥 Загрузка локальных PDF и BibTeX файлов с авто-распознаванием DOI\n"
            "<span style='color:#94a3b8;font-size:0.92rem;'>"
            "Загрузите свои файлы публикаций. Система автоматически извлечёт <b>DOI</b> из текста или метаданных, "
            "подгрузит полные аннотации, официальные названия и граф цитирований из <b>OpenAlex/Crossref</b> в контекст, "
            "а извлечённый текст PDF будет использоваться для глубокого анализа методов и ответов в научном чате."
            "</span>",
            unsafe_allow_html=True
        )
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        uploaded_files = st.file_uploader(
            "Перетащите или выберите PDF или BibTeX (.bib) файлы:",
            type=["pdf", "bib", "txt"],
            accept_multiple_files=True,
            help="Поддерживаются файлы статей в PDF и библиографии в .bib"
        )

        up_col1, up_col2 = st.columns([4, 6])
        target_mode = up_col1.radio(
            "Режим загрузки:",
            ["➕ Добавить к текущему исследованию", "✨ Создать новую тему/сессию"],
            horizontal=True
        )

        btn_process_files = st.button(
            "🚀 Обработать файлы, распознать DOI и подгрузить в контекст",
            type="primary",
            use_container_width=True,
            disabled=not uploaded_files
        )

    if btn_process_files and uploaded_files:
        status_box = st.status("Идёт обработка загруженных файлов и подгрузка метаданных по DOI…", expanded=True)
        imported_papers = []
        with status_box:
            for uf in uploaded_files:
                fname = uf.name.lower()
                st.write(f"📄 Чтение файла: `{uf.name}`...")
                fbytes = uf.read()
                try:
                    if fname.endswith(".pdf"):
                        p = parse_pdf_bytes(fbytes, filename=uf.name, api_key=st.session_state.openalex_key)
                        if p:
                            imported_papers.append(p)
                            doi_info = f" (найден DOI: `{p['doi']}`, подгружен из OpenAlex)" if p.get("doi") else " (локальный PDF, DOI не обнаружен)"
                            st.write(f"✅ **{p['title']}** ({p['year']}){doi_info}")
                    elif fname.endswith((".bib", ".txt")):
                        bib_text = fbytes.decode("utf-8", errors="ignore")
                        p_list = parse_bibtex_content(bib_text, api_key=st.session_state.openalex_key)
                        for p in p_list:
                            imported_papers.append(p)
                            doi_info = f" (найден DOI: `{p['doi']}`)" if p.get("doi") else ""
                            st.write(f"✅ **{p['title']}** ({p['year']}){doi_info}")
                except Exception as ex:
                    st.error(f"Ошибка при обработке {uf.name}: {ex}")

            status_box.update(label=f"Обработано {len(imported_papers)} публикаций!", state="complete", expanded=False)

        if imported_papers:
            if "Создать новую" in target_mode:
                new_session = create_new_session_data(
                    title=f"Загрузка: {uploaded_files[0].name[:40]}",
                    query=uploaded_files[0].name
                )
                st.session_state.current_session_id = new_session["id"]
                st.session_state.current_session_title = new_session["title"]
                st.session_state.last_query = uploaded_files[0].name
                st.session_state.papers = imported_papers
                st.session_state.cards = {}
                st.session_state.card_ratings = {}
                st.session_state.chat_history = []
                st.session_state.connections_summary = ""
                st.session_state.matrix_result = ""
            else:
                existing = st.session_state.get("papers", [])
                existing_dois = {p.get("doi") for p in existing if p.get("doi")}
                existing_ids = {p.get("id") for p in existing}
                for p in imported_papers:
                    if (p.get("doi") and p["doi"] in existing_dois) or p.get("id") in existing_ids:
                        continue
                    existing.append(p)
                st.session_state.papers = existing

            for p in imported_papers:
                st.session_state[f"check_{p['id']}"] = True

            sync_current_session_to_disk()
            st.success(f"Успешно подгружено в рабочий контекст: {len(imported_papers)} публикаций!")
            st.rerun()

with tab_dois:
    with st.container(border=True):
        st.markdown(
            "##### 🔗 Прямой импорт публикаций по списку DOI\n"
            "<span style='color:#94a3b8;font-size:0.92rem;'>"
            "Введите список DOI или URL публикаций (по одной ссылке на строку). "
            "Система автоматически сделает запросы к OpenAlex и Crossref, заполнит авторов, журналы, полные аннотации "
            "и цитирования и подгрузит статьи в активный контекст."
            "</span>",
            unsafe_allow_html=True
        )
        doi_input_text = st.text_area(
            "Список DOI (по одному на строку):",
            height=120,
            placeholder="10.48550/arXiv.1706.03762\nhttps://doi.org/10.1109/CVPR.2016.90\n10.1038/s41586-020-2649-2"
        )
        doi_col1, doi_col2 = st.columns([4, 6])
        doi_target_mode = doi_col1.radio(
            "Режим импорта DOI:",
            ["➕ Добавить к текущему исследованию", "✨ Создать новую тему/сессию"],
            horizontal=True,
            key="doi_radio_mode"
        )
        btn_import_dois = st.button(
            "⚡ Подгрузить статьи по DOI в контекст",
            type="primary",
            use_container_width=True,
            disabled=not doi_input_text.strip()
        )

    if btn_import_dois and doi_input_text.strip():
        lines = doi_input_text.strip().splitlines()
        with st.spinner("Запрос метаданных и аннотаций по DOI из OpenAlex..."):
            loaded_doi_papers = import_dois_list(lines, api_key=st.session_state.openalex_key)

        if loaded_doi_papers:
            if "Создать новую" in doi_target_mode:
                new_session = create_new_session_data(
                    title=f"DOI Импорт ({len(loaded_doi_papers)} ст.)",
                    query="Импорт по DOI"
                )
                st.session_state.current_session_id = new_session["id"]
                st.session_state.current_session_title = new_session["title"]
                st.session_state.last_query = "Импорт по DOI"
                st.session_state.papers = loaded_doi_papers
                st.session_state.cards = {}
                st.session_state.card_ratings = {}
                st.session_state.chat_history = []
                st.session_state.connections_summary = ""
                st.session_state.matrix_result = ""
            else:
                existing = st.session_state.get("papers", [])
                existing_dois = {p.get("doi") for p in existing if p.get("doi")}
                for p in loaded_doi_papers:
                    if p.get("doi") and p["doi"] in existing_dois:
                        continue
                    existing.append(p)
                st.session_state.papers = existing

            for p in loaded_doi_papers:
                st.session_state[f"check_{p['id']}"] = True

            sync_current_session_to_disk()
            st.success(f"Успешно подгружено по DOI: {len(loaded_doi_papers)} статей!")
            st.rerun()

if st.session_state.get("expanded_info") and st.session_state.papers:
    exp_info = st.session_state.expanded_info
    with st.expander("💡 Академическое расширение запроса (как система поняла тему)"):
        st.markdown(f"**Исходный запрос:** `{st.session_state.last_query}`")
        st.markdown("**Академические формулировки поиска:**")
        for qf in exp_info.get("queries", []):
            st.markdown(f"- 🔎 `{qf}`")
        if exp_info.get("domain_keywords"):
            st.caption(f"Ключевые предметные фильтры: {', '.join(exp_info['domain_keywords'])}")


# ------------------------------------------------------------------------------
# 2. ВЫБОРКА СТАТЕЙ (Сетка и списки)
# ------------------------------------------------------------------------------
papers = st.session_state.get("papers", [])

if papers:
    st.divider()

    # Header bar with metrics & layout mode
    verified_dois = sum(1 for p in papers if p.get("doi"))
    pdf_count = sum(1 for p in papers if p.get("pdf_url"))

    h_col1, h_col2 = st.columns([6, 4])
    with h_col1:
        st.markdown(f"### 2️⃣ Выборка публикаций для анализа ({len(papers)})")
        st.caption(f"Найдено: **{len(papers)} работ** · Верифицировано DOI: **{verified_dois}** · С открытым PDF: **{pdf_count}**")

    with h_col2:
        view_mode = st.radio(
            "Формат отображения:",
            ["📋 Список", "▦ Сетка 2 колонки"],
            index=1,
            horizontal=True,
            label_visibility="collapsed"
        )

    # Action bar
    sel_col1, sel_col2, sel_col3 = st.columns([1.5, 1.5, 5])
    if sel_col1.button("☑️ Выбрать все", use_container_width=True):
        for p in papers:
            st.session_state[f"check_{p['id']}"] = True
        st.rerun()

    if sel_col2.button("⬜ Снять выбор", use_container_width=True):
        for p in papers:
            st.session_state[f"check_{p['id']}"] = False
        st.rerun()

    chosen_papers = []

    # 2-Column Grid or 1-Column List container targets
    if view_mode == "▦ Сетка 2 колонки":
        col_left, col_right = st.columns(2)
        grid_targets = [col_left, col_right]
    else:
        grid_targets = [st.container()]

    for idx, p in enumerate(papers, 1):
        pid = p["id"]
        if f"check_{pid}" not in st.session_state:
            st.session_state[f"check_{pid}"] = (idx <= 12)
        target_container = grid_targets[(idx - 1) % len(grid_targets)]

        with target_container:
            with st.container(border=True):
                c_top1, c_top2 = st.columns([0.8, 9.2])
                is_checked = c_top1.checkbox(
                    f"Выбрать {idx}",
                    key=f"check_{pid}",
                    label_visibility="collapsed"
                )
                if is_checked:
                    chosen_papers.append(p)

                with c_top2:
                    st.markdown(
                        f"<div style='font-weight:700;font-size:1.02rem;color:#f8fbff;line-height:1.35;margin-bottom:4px;'>"
                        f"[{idx}] {p['title']} <span style='color:#94a3b8;font-size:0.9rem;font-weight:400;'>({p['year']})</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )

                # Badges row
                doi_badge = f"<a class='badge-doi' href='https://doi.org/{p['doi']}' target='_blank'>DOI: {p['doi']}</a>" if p.get("doi") else "<span style='color:#64748b;font-size:0.78rem;'>нет DOI</span>"
                citekey_badge = f"<span class='badge-citekey'>\\cite{{{p.get('citekey')}}}</span>"
                cites_cnt = p.get('cited_by_count', 0)
                cited_badge = f"<span class='badge-cited'>🔥 {cites_cnt} цит.</span>" if cites_cnt > 0 else ""
                journal_badge = f"<span class='badge-source'>🏛️ {p.get('journal') or 'OpenAlex'}</span>"
                origin_badge = f"<span class='badge-source' style='background:rgba(59,130,246,0.15);color:#93c5fd;border-color:rgba(59,130,246,0.4);'>📄 {p.get('source_origin')}</span>" if p.get("source_origin") else ""
                fulltext_badge = f"<span class='badge-source' style='background:rgba(16,185,129,0.15);color:#6ee7b7;border-color:rgba(16,185,129,0.4);'>📖 Полный текст PDF ({len(p.get('full_text',''))} симв.)</span>" if p.get("full_text") else ""

                st.markdown(
                    f"<div style='display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:6px 0;'>"
                    f"{doi_badge} {citekey_badge} {cited_badge} {journal_badge} {origin_badge} {fulltext_badge}"
                    f"</div>",
                    unsafe_allow_html=True
                )

                st.caption(f"👥 {p.get('authors_str', 'Не указано')}")

                # Quick links row
                l_col1, l_col2 = st.columns(2)
                if p.get("url"):
                    l_col1.link_button("Статья ↗", p["url"], use_container_width=True)
                if p.get("pdf_url"):
                    l_col2.link_button("PDF 📄", p["pdf_url"], use_container_width=True)

                with st.expander(f"Аннотация [{idx}]"):
                    st.markdown(f"<div class='abstract-box'>{p.get('abstract', 'Аннотация не указана')}</div>", unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # 3. ПОСТРОЕНИЕ МАТРИЦЫ И ИЗВЛЕЧЕНИЕ КАРТОЧЕК
    # --------------------------------------------------------------------------
    st.divider()
    with st.container(border=True):
        act_left, act_right = st.columns([6, 4])
        with act_left:
            st.markdown(
                f"### 3️⃣ Построение сравнительной матрицы (PaperCard)\n"
                f"Выбрано для анализа: **{len(chosen_papers)}** из {len(papers)} статей. "
                f"Карточки заполняются по строгой схеме без галлюцинаций («не указано»)."
            )
        with act_right:
            st.write("")
            btn_extract = st.button(
                f"📊 Собрать матрицу и запустить чат ({len(chosen_papers)} ст.)",
                type="primary",
                disabled=len(chosen_papers) == 0,
                use_container_width=True
            )

    if btn_extract:
        client = get_client(st.session_state.api_key)
        if not client:
            st.error("Для извлечения карточек укажите Gemini API key в боковой панели.")
        else:
            cards = {}
            prog_bar = st.progress(0, text="Извлечение карточек по строгой схеме PaperCard…")
            for idx, p in enumerate(chosen_papers):
                prog_bar.progress((idx + 1) / len(chosen_papers), text=f"Анализ статьи [{idx+1}/{len(chosen_papers)}]: {p['title'][:40]}…")
                card = extract_card(client, p, model=st.session_state.selected_model)
                cards[p["id"]] = card
            st.session_state.cards = cards
            sync_current_session_to_disk()
            prog_bar.empty()
            st.toast("Матрица сравнения сформирована! Чат и аналитика активированы.", icon="🚀")
            st.rerun()


# ------------------------------------------------------------------------------
# 4. АНАЛИТИЧЕСКОЕ РАБОЧЕЕ ПРОСТРАНСТВО: ЧАТ, ТАБЛИЦА, СВЯЗИ, ЭКСПОРТ
# ------------------------------------------------------------------------------
cards_map = st.session_state.get("cards", {})

if papers and cards_map:
    active_papers = [p for p in papers if p["id"] in cards_map]

    if active_papers:
        st.divider()

        # Context header
        verified_dois = sum(1 for p in active_papers if p.get("doi"))
        st.markdown(f"""
        <div style="display:flex;align-items:center;justify-content:space-between;background:#0e172a;border:1px solid #1e293b;border-radius:12px;padding:12px 18px;margin-bottom:16px;">
            <div>
                <span style="font-weight:700;font-size:1.1rem;color:#f8fafc;">Аналитический срез: {st.session_state.last_query}</span><br/>
                <span style="color:#94a3b8;font-size:0.85rem;">Активный корпус: <b>{len(active_papers)} статей</b> (верифицировано <b>{verified_dois} DOI</b>)</span>
            </div>
            <div>
                <span style="background:rgba(16,185,129,0.15);color:#34d399;border:1px solid rgba(52,211,153,0.3);padding:4px 10px;border-radius:8px;font-size:0.8rem;font-weight:600;">
                    ✓ Без галлюцинаций («не указано»)
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        tab_chat, tab_table, tab_connections, tab_cards, tab_matrix, tab_export = st.tabs([
            "💬 Научный чат и дискуссия",
            "📋 Сравнительная таблица",
            "🔗 Связи и граф статей",
            "🗂️ Карточки статей (👍/👎)",
            "🧩 Матрица «Метод × Датасет»",
            "📦 Центр экспорта (LaTeX, BibTeX)"
        ])

        client = get_client(st.session_state.api_key)

        # ======================================================================
        # TAB 1: НАУЧНЫЙ ЧАТ И ДИСКУССИЯ
        # ======================================================================
        with tab_chat:
            cur_m = st.session_state.get("selected_model", "gemini-3.8-flash")
            st.markdown(
                f"#### 💬 Исследовательский диалог с корпусом статей "
                f"<span style='background:rgba(99,102,241,0.18);color:#a5b4fc;border:1px solid rgba(99,102,241,0.3);padding:3px 8px;border-radius:6px;font-size:0.8rem;font-weight:500;'>🤖 {cur_m}</span>",
                unsafe_allow_html=True
            )
            st.caption(
                "Задавайте любые вопросы по методам, данным, противоречиям и результатам. "
                "Ассистент отвечает строго по аннотациям и карточкам с кликабельными ссылками на первоисточники [N] и \\cite{...}."
            )

            # Quick Prompt Chips inside a bordered container
            with st.container(border=True):
                st.markdown("<div style='font-size:0.8rem;font-weight:700;color:#93c5fd;letter-spacing:0.04em;margin-bottom:8px;'>⚡ БЫСТРЫЕ СЦЕНАРИИ АНАЛИЗА:</div>", unsafe_allow_html=True)
                chip_c1, chip_c2, chip_c3, chip_c4 = st.columns(4)
                q_chip = None
                if chip_c1.button("⚖️ Сравни методы", use_container_width=True, help="Сопоставление всех методов и метрик"):
                    q_chip = "Сравни используемые методы и метрики во всех статьях. Какие подходы показали наивысшую эффективность?"
                if chip_c2.button("⚔️ Разногласия", use_container_width=True, help="Точки дискуссий и споров в выводах"):
                    q_chip = "В чём заключаются основные расхождения, споры или противоречия в выводах и оценках авторов?"
                if chip_c3.button("⚠️ Ограничения", use_container_width=True, help="Слабые места и нерешённые вопросы"):
                    q_chip = "Какие общие методологические ограничения и нерешённые вопросы объединяют все выбранные работы?"
                if chip_c4.button("💡 Новая тема", use_container_width=True, help="Генерация перспективных гипотез"):
                    q_chip = "На основе выявленных пробелов в литературе сформулируй 3 перспективные темы научных исследований со свежей научной новизной."

            # Render Chat History
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

            # Chat Input handling
            user_input = st.chat_input("Спросите о методах, результатах, датасетах или ограничениях статей…")
            prompt_to_send = q_chip or user_input

            if prompt_to_send:
                st.session_state.chat_history.append({"role": "user", "content": prompt_to_send})
                with st.chat_message("user"):
                    st.markdown(prompt_to_send)

                with st.chat_message("assistant"):
                    with st.spinner(f"Анализирую корпус статей ({cur_m}) и формулирую ответ с DOI…"):
                        ans = chat_with_papers(
                            client,
                            st.session_state.chat_history,
                            active_papers,
                            cards_map,
                            model=st.session_state.selected_model
                        )
                        st.markdown(ans)
                        st.session_state.chat_history.append({"role": "assistant", "content": ans})
                        sync_current_session_to_disk()

            # Chat utilities
            if st.session_state.chat_history:
                st.markdown("---")
                chat_act1, chat_act2 = st.columns([1.5, 6])
                if chat_act1.button("🗑️ Очистить диалог", use_container_width=True):
                    st.session_state.chat_history = []
                    sync_current_session_to_disk()
                    st.rerun()

                # Transcript download
                transcript_text = f"# Протокол научного обсуждения: {st.session_state.last_query}\n\n"
                for m in st.session_state.chat_history:
                    transcript_text += f"### {m['role'].upper()}:\n{m['content']}\n\n---\n\n"
                chat_act2.download_button(
                    "📥 Скачать стенограмму диалога (.md)",
                    transcript_text,
                    file_name="tensortext_chat_transcript.md",
                    mime="text/markdown"
                )

        # ======================================================================
        # TAB 2: СРАВНИТЕЛЬНАЯ ТАБЛИЦА
        # ======================================================================
        with tab_table:
            st.markdown("#### 📋 Сравнительная матрица исследований")

            t_filter_c1, _ = st.columns([5, 5])
            with t_filter_c1:
                table_filter = st.text_input(
                    "🔍 Быстрый фильтр по таблице:",
                    placeholder="Например: LCA / telemetry / carbon / автор / метод...",
                    label_visibility="collapsed"
                )

            table_display_data = []
            for idx, p in enumerate(active_papers, 1):
                c = cards_map.get(p["id"], {})
                doi_s = f"https://doi.org/{p['doi']}" if p.get("doi") else (p.get("url") or "")

                if table_filter.strip():
                    kw = table_filter.strip().lower()
                    row_search_text = f"{p.get('title')} {p.get('authors_str')} {c.get('task')} {c.get('method')} {c.get('dataset')} {c.get('key_result')}".lower()
                    if kw not in row_search_text:
                        continue

                table_display_data.append({
                    "№": idx,
                    "Citekey": p.get("citekey", ""),
                    "Статья": p.get('title'),
                    "DOI": doi_s,
                    "Цитат": p.get("cited_by_count", 0),
                    "Задача": c.get("task", "не указано"),
                    "Метод": c.get("method", "не указано"),
                    "Датасет": c.get("dataset", "не указано"),
                    "Метрики": c.get("metrics", "не указано"),
                    "Результат": c.get("key_result", "не указано"),
                    "Ограничения": c.get("limitations", "не указано")
                })

            df_display = pd.DataFrame(table_display_data)
            st.dataframe(
                df_display,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "DOI": st.column_config.LinkColumn("DOI Ссылка", display_text="Открыть DOI ↗"),
                    "Цитат": st.column_config.NumberColumn("Цитат", format="%d 🔥")
                }
            )

        # ======================================================================
        # TAB 3: СВЯЗИ И ГРАФ СТАТЕЙ
        # ======================================================================
        with tab_connections:
            st.markdown("#### 🔗 Линии цитирования, общие источники и диалектический синтез")
            st.caption("Анализ того, как статьи выборки ссылаются друг на друга, где авторы согласны, а где их оценки расходятся.")

            net_stats = analyze_citation_network(active_papers)
            d_cites = net_stats.get("direct_citations", [])
            co_cites = net_stats.get("co_citations", [])

            c_metric1, c_metric2, c_metric3 = st.columns(3)
            with c_metric1.container(border=True):
                st.metric("📄 Статей в исследовании", len(active_papers))
            with c_metric2.container(border=True):
                st.metric("🔗 Прямых ссылок между статьями", len(d_cites))
            with c_metric3.container(border=True):
                st.metric("📚 Пар с общими первоисточниками", len(co_cites))

            if d_cites:
                st.markdown("##### 🔗 Прямые перекрёстные цитирования внутри выборки:")
                cit_col1, cit_col2 = st.columns(2)
                for i, item in enumerate(d_cites):
                    target_cit_col = cit_col1 if i % 2 == 0 else cit_col2
                    with target_cit_col.container(border=True):
                        st.markdown(
                            f"<div style='font-size:0.95rem;font-weight:700;color:#f8fafc;line-height:1.3;'>{item['source'].get('title')} <span style='color:#94a3b8;font-weight:400;'>({item['source'].get('year')})</span></div>"
                            f"<div style='color:#c084fc;font-size:0.85rem;margin:5px 0;'>↳ <i>прямо цитирует и опирается на:</i></div>"
                            f"<div style='font-size:0.92rem;font-weight:600;color:#cbd5e1;line-height:1.3;'>{item['target'].get('title')} <span style='color:#94a3b8;font-weight:400;'>({item['target'].get('year')})</span></div>",
                            unsafe_allow_html=True
                        )
            else:
                st.info("В текущей выборке прямых цитирований не обнаружено (исследования проводились параллельными научными группами).")

            if co_cites:
                with st.expander(f"📚 Общая библиографическая база (совместное цитирование: {len(co_cites)} пар)"):
                    for item in co_cites[:8]:
                        st.markdown(
                            f"- **{item['paper1'].get('title')[:45]}…** и **{item['paper2'].get('title')[:45]}…** "
                            f"— опираются на **{item['shared_count']} общих первоисточников**."
                        )

            st.divider()
            st.markdown("##### 🧭 Аналитический синтез взаимосвязей (Кластеры, Консенсус, Дискуссии)")
            btn_synth_conn = st.button("🔄 Сгенерировать глубокий синтез связей и противоречий", type="primary", use_container_width=True)

            if btn_synth_conn:
                with st.spinner(f"Анализ связей, консенсуса и противоречий ({st.session_state.selected_model})…"):
                    synth_text = synthesize_connections(
                        client,
                        st.session_state.last_query,
                        active_papers,
                        cards_map,
                        model=st.session_state.selected_model
                    )
                    st.session_state.connections_summary = synth_text
                    sync_current_session_to_disk()

            if st.session_state.get("connections_summary"):
                with st.container(border=True):
                    st.markdown(st.session_state.connections_summary)
            elif not btn_synth_conn:
                st.caption("Нажмите кнопку выше, чтобы выявить тематические кластеры, точки согласия, дискуссии и эволюцию методологии.")

        # ======================================================================
        # TAB 4: КАРТОЧКИ (PAPERCARDS)
        # ======================================================================
        with tab_cards:
            st.markdown("#### 🗂️ Карточки статей и обратная связь (👍 верно / 👎 ошибка)")
            st.caption("Оцените точность извлечённых данных для каждой статьи. Это помогает измерять метрики точности в рамках CustDev.")

            card_err_count = sum(1 for c in cards_map.values() if str(c.get("key_result", "")).startswith("Ошибка"))
            if card_err_count > 0:
                st.warning(f"⚠️ В {card_err_count} карточках обнаружена ошибка извлечения (например, из-за устаревшей модели). Нажмите кнопку ниже для переизвлечения.")

            c_re_col1, _ = st.columns([3, 5])
            if c_re_col1.button("🔄 Переизвлечь карточки с текущей моделью", use_container_width=True):
                client = get_client(st.session_state.api_key)
                if not client:
                    st.error("Укажите Gemini API key в боковой панели.")
                else:
                    new_cards = {}
                    prog_bar = st.progress(0, text="Переизвлечение карточек…")
                    for idx, p in enumerate(active_papers):
                        prog_bar.progress((idx + 1) / len(active_papers), text=f"Анализ [{idx+1}/{len(active_papers)}]: {p['title'][:40]}…")
                        new_cards[p["id"]] = extract_card(client, p, model=st.session_state.selected_model)
                    st.session_state.cards = new_cards
                    sync_current_session_to_disk()
                    prog_bar.empty()
                    st.toast("Карточки успешно обновлены!", icon="✅")
                    st.rerun()

            for idx, p in enumerate(active_papers, 1):
                pid = p["id"]
                c = cards_map.get(pid, {})
                cur_rating = st.session_state.card_ratings.get(pid, 0)

                with st.container(border=True):
                    # Header row: Title + Year + Badges on left, Ratings on right
                    hdr_left, hdr_right = st.columns([7.8, 2.2])
                    with hdr_left:
                        doi_badge = f"<a class='badge-doi' href='https://doi.org/{p['doi']}' target='_blank'>DOI: {p['doi']}</a>" if p.get("doi") else ""
                        cites_badge = f"<span class='badge-cited'>🔥 {p.get('cited_by_count', 0)} цит.</span>" if p.get('cited_by_count') else ""
                        citekey_badge = f"<span class='badge-citekey'>\\cite{{{p.get('citekey')}}}</span>"
                        journal_badge = f"<span class='badge-source'>🏛️ {p.get('journal') or 'OpenAlex'}</span>"
                        st.markdown(
                            f"<div style='font-size:1.12rem;font-weight:700;color:#f8fbff;margin-bottom:6px;'>[{idx}] {p['title']} <span style='color:#94a3b8;font-weight:400;font-size:0.95rem;'>({p['year']})</span></div>"
                            f"<div style='display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:4px;'>{doi_badge} {citekey_badge} {cites_badge} {journal_badge}</div>",
                            unsafe_allow_html=True
                        )
                        st.caption(f"👥 Авторы: {p.get('authors_str', 'Не указано')}")

                    with hdr_right:
                        st.caption("<div style='text-align:right;margin-bottom:4px;color:#8095b8;'>Оценка данных:</div>", unsafe_allow_html=True)
                        r_c1, r_c2 = st.columns(2)
                        up_label = "👍 Верно" if cur_rating == 1 else "👍"
                        down_label = "👎 Ошибка" if cur_rating == -1 else "👎"
                        if r_c1.button(up_label, key=f"thumb_up_{pid}", type="primary" if cur_rating == 1 else "secondary", use_container_width=True):
                            st.session_state.card_ratings[pid] = 1 if cur_rating != 1 else 0
                            sync_current_session_to_disk()
                            st.rerun()
                        if r_c2.button(down_label, key=f"thumb_down_{pid}", type="primary" if cur_rating == -1 else "secondary", use_container_width=True):
                            st.session_state.card_ratings[pid] = -1 if cur_rating != -1 else 0
                            sync_current_session_to_disk()
                            st.rerun()

                    st.markdown("<div style='height:1px;background:#1a2742;margin:10px 0 14px 0;'></div>", unsafe_allow_html=True)

                    # 6-Field Structured Grid (2 rows x 3 columns)
                    r1_c1, r1_c2, r1_c3 = st.columns(3)
                    with r1_c1:
                        st.markdown(render_field_cell("🎯", "Задача (Task)", c.get("task")), unsafe_allow_html=True)
                    with r1_c2:
                        st.markdown(render_field_cell("⚙️", "Метод (Method)", c.get("method")), unsafe_allow_html=True)
                    with r1_c3:
                        st.markdown(render_field_cell("📊", "Датасет (Dataset)", c.get("dataset")), unsafe_allow_html=True)

                    r2_c1, r2_c2, r2_c3 = st.columns(3)
                    with r2_c1:
                        st.markdown(render_field_cell("📏", "Метрики (Metrics)", c.get("metrics")), unsafe_allow_html=True)
                    with r2_c2:
                        st.markdown(render_field_cell("🏆", "Ключевой результат (Key Result)", c.get("key_result")), unsafe_allow_html=True)
                    with r2_c3:
                        st.markdown(render_field_cell("⚠️", "Ограничения (Limitations)", c.get("limitations")), unsafe_allow_html=True)

                    with st.expander(f"📄 Исходная аннотация статьи [{idx}]"):
                        st.markdown(f"<div class='abstract-box'>{p.get('abstract', 'Аннотация не указана')}</div>", unsafe_allow_html=True)

        # ======================================================================
        # TAB 5: МАТРИЦА «МЕТОД × ДАТАСЕТ»
        # ======================================================================
        with tab_matrix:
            st.markdown("#### 🧩 Матрица «Метод × Датасет» и исследовательские пробелы")
            st.caption("Анализ пересечений методов и датасетов для выявления белых пятен (Research Gaps) в литературе.")
            if st.button("🔄 Сформировать матрицу пробелов", use_container_width=True):
                if not client:
                    st.error("Укажите Gemini API key в боковой панели.")
                else:
                    with st.spinner(f"Анализ пересечений методов и датасетов ({st.session_state.selected_model})…"):
                        matrix_res = generate_method_dataset_matrix(
                            client,
                            active_papers,
                            cards_map,
                            model=st.session_state.selected_model
                        )
                        st.session_state.matrix_result = matrix_res
                        sync_current_session_to_disk()

            if st.session_state.get("matrix_result"):
                with st.container(border=True):
                    st.markdown(st.session_state.matrix_result)

        # ======================================================================
        # TAB 6: ЦЕНТР ЭКСПОРТА (LATEX + BIBTEX)
        # ======================================================================
        with tab_export:
            st.markdown("#### 📦 Экспорт результатов в академические форматы")
            st.caption("Все цитаты и BibTeX согласованы с метками `\\cite{...}` в компилируемом документе LaTeX.")

            exp_r1_c1, exp_r1_c2, exp_r1_c3 = st.columns(3)

            with exp_r1_c1.container(border=True):
                st.markdown("##### 📄 LaTeX Документ")
                st.caption("Компилируемый `.tex` файл: `tabularx`, `booktabs`, `hyperref`, ссылки `\\cite`.")
                latex_content = export_latex_document(
                    st.session_state.last_query,
                    active_papers,
                    cards_map,
                    st.session_state.author_profile,
                    connections_text=st.session_state.get("connections_summary")
                )
                st.download_button(
                    "📥 Скачать .tex",
                    latex_content,
                    file_name="paper_comparison.tex",
                    mime="application/x-tex",
                    use_container_width=True
                )

            with exp_r1_c2.container(border=True):
                st.markdown("##### 📚 BibTeX База")
                st.caption("Файл `refs.bib` с DOI записями через Crossref/DataCite и согласованными citekeys.")
                bibtex_content = export_bibtex(active_papers)
                st.download_button(
                    "📥 Скачать refs.bib",
                    bibtex_content,
                    file_name="refs.bib",
                    mime="application/x-bibtex",
                    use_container_width=True
                )

            with exp_r1_c3.container(border=True):
                st.markdown("##### ⚡ Комплект для Overleaf")
                st.caption("Готовый ZIP-архив (`paper_comparison.tex` + `refs.bib`) для мгновенного импорта в Overleaf.")
                zip_buf = io.BytesIO()
                with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                    zf.writestr("paper_comparison.tex", latex_content)
                    zf.writestr("refs.bib", bibtex_content)
                st.download_button(
                    "📦 Скачать ZIP для Overleaf",
                    zip_buf.getvalue(),
                    file_name="tensortext_latex_bundle.zip",
                    mime="application/zip",
                    use_container_width=True
                )

            exp_r2_c1, exp_r2_c2, exp_r2_c3 = st.columns(3)

            with exp_r2_c1.container(border=True):
                st.markdown("##### 📊 Таблица Excel / CSV")
                st.caption("Таблица со всеми параметрами, метриками, DOI и цитатами для Excel.")
                csv_content = export_csv(active_papers, cards_map)
                st.download_button(
                    "📥 Скачать table.csv",
                    csv_content,
                    file_name="table.csv",
                    mime="text/csv",
                    use_container_width=True
                )

            with exp_r2_c2.container(border=True):
                st.markdown("##### 📜 Список ГОСТ 7.0.5-2008")
                st.caption("Оформленный библиографический список по стандарту ГОСТ 7.0.5-2008.")
                gost_content = export_gost(active_papers)
                st.download_button(
                    "📥 Скачать ГОСТ (.txt)",
                    gost_content,
                    file_name="references_gost.txt",
                    mime="text/plain",
                    use_container_width=True
                )

            with exp_r2_c3.container(border=True):
                st.markdown("##### 📝 Документ Word (.docx)")
                st.caption("Отчет в формате DOCX со сравнительной таблицей и библиографией.")
                docx_bytes = export_docx(st.session_state.last_query, active_papers, cards_map, st.session_state.author_profile)
                st.download_button(
                    "📥 Скачать .docx",
                    docx_bytes,
                    file_name="paper_comparison.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True
                )

            with st.expander("👁️ Предпросмотр исходного кода LaTeX (.tex) для вставки в Overleaf"):
                st.code(latex_content, language="latex")

        # ----------------------------------------------------------------------
        # ОБРАТНАЯ СВЯЗЬ И ЛОГИРОВАНИЕ (MoSCoW Must #9)
        # ----------------------------------------------------------------------
        st.divider()
        with st.container(border=True):
            st.markdown("### 5️⃣ Оценка результатов и обратная связь (MVP CustDev)")
            st.caption("Ваш отзыв напрямую влияет на точность извлечения фактов и калибровку алгоритмов ранжирования.")

            with st.form("feedback_form"):
                fb_c1, fb_c2 = st.columns([4, 6])
                with fb_c1:
                    trust_rating = st.slider(
                        "Насколько вы доверяете этой таблице?",
                        min_value=1,
                        max_value=5,
                        value=4,
                        help="1 — совсем не доверяю, 5 — полностью доверяю и готов использовать в научной работе"
                    )
                with fb_c2:
                    feedback_note = st.text_area(
                        "Что неверно или чего не хватает в извлечённых данных?",
                        placeholder="Например: в статье [2] датасет на самом деле приватный; не хватает колонки с кодом на GitHub...",
                        height=90
                    )
                submit_fb = st.form_submit_button("📩 Отправить отзыв", type="primary", use_container_width=True)

        if submit_fb:
            ok = log_feedback(
                query=st.session_state.last_query,
                trust_rating=trust_rating,
                note=feedback_note,
                card_ratings=st.session_state.card_ratings,
                papers_count=len(active_papers)
            )
            if ok:
                st.success("Спасибо за ваш отзыв! Оценка и события успешно зафиксированы в feedback.csv.")
            else:
                st.error("Не удалось записать отзыв в файл.")
