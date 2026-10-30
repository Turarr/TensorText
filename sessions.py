import hashlib
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from sources import make_citekey

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "tensortext_data"
SESSIONS_DIR = DATA_DIR / "sessions"
LEGACY_DIR = ROOT / "chat_history"

for folder in (DATA_DIR, SESSIONS_DIR):
    folder.mkdir(parents=True, exist_ok=True)


def migrate_legacy_chat_history():
    """Migrates any session files from legacy chat_history/ to tensortext_data/sessions/."""
    if not LEGACY_DIR.exists():
        return
    for legacy_file in LEGACY_DIR.glob("*.json"):
        target_file = SESSIONS_DIR / legacy_file.name
        if not target_file.exists():
            try:
                target_file.write_text(legacy_file.read_text(encoding="utf-8"), encoding="utf-8")
            except Exception:
                pass


def normalize_paper(p: dict, idx: int = 1) -> dict:
    """Ensures paper dictionary conforms to TensorText expected schema."""
    title = p.get("title") or "Без названия"
    year = p.get("year") or ""
    authors = p.get("authors") or []
    if isinstance(authors, list):
        authors_str = ", ".join(authors) if authors else "Не указано"
    else:
        authors_str = str(authors) if authors else "Не указано"
    if p.get("authors_str"):
        authors_str = p["authors_str"]

    doi = p.get("doi") or ""
    url = p.get("url") or p.get("landing_page_url") or ""
    if not doi and "doi.org/" in url:
        doi = url.split("doi.org/")[-1].strip("/")
    if not url and doi:
        url = f"https://doi.org/{doi}"

    paper_id = p.get("id")
    if not paper_id:
        paper_id = hashlib.sha256((title + str(year)).encode("utf-8")).hexdigest()[:16]

    res = {
        "id": paper_id,
        "title": title,
        "year": year,
        "authors": authors if isinstance(authors, list) else [authors_str],
        "authors_str": authors_str,
        "abstract": p.get("abstract") or "",
        "doi": doi,
        "url": url,
        "pdf_url": p.get("pdf_url") or "",
        "cited_by_count": p.get("cited_by_count", 0),
        "journal": p.get("journal") or p.get("source") or "OpenAlex",
        "referenced_works": p.get("referenced_works") or [],
        "full_text": p.get("full_text") or "",
        "source_origin": p.get("source_origin") or ("PDF Upload" if p.get("full_text") else "OpenAlex")
    }
    res["citekey"] = p.get("citekey") or make_citekey(res, index=idx)
    return res


def normalize_messages(raw_msgs: list) -> List[Dict[str, str]]:
    """Normalizes chat messages list to standard role & content format."""
    normalized = []
    for m in raw_msgs:
        if not isinstance(m, dict):
            continue
        role = m.get("role", "user")
        if role in ("model", "assistant", "ai", "bot"):
            role = "assistant"
        else:
            role = "user"

        content = m.get("content") or m.get("text") or ""
        if not content and "parts" in m:
            parts = m["parts"]
            if isinstance(parts, list):
                content = "".join([p.get("text", "") if isinstance(p, dict) else str(p) for p in parts])
            else:
                content = str(parts)
        normalized.append({"role": role, "content": str(content)})
    return normalized


def list_saved_sessions() -> List[Dict]:
    """Returns all saved sessions sorted by most recently modified."""
    migrate_legacy_chat_history()
    results = []
    for file_path in SESSIONS_DIR.glob("*.json"):
        try:
            mtime = file_path.stat().st_mtime
            raw = json.loads(file_path.read_text(encoding="utf-8"))
            sid = raw.get("id") or raw.get("session_id") or file_path.stem
            query = raw.get("search_query") or raw.get("last_query") or ""
            title = raw.get("title")
            if not title or title in ("Новое исследование", "Импортированное исследование"):
                title = query if query else (title or "Исследование")

            papers = raw.get("papers") or raw.get("scholar_abstracts") or []
            chat_msgs = raw.get("chat_history") or raw.get("messages") or []
            results.append({
                "id": sid,
                "title": title,
                "query": query,
                "papers_count": len(papers),
                "chat_count": len(chat_msgs),
                "mtime": mtime,
                "date_str": datetime.fromtimestamp(mtime).strftime("%d.%m.%Y %H:%M")
            })
        except Exception:
            continue

    results.sort(key=lambda s: s["mtime"], reverse=True)
    return results


def load_session_data(session_id: str) -> Optional[Dict]:
    """Loads and normalizes session data from disk."""
    file_path = SESSIONS_DIR / f"{session_id}.json"
    if not file_path.exists():
        # Check legacy directory
        legacy_path = LEGACY_DIR / f"{session_id}.json"
        if legacy_path.exists():
            file_path = legacy_path
        else:
            return None

    try:
        raw = json.loads(file_path.read_text(encoding="utf-8"))
        sid = raw.get("id") or raw.get("session_id") or session_id
        query = raw.get("search_query") or raw.get("last_query") or ""
        title = raw.get("title") or (query[:50] if query else "Исследование")

        raw_papers = raw.get("papers") or raw.get("scholar_abstracts") or []
        normalized_papers = [normalize_paper(p, idx=i) for i, p in enumerate(raw_papers, 1)]

        selected_ids = raw.get("selected_paper_ids")
        if selected_ids is None:
            # If not explicitly saved, select all or top 12
            selected_ids = [p["id"] for p in normalized_papers[:12]]

        return {
            "id": sid,
            "title": title,
            "search_query": query,
            "created_at": raw.get("created_at") or datetime.now().isoformat(timespec="seconds"),
            "papers": normalized_papers,
            "selected_paper_ids": selected_ids,
            "cards": raw.get("cards") or {},
            "card_ratings": raw.get("card_ratings") or {},
            "chat_history": normalize_messages(raw.get("chat_history") or raw.get("messages") or []),
            "connections_summary": raw.get("connections_summary") or raw.get("literature_review") or "",
            "matrix_result": raw.get("matrix_result") or "",
            "author_profile": raw.get("author_profile") or {}
        }
    except Exception:
        return None


def save_session_data(session_data: Dict) -> bool:
    """Saves session data to disk in UTF-8 format."""
    sid = session_data.get("id")
    if not sid:
        sid = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
        session_data["id"] = sid

    file_path = SESSIONS_DIR / f"{sid}.json"
    try:
        file_path.write_text(json.dumps(session_data, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception:
        return False


def create_new_session_data(title: str = "", query: str = "") -> Dict:
    """Creates a new empty session schema."""
    sid = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    display_title = title or (query[:50] if query else "Новое исследование")
    return {
        "id": sid,
        "title": display_title,
        "search_query": query,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "papers": [],
        "selected_paper_ids": [],
        "cards": {},
        "card_ratings": {},
        "chat_history": [],
        "connections_summary": "",
        "matrix_result": "",
        "author_profile": {}
    }


def delete_session_data(session_id: str) -> bool:
    """Deletes a session file from disk."""
    file_path = SESSIONS_DIR / f"{session_id}.json"
    try:
        if file_path.exists():
            file_path.unlink()
        legacy_path = LEGACY_DIR / f"{session_id}.json"
        if legacy_path.exists():
            legacy_path.unlink()
        return True
    except Exception:
        return False
