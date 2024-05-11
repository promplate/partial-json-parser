"""Myelin acts as the highway among neurons, epitomizing the leapfrog methodology within this algorithm."""

from re import compile
from typing import List, Tuple, Union

from .complete import complete_str, fix
from .exceptions import PartialJSON
from .options import *

finditer = compile(r'["\[\]{}]').finditer


def scan(json_string: str):
    return [(match.start(), match.group()) for match in finditer(json_string)]


def join_closing_tokens(stack: List[Tuple[int, str]]):
    return "".join("}" if char == "{" else "]" for _, char in reversed(stack))


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

    # check if the opening tokens are allowed

    allow = Allow(allow_partial)

    if OBJ not in allow:
        for index, [i, char] in enumerate(stack):
            if char == "{":
                if index == 0:
                    raise PartialJSON("Partial object is not allowed")
                return json_string[:i], join_closing_tokens(stack[:index])
    if ARR not in allow:
        for index, [i, char] in enumerate(stack):
            if char == "[":
                if index == 0:
                    raise PartialJSON("Partial array is not allowed")
                return json_string[:i], join_closing_tokens(stack[:index])

    if json_string[-1] in "]}" and not in_string:  # the last token is a closing token
        return json_string[: i + 1], "".join("}" if char == "{" else "]" for _, char in reversed(stack))

    if char == '"':
        if in_string:
            if STR not in allow:
                i, char = tokens[-2]
                if char != '"' or stack[-2][1] != "{":
                    return json_string[: i + 1], join_closing_tokens(stack)
            elif stack[-1][1] != "{":
                index, tail = complete_str(json_string[i:], allow)  # type: ignore
                return json_string[: i + index], tail + join_closing_tokens(stack)  # type: ignore

        if stack[-1][1] == "[":
            rest = json_string[i + 1 :].rstrip("-").strip().lstrip(",")  # maybe `, -`
            if rest:
                head, tail = fix("[" + rest, allow)
                assert head[0] == "[" and tail[-1] == "]"
                return json_string[: i + 1] + "," + head[1:], tail + join_closing_tokens(stack[:-1])
            return json_string[: i + 1], join_closing_tokens(stack)

    # worst case when the last container need to be parsed by the fallback parser

    index, char = stack.pop()

    last_entity = json_string[index:]

    if not last_entity:
        return json_string[:index], join_closing_tokens(stack)

    head, tail = fix(last_entity, allow_partial)

    return json_string[:index] + head, tail + join_closing_tokens(stack)
