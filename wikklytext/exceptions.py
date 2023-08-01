class WikklyError(Exception):
    """
	General-purpose exception raised when errors occur during parsing
	or XML/HTML generation.

	'message' is brief error message (no HTML)
	'looking_at' is text near/after error location
	'trace' is exception trace (raw text) , or '' if no exception occurred.
	'remainder' is buffer after point of error.
	"""
    def __init__(self, message, lineno=None, looking_at=None, trace=None):
        Exception.__init__(self, message)
        self.message = message
        self.lineno = lineno
        if looking_at is None:
            self.looking_at = None
        else:
            self.looking_at = looking_at[:20]
            if len(looking_at) > 20:
                self.looking_at += " …"

        self.trace = trace

    def __str__(self):
        return ( f"WikklyError: Message: {self.message} "
                 f"Line: {self.lineno} "
                 f"Looking at: {self.looking_at} "
                 f"Traceback: {self.trace}" )

class SyntaxError(WikklyError):
    pass

class UnknownMacro(WikklyError):
    pass
