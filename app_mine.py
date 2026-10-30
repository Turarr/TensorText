import runpy
from pathlib import Path

# Delegate to app.py so running either app_mine.py or app.py starts TensorText
app_path = Path(__file__).resolve().parent / "app.py"
runpy.run_path(str(app_path), run_name="__main__")
