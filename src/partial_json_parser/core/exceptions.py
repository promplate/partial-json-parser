class JSONDecodeError(ValueError):
    pass


class PartialJSON(JSONDecodeError):
    pass


class MalformedJSON(JSONDecodeError):
    pass
