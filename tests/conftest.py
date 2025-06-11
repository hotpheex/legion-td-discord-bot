import os
import sys
from pathlib import Path

# Add functions directory to Python path
functions_path = Path(__file__).parent.parent / "functions"
sys.path.insert(0, str(functions_path)) 