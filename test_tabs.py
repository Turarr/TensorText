import time
import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(r"c:\Users\loser\OneDrive\Рабочий стол\libro")
SCREENSHOTS_DIR = ROOT / "screenshots"

proc = subprocess.Popen(
    ["streamlit", "run", "app.py", "--server.port=8533", "--server.headless=true"],
    cwd=str(ROOT)
)
time.sleep(5)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 900}, device_scale_factor=1.5)
    page.goto("http://localhost:8533", wait_until="networkidle", timeout=30000)
    time.sleep(3)

    # Full page screenshot of initial load
    page.screenshot(path=str(SCREENSHOTS_DIR / "full_overview.png"), full_page=True)
    print("Full page captured: full_overview.png")

    # Get all tabs
    tabs = page.locator('[data-baseweb="tab"]').all()
    print(f"Found {len(tabs)} tabs:")
    for idx, t in enumerate(tabs):
        print(f"Tab {idx}: '{t.inner_text()}'")

    browser.close()

proc.terminate()
