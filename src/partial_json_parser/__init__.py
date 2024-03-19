from typing import Callable, Dict, List, Literal, Optional, Tuple, Union

from .options import *

Number = Union[int, float]
JSON = Union[str, bool, Number, List["JSON"], Dict[str, "JSON"], None]

CompleteResult = Union[Tuple[int, Union[str, Literal[True]]], Literal[False]]  # (length, complete_string / already completed) / partial


class JSONDecodeError(ValueError):
    pass


class PartialJSON(JSONDecodeError):
    pass


class MalformedJSON(JSONDecodeError):
    pass


def parse_json(json_string: str, allow_partial: Union[Allow, int] = ALL, parser: Optional[Callable[[str], JSON]] = None) -> JSON:
    if parser is None:
        from json import loads as parser

    if not isinstance(json_string, str):
        raise TypeError(f"Expected str, got {type(json_string).__name__}")
    if not json_string.strip():
        raise ValueError(f"{json_string!r} is empty")
    return _parse_json(json_string.strip(), Allow(allow_partial), parser)


def _parse_json(json_string: str, allow: Allow, parser: Callable[[str], JSON]):
    result = complete_any(json_string, allow, is_top_level=True)  # setting is_top_level to True to treat literal numbers as complete
    if result is False:
        raise PartialJSON
    if result[1] is True:
        return parser(json_string[: result[0]])
    return parser(json_string[: result[0]] + result[1])


def skip_blank(text: str, index: int):
    try:
        while text[index].isspace():
            index += 1
    finally:
        return index


def complete_any(json_string: str, allow: Allow, is_top_level=False) -> CompleteResult:
    i = skip_blank(json_string, 0)
    char = json_string[i]

    if char == '"':
        return complete_str(json_string, allow)

    if char in "1234567890":
        return complete_num(json_string, allow, is_top_level)

    if char == "[":
        return complete_arr(json_string, allow)

    if char == "{":
        return complete_obj(json_string, allow)

    if json_string.startswith("null"):
        return (4, True)
    if "null".startswith(json_string):
        return (0, "null") if NULL in allow else False

    if json_string.startswith("true"):
        return (4, True)
    if "true".startswith(json_string):
        return (0, "true") if BOOL in allow else False

    if json_string.startswith("false"):
        return (5, True)
    if "false".startswith(json_string):
        return (0, "false") if BOOL in allow else False

    if json_string.startswith("Infinity"):
        return (8, True)
    if "Infinity".startswith(json_string):
        return (0, "Infinity") if INFINITY in allow else False

    if char == "-":
        if len(json_string) == 1:
            return False
        elif json_string[1] != "I":
            return complete_num(json_string, allow, is_top_level)

    if json_string.startswith("-Infinity"):
        return (9, True)
    if "-Infinity".startswith(json_string):
        return (0, "-Infinity") if _INFINITY in allow else False

    if json_string.startswith("NaN"):
        return (3, True)
    if "NaN".startswith(json_string):
        return (0, "NaN") if NAN in allow else False

    raise MalformedJSON(f"Unexpected character {char}")


def complete_str(json_string: str, allow: Allow) -> CompleteResult:
    assert json_string[0] == '"'

    i = 1
    escaped = False

    try:
        while json_string[i] != '"' or escaped:
            escaped = not escaped if json_string[i] == "\\" else False
            i += 1

        return i + 1, True

    except IndexError:
        if STR not in allow:
            return False

        # \uXXXX
        _u = json_string.rfind("\\u", max(0, i - 5), i)
        if _u != -1:
            return _u, '"'

        # \UXXXXXXXX
        _U = json_string.rfind("\\U", max(0, i - 9), i)
        if _U != -1:
            return _U, '"'

        # \xXX
        _x = json_string.rfind("\\x", max(0, i - 3), i)
        if _x != -1:
            return _x, '"'

        return i - escaped, '"'


def complete_arr(json_string: str, allow: Allow) -> CompleteResult:
    assert json_string[0] == "["
    i = j = 1

    try:
        while True:
            j = skip_blank(json_string, j)

            if json_string[j] == "]":
                return j + 1, True

            result = complete_any(json_string[j:], allow)

            if result is False:  # incomplete
                return (i, "]") if ARR in allow else False
            if result[1] is True:  # complete
                i = j = j + result[0]
            else:  # incomplete
                return (j + result[0], result[1] + "]") if ARR in allow else False

            j = skip_blank(json_string, j)

            if json_string[j] == ",":
                j += 1
            elif json_string[j] == "]":
                return j + 1, True
            else:
                raise MalformedJSON(f"Expected ',' or ']', got {json_string[j]}")
    except IndexError:
        return (i, "]") if ARR in allow else False


def complete_obj(json_string: str, allow: Allow) -> CompleteResult:
    assert json_string[0] == "{"
    i = j = 1

    try:
        while True:
            j = skip_blank(json_string, j)

            if json_string[j] == "}":
                return j + 1, True

            result = complete_str(json_string[j:], allow)
            if result and result[1] is True:  # complete
                j += result[0]
            else:  # incomplete
                return (i, "}") if OBJ in allow else False

            j = skip_blank(json_string, j)

            if json_string[j] != ":":
                raise MalformedJSON(f"Expected ':', got {json_string[j]}")
            j += 1

            j = skip_blank(json_string, j)

            result = complete_any(json_string[j:], allow)
            if result is False:  # incomplete
                return (i, "}") if OBJ in allow else False
            if result[1] is True:  # complete
                i = j = j + result[0]
            else:  # incomplete
                return (j + result[0], result[1] + "}") if OBJ in allow else False

            j = skip_blank(json_string, j)

            if json_string[j] == ",":
                j += 1
            elif json_string[j] == "}":
                return j + 1, True
            else:
                raise MalformedJSON(f"Expected ',' or '}}', got {json_string[j]}")
    except IndexError:
        return (i, "}") if OBJ in allow else False


def complete_num(json_string: str, allow: Allow, is_top_level=False) -> CompleteResult:
    i = 1
    length = len(json_string)

    # forward
    while i < length and json_string[i] in "1234567890.-+eE":
        i += 1

    modified = False

    # backward
    while json_string[i - 1] in ".-+eE":
        modified = True
        i -= 1

    if modified or i == length and not is_top_level:
        return (i, "") if NUM in allow else False
    else:
        return i, True


loads = decode = parse_json


__all__ = ["loads", "decode", "parse_json", "JSONDecodeError", "PartialJSON", "MalformedJSON", "Allow", "JSON"]
