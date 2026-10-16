from itertools import accumulate
from json import dumps
from json import loads as standard_loads
from math import isnan

from hypothesis import given, settings
from hypothesis.strategies import integers
from pytest import mark, raises
from test_hypotheses import json

from partial_json_parser import *
from partial_json_parser.core.options import *


def test_str():
    assert parse_json('"', STR) == ""
    with raises(PartialJSON):
        parse_json('"', ~STR)

    assert parse_json(r'"\\') == "\\"
    assert parse_json(r'"\\u') == "\\u"
    assert parse_json(r'"\\U\\u') == "\\U\\u"


def test_arr():
    assert parse_json('["', ARR) == []
    assert parse_json('["', ARR | STR) == [""]

    with raises(PartialJSON):
        parse_json("[", STR)
    with raises(PartialJSON):
        parse_json('["', STR)
    with raises(PartialJSON):
        parse_json('[""', STR)
    with raises(PartialJSON):
        parse_json('["",', STR)


def test_obj():
    assert parse_json('{"": "', OBJ) == {}
    assert parse_json('{"": "', OBJ | STR) == {"": ""}

    with raises(PartialJSON):
        parse_json("{", STR)
    with raises(PartialJSON):
        parse_json('{"', STR)
    with raises(PartialJSON):
        parse_json('{""', STR)
    with raises(PartialJSON):
        parse_json('{"":', STR)
    with raises(PartialJSON):
        parse_json('{"":"', STR)
    with raises(PartialJSON):
        parse_json('{"":""', STR)


def test_singletons():
    assert parse_json("n", NULL) is None
    with raises(PartialJSON):
        parse_json("n", ~NULL)

    assert parse_json("t", BOOL) == True
    with raises(PartialJSON):
        parse_json("t", ~BOOL)

    assert parse_json("f", BOOL) == False
    with raises(PartialJSON):
        parse_json("f", ~BOOL)

    assert parse_json("I", INF) == float("inf")
    with raises(PartialJSON):
        parse_json("I", ~INFINITY)

    assert parse_json("-I", INF) == float("-inf")
    with raises(PartialJSON):
        parse_json("-I", ~_INFINITY)

    assert isnan(parse_json("N", NAN))  # type: ignore
    with raises(PartialJSON):
        parse_json("N", ~NAN)


def test_num():
    assert parse_json("0", ~NUM) == 0
    assert parse_json("-1.25e+4", ~NUM) == -1.25e4
    assert parse_json("-1.25e+", NUM) == -1.25
    assert parse_json("-1.25e", NUM) == -1.25


def test_error():
    with raises(MalformedJSON):
        parse_json("a")
    with raises(MalformedJSON):
        parse_json("{0")
    with raises(MalformedJSON):
        parse_json("--")


def test_fix():
    assert fix("[") == fix_fast("[") == ("[", "]")
    assert fix("[0.") == fix_fast("[0.") == ("[0", "]")
    assert fix('{"key": ') == fix_fast('{"key": ') == ("{", "}")
    assert fix("t") == fix_fast("t") == ("", "true")
    assert fix("[1", ~NUM) == fix_fast("[1", ~NUM) == ("[", "]")
    assert fix("1", ~NUM) == fix_fast("1", ~NUM) == ("1", "")
    with raises(PartialJSON):
        fix("-")


def test_fix_fast():
    assert fix_fast('["a", "b', ~STR) == ('["a"', "]")
    assert fix_fast('["a","b', ~STR) == ('["a"', "]")
    assert fix_fast('["a" ,"b', ~STR) == ('["a" ', "]")


def consistent(json_string, allow):
    try:
        res = fix(json_string, allow)
        return res == fix_fast(json_string, allow)
    except PartialJSON as err:
        with raises(PartialJSON, match=f"^{err}$"):
            fix_fast(json_string, allow)
        return True


def test_consistency():
    dict_example = {"key1": 123, "key2": "value"}
    list_example = [1, 2, None, float("inf"), float("-inf"), float("nan"), True, False, "string", dict_example]

    dict_json = dumps(dict_example)
    list_json = dumps(list_example)

    for json_string in (*accumulate(dict_json), *accumulate(list_json)):
        for allow in range(ALL + 1):
            assert consistent(json_string, allow), f"{Allow(allow)!r} - {json_string}"


