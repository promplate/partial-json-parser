from pathlib import Path
from re import sub
from sys import argv

file = Path(__file__).parent.parent / "pyproject.toml"

file.write_text(sub(r'requires-python = ".*?"', f'requires-python = ">={argv[-1]}"', file.read_text()))
