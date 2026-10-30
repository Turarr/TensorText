import hashlib
import json
import math
import os
import re
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
load_dotenv()

import numpy as np
import pydantic
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

from sources import analyze_citation_network

ROOT = Path(__file__).resolve().parent
EMBEDDINGS_DIR = ROOT / "tensortext_data" / "embeddings"
CARDS_CACHE_DIR = ROOT / "tensortext_data" / "cards_cache"

for folder in (EMBEDDINGS_DIR, CARDS_CACHE_DIR):
    folder.mkdir(parents=True, exist_ok=True)

DEFAULT_LLM_MODEL = os.getenv("GEMINI_LLM_MODEL", "gemini-3.5-flash")
DEFAULT_EMB_MODEL = os.getenv("GEMINI_EMB_MODEL", "gemini-embedding-2")


def sanitize_model_name(model: Optional[str] = None) -> str:
    """
    Ensures modern Gemini models are used, automatically mapping legacy/deprecated
    models (gemini-2.5, gemini-2.0, gemini-1.5, etc.) to gemini-3.5-flash.
    """
    if not model or not str(model).strip():
        model = os.getenv("GEMINI_LLM_MODEL", DEFAULT_LLM_MODEL)
    m = str(model).strip()
    if any(m.startswith(dep) for dep in ("gemini-2.5", "gemini-2.0", "gemini-1.5", "gemini-1.0")):
        return "gemini-3.5-flash"
    return m


class PaperCard(BaseModel):
    task: Optional[str] = Field(
        default=None,
        description="Исследовательская задача или цель работы. 'не указано', если не упомянуто в абстракте."
    )
    method: Optional[str] = Field(
        default=None,
        description="Используемый метод, архитектура или алгоритм. 'не указано', если не упомянуто в абстракте."
    )
    dataset: Optional[str] = Field(
        default=None,
        description="Датасет, корпус или исследуемая выборка. 'не указано', если не упомянуто в абстракте."
    )
    metrics: Optional[str] = Field(
        default=None,
        description="Метрики оценки (F1, точность, mAP, BLEU и др.). 'не указано', если не упомянуто в абстракте."
    )
    key_result: Optional[str] = Field(
        default=None,
        description="Ключевой доказанный результат или вывод. 'не указано', если не упомянуто в абстракте."
    )
    limitations: Optional[str] = Field(
        default=None,
        description="Ограничения, недостатки или нерешённые вопросы. 'не указано', если не упомянуто в абстракте."
    )


def get_client(api_key=None):
    key = api_key or os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        return None
    try:
        return genai.Client(api_key=key)
    except Exception:
        return None


def generate_content_with_fallback(client, contents, config=None, model=None):
    """
    Executes generate_content with automatic fallback across reliable Gemini models
    to handle 404 deprecations or temporary 503 high-demand spikes.
    """
    initial_model = sanitize_model_name(model)
    candidate_models = [initial_model]
    for alt in ("gemini-3.5-flash", "gemini-3.8-flash", "gemini-flash-latest", "gemini-3.5-flash-lite"):
        if alt not in candidate_models:
            candidate_models.append(alt)

    last_error = None
    for candidate in candidate_models:
        try:
            return client.models.generate_content(
                model=candidate,
                contents=contents,
                config=config
            )
        except Exception as exc:
            last_error = exc
            err_str = str(exc)
            if any(code in err_str for code in ("404", "503", "429")):
                continue
            raise exc
    raise last_error


def tokenize_text(text):
    if not text:
        return []
    return re.findall(r"\b[\w-]{2,}\b", text.lower())


def simple_bm25_rank(query, texts, k=15):
    q_tokens = tokenize_text(query)
    scores = []
    for doc in texts:
        d_tokens = tokenize_text(doc)
        if not d_tokens:
            scores.append(0.0)
            continue
        matches = sum(1 for t in q_tokens if t in d_tokens)
        scores.append(matches / (len(d_tokens) ** 0.5 + 1.0))
    indices = np.argsort(-np.array(scores))[:k]
    return indices.tolist()


