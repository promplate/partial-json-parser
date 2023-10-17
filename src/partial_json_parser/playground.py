from json import dumps
from traceback import format_exception_only

from rich.console import Console

from partial_json_parser import parse_json

console = Console()


def main():
    while True:
        try:
            json = dumps(parse_json(console.input("[d]>>> ")), ensure_ascii=False)
            print(" " * 4, end="")
            console.print(json)
        except KeyboardInterrupt:
            return
        except Exception as err:
            name, value = "".join(format_exception_only(err)).split(":", 1)
            console.print(f"{name}:", style="bold red", highlight=False, end="")
            console.print(value, style="yellow", highlight=False, end="")
