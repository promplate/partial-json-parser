from enum import IntFlag, auto


class Allow(IntFlag):
    """Specify what kind of partialness is allowed during JSON parsing"""

    STR = auto()
    NUM = auto()
    ARR = auto()
    OBJ = auto()
    NULL = auto()
    BOOL = auto()
    NAN = auto()
    INFINITY = auto()
    _INFINITY = auto()

    INF = INFINITY | _INFINITY
    SPECIAL = NULL | BOOL | INF | NAN
    ATOM = STR | NUM | SPECIAL
    COLLECTION = ARR | OBJ
    ALL = ATOM | COLLECTION


STR = Allow.STR
NUM = Allow.NUM
ARR = Allow.ARR
OBJ = Allow.OBJ
NULL = Allow.NULL
BOOL = Allow.BOOL
NAN = Allow.NAN
INFINITY = Allow.INFINITY
_INFINITY = Allow._INFINITY
INF = Allow.INF
SPECIAL = Allow.SPECIAL
ATOM = Allow.ATOM
COLLECTION = Allow.COLLECTION
ALL = Allow.ALL


__all__ = [
    "Allow",
    "STR",
    "NUM",
    "ARR",
    "OBJ",
    "NULL",
    "BOOL",
    "NAN",
    "INFINITY",
    "_INFINITY",
    "INF",
    "SPECIAL",
    "ATOM",
    "COLLECTION",
    "ALL",
]
