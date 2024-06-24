from typing import TYPE_CHECKING, Tuple, Union

from .exceptions import MalformedJSON, PartialJSON
from .options import *

if TYPE_CHECKING:
    from typing import Literal

CompleteResult = Union[Tuple[int, Union[str, "Literal[True]"]], "Literal[False]"]  # (length, complete_string / already completed) / partial


def fix(json_string: str, allow_partial: Union[Allow, int] = ALL):
    """get the original slice and the trailing suffix separately"""

    return _fix(json_string, Allow(allow_partial), True)


def _fix(json_string: str, allow: Allow, is_top_level=False):
    try:
        result = complete_any(json_string.strip(), allow, is_top_level)
        if result is False:
            raise PartialJSON

        index, completion = result
        return json_string[:index], ("" if completion is True else completion)

    except (AssertionError, IndexError) as err:
        raise MalformedJSON(*err.args) from err


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

    length = len(json_string)

    i = 1

    try:
        while True:
            char = json_string[i]

            if char == "\\":
                if i + 1 == length:
                    raise IndexError
                i += 2
                continue
            if char == '"':
                return i + 1, True

            i += 1

    except IndexError:
        if STR not in allow:
            return False

        def not_escaped(index: int):
            text_before = json_string[:index]
            count = index - len(text_before.rstrip("\\"))
            return count % 2 == 0

        # \uXXXX
        _u = json_string.rfind("\\u", max(0, i - 5), i)
        if _u != -1 and not_escaped(_u):
            return _u, '"'

        # \UXXXXXXXX
        _U = json_string.rfind("\\U", max(0, i - 9), i)
        if _U != -1 and not_escaped(_U):
            return _U, '"'

        # \xXX
        _x = json_string.rfind("\\x", max(0, i - 3), i)
        if _x != -1 and not_escaped(_x):
            return _x, '"'

        return i, '"'


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
