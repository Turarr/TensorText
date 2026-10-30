import os
import subprocess
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(r"c:\Users\loser\OneDrive\Рабочий стол\libro")
SCREENSHOTS_DIR = ROOT / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

PORT = 8530
URL = f"http://localhost:{PORT}"

print(f"1. Starting Streamlit on port {PORT}...")
streamlit_proc = subprocess.Popen(
    ["streamlit", "run", "app.py", f"--server.port={PORT}", "--server.headless=true"],
    cwd=str(ROOT),
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

# Wait for server to become responsive
time.sleep(5)

print("2. Connecting Playwright Chromium browser...")
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1440, "height": 1050}, device_scale_factor=1.5)
    page = context.new_page()

    print(f"Navigating to {URL}...")
    page.goto(URL, wait_until="networkidle", timeout=30000)
    time.sleep(3) # allow Streamlit hydration

    # 1. Hero & Overview Screenshot
    page.screenshot(path=str(SCREENSHOTS_DIR / "01_hero_and_search.png"))
    print("Saved: 01_hero_and_search.png")

    # 2. Switch to Upload Tab
    try:
        upload_tab = page.locator('button[data-baseweb="tab"]:has-text("Загрузить свои PDF")')
        if upload_tab.count() > 0:
            upload_tab.first.click()
            time.sleep(1)
            page.screenshot(path=str(SCREENSHOTS_DIR / "02_upload_pdf_bibtex.png"))
            print("Saved: 02_upload_pdf_bibtex.png")
    except Exception as e:
        print("Upload tab click notice:", e)

    # 3. Scroll to Paper Selection (Section 2)
    try:
        sec2 = page.locator('text=Выборка публикаций для анализа')
        if sec2.count() > 0:
            sec2.first.scroll_into_view_if_needed()
            time.sleep(1)
            page.screenshot(path=str(SCREENSHOTS_DIR / "03_paper_selection_grid.png"))
            print("Saved: 03_paper_selection_grid.png")
    except Exception as e:
        print("Section 2 scroll notice:", e)

    # 4. Scroll to Tabs & click Tab 4: Карточки статей
    try:
        tab_cards = page.locator('button[data-baseweb="tab"]:has-text("Карточки")')
        if tab_cards.count() > 0:
            tab_cards.first.scroll_into_view_if_needed()
            tab_cards.first.click()
            time.sleep(1.5)
            page.screenshot(path=str(SCREENSHOTS_DIR / "04_structured_papercards.png"))
            print("Saved: 04_structured_papercards.png")
    except Exception as e:
        print("Tab 4 notice:", e)

    # 5. Tab 1: Scientific Chat
    try:
        tab_chat = page.locator('button[data-baseweb="tab"]:has-text("Научный чат")')
        if tab_chat.count() > 0:
            tab_chat.first.click()
            time.sleep(1.5)
            page.screenshot(path=str(SCREENSHOTS_DIR / "05_scientific_chat.png"))
            print("Saved: 05_scientific_chat.png")
    except Exception as e:
        print("Tab 1 notice:", e)

    # 6. Tab 2: Comparative Matrix Table
    try:
        tab_tbl = page.locator('button[data-baseweb="tab"]:has-text("Сравнительная таблица")')
        if tab_tbl.count() > 0:
            tab_tbl.first.click()
            time.sleep(1.5)
            page.screenshot(path=str(SCREENSHOTS_DIR / "06_comparison_matrix.png"))
            print("Saved: 06_comparison_matrix.png")
    except Exception as e:
        print("Tab 2 notice:", e)

    # 7. Tab 3: Citation Network & Synthesis
    try:
        tab_net = page.locator('button[data-baseweb="tab"]:has-text("Связи")')
        if tab_net.count() > 0:
            tab_net.first.click()
            time.sleep(1.5)
            page.screenshot(path=str(SCREENSHOTS_DIR / "07_citation_network_synthesis.png"))
            print("Saved: 07_citation_network_synthesis.png")
    except Exception as e:
        print("Tab 3 notice:", e)

    # 8. Tab 6: Export Grid
    try:
        tab_exp = page.locator('button[data-baseweb="tab"]:has-text("Центр экспорта")')
        if tab_exp.count() > 0:
            tab_exp.first.click()
            time.sleep(1.5)
            page.screenshot(path=str(SCREENSHOTS_DIR / "08_export_integrations.png"))
            print("Saved: 08_export_integrations.png")
    except Exception as e:
        print("Tab 6 notice:", e)

    browser.close()

# Terminate Streamlit
streamlit_proc.terminate()
try:
    streamlit_proc.wait(timeout=3)
except Exception:
    streamlit_proc.kill()

print("All screenshots successfully captured!")
