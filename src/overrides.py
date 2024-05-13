from pathlib import Path
from re import sub

file = Path(__file__).parent.parent / "pyproject.toml"

file.write_text(sub(r'requires-python = ".*"', 'requires-python = ">=3.6"', file.read_text()))
