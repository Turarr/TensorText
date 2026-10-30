import hashlib
import io
import json
import os
import re
from pathlib import Path
from typing import Optional, List, Dict
import requests

try:
    import pymupdf
except ImportError:
    pymupdf = None

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

ROOT = Path(__file__).resolve().parent
SEARCH_CACHE_DIR = ROOT / "tensortext_data" / "search_cache"
SEARCH_CACHE_DIR.mkdir(parents=True, exist_ok=True)

CYR_TO_LAT = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
    'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
    'ә': 'ae', 'ғ': 'gh', 'қ': 'q', 'ң': 'ng', 'ө': 'oe', 'ұ': 'u', 'ү': 'ue', 'һ': 'h', 'і': 'i'
}

# Mapping common casual/informal terms to rigorous academic concepts
CASUAL_TO_ACADEMIC = {
    # English
    'pollutes': ['environmental impact', 'carbon footprint', 'greenhouse gas emissions', 'pollution'],
    'pollute': ['environmental impact', 'pollution', 'carbon footprint'],
    'polluting': ['environmental impact', 'emissions', 'carbon footprint'],
    'nature': ['environment', 'ecological impact', 'sustainability', 'biosphere'],
    'centers': ['center', 'infrastructure', 'facilities'],
    'bad': ['adverse effects', 'environmental damage', 'risks', 'inefficiencies'],
    'harms': ['environmental impact', 'damage', 'hazards'],
    'kills': ['negative impact', 'environmental degradation'],
    'global warming': ['climate change', 'greenhouse gas emissions', 'carbon footprint'],
    'dirty': ['carbon-intensive', 'high-emission'],
    'green': ['sustainable', 'energy-efficient', 'renewable'],

    # Russian
    'загрязняют': ['воздействие на окружающую среду', 'углеродный след', 'выбросы парниковых газов', 'экология'],
    'загрязнение': ['экологический след', 'выбросы', 'environmental impact'],
    'природу': ['окружающая среда', 'экосистема', 'экологический баланс'],
    'природа': ['окружающая среда', 'экосистема'],
    'дата центры': ['центры обработки данных', 'ЦОД', 'data center infrastructure'],
    'датацентры': ['центры обработки данных', 'ЦОД', 'data center'],
    'вред': ['негативное воздействие', 'экологический ущерб', 'риски'],
    'плохо': ['негативное влияние', 'риски', 'ущерб'],

    # Kazakh
    'ластайды': ['қоршаған ортаға әсері', 'көміртегі ізі', 'экологиялық зардап'],
    'табиғатты': ['қоршаған орта', 'экожүйе', 'экология'],
    'деректер орталықтары': ['мәліметтер өңдеу орталығы', 'data center'],
    'жаман': ['теріс әсері', 'экологиялық қауіптер']
}


def transliterate(text):
    if not text:
        return "ref"
    res = []
    for ch in text.lower():
        res.append(CYR_TO_LAT.get(ch, ch))
    return re.sub(r"[^a-z0-9]", "", "".join(res))


def make_citekey(paper, index=1):
    authors = paper.get("authors", [])
    first_author = authors[0] if authors else "Author"
    last_name = first_author.split()[-1] if first_author else "Author"
    clean_author = transliterate(last_name) or "ref"
    year = str(paper.get("year") or "2026")

    title_words = re.findall(r"\b[a-zA-Zа-яА-ЯёЁәғқңөұүһі]{3,}\b", paper.get("title", ""))
    slug = ""
    for w in title_words:
        tr = transliterate(w)
        if tr and tr not in ("the", "and", "for", "with", "from", "vliyanie", "issledovanie", "analiz"):
            slug = tr[:8]
            break
    if not slug:
        slug = f"w{index}"

    return f"{clean_author}{year}{slug}"


def abstract(inv):
    if not inv or not isinstance(inv, dict):
        return ""
    try:
        sorted_words = sorted((pos, word) for word, positions in inv.items() for pos in positions)
        return " ".join(word for _, word in sorted_words).strip()
    except Exception:
        return ""


