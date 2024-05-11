from typing import Callable, Dict, List, Optional, Union

from .complete import fix
from .myelin import fix_fast
from .options import *

Number = Union[int, float]
JSON = Union[str, bool, Number, List["JSON"], Dict[str, "JSON"], None]


def parse_json(json_string: str, allow_partial: Union[Allow, int] = ALL, parser: Optional[Callable[[str], JSON]] = None, use_fast_fix=True) -> JSON:
    if parser is None:
        from json import loads as parser

    return parser(ensure_json(json_string, allow_partial, use_fast_fix))


def ensure_json(json_string: str, allow_partial: Union[Allow, int] = ALL, use_fast_fix=True) -> str:
    """get the completed JSON string"""

    if use_fast_fix:
        head, tail = fix_fast(json_string, allow_partial)
    else:
        head, tail = fix(json_string, allow_partial)

    return head + tail