@settings(deadline=None)
@given(json.map(dumps), integers(0, ALL).map(Allow))
def test_consistencies(json_string, allow):
    for json_string in accumulate(json_string):
        assert consistent(json_string, allow), f"{Allow(allow)!r} - {json_string}"


@mark.parametrize("use_fast_fix", [True, False])
@mark.parametrize(
    "text, expected",
    [
        ('"hello ', "hello "),
        ('"   ', "   "),
        ('"hello\u00a0', "hello\u00a0"),
        ('"hello\u3000', "hello\u3000"),
        ('["hello ', ["hello "]),
        ('[0, "hello ', [0, "hello "]),
        ('{"key": "hello ', {"key": "hello "}),
        ('{"ok": true, "key": "hello ', {"ok": True, "key": "hello "}),
        ('[{"key": "hello ', [{"key": "hello "}]),
    ],
)
def test_partial_string_keeps_trailing_whitespace(text, expected, use_fast_fix):
    assert parse_json(text, use_fast_fix=use_fast_fix) == expected


@mark.parametrize("use_fast_fix", [True, False])
@mark.parametrize("text", ['"hello "', '["hello "]', '{"key": "hello "}'])
def test_complete_string_with_trailing_json_whitespace(text, use_fast_fix):
    text += " \t\r\n"
    assert parse_json(text, use_fast_fix=use_fast_fix) == standard_loads(text)


@mark.parametrize("use_fast_fix", [True, False])
@mark.parametrize("text, allow, expected", [('["hello ', ARR, []), ('{"key": "hello ', OBJ, {})])
def test_string_whitespace_does_not_enable_partial_strings(text, allow, expected, use_fast_fix):
    assert parse_json(text, allow, use_fast_fix=use_fast_fix) == expected


@mark.parametrize("use_fast_fix", [True, False])
@mark.parametrize("container", ["{text}", "[{text}", '{{"key": {text}'])
@mark.parametrize("prefix, expected", [("t", True), ("f", False), ("n", None), ("Inf", float("inf")), ("-Inf", float("-inf")), ("Na", float("nan"))])
def test_partial_literal_keeps_whitespace_recovery(prefix, expected, container, use_fast_fix):
    value = parse_json(container.format(text=prefix + " \t\r\n"), use_fast_fix=use_fast_fix)
    if container.startswith("["):
        value = value[0]
    elif container.startswith("{{"):
        value = value["key"]
    if isinstance(expected, float) and isnan(expected):
        assert isnan(value)
    else:
        assert value == expected


@mark.parametrize("use_fast_fix", [True, False])
@mark.parametrize("container", ["{text}", "[{text}", '{{"key": {text}'])
@mark.parametrize(
    "text, expected",
    [
        ('"hello\t', "hello"),
        ('"hello\n ', "hello"),
        ('"hello\\ ', "hello"),
        (r'"\u0                 ', ""),
        (r'"\U0                 ', ""),
        (r'"\x0                 ', ""),
        (r'"\u000\                 ', ""),
    ],
)
def test_partial_string_keeps_invalid_suffix_recovery(text, expected, container, use_fast_fix):
    value = parse_json(container.format(text=text), use_fast_fix=use_fast_fix)
    if container.startswith("["):
        value = value[0]
    elif container.startswith("{{"):
        value = value["key"]
    assert value == expected


@mark.parametrize("use_fast_fix", [True, False])
@mark.parametrize(
    "text, expected",
    [
        (r'"hello\t ', "hello\t "),
        (r'"hello\n ', "hello\n "),
        (r'"\u0061 ', "a "),
        (r'"\\u0 ', "\\u0 "),
        (r'"\\x0 ', "\\x0 "),
        (r'"hello\\ ', "hello\\ "),
    ],
)
def test_partial_string_keeps_spaces_after_valid_escapes(text, expected, use_fast_fix):
    assert parse_json(text, use_fast_fix=use_fast_fix) == expected


@mark.parametrize("use_fast_fix", [True, False])
@mark.parametrize("number", ["1", "-1", "1e+2", "-1e+2"])
@mark.parametrize("container, allow, expected", [("[{text}", ARR, []), ('{{"key": {text}', OBJ, {})])
def test_numeric_whitespace_keeps_partial_restrictions(number, container, allow, expected, use_fast_fix):
    text = container.format(text=number + " \t\n")
    assert parse_json(text, allow, use_fast_fix=use_fast_fix) == expected