def embed(client, texts, model=None, task="RETRIEVAL_DOCUMENT"):
    if not client or not texts:
        return None

    emb_model = model or os.getenv("GEMINI_EMB_MODEL", DEFAULT_EMB_MODEL)
    vectors = [None] * len(texts)
    missing = []

    for idx, text in enumerate(texts):
        h = hashlib.sha256((emb_model + task + text).encode("utf-8")).hexdigest()
        cache_path = EMBEDDINGS_DIR / f"{h}.json"
        if cache_path.exists():
            try:
                vectors[idx] = json.loads(cache_path.read_text(encoding="utf-8"))
            except Exception:
                missing.append((idx, text, cache_path))
        else:
            missing.append((idx, text, cache_path))

    for offset in range(0, len(missing), 20):
        batch = missing[offset:offset + 20]
        batch_strings = [item[1] for item in batch]
        try:
            res = client.models.embed_content(
                model=emb_model,
                contents=batch_strings,
                config=types.EmbedContentConfig(output_dimensionality=768)
            )
            embeddings = getattr(res, "embeddings", None)
            if embeddings:
                for (orig_idx, _, cache_path), emb in zip(batch, embeddings):
                    v = emb.values
                    vectors[orig_idx] = v
                    cache_path.write_text(json.dumps(v), encoding="utf-8")
            elif getattr(res, "embedding", None):
                v = res.embedding.values
                orig_idx, _, cache_path = batch[0]
                vectors[orig_idx] = v
                cache_path.write_text(json.dumps(v), encoding="utf-8")
        except Exception:
            pass

    if any(v is None for v in vectors):
        return None

    return np.array(vectors)


def rerank(client, query, papers, k=15):
    if not papers:
        return []
    if len(papers) <= k and not client:
        return papers

    corpus = [(p.get("title", "") + ". " + p.get("abstract", "")) for p in papers]

    # Keyword presence boost
    q_words = [w.lower() for w in re.findall(r"\b[a-zA-Zа-яА-ЯёЁәғқңөұүһі]{3,}\b", query) if len(w) > 3]

    if client:
        try:
            P = embed(client, corpus, task="RETRIEVAL_DOCUMENT")
            q = embed(client, [query], task="RETRIEVAL_QUERY")
            if P is not None and q is not None and len(P) == len(papers):
                q_vec = q[0]
                q_norm = np.linalg.norm(q_vec)
                P_norms = np.linalg.norm(P, axis=1)
                denom = P_norms * q_norm
                denom[denom == 0] = 1e-9
                sims = (P @ q_vec) / denom

                # Apply boost for title keyword overlap and citations
                final_scores = np.copy(sims)
                for i, p in enumerate(papers):
                    t = p.get("title", "").lower()
                    overlap = sum(1 for w in q_words if w in t)
                    if overlap:
                        final_scores[i] += 0.08 * overlap
                    cites = p.get("cited_by_count", 0)
                    if cites > 10:
                        final_scores[i] += min(0.05, math.log10(cites) * 0.02)

                top_indices = np.argsort(-final_scores)[:k]
                return [papers[i] for i in top_indices]
        except Exception:
            pass

    # Fallback to BM25
    bm_indices = simple_bm25_rank(query, corpus, k=k)
    return [papers[i] for i in bm_indices]


PROMPT_EXTRACT = """Извлеки факты ИСКЛЮЧИТЕЛЬНО из названия и аннотации статьи.
СТРОГОЕ ПРАВИЛО:
- Если поле явно не упомянуто в аннотации, верни null или "не указано".
- Ни в коем случае НЕ додумывай датасеты, проценты, метрики или детали, которых нет в тексте!
- Язык вывода: русский.

Название: {title}
Аннотация: {abstract}"""