def expand_academic_queries(query, client=None):
    """
    Intelligently expands casual/conversational queries into rigorous academic search terms.
    For 'data centers pollutes the nature' -> generates queries about data center environmental impact,
    carbon footprint, and energy consumption.
    """
    raw_clean = query.strip()
    queries = [raw_clean]
    domain_keywords = []

    # 1. LLM-powered academic query formulation (if client is available)
    if client:
        prompt = f"""You are an expert scientific librarian and academic search specialist.
The user entered this research topic: "{raw_clean}"

Task:
1. Translate casual, colloquial, or broad terms into formal scientific keywords used in academic literature (IEEE, ACM, Nature, Elsevier, OpenAlex).
2. Generate 2-3 optimal academic search queries in English (and Russian if query is Russian).
3. Identify 3-6 core domain keywords that ANY relevant paper MUST address to eliminate completely unrelated papers (e.g. for data center emissions, domain keywords must include data center, computing, cloud, server, etc.).

Format strictly as JSON:
{{
  "academic_queries": [
    "data center environmental impact carbon footprint",
    "cloud computing energy consumption greenhouse gas emissions"
  ],
  "domain_keywords": ["data center", "computing", "cloud", "server", "carbon footprint"]
}}"""
        candidate_models = ["gemini-3.5-flash", "gemini-3.8-flash", "gemini-flash-latest"]
        for llm_model in candidate_models:
            try:
                res = client.models.generate_content(
                    model=llm_model,
                    contents=prompt,
                    config={"response_mime_type": "application/json", "temperature": 0.0}
                )
                data = json.loads(res.text)
                for q_gen in data.get("academic_queries", []):
                    if q_gen and q_gen not in queries:
                        queries.append(q_gen)
                domain_keywords = [k.lower() for k in data.get("domain_keywords", []) if k]
                return queries, domain_keywords
            except Exception:
                continue

    # 2. Rule-based & Synonym Academic Expansion (works 100% offline without API key)
    words = [w.lower() for w in re.findall(r"\b[a-zA-Zа-яА-ЯёЁәғқңөұүһі]{2,}\b", raw_clean)]
    stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'in', 'on', 'at', 'by', 'for', 'with', 'about', 'to', 'from', 'of'}
    core_words = [w for w in words if w not in stopwords]

    # Detect domain concepts
    if any(k in raw_clean.lower() for k in ['data center', 'data centers', 'datacenter', 'datacenters', 'дата центр', 'цод']):
        queries.append("data center environmental impact carbon footprint")
        queries.append("data centers energy consumption carbon emissions sustainability")
        domain_keywords.extend(['data center', 'datacenter', 'computing', 'cloud', 'server', 'digital infrastructure'])

    elif any(k in raw_clean.lower() for k in ['student', 'students', 'grading', 'оцениван', 'студент', 'білім']):
        queries.append("artificial intelligence in student assessment and academic grading")
        domain_keywords.extend(['student', 'assessment', 'grading', 'education', 'learning', 'academic'])

    elif any(k in raw_clean.lower() for k in ['plant', 'plants', 'crop', 'растен', 'болезн', 'дақыл']):
        queries.append("deep learning plant disease detection computer vision agriculture")
        domain_keywords.extend(['plant', 'disease', 'leaf', 'crop', 'agriculture', 'vision'])

    # Generic term substitution
    academic_sub = []
    for w in core_words:
        if w in CASUAL_TO_ACADEMIC:
            academic_sub.append(CASUAL_TO_ACADEMIC[w][0])
            domain_keywords.extend(CASUAL_TO_ACADEMIC[w][:2])
        else:
            academic_sub.append(w)
            domain_keywords.append(w)

    q_sub = " ".join(academic_sub)
    if q_sub and q_sub not in queries:
        queries.append(q_sub)

    # Clean domain keywords
    clean_domain = list(dict.fromkeys([k.lower() for k in domain_keywords if len(k) >= 3 and k not in stopwords]))
    return queries, clean_domain


