import inspect, functools, html
from .exceptions import UnknownMacro

empty = inspect.Parameter.empty
def macromethod(method):
    """
    Wrap a macro’s html() or tsearch() function in such a way that
    the arguments provided by

        <<mymacro 'a' 1.2 filename='test.jpg'>>

    are mapped correctly to a Python function as

    class MyMacro:
        def html(self, letter, length, filename=None, color='default')
    """
    parameters_by_name = inspect.signature(method).parameters
    parameters = list(parameters_by_name.values())

    parameters = parameters[1:] # skip “self”

    def call_it(macro, args, kw):
        from .compiler import Context

        def convert_maybe(value, param):
            """
            Provided a value from lexer.parse_macro_parameter_list_from()
            as a string, this function will attempt to cast it to the
            type indicated by the function parameter annotation.
            """
            if param.annotation is not empty:
                kw = {}

                # Does the annotation have a parameter that’s annotated
                # with a parser.Context class?
                sig = inspect.signature(param.annotation)
                for pp in sig.parameters.values():
                    if issubclass(pp.annotation, Context):
                        kw[pp.name] = macro.context
                        break

                return param.annotation(value, **kw)
            else:
                # These will be provided as strings by
                # parse_macro_pa_list_from()
                # except for `self`.
                return value

        # These are provided as positional arguments.
        positional = parameters[:len(args)]
        # These came with identifier= keywords.
        throughkw = parameters[len(args):]

        # Convert the positional arguments.
        args = [ convert_maybe(arg, param)
                 for arg, param in zip(args, positional) ]

        # Convert the keyword arguments.
        kw = dict([ (name, convert_maybe(value, parameters_by_name[name]),)
                    for name, value in kw.items() ])

        # Fill up the **kw dict to have the provided default values
        # in it.
        for param in throughkw:
            if not param.name in kw and param.default is not empty:
                kw[param.name] = param.default

        # Call the function we wrap.
        return method(macro, *args, **kw)

    return call_it

class Macro(object):
    """
    Base class for Wikkly Macros. The macro will be
    """

    # The “name” will be used in the macro library.
    name = None

    def __init__(self, context):
        self.context = context

    def html(self):
        return None

    def tsearch(self, *args, **kw):
        return None


class InlineMacro(Macro):
    """
    The HTML returned may be used within a <p> tag.
    """
    @macromethod
    def html(self, contents, *args, **kw):
        params = self.span_params(args, kw)
        params = [ f'{key}="{html.escape(value)}"'
                   for (key, value) in params.items() ]
        params =" ".join(params)

        return f'<span {params}>{contents}</span>'

    @macromethod
    def span_params(self, *args, **kw):
        raise NotImplementedError()

class BlockLevelMacro(Macro):
    """
    The HTML returned requires the current paragraph (-like element)
    to be closed to create valid HTML.
    """
    pass


class MacroLibrary(dict):
    def __init__(self, *macros):
        super().__init__()

        for macro in macros:
            self.register(macro)

    def register(self, macro_class:type[Macro]):
        """
        Register a macro class with this library using its “name” attribute
        or its class name, if not present.
        """
        name = macro_class.name or macro_class.__name__.lower()
        if name in self:
            raise NameError(f"A macro named {name} already exists.")
        else:
            self[name] = macro_class

    def register_module(self, module):
        for item in module.values():
            if type(item) == type and issubclass(item, Macro):
                self.register(item)

    def get(self, name):
        if name not in self:
            raise UnknownMacro(f"Macro named “{name}” not found.")
        else:
            return self[name]

    def extend(self, other):
        for item in other.values():
            self.register(item)
