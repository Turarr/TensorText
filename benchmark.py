"""
Benchmark script for evaluating TensorText on RU / KZ / EN research topics.
Compares search recall and reranked relevance against academic queries.
"""

import sys
import time
from sources import search_openalex
from ai import get_client, rerank

BENCHMARK_QUERIES = [
    # Russian research topics (12)
    {"query": "влияние искусственного интеллекта на академическую успеваемость студентов", "lang": "ru"},
    {"query": "сравнительный анализ моделей машинного обучения в медицинской диагностике", "lang": "ru"},
    {"query": "методы распознавания болезней сельскохозяйственных растений по изображениям листьев", "lang": "ru"},
    {"query": "обработка естественного языка для анализа тональности финансовых новостей", "lang": "ru"},
    {"query": "применение сверточных нейронных сетей в задачах сегментации МРТ снимков", "lang": "ru"},
    {"query": "оценка надежности и галлюцинаций больших языковых моделей", "lang": "ru"},
    {"query": "квантовые алгоритмы оптимизации в логистических сетях", "lang": "ru"},
    {"query": "алгоритмы обнаружения аномалий в потоках сетевого трафика", "lang": "ru"},
    {"query": "генеративно-состязательные сети для аугментации данных в компьютерном зрении", "lang": "ru"},
    {"query": "анализ временных рядов для прогнозирования потребления электроэнергии", "lang": "ru"},
    {"query": "этические аспекты и прозрачность систем искусственного интеллекта в образовании", "lang": "ru"},
    {"query": "методы понижения размерности в геномных исследованиях", "lang": "ru"},

    # Kazakh research topics (8)
    {"query": "қазақ тіліндегі мәтіндерді талдауға арналған машиналық оқыту модельдері", "lang": "kk"},
    {"query": "жасанды интеллекттің жоғары білім беру жүйесіндегі рөлі мен тиімділігі", "lang": "kk"},
    {"query": "қазақ тілі үшін үлкен тілдік модельдерді бейімдеу және бағалау", "lang": "kk"},
    {"query": "ауыл шаруашылығындағы дақылдар ауруларын анықтауға арналған компьютерлік көру", "lang": "kk"},
    {"query": "қазақ тіліндегі дауысты тану жүйелерін терең оқыту негізінде құру", "lang": "kk"},
    {"query": "білім беру процесіндегі нейрожелілік технологияларды қолдану", "lang": "kk"},
    {"query": "цифрлық медицинадағы деректерді өңдеу әдістері", "lang": "kk"},
    {"query": "қазақстан энергетикалық жүйесіндегі жаңартылатын қуат көздерін модельдеу", "lang": "kk"},

    # English research topics (10)
    {"query": "large language models for automated literature review synthesis", "lang": "en"},
    {"query": "deep learning architectures for plant disease detection in precision agriculture", "lang": "en"},
    {"query": "evaluating retrieval augmented generation for scientific question answering", "lang": "en"},
    {"query": "vision transformers versus convolutional networks for medical image analysis", "lang": "en"},
    {"query": "hallucination mitigation techniques in multi-hop reasoning", "lang": "en"},
    {"query": "graph neural networks for drug discovery and molecular property prediction", "lang": "en"},
    {"query": "multimodal learning for cross-lingual academic search", "lang": "en"},
    {"query": "diffusion models for high-fidelity time series forecasting", "lang": "en"},
    {"query": "federated learning privacy guarantees in electronic health records", "lang": "en"},
    {"query": "zero-shot generalization in large reasoning models benchmark", "lang": "en"}
]


def run_benchmark(sample_size=5):
    print(f"=== TensorText Benchmark: Testing {sample_size} Queries ===")
    client = get_client()
    print(f"Gemini Client available: {bool(client)}")

    queries = BENCHMARK_QUERIES[:sample_size]
    results = []

    for i, item in enumerate(queries, 1):
        q = item["query"]
        lang = item["lang"]
        t0 = time.time()
        try:
            papers = search_openalex(q, n=15, lang=lang)
            search_time = round(time.time() - t0, 2)
            has_doi = sum(1 for p in papers if p.get("doi"))
            
            t1 = time.time()
            reranked = rerank(client, q, papers, k=10)
            rerank_time = round(time.time() - t1, 2)

            res = {
                "query": q[:40] + "…",
                "lang": lang,
                "found": len(papers),
                "has_doi": has_doi,
                "top_title": reranked[0]["title"][:45] + "…" if reranked else "None",
                "search_time": search_time,
                "rerank_time": rerank_time
            }
            results.append(res)
            print(f"[{i}/{sample_size}] [{lang.upper()}] Found {len(papers)} papers ({has_doi} with DOI) in {search_time}s | Rerank: {rerank_time}s")
        except Exception as exc:
            print(f"[{i}/{sample_size}] [{lang.upper()}] Error: {exc}")

    print("\n=== Benchmark Summary ===")
    avg_found = sum(r["found"] for r in results) / max(1, len(results))
    avg_doi = sum(r["has_doi"] for r in results) / max(1, len(results))
    print(f"Average papers returned: {avg_found:.1f} (avg {avg_doi:.1f} with verified DOI)")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    run_benchmark(sample_size=n)
