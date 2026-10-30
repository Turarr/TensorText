import csv
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FEEDBACK_FILE = ROOT / "feedback.csv"


def log_feedback(query, trust_rating, note, card_ratings=None, papers_count=0):
    fieldnames = ["timestamp", "query", "trust_rating", "papers_count", "card_ratings_summary", "note"]
    is_new = not FEEDBACK_FILE.exists()

    card_ratings = card_ratings or {}
    thumbs_up = sum(1 for v in card_ratings.values() if v == 1)
    thumbs_down = sum(1 for v in card_ratings.values() if v == -1)
    ratings_summary = f"+{thumbs_up}/-{thumbs_down}" if card_ratings else "none"

    try:
        with open(FEEDBACK_FILE, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if is_new:
                writer.writeheader()
            writer.writerow({
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "query": query.strip(),
                "trust_rating": trust_rating,
                "papers_count": papers_count,
                "card_ratings_summary": ratings_summary,
                "note": (note or "").strip().replace("\n", " ")
            })
        return True
    except Exception:
        return False


def get_feedback_summary():
    if not FEEDBACK_FILE.exists():
        return {"total": 0, "avg_trust": 0.0, "thumbs_up": 0, "thumbs_down": 0}

    total = 0
    trust_sum = 0
    up_sum = 0
    down_sum = 0

    try:
        with open(FEEDBACK_FILE, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                total += 1
                try:
                    trust_sum += float(r.get("trust_rating", 0))
                except Exception:
                    pass
                summary = r.get("card_ratings_summary", "")
                if "+" in summary and "/-" in summary:
                    try:
                        parts = summary.split("/-")
                        up_sum += int(parts[0].replace("+", ""))
                        down_sum += int(parts[1])
                    except Exception:
                        pass
        return {
            "total": total,
            "avg_trust": round(trust_sum / total, 2) if total else 0.0,
            "thumbs_up": up_sum,
            "thumbs_down": down_sum
        }
    except Exception:
        return {"total": 0, "avg_trust": 0.0, "thumbs_up": 0, "thumbs_down": 0}
