import dataclasses, io

@dataclasses.dataclass
class Location:
    lineno: int
    looking_at: str

class WikklyError(Exception):
    """
	General-purpose exception raised when errors occur during parsing
	or XML/HTML generation.

	'message' is brief error message (no HTML)
	'looking_at' is text near/after error location
	'trace' is exception trace (raw text) , or '' if no exception occurred.
	'remainder' is buffer after point of error.
	"""
    def __init__(self, message, trace=None, location=None):
        Exception.__init__(self, message)

        self.message = message
        self.trace = trace
        self.location = location

    @property
    def lineno(self):
        if self.location:
            return self.location.lineno
        else:
            return None

    @property
    def looking_at(self):
        if self.location:
            return self.location.looking_at
        else:
            return None

    def __str__(self):
        ret = io.StringIO()

        def say(*args):
            print(*args, end=" ", file=ret)

        say(f"{self.message}")
        if self.location:
            say(f"Line: {self.lineno}")
            say(f"Looking at: {repr(self.looking_at)}")

        if self.trace:
            say(f"Traceback: {self.trace}")

        return ret.getvalue()

class SyntaxError(WikklyError):
    pass

class UnknownMacro(WikklyError):
    pass

class RestrictionError(WikklyError):
    pass

class ParseError(WikklyError):
    pass
