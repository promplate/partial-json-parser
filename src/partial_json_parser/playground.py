from rich.console import Console
from rich.highlighter import JSONHighlighter
from rich.style import Style
from rich.text import Span

from partial_json_parser import fix_fast

console = Console()
highlight = JSONHighlighter()


def main():
    while True:
        try:
            input_str = console.input("[d]>>> ")

            head, tail = fix_fast(input_str)
            json = head + tail

            rich_text = highlight(json)
            if tail:
                rich_text.spans.append(Span(len(head), len(json), Style(dim=True)))

            console.print(" " * 3, rich_text)

        except KeyboardInterrupt:
            return
        except Exception as err:
            console.print(f"{err.__class__.__name__}:", style="bold red", highlight=False, end=" ")
            console.print(" ".join(map(str, err.args)), style="yellow", highlight=False)
