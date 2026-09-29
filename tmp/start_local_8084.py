import sys
from pathlib import Path
repo = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo / "src"))
from main import run_server
run_server(8084)
