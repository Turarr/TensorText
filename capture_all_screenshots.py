import time
import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(r"c:\Users\loser\OneDrive\Рабочий стол\libro")
SCREENSHOTS_DIR = ROOT / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

PORT = 8535
URL = f"http://localhost:{PORT}"

print("1. Launching Streamlit server...")
proc = subprocess.Popen(
    ["streamlit", "run", "app.py", f"--server.port={PORT}", "--server.headless=true"],
    cwd=str(ROOT),
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

time.sleep(5)

print("2. Starting Playwright...")
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    # 1500x950 high-res viewport for clean academic report visuals
    page = browser.new_page(viewport={"width": 1500, "height": 950}, device_scale_factor=1.5)
    page.goto(URL, wait_until="networkidle", timeout=35000)
    time.sleep(3)

    # 1. Hero & Search Tab
    page.screenshot(path=str(SCREENSHOTS_DIR / "01_hero_and_search.png"))
    print("[OK] Saved 01_hero_and_search.png")

    tabs = page.locator('[data-baseweb="tab"]').all()
    print(f"Detected {len(tabs)} tabs.")

    # 2. Upload PDF / BibTeX Tab (Tab index 1)
    if len(tabs) > 1:
        tabs[1].click()
        time.sleep(1.2)
        page.screenshot(path=str(SCREENSHOTS_DIR / "02_upload_pdf_bibtex.png"))
        print("[OK] Saved 02_upload_pdf_bibtex.png")

    # 3. Paper Selection 2-Column Grid (Section 2)
    sec2 = page.locator('text=Выборка публикаций для анализа')
    if sec2.count() > 0:
        sec2.first.scroll_into_view_if_needed()
        time.sleep(1.2)
        page.screenshot(path=str(SCREENSHOTS_DIR / "03_paper_selection_grid.png"))
        print("[OK] Saved 03_paper_selection_grid.png")

    # Re-query tabs in Section 4
    tabs = page.locator('[data-baseweb="tab"]').all()

    # 4. Scientific Chat (Tab index 3)
    if len(tabs) > 3:
        tabs[3].scroll_into_view_if_needed()
        tabs[3].click()
        time.sleep(1.5)
        page.screenshot(path=str(SCREENSHOTS_DIR / "04_scientific_chat.png"))
        print("[OK] Saved 04_scientific_chat.png")

    # 5. Comparative Table (Tab index 4)
    if len(tabs) > 4:
        tabs[4].click()
        time.sleep(1.5)
        page.screenshot(path=str(SCREENSHOTS_DIR / "05_comparison_matrix.png"))
        print("[OK] Saved 05_comparison_matrix.png")

    # 6. Citation Network & Synthesis (Tab index 5)
    if len(tabs) > 5:
        tabs[5].click()
        time.sleep(1.5)
        page.screenshot(path=str(SCREENSHOTS_DIR / "06_citation_network_synthesis.png"))
        print("[OK] Saved 06_citation_network_synthesis.png")

    # 7. PaperCards with Ratings (Tab index 6)
    if len(tabs) > 6:
        tabs[6].click()
        time.sleep(1.5)
        page.screenshot(path=str(SCREENSHOTS_DIR / "07_structured_papercards.png"))
        print("[OK] Saved 07_structured_papercards.png")

    # 8. Method x Dataset Matrix (Tab index 7)
    if len(tabs) > 7:
        tabs[7].click()
        time.sleep(1.5)
        page.screenshot(path=str(SCREENSHOTS_DIR / "08_method_dataset_matrix.png"))
        print("[OK] Saved 08_method_dataset_matrix.png")

    # 9. Export Center Grid (Tab index 8)
    if len(tabs) > 8:
        tabs[8].click()
        time.sleep(1.5)
        page.screenshot(path=str(SCREENSHOTS_DIR / "09_export_integrations.png"))
        print("[OK] Saved 09_export_integrations.png")

    browser.close()

proc.terminate()
try:
    proc.wait(timeout=3)
except Exception:
    proc.kill()

print("ALL SCREENSHOTS CAPTURED!")
