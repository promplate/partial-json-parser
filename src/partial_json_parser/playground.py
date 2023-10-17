from json import dumps

from rich.console import Console
from rich.highlighter import JSONHighlighter

from partial_json_parser import parse_json

console = Console()
highlight = JSONHighlighter()


def main():
    while True:
        try:
            json = dumps(parse_json(console.input("[d]>>> ")), ensure_ascii=False)
            console.print(" " * 3, highlight(json))
        except KeyboardInterrupt:
            return
        except Exception as err:
            console.print(f"{err.__class__.__name__}:", style="bold red", highlight=False, end=" ")
            console.print(" ".join(map(str, err.args)), style="yellow", highlight=False)
