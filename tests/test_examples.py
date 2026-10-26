from itertools import accumulate
from json import dumps
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


class SliceCounter(str):
    """Measure requested slice lengths without timing or large allocations."""

    def __new__(cls, value):
        instance = super().__new__(cls, value)
        instance.sliced_characters = 0
        return instance

    def __getitem__(self, key):
        result = super().__getitem__(key)
        if isinstance(key, slice):
            self.sliced_characters += len(result)
        return result


@mark.parametrize("count", [32, 64, 128])
@mark.parametrize("partial", [False, True])
def test_string_array_slice_work_is_linear(count, partial):
    values = ["abc"] * count
    encoded = dumps(values)
    text = SliceCounter(encoded[:-1] if partial else encoded)
    assert loads(text) == values
    # Permit linear copying for completion, but not a prefix copy per quote.
    assert text.sliced_characters <= 4 * len(text)


@mark.parametrize("slashes", range(9))
@mark.parametrize("container", [list, dict])
def test_escape_runs_in_every_prefix(slashes, container):
    value = "\\" * slashes + '"[]{}'
    document = [value, "tail\\"] if container is list else {value: value, "tail\\": "end"}
    encoded = dumps(document)
    assert loads(encoded) == document
    for end in range(1, len(encoded) + 1):
        prefix = encoded[:end]
        for allow in range(ALL + 1):
            try:
                expected = fix(prefix, allow)
            except PartialJSON:
                with raises(PartialJSON):
                    fix_fast(prefix, allow)
            else:
                assert fix_fast(prefix, allow) == expected
