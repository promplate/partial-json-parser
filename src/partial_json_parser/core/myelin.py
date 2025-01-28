"""Myelin acts as the highway among neurons, epitomizing the leapfrog methodology within this algorithm."""

from re import compile
from typing import List, Tuple, Union

from .complete import _fix
from .exceptions import PartialJSON
from .options import *

finditer = compile(r'["\[\]{}]').finditer


def scan(json_string: str):
    return [(match.start(), match.group()) for match in finditer(json_string)]


def join_closing_tokens(stack: List[Tuple[int, str]]):
    return "".join("}" if char == "{" else "]" for _, char in reversed(stack))


def fix_fast(json_string: str, allow_partial: Union[Allow, int] = ALL):
    allow = Allow(allow_partial)
    
    # Handle PREFIX by finding first { or [
    if PREFIX in allow:
        first_brace = json_string.find('{')
        first_bracket = json_string.find('[')
        
        if first_brace != -1 and (first_bracket == -1 or first_brace < first_bracket):
            json_string = json_string[first_brace:]
        elif first_bracket != -1:
            json_string = json_string[first_bracket:]
    
    # Handle POSTFIX by finding last } or ]
    if POSTFIX in allow:
        last_brace = json_string.rfind('}')
        last_bracket = json_string.rfind(']')
        
        if last_brace != -1 and (last_bracket == -1 or last_brace > last_bracket):
            json_string = json_string[:last_brace + 1]
        elif last_bracket != -1:
            json_string = json_string[:last_bracket + 1]
    
    # Always enable STR when handling PREFIX/POSTFIX
    if PREFIX in allow or POSTFIX in allow:
        allow = Allow(allow | STR)
    
    return _fix(json_string, allow, True)


