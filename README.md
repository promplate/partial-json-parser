# Partial JSON Parser

Sometimes we need **LLM (Large Language Models)** to produce **structural information** instead of natural language. The easiest way is to use JSON.

But before receiving the last token of response, the JSON is broken, which means you can't use `JSON.parse` to decode it. But we still want to stream the data to the user.

Here comes `partial-json-parser`, a lightweight and customizable library for parsing partial JSON strings. Here is a [demo](https://promplate.dev/partial-json-parser).

(Note that there is [a JavaScript implementation](https://github.com/promplate/partial-json-parser-js) too)

## Installation

```sh
pip install partial-json-parser # or poetry / pdm / uv
```

`partial-json-parser` is implemented purely in Python, with good type hints. It is zero-dependency and works with Python 3.6+.

You can install run its demo playground by installing `rich` too or:

```sh
pip install partial-json-parser[playground]
```

Then run the `json-playground` in your terminal, and you can try the parser interactively.

## Usage

```py
from partial_json_parser import loads

>>> loads('{"key": "v')  # {'key': 'v'}
```

Alternatively, you can use `ensure_json` to get the completed JSON string:

```py
from partial_json_parser import ensure_json

>>> ensure_json('{"key": "v')  # '{"key": "v"}'
```

### Detailed Usage

You can import the `loads` function and the `Allow` object from the library like this:

```py
from partial_json_parser import loads, Allow
```

The `Allow` object is just an Enum for options. It determines what types can be partial. types not included in `allow` only appears after its completion can be ensured.

### Parsing complete / partial JSON strings

The `loads` function works just like the built-in `json.loads` when parsing a complete JSON string:

```py
result = loads('{"key":"value"}')
print(result)  # Outputs: {'key': 'value'}
```

You can parse a partial JSON string by passing an additional parameter to the `loads` function. This parameter is a **bitwise OR** of the constants from the `Allow` flag:

(Note that you can directly import the constants you need from `partial-json-parser`)

```py
from partial_json_parser import loads, Allow, STR, OBJ

result = loads('{"key": "v', STR | OBJ)
print(result)  # Outputs: {'key': 'v'}
```

In this example, `Allow.STR` tells the parser that it's okay if a string is incomplete, and `Allow.OBJ` tells the parser so as a dict. The parser then try to return as much data as it can.

If you don't allow partial strings, then it will not add `"key"` to the object because `"v` is not close:

```py
result = loads('{"key": "v', OBJ)
print(result)  # Outputs: {}

result = loads('{"key": "value"', OBJ)
print(result)  # Outputs: {'key': 'value'}
```

Similarity, you can parse partial lists or even partial special values if you allow it:

(Note that `allow` defaults to `Allow.ALL`)

```py
result = loads('[ {"key1": "value1", "key2": [ "value2')
print(result)  # Outputs: [{'key1': 'value1', 'key2': ['value2']}]

result = loads("-Inf")
print(result)  # Outputs: -inf
```

### Handling malformed JSON

If the JSON string is malformed, the `parse` function will throw an error:

```py
loads("wrong")  # MalformedJSON: Malformed node or string on line 1
```

## API Reference

### loads(json_string, [allow_partial], [parser])

- `json_string` `<string>`: The (incomplete) JSON string to parse.
- `allow_partial` `<Allow | int>`: Specify what kind of partialness is allowed during JSON parsing (default: `Allow.ALL`).
- `parser` `(str) -> JSON`: An ordinary JSON parser. Default is `json.loads`.

Complete the JSON string and parse it with `parser` function.

Returns the parsed Python value.

Alias: `decode`, `parse_json`.

### ensure_json(json_string, [allow_partial])

- `json_string` `<string>`: The (incomplete) JSON string to complete.
- `allow_partial` `<Allow | int>`: Specify what kind of partialness is allowed during JSON parsing (default: `Allow.ALL`).

Returns the completed JSON string.

### fix(json_string, [allow_partial])

- `json_string` `<string>`: The (incomplete) JSON string to complete.
- `allow_partial` `<Allow | int>`: Specify what kind of partialness is allowed during JSON parsing (default: `Allow.ALL`).

Returns a tuple of a slice of the input string and the completion.

Note that this is a low-level API, only useful for debugging and demonstration.

### Allow

Enum class that specifies what kind of partialness is allowed during JSON parsing. It has the following members:

- `STR`: Allow partial string.
- `NUM`: Allow partial number.
- `ARR`: Allow partial array.
- `OBJ`: Allow partial object.
- `NULL`: Allow partial null.
- `BOOL`: Allow partial boolean.
- `NAN`: Allow partial NaN.
- `INFINITY`: Allow partial Infinity.
- `_INFINITY`: Allow partial -Infinity.
- `INF`: Allow both partial Infinity and -Infinity.
- `SPECIAL`: Allow all special values.
- `ATOM`: Allow all atomic values.
- `COLLECTION`: Allow all collection values.
- `ALL`: Allow all values.

## Testing

To run the tests for this library, you should clone the repository and install the dependencies:

```sh
git clone https://github.com/promplate/partial-json-parser.git
cd partial-json-parser
pdm install
```

Then, you can run the tests using [Hypothesis](https://hypothesis.works/) and [Pytest](https://pytest.org/):

```sh
pdm test
```

Please note that while we strive to cover as many edge cases as possible, it's always possible that some cases might not be covered.

## License

This project is licensed under the MIT License.
