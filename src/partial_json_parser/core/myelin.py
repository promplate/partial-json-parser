"""Myelin acts as the highway among neurons, epitomizing the leapfrog methodology within this algorithm."""

from re import compile
from typing import List, Tuple, Union

from .complete import fix
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
    last_string_start = 0
    last_string_end = 0

    tokens = scan(json_string)

    if not tokens or tokens[0][1] == '"':
        return fix(json_string, allow_partial)

    for i, char in tokens:
        if char == '"':
            if not in_string:
                in_string = True
                last_string_start = i
            elif not is_escaped(i):
                in_string = False
                last_string_end = i

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

    if STR not in allow and in_string:
        last_comma = json_string.rfind(",", i + 1)
        if last_comma == -1:
            return json_string[: stack[-1][0] + 1], join_closing_tokens(stack)
        i, char = stack.pop()  # get last container token
        head, tail = fix(char + json_string[last_comma + 1 :], allow)
        return json_string[:i] + head, tail + join_closing_tokens(stack)
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

    # only fix the rest of the container in O(1) time complexity

    assert in_string == (last_string_end < last_string_start)

    if in_string:
        if stack[-1][1] == "[":  # [ ... "val
            head, tail = fix(json_string[last_string_start:], allow)  # fix the last string
            return json_string[:last_string_start] + head, tail + join_closing_tokens(stack)

        assert stack[-1][1] == "{"  # { ... "val

        start = max(last_string_end, stack[-1][0])

        if "," in json_string[start + 1 : last_string_start]:
            # { ... "k": "v", "key
            # { ... "k": 123, "key
            last_comma = json_string.rindex(",", start, last_string_start)
            head, tail = fix(stack[-1][1] + json_string[last_comma + 1 :], allow)
            return json_string[:last_comma] + head[1:], tail + join_closing_tokens(stack[:-1])

        if ":" in json_string[start + 1 : last_string_start]:
            # { ... ": "val
            head, tail = fix(json_string[last_string_start:], allow)  # fix the last string (same as array)
            return json_string[:last_string_start] + head, tail + join_closing_tokens(stack)

        # {"key
        return json_string[:last_string_start], join_closing_tokens(stack)

    last_comma = json_string.rfind(",", max(last_string_end, i) + 1)

    if last_comma != -1:
        i, char = stack[-1]

        if not json_string[last_comma + 1 :].strip():  # comma at the end
            # { ... "key": "value",
            return json_string[:last_comma], join_closing_tokens(stack)

        assert char == "[", json_string  # array with many non-string literals

        # [ ..., 1, 2, 3, 4

        head, tail = fix(char + json_string[last_comma + 1 :], allow)
        if not head[1:] + tail[:-1].strip():  # empty, so trim the last comma
            return json_string[:last_comma] + head[1:], tail + join_closing_tokens(stack[:-1])
        return json_string[: last_comma + 1] + head[1:], tail + join_closing_tokens(stack[:-1])

    # can't find comma after the last string and after the last container token

    if char in "]}":
        # ... [ ... ]
        # ... { ... }
        assert not json_string[i + 1 :].strip()
        return json_string, join_closing_tokens(stack)

    if char in "[{":
        # ... [ ...
        # ... { ...
        head, tail = fix(json_string[i:], allow)
        return json_string[:i] + head, tail + join_closing_tokens(stack[:-1])

    assert char == '"'

    i, char = stack[-1]

    if char == "[":  # [ ... "val"
        return json_string, join_closing_tokens(stack)

    assert char == "{"
    last_colon = json_string.rfind(":", last_string_end)
    last_comma = json_string.rfind(",", i + 1, last_string_start)

    if last_comma == -1:  # only 1 key
        # ... { "key"
        # ... { "key": "value"
        head, tail = fix(json_string[i:], allow)
        return json_string[:i] + head, tail + join_closing_tokens(stack[:-1])

    if last_colon == -1:
        if json_string.rfind(":", max(i, last_comma) + 1, last_string_start) != -1:
            # { ... , "key": "value"
            return json_string, join_closing_tokens(stack)

        # { ... , "key"
        head, tail = fix("{" + json_string[last_comma + 1 :], allow)
        if not head[1:] + tail[:-1].strip():
            return json_string[:last_comma] + head[1:], tail + join_closing_tokens(stack[:-1])
        return json_string[: last_comma + 1] + head[1:], tail + join_closing_tokens(stack)

    assert last_colon > last_comma  # { ... , "key":

    head, tail = fix("{" + json_string[last_comma + 1 :], allow)
    if not head[1:] + tail[:-1].strip():
        return json_string[:last_comma] + head[1:], tail + join_closing_tokens(stack[:-1])
    return json_string[: last_comma + 1] + head[1:], tail + join_closing_tokens(stack[:-1])
