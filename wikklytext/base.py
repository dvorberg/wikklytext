import time

class WikklyError(Exception):
	"""
	General-purpose exception raised when errors occur during parsing
	or XML/HTML generation.

	'message' is brief error message (no HTML)
	'looking_at' is text near/after error location
	'trace' is exception trace (raw text) , or '' if no exception occurred.
	'remainder' is buffer after point of error.
	"""
	def __init__(self, message, looking_at=None, trace=None, remainder=''):
		Exception.__init__(self, message)
		self.message = message
		self.looking_at = looking_at
		self.trace = trace
		self.remainder = remainder

	def __str__(self):
		return ( f"WikklyError: Message: {self.message} "
                 f"Looking at: {self.looking_at} "
	             f"Traceback: {self.trace}" )

class Context(object):
	"""
    An instance of WikContext is passed to around through the
	lexer, parser, and called macros. This allows saving/retrieve any
	persistent data in a thread safe way.
    """
	def __init__(self, max_runtime=-1):
		# calculate stop time
		if max_runtime < 0:
			self.stoptime = time() + 1000000 # "unlimited"
		else:
			self.stoptime = time() + max_runtime

	def add_runtime(self, seconds):
		"""
        Add additional runtime before parser/generator will stop.
        """
		self.stoptime += seconds
