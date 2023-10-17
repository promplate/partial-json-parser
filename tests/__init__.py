from json import dumps

from hypothesis import given, settings
from hypothesis import strategies as st
from tqdm import tqdm

from partial_json_parser import parse_json

json = st.recursive(
    st.none() | st.booleans() | st.floats() | st.text(),
    lambda children: st.lists(children) | st.dictionaries(st.text(), children),
)


fine_json_bar = tqdm(total=1000, desc="Testing Fine JSON", mininterval=0)


@settings(max_examples=1000)
@given(json)
def test_fine_json(anything):
    assert str(anything) == str(parse_json(dumps(anything, ensure_ascii=False)))
    fine_json_bar.update()


def main():
    test_fine_json()
