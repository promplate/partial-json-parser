from ast import literal_eval


def parse_json(json_string: str):
    if not isinstance(json_string, str):
        raise TypeError(f"expecting str, got {type(json_string).__name__}")
    if not json_string.strip():
        raise ValueError(f"{json_string!r} is empty")
    return _parse_json(json_string)


def _parse_json(json_string: str):
    length = len(json_string)
    index = 0

    def raise_parsing_error(msg: str):
        raise ValueError(f"{msg} at position {index}")

    def parse_any():  # type: () -> str | dict | list | int | float | bool | None
        nonlocal index
        skip_blank()
        if index >= length:
            raise_parsing_error("unexpected end of input")
        if json_string[index] == '"':
            return parse_str()
        if json_string[index] == "{":
            return parse_obj()
        if json_string[index] == "[":
            return parse_arr()
        if json_string[index : index + 4] == "null":
            index += 4
            return None
        if json_string[index : index + 4] == "true":
            index += 4
            return True
        if json_string[index : index + 5] == "false":
            index += 5
            return False
        if json_string[index : index + 8] == "Infinity":
            index += 8
            return float("inf")
        if json_string[index : index + 9] == "-Infinity":
            index += 9
            return float("-inf")
        if json_string[index : index + 3] == "NaN":
            index += 3
            return float("nan")
        return parse_num()

    def parse_str():  # type: () -> str
        nonlocal index
        start = index
        escape = False
        index += 1  # skip initial quote
        while json_string[index] != '"' or escape and json_string[index - 1] == "\\":
            escape = not escape if json_string[index] == "\\" else False
            index += 1
        if index >= length:
            raise_parsing_error("unterminated string literal")
        index += 1  # skip final quote
        return literal_eval(json_string[start:index])

    def parse_obj():
        nonlocal index
        index += 1  # skip initial brace
        skip_blank()
        obj = {}
        while json_string[index] != "}":
            skip_blank()
            key = parse_str()
            skip_blank()
            if index >= length or json_string[index] != ":":
                raise_parsing_error("expected ':' after key in object")
            index += 1  # skip colon
            value = parse_any()
            obj[key] = value
            skip_blank()
            if json_string[index] == ",":
                index += 1  # skip comma
        if index >= length:
            raise_parsing_error("expected '}' at end of object")
        index += 1  # skip final brace
        return obj

    def parse_arr():
        nonlocal index
        index += 1  # skip initial bracket
        arr = []
        while json_string[index] != "]":
            arr.append(parse_any())
            skip_blank()
            if json_string[index] == ",":
                index += 1  # skip comma
        if index >= length or json_string[index] != "]":
            raise_parsing_error("Expected ']' at end of array")
        index += 1  # skip final bracket
        return arr

    def parse_num():  # type: () -> int | float
        nonlocal index
        skip_blank()
        start = index
        try:
            if json_string[index] == "-":
                index += 1
            while json_string[index] not in ",]}":
                index += 1
        except IndexError:
            pass
        return literal_eval(json_string[start:index])

    def skip_blank():
        nonlocal index
        while index < length and (json_string[index] == " " or json_string[index] == "\n"):
            index += 1

    result = parse_any()
    skip_blank()
    if index < length:
        raise_parsing_error("unexpected character after JSON value")
    return result