def fix_fast_old(json_string: str, allow_partial: Union[Allow, int] = ALL):
    allow = Allow(allow_partial)
    original_allow = allow
    
    # Handle PREFIX by finding first { or [
    if PREFIX in allow:
        first_brace = json_string.find('{')
        first_bracket = json_string.find('[')
        
        if first_brace != -1 and (first_bracket == -1 or first_brace < first_bracket):
            json_string = json_string[first_brace:]
        elif first_bracket != -1:
            json_string = json_string[first_bracket:]
    
    # Handle POSTFIX by finding matching closing brace/bracket
    if POSTFIX in allow:
        # Find opening token
        first_char = json_string[0] if json_string else ''
        if first_char not in '{[':
            # No valid JSON start found
            return _fix(json_string, original_allow, True)
            
        # Find matching closing token
        closing_char = '}' if first_char == '{' else ']'
        stack = []
        in_string = False
        
        for i, char in enumerate(json_string):
            if char == '"' and (i == 0 or json_string[i-1] != '\\'):
                in_string = not in_string
            elif not in_string:
                if char in '{[':
                    stack.append(char)
                elif char in ']}':
                    if not stack:
                        break
                    if (char == '}' and stack[-1] == '{') or (char == ']' and stack[-1] == '['):
                        stack.pop()
                        if not stack:  # Found matching closing token
                            json_string = json_string[:i+1]
                            break
        
        # Remove PREFIX/POSTFIX from allow since we've handled them
        allow = Allow(allow & ~(PREFIX | POSTFIX))

    def is_escaped(index: int):
        text_before = json_string[:index]
        count = index - len(text_before.rstrip("\\"))
        return count % 2

    stack = []
    in_string = False
    last_string_start = -1
    last_string_end = -1

    tokens = scan(json_string)

    if not tokens or tokens[0][1] == '"':
        return _fix(json_string, allow, True)

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

    if (STR | COLLECTION) not in allow:

        def truncate_before_last_key_start(container_start: int, last_string_end: int, stack):
            last_key_start = last_string_end  # backtrace the last key's start and retry finding the last comma
            while True:
                last_key_start = json_string.rfind('"', container_start, last_key_start)
                if last_key_start == -1:  # this is the only key
                    # { "key": "v
                    return json_string[: container_start + 1], join_closing_tokens(stack)
                if is_escaped(last_key_start):
                    last_key_start -= 1
                else:
                    last_comma = json_string.rfind(",", container_start, last_key_start)
                    if last_comma == -1:
                        # { "key": "
                        return json_string[: container_start + 1], join_closing_tokens(stack)
                    # # { ... "key": ... , "
                    return json_string[:last_comma], join_closing_tokens(stack)

    if COLLECTION not in allow:
        for index, [_i, _char] in enumerate(stack):
            if _char == "{" and OBJ not in allow or _char == "[" and ARR not in allow:
                if index == 0:
                    raise PartialJSON

                # to truncate before the last container token and the last comma (if exists) of its parent container

                # reset `last_string_end` to before `_i`
                if _i < last_string_start:
                    if last_string_start < _i:  # ... { "k
                        last_string_end = json_string.rfind('"', last_string_end, _i)
                    else:  # ... { "" ...
                        last_string_end = json_string.rfind('"', None, _i)

                last_comma = json_string.rfind(",", max(stack[index - 1][0], last_string_end) + 1, _i)

                if last_comma == -1:
                    if stack[index - 1][1] == "[":
                        # [ ... [
                        return json_string[:_i], join_closing_tokens(stack[:index])

                    # { "key": [ 1, 2, "v
                    # { "key": [ 1, 2, "value"
                    if last_string_start > last_string_end:
                        return truncate_before_last_key_start(stack[index - 1][0], last_string_end, stack[:index])

                    last_comma = json_string.rfind(",", stack[index - 1][0] + 1, last_string_start)
                    if last_comma == -1:
                        return json_string[: stack[index - 1][0] + 1], join_closing_tokens(stack[:index])
                    return json_string[:last_comma], join_closing_tokens(stack[:index])

                # { ..., "key": {
                # ..., {
                return json_string[:last_comma], join_closing_tokens(stack[:index])

    if STR not in allow and in_string:  # truncate before the last key
        if stack[-1][0] > last_string_end and stack[-1][1] == "{":
            # { "k
            return json_string[: stack[-1][0] + 1], join_closing_tokens(stack)

        last_comma = json_string.rfind(",", max(stack[-1][0], last_string_end) + 1, last_string_start - 1)
        if last_comma != -1:
            # { "key": "v", "k
            # { "key": 123, "k
            # [ 1, 2, 3, "k
            return json_string[:last_comma], join_closing_tokens(stack)

        # { ... "key": "v
        return truncate_before_last_key_start(stack[-1][0], last_string_end, stack)

    # only fix the rest of the container in O(1) time complexity

    assert in_string == (last_string_end < last_string_start)

    if in_string:
        if stack[-1][1] == "[":  # [ ... "val
            head, tail = _fix(json_string[last_string_start:], allow)  # fix the last string
            return json_string[:last_string_start] + head, tail + join_closing_tokens(stack)

        assert stack[-1][1] == "{"  # { ... "val

        start = max(last_string_end, stack[-1][0])

        if "," in json_string[start + 1 : last_string_start]:
            # { ... "k": "v", "key
            # { ... "k": 123, "key
            last_comma = json_string.rindex(",", start, last_string_start)
            head, tail = _fix(stack[-1][1] + json_string[last_comma + 1 :], allow)
            return json_string[:last_comma] + head[1:], tail + join_closing_tokens(stack[:-1])

        if ":" in json_string[start + 1 : last_string_start]:
            # { ... ": "val
            head, tail = _fix(json_string[last_string_start:], allow)  # fix the last string (same as array)
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

        head, tail = _fix(char + json_string[last_comma + 1 :], allow)
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
        head, tail = _fix(json_string[i:], allow)
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
        head, tail = _fix(json_string[i:], allow)
        return json_string[:i] + head, tail + join_closing_tokens(stack[:-1])

    if last_colon == -1:
        if json_string.rfind(":", max(i, last_comma) + 1, last_string_start) != -1:
            # { ... , "key": "value"
            return json_string, join_closing_tokens(stack)

        # { ... , "key"
        head, tail = _fix("{" + json_string[last_comma + 1 :], allow)
        if not head[1:] + tail[:-1].strip():
            return json_string[:last_comma] + head[1:], tail + join_closing_tokens(stack[:-1])
        return json_string[: last_comma + 1] + head[1:], tail + join_closing_tokens(stack)

    assert last_colon > last_comma  # { ... , "key":

    head, tail = _fix("{" + json_string[last_comma + 1 :], allow)
    if not head[1:] + tail[:-1].strip():
        return json_string[:last_comma] + head[1:], tail + join_closing_tokens(stack[:-1])
    return json_string[: last_comma + 1] + head[1:], tail + join_closing_tokens(stack[:-1])