def extract_card(client, paper, model=None):
    title = paper.get("title") or "Без названия"
    abstract = paper.get("abstract") or ""
    full_text = paper.get("full_text") or ""

    context_abstract = abstract
    if full_text and len(full_text) > len(abstract):
        context_abstract = f"{abstract}\n\n[Фрагменты полного текста загруженного PDF для точного извлечения методов, датасетов и метрик]:\n{full_text[:5000]}"

    cache_key = hashlib.sha256((title + context_abstract[:500]).encode("utf-8")).hexdigest()
    cache_file = CARDS_CACHE_DIR / f"{cache_key}.json"
    if cache_file.exists():
        try:
            cached = json.loads(cache_file.read_text(encoding="utf-8"))
            if not str(cached.get("key_result", "")).startswith("Ошибка"):
                return cached
        except Exception:
            pass

    default_card = {
        "task": "не указано",
        "method": "не указано",
        "dataset": "не указано",
        "metrics": "не указано",
        "key_result": "не указано",
        "limitations": "не указано"
    }

    if not client:
        return default_card

    llm_model = sanitize_model_name(model)
    prompt = PROMPT_EXTRACT.format(title=title, abstract=context_abstract)

    card_dict = default_card.copy()
    try:
        res = generate_content_with_fallback(
            client=client,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=PaperCard,
                temperature=0.0
            ),
            model=llm_model
        )
        if getattr(res, "parsed", None):
            raw = res.parsed.model_dump()
        else:
            txt = res.text or "{}"
            m = re.search(r"(\{.*\})", txt.strip(), re.DOTALL)
            raw = json.loads(m.group(1)) if m else {}

        for k in default_card:
            val = raw.get(k)
            if val is not None and str(val).strip() and str(val).strip().lower() not in ("none", "null", "none."):
                card_dict[k] = str(val).strip()
            else:
                card_dict[k] = "не указано"

        cache_file.write_text(json.dumps(card_dict, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        card_dict["key_result"] = f"Ошибка извлечения: {exc}"

    return card_dict


def synthesize_connections(client, query, papers, cards_map, model=None):
    """
    Synthesizes scientific connections, thematic clusters, consensus, and debates across papers.
    """
    if not papers:
        return "В выборке нет статей для анализа связей."

    net = analyze_citation_network(papers)
    direct_cites = [d["label"] for d in net.get("direct_citations", [])]
    co_cites = [c["label"] for c in net.get("co_citations", [])]

    paper_summaries = []
    for i, p in enumerate(papers, 1):
        c = cards_map.get(p.get("id"), {})
        doi_str = f"DOI: https://doi.org/{p['doi']}" if p.get("doi") else "нет DOI"
        paper_summaries.append(
            f"[{i}] {p.get('citekey')} | {p.get('title')} ({p.get('year')}) | {doi_str}\n"
            f"   - Метод: {c.get('method', 'не указано')}\n"
            f"   - Датасет: {c.get('dataset', 'не указано')}\n"
            f"   - Результат: {c.get('key_result', 'не указано')}\n"
            f"   - Ограничения: {c.get('limitations', 'не указано')}\n"
            f"   - Цитат в мире: {p.get('cited_by_count', 0)}"
        )

    corpus_text = "\n\n".join(paper_summaries)

    prompt = f"""Ты ведущий академический рецензент и научный аналитик.
Проанализируй взаимосвязи, различия и преемственность между следующими научными статьями по теме: "{query}".

Корпус статей:
{corpus_text}

Обнаруженные перекрёстные связи в метаданных:
- Прямые цитирования внутри выборки: {', '.join(direct_cites) if direct_cites else 'не обнаружены (независимые группы)'}
- Совместные первоисточники (co-citations): {', '.join(co_cites[:5]) if co_cites else 'разные библиографические базы'}

Составь глубокий аналитический отчёт на русском языке по следующей академической структуре:

### 1. Тематические кластеры корпуса
Раздели статьи на 2-4 ключевых смысловых направления/кластера. Укажи, какие статьи входят в каждый кластер (в формате `[N] \\cite{{citekey}}`).

### 2. Точки научного консенсуса (В чём авторы согласны)
Какие факты, тенденции или выводы подтверждаются одновременно несколькими независимыми статьями из корпуса? Обоснуй ссылками на авторов.

### 3. Противоречия, расхождения и научные дискуссии
В чём выводы, методологии или оценки авторов расходятся? Например: различия в метриках, оценки влияния (локальные vs глобальные), критика предшествующих подходов.

### 4. Методологическая эволюция и преемственность
Как развивалась научная мысль по хронологии статей: от более ранних работ к современным? Кто развивает чужие методы, а кто предлагает принципиально новый подход?

### 5. Перспективные нерешённые вопросы (Research Gaps)
Какие аспекты темы остались незатронутыми или требуют дальнейших эмпирических исследований?

Каждое утверждение обязательно сопровождай точной ссылкой на статью в виде `[N] (Название)` или `\\cite{{citekey}}`."""

    if not client:
        out = [
            f"### Анализ взаимосвязей публикаций по теме «{query}»",
            f"Всего проанализировано статей: **{len(papers)}**.\n",
            "#### Сеть цитирований:"
        ]
        if direct_cites:
            out.append("**Прямые цитирования между выбранными работами:**")
            for dc in direct_cites:
                out.append(f"- 🔗 {dc}")
        else:
            out.append("- Прямых перекрёстных цитирований внутри текущей выборки не найдено (исследования проводились параллельными научными коллективами).")

        if co_cites:
            out.append("\n**Общая библиографическая база (совместное цитирование):**")
            for cc in co_cites[:6]:
                out.append(f"- 📚 {cc}")

        out.append("\n#### Наиболее авторитетные работы в выборке (по цитируемости):")
        for p in net.get("top_cited", [])[:5]:
            doi_link = f"https://doi.org/{p['doi']}" if p.get("doi") else ""
            out.append(f"- **{p['title']}** ({p['year']}) — **{p.get('cited_by_count', 0)} цитирований** [DOI: {doi_link}]")

        out.append("\n*(Для формирования развёрнутого смыслового синтеза и кластеров укажите Gemini API key в боковой панели).*")
        return "\n".join(out)

    llm_model = sanitize_model_name(model)
    try:
        res = generate_content_with_fallback(
            client=client,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.15),
            model=llm_model
        )
        return res.text or "Не удалось сгенерировать синтез связей."
    except Exception as exc:
        return f"Ошибка построения связей: {exc}"


def chat_with_papers(client, conversation_messages, papers, cards_map, model=None):
    """
    Multi-turn interactive research chat discussing the selected papers.
    Strictly grounded in abstracts and extracted PaperCards, with verified DOI citations.
    """
    if not client:
        return "Для обсуждения статей в чате укажите Gemini API key в боковой панели."

    corpus_blocks = []
    for i, p in enumerate(papers, 1):
        c = cards_map.get(p.get("id"), {})
        doi_url = f"https://doi.org/{p['doi']}" if p.get("doi") else (p.get("url") or "нет DOI")
        full_text_snippet = ""
        if p.get("full_text"):
            full_text_snippet = f"\nФрагмент текста загруженного PDF:\n{p['full_text'][:1500]}...\n"
        block = (
            f"[Статья {i}] {p.get('title')} ({p.get('year')})\n"
            f"Citekey: \\cite{{{p.get('citekey')}}}\n"
            f"Авторы: {p.get('authors_str')}\n"
            f"DOI: {doi_url}\n"
            f"Задача: {c.get('task', 'не указано')}\n"
            f"Метод: {c.get('method', 'не указано')}\n"
            f"Датасет: {c.get('dataset', 'не указано')}\n"
            f"Метрики: {c.get('metrics', 'не указано')}\n"
            f"Ключевой результат: {c.get('key_result', 'не указано')}\n"
            f"Ограничения: {c.get('limitations', 'не указано')}\n"
            f"Аннотация: {p.get('abstract', '')}\n"
            f"{full_text_snippet}"
        )
        corpus_blocks.append(block)

    grounding_corpus = "\n\n---\n\n".join(corpus_blocks)

    system_instruction = f"""Ты — интеллектуальный академический собеседник и научный ассистент TensorText.
Ты ведешь предметный диалог с исследователем по выбранному корпусу научных статей.

Твои правила:
1. Строгая доказательность: опирайся ИСКЛЮЧИТЕЛЬНО на факты из предоставленных статей (карточки и аннотации).
2. Обязательные ссылки: каждое фактическое утверждение, сравнение или вывод подкрепляй точной ссылкой в формате [Статья N: Название](DOI) или \\cite{{citekey}}.
3. Борьба с галлюцинациями: если в статьях нет ответа на вопрос или методология не раскрыта, прямо скажи: «В предоставленных статьях эти сведения не указаны». Не придумывай несуществующие эксперименты.
4. Академический стиль: отвечай структурированно, профессионально, логично и на русском языке.
5. Аналитическая глубина: помогай сопоставлять работы, находить противоречия, выявлять ограничения и генерировать гипотезы на стыке статей.

База знаний (выбранный корпус публикаций):
{grounding_corpus}"""

    formatted_history = []
    for m in conversation_messages[-8:]:
        role_label = "Пользователь" if m["role"] == "user" else "Ассистент"
        formatted_history.append(f"{role_label}: {m['content']}")

    history_str = "\n\n".join(formatted_history)

    prompt = f"""История диалога:
{history_str}

Ответь на последнюю реплику пользователя с точными ссылками на статьи:"""

    llm_model = sanitize_model_name(model)
    try:
        res = generate_content_with_fallback(
            client=client,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                system_instruction=system_instruction
            ),
            model=llm_model
        )
        return res.text or "Модель не смогла сформировать ответ."
    except Exception as exc:
        return f"Ошибка генерации ответа: {exc}"


