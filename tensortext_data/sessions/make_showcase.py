import json
from pathlib import Path
from datetime import datetime

ROOT = Path(r"c:\Users\loser\OneDrive\Рабочий стол\libro")
SESSIONS_DIR = ROOT / "tensortext_data" / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

# Showcase Session on Environmental Impact of AI & Data Centers
showcase_session = {
    "id": "showcase_ai_datacenters",
    "title": "Data Centers & AI Environmental Impact",
    "search_query": "data centers carbon footprint energy consumption and environmental impact",
    "created_at": datetime.now().isoformat(timespec="seconds"),
    "papers": [
        {
            "id": "oa_w1_transformer_carbon",
            "doi": "10.18653/v1/P19-1355",
            "doi_url": "https://doi.org/10.18653/v1/P19-1355",
            "title": "Energy and Policy Considerations for Deep Learning in NLP",
            "year": 2019,
            "lang": "en",
            "authors": ["Emma Strubell", "Ananya Ganesh", "Andrew McCallum"],
            "authors_str": "Emma Strubell, Ananya Ganesh, Andrew McCallum",
            "abstract": "Recent progress in NLP has been driven by deep neural network architectures with billions of parameters. We quantify the financial and environmental cost of training state-of-the-art models for NLP tasks. We provide actionable recommendations to reduce energy consumption and improve computational efficiency.",
            "pdf_url": "https://aclanthology.org/P19-1355.pdf",
            "url": "https://doi.org/10.18653/v1/P19-1355",
            "journal": "ACL 2019",
            "cited_by_count": 3140,
            "referenced_works": ["oa_w2_patterson_carbon", "oa_w4_schwartz_green_ai"],
            "related_works": [],
            "source_origin": "OpenAlex",
            "citekey": "strubell2019energy",
            "full_text": ""
        },
        {
            "id": "oa_w2_patterson_carbon",
            "doi": "10.48550/arXiv.2104.10350",
            "doi_url": "https://doi.org/10.48550/arXiv.2104.10350",
            "title": "Carbon Emissions and Large Neural Network Training",
            "year": 2021,
            "lang": "en",
            "authors": ["David Patterson", "Joseph Gonzalez", "Quoc Le", "Chen Liang", "Lluis-Miquel Munguia"],
            "authors_str": "David Patterson, Joseph Gonzalez, Quoc Le et al.",
            "abstract": "We analyze energy consumption and carbon footprints across datacenter hardware, machine learning model architectures, and geographical grid carbon intensity. We demonstrate the 4M framework (Model, Machine, Mechanization, Map) to reduce ML training carbon footprints by up to 100-1000x.",
            "pdf_url": "https://arxiv.org/pdf/2104.10350.pdf",
            "url": "https://doi.org/10.48550/arXiv.2104.10350",
            "journal": "Communications of the ACM",
            "cited_by_count": 1285,
            "referenced_works": ["oa_w1_transformer_carbon", "oa_w3_datacenter_pue"],
            "related_works": [],
            "source_origin": "PDF + OpenAlex DOI",
            "citekey": "patterson2021carbon",
            "full_text": "Section 3. Methodology and Carbon Accounting. We measure the carbon intensity of energy grids using location-based and market-based accounting. Datacenter Power Usage Effectiveness (PUE) averaged 1.1 across Google hyper-scale infrastructure. Model architecture optimizations reduce training FLOPs by 40%."
        },
        {
            "id": "oa_w3_datacenter_pue",
            "doi": "10.1126/science.aba3758",
            "doi_url": "https://doi.org/10.1126/science.aba3758",
            "title": "Recalibrating Global Data Center Energy-Use Estimates",
            "year": 2020,
            "lang": "en",
            "authors": ["Eric Masanet", "Arman Shehabi", "Nuhoa Ramakrishnan", "Jonathan Liang", "Xiaohui Fan"],
            "authors_str": "Eric Masanet, Arman Shehabi, Nuhoa Ramakrishnan et al.",
            "abstract": "While global datacenter compute instances rose by 550% from 2010 to 2018, global datacenter energy use increased by only 6%, due to major efficiency gains in hyperscale consolidation and server virtualization. We present a bottom-up mathematical model of global datacenter energy demand.",
            "pdf_url": "",
            "url": "https://doi.org/10.1126/science.aba3758",
            "journal": "Science (AAAS)",
            "cited_by_count": 2180,
            "referenced_works": [],
            "related_works": [],
            "source_origin": "OpenAlex",
            "citekey": "masanet2020recalibrating",
            "full_text": ""
        },
        {
            "id": "oa_w4_schwartz_green_ai",
            "doi": "10.1145/3381831",
            "doi_url": "https://doi.org/10.1145/3381831",
            "title": "Green AI: Efficiency As An Evaluation Metric",
            "year": 2020,
            "lang": "en",
            "authors": ["Roy Schwartz", "Jesse Dodge", "Noah A. Smith", "Oren Etzioni"],
            "authors_str": "Roy Schwartz, Jesse Dodge, Noah A. Smith, Oren Etzioni",
            "abstract": "Computations required for deep learning research have doubled every 3.4 months. We advocate for Green AI, an initiative prioritizing computational efficiency alongside raw predictive accuracy. We introduce floating point operations (FPO) as a standard reporting metric for academic benchmarking.",
            "pdf_url": "https://arxiv.org/pdf/1907.10597.pdf",
            "url": "https://doi.org/10.1145/3381831",
            "journal": "Communications of the ACM",
            "cited_by_count": 1690,
            "referenced_works": ["oa_w1_transformer_carbon"],
            "related_works": [],
            "source_origin": "BibTeX + OpenAlex DOI",
            "citekey": "schwartz2020green",
            "full_text": ""
        },
        {
            "id": "oa_w5_cooling_water",
            "doi": "10.1038/s41545-023-00263-w",
            "doi_url": "https://doi.org/10.1038/s41545-023-00263-w",
            "title": "The Overlooked Environmental Cost of AI: Water Consumption in Datacenters",
            "year": 2023,
            "lang": "en",
            "authors": ["Pengfei Li", "Jianyi Yang", "Mohammad A. Islam", "Shaolei Ren"],
            "authors_str": "Pengfei Li, Jianyi Yang, Mohammad A. Islam, Shaolei Ren",
            "abstract": "AI compute consumes immense amounts of freshwater for evaporative datacenter cooling and electricity generation. We quantify the water footprint of training state-of-the-art models like GPT-3, estimating that training directly consumed 700,000 liters of clean freshwater, highlighting regional ecological stress.",
            "pdf_url": "",
            "url": "https://doi.org/10.1038/s41545-023-00263-w",
            "journal": "Nature npj Clean Water",
            "cited_by_count": 485,
            "referenced_works": ["oa_w2_patterson_carbon", "oa_w3_datacenter_pue"],
            "related_works": [],
            "source_origin": "OpenAlex",
            "citekey": "li2023overlooked",
            "full_text": ""
        }
    ],
    "selected_paper_ids": [
        "oa_w1_transformer_carbon",
        "oa_w2_patterson_carbon",
        "oa_w3_datacenter_pue",
        "oa_w4_schwartz_green_ai",
        "oa_w5_cooling_water"
    ],
    "cards": {
        "oa_w1_transformer_carbon": {
            "task": "Оценка финансового и углеродного следа обучения современных моделей NLP (Transformer, BERT, GPT)",
            "method": "Анализ энергопотребления GPU/TPU оборудования при полном цикле обучения и подбора гиперпараметров",
            "dataset": "BERT, Transformer, ELMo, GPT-2 benchmark training logs",
            "metrics": "kWh (энергопотребление), lbs CO2 equivalent, финансовая стоимость в облаке ($)",
            "key_result": "Обучение одной крупной модели NLP производит выбросы до 626 000 фунтов CO2 (эквивалент 5 автомобилей за весь срок службы)",
            "limitations": "Расчёты опирались на среднюю по США углеродоёмкость энергосети; не учитывались охлаждение датацентров и возобновляемые PPA"
        },
        "oa_w2_patterson_carbon": {
            "task": "Комплексное измерение реальных углеродных выбросов при обучении нейросетей в гиперскейл-датацентрах",
            "method": "Фреймворк 4M (Model, Machine, Mechanization, Map) с учётом PUE датацентров и гео-привязки энергосетей",
            "dataset": "Логи обучения T5, Meena, GShard, GPT-3 в датацентрах Google и публичных облаках",
            "metrics": "PUE (Power Usage Effectiveness), tCO2e, MWh, энергоэффективность на 1 FLOP",
            "key_result": "Выбор эффективной архитектуры и датацентров с PUE 1.1 и чистой энергией снижает углеродный след в 100–1000 раз",
            "limitations": "Фокус в основном на инфраструктуре Google; эмпирические данные сторонних закрытых датацентров ограничены"
        },
        "oa_w3_datacenter_pue": {
            "task": "Глобальная оценка динамики мирового энергопотребления датацентров за 2010–2018 гг.",
            "method": "Нисходящая аналитическая математическая модель энергопотребления серверов, систем хранения и охлаждения",
            "dataset": "Глобальная статистика IEA, IDC, Cisco Cloud Index, операционная телеметрия гиперскейлеров",
            "metrics": "TWh/год, плотность вычислений, средний глобальный PUE",
            "key_result": "При росте вычислительной нагрузки на 550% глобальное энергопотребление ЦОД выросло лишь на 6% благодаря консолидации в гиперскейлеры",
            "limitations": "Потенциал аппаратной оптимизации близок к пределу; взрывной рост генеративного ИИ в 2023–2026 гг. требует повторной калибровки"
        },
        "oa_w4_schwartz_green_ai": {
            "task": "Формулирование концепции Green AI и введение метрик вычислительной эффективности в научный оборот",
            "method": "Теоретический и сравнительный анализ роста вычислительной сложности Red AI vs Green AI",
            "dataset": "Анализ публикаций конференций NeurIPS, ICML, ACL за 2012–2019 гг.",
            "metrics": "FPO (Floating Point Operations), время до достижения пороговой точности, энергозатраты на вывод",
            "key_result": "Предложен стандарт обязательной публикации FPO наряду с метриками качества модели (Accuracy/F1)",
            "limitations": "не указано (в работе не приведён количественный датасет по выбросам конкретных аппаратных комплексов)"
        },
        "oa_w5_cooling_water": {
            "task": "Оценка прямого и косвенного потребления пресной воды системами охлаждения ЦОД при обучении LLM",
            "method": "Моделирование испарительного охлаждения ЦОД (WUE) и расхода воды на гидро- и теплоэлектростанциях",
            "dataset": "Данные водопотребления серверов Microsoft, Google и региональных метеостанций",
            "metrics": "Литры чистой пресной воды на 1 kWh и на цикл обучения модели",
            "key_result": "Обучение GPT-3 напрямую испарило ~700 000 литров пресной воды; каждый сеанс из 20-50 диалогов расходует ~500 мл воды",
            "limitations": "Сильная географическая неравномерность водопотребления; коммерческая закрытость данных охлаждения частных ЦОД"
        }
    },
    "card_ratings": {
        "oa_w1_transformer_carbon": 1,
        "oa_w2_patterson_carbon": 1,
        "oa_w3_datacenter_pue": 1,
        "oa_w4_schwartz_green_ai": 1,
        "oa_w5_cooling_water": 1
    },
    "chat_history": [
        {
            "role": "user",
            "content": "В чем главное противоречие между оценками энергопотребления ЦОД у Masanet et al. (2020) и Strubell et al. (2019)?"
        },
        {
            "role": "assistant",
            "content": "Главное противоречие заключается в **масштабе и фокусе анализа**:\n\n1. **Эффект агрегации против экспоненты обучения моделей**:\n   - \\cite{masanet2020recalibrating} (Science, 2020) рассматривают глобальное макро-потребление всех ЦОД мира и показывают, что с 2010 по 2018 гг. энергопотребление выросло лишь на 6% при 550% росте вычислений благодаря снижению среднего PUE и закрытию неэффективных локальных серверов.\n   - \\cite{strubell2019energy} (ACL 2019), напротив, анализируют микро-уровень разработки deep learning и предупреждают, что подбор гиперпараметров для одной NLP-модели требует до 626 000 фунтов CO2, экспоненциально опережая успехи аппаратной оптимизации.\n\n2. **Фактор энергосетей (Grid Map)**:\n   - Как отмечают \\cite{patterson2021carbon}, Strubell et al. рассчитывали выбросы исходя из средней «грязной» энергосети США, тогда как гиперскейлеры Masanet et al. размещают датацентры в регионах с высокой долей гидро- и ветроэнергетики (PUE ~1.1).\n\nПодтверждённые ссылки: [Masanet et al., 2020](https://doi.org/10.1126/science.aba3758), [Strubell et al., 2019](https://doi.org/10.18653/v1/P19-1355)."
        },
        {
            "role": "user",
            "content": "Какие метрики авторы предлагают использовать для объективной оценки экологичности моделей?"
        },
        {
            "role": "assistant",
            "content": "На основе проанализированных работ авторы выделяют четыре ключевые метрики:\n\n1. **FPO (Floating Point Operations)**: \\cite{schwartz2020green} предлагают сделать число операций с плавающей точкой обязательной метрикой в академических публикациях наряду с Accuracy/F1, поскольку FPO не зависит от конкретной модели процессора.\n2. **PUE (Power Usage Effectiveness)**: \\cite{patterson2021carbon} и \\cite{masanet2020recalibrating} используют PUE как стандарт эффективности инфраструктуры ЦОД (отношение общего энергопотребления датацентра к энергии серверов; идеальный показатель = 1.0).\n3. **Углеродоёмкость с привязкой к локации (tCO2e / kWh)**: \\cite{patterson2021carbon} подчеркивают необходимость измерения реальных выбросов с учётом почасовой генерации местной энергосети (фреймворк 4M: Model, Machine, Mechanization, Map).\n4. **WUE и водный след (Water Consumption)**: \\cite{li2023overlooked} вводят оценку литров пресной воды, расходуемой системами испарительного охлаждения ЦОД на единицу вычислений.\n\nПодтверждённые ссылки: [Schwartz et al., 2020](https://doi.org/10.1145/3381831), [Li et al., 2023](https://doi.org/10.1038/s41545-023-00263-w)."
        }
    ],
    "connections_summary": "### Академический синтез связей публикаций\nКорпус сформирован вокруг ключевой экологической дилеммы цифровизации: баланса между эффективностью серверных мощностей датацентров (Masanet et al., 2020) и экспоненциальным ростом вычислений генеративного ИИ (Strubell et al., 2019; Schwartz et al., 2020).\n\n1. **Кластер макро-энергетики ЦОД**: Masanet et al. (2020) и Patterson et al. (2021) образуют фундаментальный базис, подтверждающий, что гиперскейл-архитектура с PUE ≤ 1.1 способна компенсировать рост объемов данных.\n2. **Кластер Green AI**: Schwartz et al. (2020) цитируют Strubell et al. (2019) как ключевое свидетельство неэффективности «Red AI» и формулируют методологию отчётности FPO.\n3. **Кластер скрытых экологических экстерналий**: Li et al. (2023) расширяют углеродную парадигму Patterson et al., доказывая, что охлаждение датацентров создаёт локальный кризис пресной воды.",
    "matrix_result": "### Матрица «Метод исследования × Датасет/Инфраструктура»\n\n| Нормализованный метод | Логи обучения NLP (BERT/GPT) | Телеметрия гиперскейлеров | Глобальная статистика (IEA/IDC) | Метеоданные & Охлаждение |\n| :--- | :---: | :---: | :---: | :---: |\n| **Анализ углеродного следа GPU** | [1] Strubell (2019) | — | — | — |\n| **Фреймворк 4M (PUE + Grid Map)** | [2] Patterson (2021) | [2] Patterson (2021) | — | — |\n| **Нисходящее мат. моделирование ЦОД** | — | [3] Masanet (2020) | [3] Masanet (2020) | — |\n| **Теоретический анализ Green AI (FPO)**| [4] Schwartz (2020) | — | — | — |\n| **Моделирование испарительного WUE** | [5] Li (2023) | [5] Li (2023) | — | [5] Li (2023) |\n\n#### Выявленные исследовательские пробелы (Research Gaps):\n1. Отсутствие открытых кросс-датасетных сопоставлений водного следа (WUE) при распределённом мультиоблачном обучении.\n2. Недостаток верифицированных полевых измерений углеродоёмкости для региональных ЦОД стран Центральной Азии и СНГ.",
    "author_profile": {
        "name": "Kassenov Turar",
        "university": "Astana IT University",
        "field": "Technology Entrepreneurship (BDA-2404)"
    }
}

target_file = SESSIONS_DIR / "showcase_ai_datacenters.json"
target_file.write_text(json.dumps(showcase_session, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Showcase session successfully saved to: {target_file}")
