import inspect, functools, html, dataclasses
from .exceptions import (WikklyError, ErrorInMacroCall,
                         UnknownLanguage, UnknownMacro, UnsuitableMacro)

def html_start_tag(tag, **params):
    def fixkey(key):
        if key.endswith("_"):
            return key[:-1]
        else:
            return key

    if params:
        params = [ f'{fixkey(key)}="{html.escape(value)}"'
                   for (key, value) in params.items() ]
        params = " " + " ".join(params)
    else:
        params = ""

    return f"<{tag}{params}>"

## Macros and their MacroLibrary
empty = inspect.Parameter.empty
def call_macro_method(method, args, kw, location=None):
    """
    Wrap a macro’s html() or tsearch() function in such a way that
    the arguments provided by

        <<mymacro 'a' 1.2 filename='test.jpg'>>

    are mapped correctly to a Python function as

    class MyMacro:
        def html(self, letter, length, filename=None, color='default')

    If the method raises an exception that is not a WikklyError
    it will be wrapped in a ErrorInMacroCall. In any case,
    the “location” information will be provided, if present.
    """
    parameters_by_name = inspect.signature(method).parameters
    parameters = list(parameters_by_name.values())

    def convert_maybe(value, param):
        """
        Provided a value from lexer.parse_macro_parameter_list_from()
        as a string, this function will attempt to cast it to the
        type indicated by the function parameter annotation.
        """
        if param.annotation is not empty:
            kw = {}

            # If the param.annotation is callable and accepts a
            # context parameter, provide it.
            if callable(param.annotation):
                try:
                    sig = inspect.signature(param.annotation)
                except ValueError:
                    pass
                else:
                    for pp in sig.parameters.values():
                        if issubclass(pp.annotation, Context):
                            kw[pp.name] = method.__self__.context
                            break

            try:
                return param.annotation(value, **kw)
            except WikklyError as exc:
                if exc.location:
                    exc.location.lineno += location.lineno - 1
                raise exc
            #ErrorInMacroCall(f"Error in wikkly for {param.name}.",
            #                           location=location) from exc
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

    # Call the method.
    try:
        if "location" in kw and not "location" in parameters_by_name:
            del kw["location"]

        return method(*args, **kw)
    except Exception as exc:
        if not isinstance(exc, WikklyError):
            raise ErrorInMacroCall(f"Error calling {method}",
                                   location=location) from exc
        else:
            exc.location = location
            raise exc


class Macro(object):
    """
    Base class for Wikkly Macros. The macro will be
    """

    # The “name” will be used in the macro library.
    name = None

    def __init__(self, context):
        self.context = context

    def tag_params(self, *args, **kw):
        raise UnsuitableMacro(f"{self} does not implement tag_params().")

    def block_html(self, *args, **kw):
        raise UnsuitableMacro(f"{self} is not suitable for block-level "
                              "usage (only inline markup.")

    def inline_html(self, *args, **kw):
        raise UnsuitableMacro(f"{self} macro is not suitable for inline "
                              "usage (only block-level markup.")

    def tsearch(self, *args, **kw):
        raise NotImplemented()

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

    def get(self, name, source_location):
        if name not in self:
            raise UnknownMacro(f"Macro named “{name}” not found.",
                               location=source_location)

        return self[name]

    def extend(self, other):
        for item in other.values():
            self.register(item)


## Languages
@dataclasses.dataclass
class Language(object):
    iso: str
    tsearch_configuration: str

class Languages(dict):
    def __init__(self, *languages):
        super().__init__()
        for language in languages:
            self.register(language)

    def register(self, language):
        self[language.iso] = language

    def by_iso(self, iso):
        try:
            return self[isi]
        except KeyError:
            raise UnknownLanguage(f"Unknown language (ISO) code: “{iso}”")

## Context
class Context(object):
    def __init__(self, macro_library:MacroLibrary={},
                 languages:Languages=Languages()):
        self.macro_library = macro_library
        self.languages = languages

    def register_language(self, language):
        self.languages.register(language)

    def language(self, iso):
        return self.languages.by_iso(iso)