def search_openalex(query, n=30, lang=None, api_key=None, client=None):
    if not query or not query.strip():
        return []

    # 1. Expand queries to academic standard terms
    expanded_queries, domain_keywords = expand_academic_queries(query, client=client)

    cache_hash = hashlib.sha256(f"{query}_{lang}_{n}".encode("utf-8")).hexdigest()
    cache_path = SEARCH_CACHE_DIR / f"{cache_hash}.json"

    # Check disk cache first to prevent rate limits
    if cache_path.exists():
        try:
            cached_data = json.loads(cache_path.read_text(encoding="utf-8"))
            if cached_data and len(cached_data) >= 5:
                return cached_data
        except Exception:
            pass

    key = api_key or os.getenv("OPENALEX_API_KEY", "").strip() or None
    headers = {"User-Agent": "TensorText/2.0 (mailto:support@tensortext.local)"}

    flt = ["has_abstract:true"]
    if lang and lang in ("ru", "en", "kk"):
        flt.append(f"language:{lang}")

    raw_candidates = []
    seen_ids = set()

    # Search OpenAlex across the expanded query variants
    # Start with the most formal academic formulation first, then original
    search_queries_ordered = list(reversed(expanded_queries))

    for q_term in search_queries_ordered:
        params = {
            "search": q_term,
            "filter": ",".join(flt),
            "per_page": min(40, max(10, n)),
            "select": "id,doi,title,publication_year,abstract_inverted_index,language,open_access,authorships,primary_location,cited_by_count,referenced_works,related_works"
        }
        if key:
            params["api_key"] = key

        try:
            r = requests.get("https://api.openalex.org/works", params=params, headers=headers, timeout=20)
            if r.ok:
                for w in r.json().get("results", []):
                    wid = w.get("id")
                    if not wid or wid in seen_ids:
                        continue
                    seen_ids.add(wid)
                    raw_candidates.append(w)
            elif r.status_code == 429:
                # Rate limited
                break
        except Exception:
            continue

        if len(raw_candidates) >= n * 2:
            break

    # If OpenAlex returned nothing (or rate limit 429), fall back to Crossref
    if not raw_candidates:
        try:
            cr_url = "https://api.crossref.org/works"
            cr_params = {
                "query": expanded_queries[-1] if expanded_queries else query,
                "rows": n,
                "select": "DOI,title,author,issued,URL,abstract"
            }
            cr_resp = requests.get(cr_url, params=cr_params, headers=headers, timeout=15)
            if cr_resp.ok:
                for it in cr_resp.json().get("message", {}).get("items", []):
                    doi = it.get("DOI", "")
                    title = (it.get("title") or ["Без названия"])[0]
                    authors = [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in it.get("author", []) if a.get("family")]
                    issued = it.get("issued", {}).get("date-parts", [[2024]])[0][0]
                    raw_candidates.append({
                        "id": f"https://doi.org/{doi}" if doi else f"cr_{hashlib.md5(title.encode()).hexdigest()[:10]}",
                        "doi": doi,
                        "title": title,
                        "publication_year": issued,
                        "abstract_inverted_index": None,
                        "abstract_text": it.get("abstract", "").replace("<jats:p>", "").replace("</jats:p>", ""),
                        "language": lang or "en",
                        "authorships": [{"author": {"display_name": a}} for a in authors],
                        "cited_by_count": 0,
                        "referenced_works": [],
                        "primary_location": {"landing_page_url": it.get("URL") or f"https://doi.org/{doi}"}
                    })
        except Exception:
            pass

    # 3. Subject Relevance Filter: discard non-domain outliers (e.g. white dwarfs, soil vegetables)
    filtered_candidates = []
    for w in raw_candidates:
        title = (w.get("title") or "").lower()
        abs_raw = abstract(w.get("abstract_inverted_index")) or w.get("abstract_text", "")
        abs_lower = abs_raw.lower()
        full_text = f"{title} {abs_lower}"

        # If domain keywords were extracted, verify that the paper touches the primary topic
        if domain_keywords:
            has_domain_overlap = any(kw in full_text for kw in domain_keywords)
            if not has_domain_overlap:
                continue

        w["_clean_abstract"] = abs_raw
        filtered_candidates.append(w)

    # If domain filter was too strict, fallback to raw_candidates
    candidates_to_use = filtered_candidates if len(filtered_candidates) >= 3 else raw_candidates

    # Convert to standard TensorText Paper objects
    papers = []
    for i, w in enumerate(candidates_to_use[:n], 1):
        raw_doi = w.get("doi") or ""
        clean_doi = raw_doi.replace("https://doi.org/", "").strip()
        title = w.get("title") or "Без названия"
        year = w.get("publication_year") or "н/д"
        abs_text = w.get("_clean_abstract") or abstract(w.get("abstract_inverted_index")) or w.get("abstract_text")

        authors = []
        for a in w.get("authorships", []):
            name = a.get("author", {}).get("display_name")
            if name:
                authors.append(name.strip())
        authors_str = ", ".join(authors) if authors else "Не указано"

        oa = w.get("open_access") or {}
        prim = w.get("primary_location") or {}
        pdf_url = oa.get("oa_url") or prim.get("pdf_url")
        landing_url = (f"https://doi.org/{clean_doi}" if clean_doi else (prim.get("landing_page_url") or w.get("id")))
        journal = (prim.get("source") or {}).get("display_name") or ""

        paper_obj = {
            "id": w.get("id") or f"openalex_{i}",
            "doi": clean_doi,
            "doi_url": f"https://doi.org/{clean_doi}" if clean_doi else None,
            "title": title,
            "year": year,
            "lang": w.get("language") or "",
            "authors": authors,
            "authors_str": authors_str,
            "abstract": abs_text if abs_text else "Аннотация отсутствует.",
            "pdf_url": pdf_url,
            "url": landing_url,
            "journal": journal,
            "cited_by_count": w.get("cited_by_count", 0),
            "referenced_works": w.get("referenced_works", []),
            "related_works": w.get("related_works", []),
            "citekey": ""
        }
        paper_obj["citekey"] = make_citekey(paper_obj, i)
        papers.append(paper_obj)

    # Cache on disk
    if papers:
        try:
            cache_path.write_text(json.dumps(papers, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    return papers


def analyze_citation_network(papers):
    """
    Analyzes connections, cross-citations, and co-citations among the selected corpus of papers.
    """
    if not papers:
        return {"direct_citations": [], "co_citations": [], "top_cited": []}

    id_to_paper = {p["id"]: p for p in papers}

    # 1. Direct cross-citations (which paper in the selection cites another in the selection)
    direct_citations = []
    for p in papers:
        refs = set(p.get("referenced_works") or [])
        for other in papers:
            if other["id"] != p["id"] and other["id"] in refs:
                direct_citations.append({
                    "source": p,
                    "target": other,
                    "label": f"[{p.get('citekey')}] цитирует [{other.get('citekey')}]"
                })

    # 2. Co-citations (papers sharing 2+ references in their bibliographies)
    co_citations = []
    for i in range(len(papers)):
        for j in range(i + 1, len(papers)):
            p1 = papers[i]
            p2 = papers[j]
            r1 = set(p1.get("referenced_works") or [])
            r2 = set(p2.get("referenced_works") or [])
            common = r1 & r2
            if len(common) >= 2:
                co_citations.append({
                    "paper1": p1,
                    "paper2": p2,
                    "shared_count": len(common),
                    "label": f"[{p1.get('citekey')}] и [{p2.get('citekey')}] — {len(common)} общих первоисточников"
                })

    # 3. Top cited / Most authoritative papers
    top_cited = sorted(papers, key=lambda x: x.get("cited_by_count", 0), reverse=True)

    return {
        "direct_citations": direct_citations,
        "co_citations": co_citations,
        "top_cited": top_cited
    }


def get_bibtex_from_doi(doi):
    if not doi:
        return None
    clean = doi.replace("https://doi.org/", "").strip()
    try:
        r = requests.get(
            f"https://doi.org/{clean}",
            headers={"Accept": "application/x-bibtex"},
            timeout=15
        )
        if r.ok and r.text.strip().startswith("@"):
            return r.text.strip()
    except Exception:
        pass
    return None


def synthesize_bibtex(paper, citekey=None):
    key = citekey or paper.get("citekey") or "reference"
    authors = " and ".join(paper.get("authors", [])) or paper.get("authors_str") or "Unknown"
    title = paper.get("title", "Untitled").replace("{", "").replace("}", "")
    year = str(paper.get("year") or "2026")
    doi = paper.get("doi") or ""
    url = paper.get("url") or (f"https://doi.org/{doi}" if doi else "")
    journal = paper.get("journal") or "OpenAlex Database"

    lines = [
        f"@article{{{key},",
        f"  title = {{{{{title}}}}},",
        f"  author = {{{authors}}},",
        f"  journal = {{{journal}}},",
        f"  year = {{{year}}},"
    ]
    if doi:
        lines.append(f"  doi = {{{doi}}},")
    if url:
        lines.append(f"  url = {{{url}}},")
    lines.append("}")
    return "\n".join(lines)


def get_paper_bibtex(paper, citekey=None):
    key = citekey or paper.get("citekey") or "reference"
    doi = paper.get("doi")
    raw_bib = get_bibtex_from_doi(doi) if doi else None

    if raw_bib:
        modified = re.sub(r"^@(\w+)\s*\{[^,]+,", f"@\\1{{{key},", raw_bib, count=1)
        return modified
    return synthesize_bibtex(paper, key)


def extract_doi_from_text(text: str) -> Optional[str]:
    """Finds and cleans a DOI from arbitrary text, link or citation."""
    if not text:
        return None
    if "doi.org/" in text:
        sub = text.split("doi.org/")[-1].strip().split()[0]
        sub = sub.rstrip(".;,)>]\"'")
        if "/" in sub and sub.startswith("10."):
            return sub
    m = re.search(r'\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\b', text)
    if m:
        doi = m.group(0).rstrip(".;,)>]\"'")
        return doi
    return None


def fetch_work_by_doi(doi: str, api_key: Optional[str] = None) -> Optional[dict]:
    """
    Fetches full academic metadata, abstract and citation graph from OpenAlex by DOI.
    Falls back to doi.org / Crossref content negotiation if OpenAlex is unavailable.
    """
    clean_doi = extract_doi_from_text(doi) or doi.replace("https://doi.org/", "").strip()
    if not clean_doi:
        return None

    headers = {"User-Agent": "TensorText/1.0 (mailto:scholar@tensortext.org)"}
    # 1. Try OpenAlex by DOI
    try:
        oa_url = f"https://api.openalex.org/works/doi:{clean_doi}"
        params = {}
        if api_key:
            params["api_key"] = api_key
        r = requests.get(oa_url, headers=headers, params=params, timeout=12)
        if r.ok:
            w = r.json()
            title = w.get("title") or "Без названия"
            year = w.get("publication_year") or "н/д"
            abs_text = abstract(w.get("abstract_inverted_index")) or ""
            authors = []
            for a in w.get("authorships", []):
                name = a.get("author", {}).get("display_name")
                if name:
                    authors.append(name.strip())
            authors_str = ", ".join(authors) if authors else "Не указано"

            prim = w.get("primary_location") or {}
            journal = (prim.get("source") or {}).get("display_name") or ""
            oa = w.get("open_access") or {}
            pdf_url = oa.get("oa_url") or prim.get("pdf_url") or ""

            paper_obj = {
                "id": w.get("id") or f"oa_doi_{clean_doi.replace('/', '_')}",
                "doi": clean_doi,
                "doi_url": f"https://doi.org/{clean_doi}",
                "title": title,
                "year": year,
                "lang": w.get("language") or "en",
                "authors": authors,
                "authors_str": authors_str,
                "abstract": abs_text if abs_text else "Аннотация отсутствует.",
                "pdf_url": pdf_url,
                "url": f"https://doi.org/{clean_doi}",
                "journal": journal or "OpenAlex",
                "cited_by_count": w.get("cited_by_count", 0),
                "referenced_works": w.get("referenced_works", []),
                "related_works": w.get("related_works", []),
                "source_origin": "DOI / OpenAlex",
                "citekey": ""
            }
            paper_obj["citekey"] = make_citekey(paper_obj, 1)
            return paper_obj
    except Exception:
        pass

    # 2. Fallback to doi.org Crossref CSL JSON
    try:
        cr_url = f"https://doi.org/{clean_doi}"
        cr_headers = {"Accept": "application/vnd.citationstyles.csl+json", "User-Agent": "TensorText/1.0"}
        r2 = requests.get(cr_url, headers=cr_headers, timeout=10)
        if r2.ok:
            d = r2.json()
            title = d.get("title") or "Без названия"
            issued = d.get("issued", {}).get("date-parts", [[2024]])[0][0]
            authors = [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in d.get("author", []) if a.get("family")]
            authors_str = ", ".join(authors) if authors else "Не указано"
            journal = d.get("container-title") or ""
            abs_text = d.get("abstract", "").replace("<jats:p>", "").replace("</jats:p>", "")
            paper_obj = {
                "id": f"doi_{clean_doi.replace('/', '_')}",
                "doi": clean_doi,
                "doi_url": f"https://doi.org/{clean_doi}",
                "title": title,
                "year": issued,
                "lang": "en",
                "authors": authors,
                "authors_str": authors_str,
                "abstract": abs_text if abs_text else "Аннотация отсутствует.",
                "pdf_url": "",
                "url": f"https://doi.org/{clean_doi}",
                "journal": journal or "Crossref",
                "cited_by_count": 0,
                "referenced_works": [],
                "related_works": [],
                "source_origin": "DOI / Crossref",
                "citekey": ""
            }
            paper_obj["citekey"] = make_citekey(paper_obj, 1)
            return paper_obj
    except Exception:
        pass

    return None


def search_openalex_exact_title(title: str, api_key: Optional[str] = None) -> Optional[dict]:
    """Finds a matching paper in OpenAlex by title to retrieve its official DOI and metadata."""
    if not title or len(title.strip()) < 8:
        return None
    headers = {"User-Agent": "TensorText/1.0 (mailto:scholar@tensortext.org)"}
    params = {"search": title.strip(), "per_page": 2}
    if api_key:
        params["api_key"] = api_key
    try:
        r = requests.get("https://api.openalex.org/works", headers=headers, params=params, timeout=10)
        if r.ok:
            results = r.json().get("results", [])
            if results:
                w = results[0]
                raw_doi = w.get("doi") or ""
                clean_doi = raw_doi.replace("https://doi.org/", "").strip()
                abs_text = abstract(w.get("abstract_inverted_index")) or ""
                authors = [a.get("author", {}).get("display_name", "") for a in w.get("authorships", []) if a.get("author", {}).get("display_name")]
                prim = w.get("primary_location") or {}
                journal = (prim.get("source") or {}).get("display_name") or ""
                paper_obj = {
                    "id": w.get("id") or f"oa_title_{hashlib.md5(title.encode()).hexdigest()[:8]}",
                    "doi": clean_doi,
                    "doi_url": f"https://doi.org/{clean_doi}" if clean_doi else None,
                    "title": w.get("title") or title,
                    "year": w.get("publication_year") or "",
                    "lang": w.get("language") or "en",
                    "authors": authors,
                    "authors_str": ", ".join(authors) if authors else "Не указано",
                    "abstract": abs_text if abs_text else "Аннотация отсутствует.",
                    "pdf_url": (w.get("open_access") or {}).get("oa_url") or "",
                    "url": f"https://doi.org/{clean_doi}" if clean_doi else "",
                    "journal": journal or "OpenAlex",
                    "cited_by_count": w.get("cited_by_count", 0),
                    "referenced_works": w.get("referenced_works", []),
                    "related_works": w.get("related_works", []),
                    "source_origin": "Title Match / OpenAlex",
                    "citekey": ""
                }
                paper_obj["citekey"] = make_citekey(paper_obj, 1)
                return paper_obj
    except Exception:
        pass
    return None


def parse_bibtex_content(bib_text: str, api_key: Optional[str] = None) -> List[dict]:
    """
    Parses a BibTeX string (.bib file) and enriches all entries with verified DOIs and OpenAlex abstracts.
    """
    entries = []
    entry_pattern = re.compile(r'@([a-zA-Z]+)\s*\{\s*([^,\s]+)\s*,', re.MULTILINE)
    matches = list(entry_pattern.finditer(bib_text))

    for i, m in enumerate(matches):
        entry_type = m.group(1).lower()
        citekey = m.group(2).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(bib_text)
        body = bib_text[start:end].rstrip()
        if body.endswith('}'):
            body = body[:-1]

        fields = {}
        lines = re.split(r',\s*(?=[a-zA-Z0-9_-]+\s*=)', body)
        for line in lines:
            line = line.strip()
            if '=' in line:
                k, v = line.split('=', 1)
                k = k.strip().lower()
                v = v.strip().strip('"').strip('{}')
                v = re.sub(r'\s+', ' ', v).strip()
                fields[k] = v

        raw_doi = fields.get('doi', '') or fields.get('url', '')
        doi = extract_doi_from_text(raw_doi) or ""
        title = fields.get('title', '')
        author_field = fields.get('author', '')
        authors = [a.strip() for a in re.split(r'\s+and\s+', author_field, flags=re.IGNORECASE) if a.strip()]
        year = fields.get('year', '')
        abs_text = fields.get('abstract', '')
        journal = fields.get('journal') or fields.get('booktitle') or 'BibTeX Import'

        # If DOI is present, enrich with OpenAlex
        paper = None
        if doi:
            paper = fetch_work_by_doi(doi, api_key=api_key)

        # If no DOI or fetch failed, but title is present, try finding DOI in OpenAlex
        if not paper and title and len(title) > 10:
            paper = search_openalex_exact_title(title, api_key=api_key)

        if paper:
            if citekey:
                paper["citekey"] = citekey
            if abs_text and (not paper.get("abstract") or paper["abstract"] == "Аннотация отсутствует."):
                paper["abstract"] = abs_text
            paper["source_origin"] = "BibTeX + OpenAlex DOI"
            entries.append(paper)
        else:
            paper_id = hashlib.sha256((title + str(year)).encode("utf-8")).hexdigest()[:16]
            standalone = {
                "id": f"bib_{paper_id}",
                "doi": doi,
                "doi_url": f"https://doi.org/{doi}" if doi else None,
                "title": title or citekey,
                "year": year or "н/д",
                "lang": "en",
                "authors": authors,
                "authors_str": ", ".join(authors) if authors else "Не указано",
                "abstract": abs_text if abs_text else "Аннотация отсутствует (из BibTeX).",
                "pdf_url": fields.get("eprint") or fields.get("url") or "",
                "url": f"https://doi.org/{doi}" if doi else fields.get("url", ""),
                "journal": journal,
                "cited_by_count": 0,
                "referenced_works": [],
                "related_works": [],
                "source_origin": "BibTeX Import",
                "citekey": citekey or make_citekey({"title": title, "year": year, "authors": authors}, i + 1)
            }
            entries.append(standalone)

    return entries


def parse_pdf_bytes(pdf_bytes: bytes, filename: str = "", api_key: Optional[str] = None) -> dict:
    """
    Extracts text from PDF bytes, finds DOI, and enriches paper metadata via OpenAlex.
    Retains full text excerpt for deep LLM reasoning and PaperCard extraction.
    """
    first_pages_text = ""
    full_text = ""

    # 1. Extract text with pymupdf or pypdf
    try:
        if pymupdf:
            doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
            for page_idx in range(len(doc)):
                p_text = doc[page_idx].get_text()
                if page_idx < 4:
                    first_pages_text += p_text + "\n"
                if len(full_text) < 30000:
                    full_text += p_text + "\n"
            doc.close()
    except Exception:
        pass

    if not first_pages_text and PdfReader:
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            for page_idx in range(len(reader.pages)):
                p_text = reader.pages[page_idx].extract_text() or ""
                if page_idx < 4:
                    first_pages_text += p_text + "\n"
                if len(full_text) < 30000:
                    full_text += p_text + "\n"
        except Exception:
            pass

    # 2. Extract DOI from PDF text
    found_doi = extract_doi_from_text(first_pages_text) or extract_doi_from_text(full_text[:4000])

    paper = None
    if found_doi:
        paper = fetch_work_by_doi(found_doi, api_key=api_key)

    # 3. If no DOI or fetch failed, extract title heuristic
    if not paper:
        clean_lines = [l.strip() for l in first_pages_text.splitlines() if l.strip()]
        candidate_title = ""
        candidate_abstract = ""

        title_candidates = [l for l in clean_lines[:8] if len(l) > 12 and not l.lower().startswith(("arxiv:", "http", "vol.", "issn", "doi:"))]
        if title_candidates:
            candidate_title = title_candidates[0]

        abs_match = re.search(r'(?:abstract|аннотация)[:\s]+([\s\S]{80,1800}?)(?:\n\s*(?:introduction|введение|keywords|ключевые слова|1[\.\s]))', first_pages_text, re.IGNORECASE)
        if abs_match:
            candidate_abstract = re.sub(r'\s+', ' ', abs_match.group(1)).strip()

        if candidate_title and len(candidate_title) > 12:
            paper = search_openalex_exact_title(candidate_title, api_key=api_key)

        if not paper:
            display_title = candidate_title or Path(filename).stem.replace("_", " ").title() or "Загруженная статья (PDF)"
            paper_id = hashlib.sha256((display_title + str(len(pdf_bytes))).encode("utf-8")).hexdigest()[:16]
            paper = {
                "id": f"pdf_{paper_id}",
                "doi": found_doi or "",
                "doi_url": f"https://doi.org/{found_doi}" if found_doi else None,
                "title": display_title,
                "year": "н/д",
                "lang": "en",
                "authors": ["Автор из PDF"],
                "authors_str": "Не указано (извлечено из PDF)",
                "abstract": candidate_abstract if candidate_abstract else (first_pages_text[:800].strip() or "Текст извлечён из загруженного PDF."),
                "pdf_url": "",
                "url": f"https://doi.org/{found_doi}" if found_doi else "",
                "journal": f"PDF: {filename}" if filename else "Загруженный PDF",
                "cited_by_count": 0,
                "referenced_works": [],
                "related_works": [],
                "source_origin": "Загруженный PDF",
                "citekey": ""
            }
            paper["citekey"] = make_citekey(paper, 1)

    paper["full_text"] = full_text
    paper["filename"] = filename
    if not paper.get("source_origin"):
        paper["source_origin"] = "PDF + OpenAlex DOI" if found_doi else "PDF Upload"
    return paper


def import_dois_list(doi_lines: List[str], api_key: Optional[str] = None) -> List[dict]:
    """Imports a batch of DOIs or URLs, fetching verified metadata from OpenAlex."""
    papers = []
    seen_dois = set()
    for line in doi_lines:
        line = line.strip()
        if not line:
            continue
        doi = extract_doi_from_text(line)
        if doi and doi not in seen_dois:
            seen_dois.add(doi)
            p = fetch_work_by_doi(doi, api_key=api_key)
            if p:
                papers.append(p)
            else:
                p_id = hashlib.sha256(doi.encode()).hexdigest()[:16]
                papers.append({
                    "id": f"doi_{p_id}",
                    "doi": doi,
                    "doi_url": f"https://doi.org/{doi}",
                    "title": f"Публикация {doi}",
                    "year": "н/д",
                    "lang": "en",
                    "authors": [],
                    "authors_str": "Не указано",
                    "abstract": f"Метаданные для DOI {doi} не найдены в OpenAlex/Crossref.",
                    "pdf_url": "",
                    "url": f"https://doi.org/{doi}",
                    "journal": "DOI Import",
                    "cited_by_count": 0,
                    "referenced_works": [],
                    "related_works": [],
                    "source_origin": "Ручной ввод DOI",
                    "citekey": make_citekey({"title": doi, "year": "2026"}, len(papers) + 1)
                })
    return papers
