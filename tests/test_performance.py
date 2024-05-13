from functools import partial
from json import dumps
from timeit import timeit

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from partial_json_parser import ALL, ARR, COLLECTION, OBJ, SPECIAL, STR, fix, fix_fast


def deep_json(depth: int):
    strategy: st.SearchStrategy = st.none() | st.booleans() | st.floats() | st.text()
    for _ in range(depth):
        strategy = st.lists(strategy, min_size=5, max_size=20) | st.dictionaries(st.text(), strategy, min_size=5, max_size=20)
    return strategy


dumps = partial(dumps, ensure_ascii=False)


@settings(deadline=None, suppress_health_check={HealthCheck.data_too_large, HealthCheck.too_slow})
@given(deep_json(2).map(dumps))
def test_complete_json_faster(json_string: str):
    t1 = timeit(lambda: fix(json_string, 0), number=500) * 1000
    t2 = timeit(lambda: fix_fast(json_string, 0), number=500) * 1000

    v1 = 1 / t1
    v2 = 1 / t2
    if t1 > t2:
        print(f" {len(json_string):>10} chars - {(v2 - v1) / v1:>6.1%} faster")
    else:
        print(f"\n {json_string}\n")
        print(f" {len(json_string):>10} chars - {(v1 - v2) / v1:>6.1%} slower")


@settings(deadline=None, suppress_health_check={HealthCheck.data_too_large, HealthCheck.too_slow})
@given(deep_json(2).map(dumps).map(lambda s: s[: -len(s) // 2]), st.integers(0, 3).map([ALL, COLLECTION, ARR | STR, OBJ | SPECIAL].__getitem__))
def test_incomplete_json_faster(json_string: str, allow):
    if json_string.startswith("[") and ARR not in allow or json_string.startswith("{") and OBJ not in allow:
        return

    t1 = timeit(lambda: fix(json_string, allow), number=200) * 1000
    t2 = timeit(lambda: fix_fast(json_string, allow), number=200) * 1000

    v1 = 1 / t1
    v2 = 1 / t2
    if t1 > t2:
        print(f" {len(json_string):>10} chars - {(v2 - v1) / v1:>6.1%} faster : {allow!r}")
    else:
        print(f"\n {json_string}\n")
        print(f" {len(json_string):>10} chars - {(v1 - v2) / v1:>6.1%} slower : {allow!r}")


def main():
    print()
    test_incomplete_json_faster()
    test_complete_json_faster()
    print()
