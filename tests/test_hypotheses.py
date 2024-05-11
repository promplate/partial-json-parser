from json import dumps

from hypothesis import given, settings
from hypothesis import strategies as st
from tqdm import tqdm

from partial_json_parser import parse_json

json = st.recursive(
    st.none() | st.booleans() | st.floats() | st.text(),
    lambda children: st.lists(children) | st.dictionaries(st.text(), children),
)


bar = tqdm(mininterval=0, dynamic_ncols=True)
FINE_JSON_EXAMPLES = 333
PARTIAL_JSON_EXAMPLES = 333


@settings(max_examples=FINE_JSON_EXAMPLES, deadline=None)
@given(json)
def test_fine_json(anything):
    assert str(anything) == str(parse_json(dumps(anything, ensure_ascii=False)))
    bar.update()


@settings(max_examples=PARTIAL_JSON_EXAMPLES, deadline=None)
@given(json)
def test_partial_json(anything):
    json_string = dumps(anything, ensure_ascii=False)
    for i in range(1, len(json_string), max(1, len(json_string) // 10)):
        if json_string.startswith("-", 0, i):
            continue
        parse_json(json_string[:i])
    bar.update()


def main():
    bar.clear()
    bar.reset(PARTIAL_JSON_EXAMPLES)
    bar.set_description(" Testing Partial JSON ")
    test_partial_json()

    print()

    bar.clear()
    bar.reset(FINE_JSON_EXAMPLES)
    bar.set_description(" Testing F i n e JSON ")
    test_fine_json()

    bar.close()
