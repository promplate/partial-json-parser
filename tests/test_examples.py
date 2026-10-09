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


@mark.parametrize("prefix", [" ", "\t", "\r\n", " \t\r\n "])
@mark.parametrize("use_fast_fix", [True, False])
@mark.parametrize("json_string", ["123", "-1.25e4", "true", "false", "null", '"tennis"', '"\\u0061"', "[1, true]", '{"score": 0}'])
def test_complete_json_with_leading_whitespace(prefix, use_fast_fix, json_string):
    original = prefix + json_string + " \r\n"
    for allow in (ALL, 0):
        assert parse_json(original, allow, use_fast_fix=use_fast_fix) == standard_loads(original)
        assert ensure_json(original, allow, use_fast_fix=use_fast_fix).startswith(prefix)


@mark.parametrize("prefix", [" ", "\t", "\r\n", " \t\r\n "])
@mark.parametrize("complete", [fix, fix_fast])
@mark.parametrize(
    "json_string, head, tail, allow, expected",
    [
        ('"tennis', '"tennis', '"', STR, "tennis"),
        ('"te\\u00', '"te', '"', STR, "te"),
        ("12e+", "12", "", NUM, 12),
        ("t", "", "true", BOOL, True),
        ("f", "", "false", BOOL, False),
        ("n", "", "null", NULL, None),
        ('[1, "tennis', '[1, "tennis', '"]', ARR | STR, [1, "tennis"]),
        ('{"score": t', '{"score": ', "true}", OBJ | BOOL, {"score": True}),
    ],
)
def test_partial_json_with_leading_whitespace(prefix, complete, json_string, head, tail, allow, expected):
    original = prefix + json_string
    actual_head, actual_tail = complete(original, allow)
    assert (actual_head, actual_tail) == (prefix + head, tail)
    assert original.startswith(actual_head)
    assert standard_loads(actual_head + actual_tail) == expected


@mark.parametrize("prefix", [" ", "\t", "\r\n", " \t\r\n "])
@mark.parametrize("complete", [fix, fix_fast])
def test_leading_whitespace_keeps_partial_restrictions(prefix, complete):
    with raises(PartialJSON):
        complete(prefix + "t", ~BOOL)
    with raises(MalformedJSON):
        complete(prefix)


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
