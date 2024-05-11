"""Myelin acts as the highway among neurons, epitomizing the leapfrog methodology within this algorithm."""

from re import compile
from typing import Union

from .complete import fix
from .options import *

finditer = compile(r'["\[\]{}]').finditer


def scan(json_string: str):
    return [(match.start(), match.group()) for match in finditer(json_string)]


def fix_fast(json_string: str, allow_partial: Union[Allow, int] = ALL):
    def is_escaped(index: int):
        text_before = json_string[:index]
        count = index - len(text_before.rstrip("\\"))
        return count % 2

    stack = []
    in_string = False

    tokens = scan(json_string)

    if not tokens or tokens[0][1] == '"':
        return fix(json_string, allow_partial)

    for i, char in tokens:
        if char == '"':
            if not in_string or not is_escaped(i):
                in_string = not in_string

        elif not in_string:
            if char == "}":
                _i, _char = stack.pop()
                assert _char == "{", f"Expected '{{' at index {_i}, got '{_char}'"
            elif char == "]":
                _i, _char = stack.pop()
                assert _char == "[", f"Expected '[' at index {_i}, got '{_char}'"
            else:
                stack.append((i, char))

    if not stack:
        return json_string, ""

    index, char = stack.pop()

    last_entity = json_string[index:]

    stack.reverse()

    if not last_entity:
        return json_string[:index], "".join("}" if char == "{" else "]" for _, char in stack)

    head, tail = fix(last_entity, allow_partial)

    return json_string[:index] + head, tail + "".join("}" if char == "{" else "]" for _, char in stack)