def qa_over_cards(client, query, papers, cards_map, model=None):
    return chat_with_papers(client, [{"role": "user", "content": query}], papers, cards_map, model=model)


def generate_method_dataset_matrix(client, papers, cards_map, model=None):
    if not client:
        return None

    items = []
    for i, p in enumerate(papers, 1):
        c = cards_map.get(p.get("id"), {})
        items.append({
            "paper": f"[{i}] {p.get('title')[:40]}…",
            "method": c.get("method", "не указано"),
            "dataset": c.get("dataset", "не указано")
        })

    prompt = f"""Проанализируй список пар «Метод — Датасет» из научных статей:
{json.dumps(items, ensure_ascii=False, indent=2)}

Задача:
1. Нормализуй названия методов (например: Life Cycle Assessment (LCA), Power Usage Effectiveness (PUE), Thermal Modeling, Carbon Accounting).
2. Нормализуй названия датасетов/выборок (например: EPA Data, Hyperscale Telemetry, US Grid Data).
3. Построй матрицу «Метод × Датасет», где на пересечении указаны номера статей.
4. Выдели пробелы (white spaces / research gaps) — какие методы ещё не проверялись на данных датасетах.

Верни компактный академический аналитический отчет на русском языке с Markdown-таблицей."""

    llm_model = sanitize_model_name(model)
    try:
        res = generate_content_with_fallback(
            client=client,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.1),
            model=llm_model
        )
        return res.text or ""
    except Exception as exc:
        return f"Ошибка построения матрицы: {exc}"
