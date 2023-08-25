"""
Copyright (C) 2023 Diedrich Vorberg

Contact: diedrich@tux4web.de

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.
"""

import re
from tinymarkup.macro import Macro, MacroLibrary
from tinymarkup.context import Context
from tinymarkup.utils import html_start_tag
from .to_html import to_html, to_inline_html
from . import lextokens

class WikklyMacro(Macro):
    """
    A Wikkly Macro is called through the call_macro_method() mechanism.
    In Wikkly, a regular macro call has space-separated parameters
    that may be any Python literal.

       <<macro 1 2.3 "String" '''String with
          line breaks in it.'''>>

    These will be passed to the macro methods as strings unless the method
    is defined with type hints, for example:

       def tag_params(self, count:int, width:float, comment:str):

    Will be called with the parameters above. The macro method may require
    a string paramter to be parsed as Wikkly and then passed as HTML like
    this:

       class blockquote(WikklyMacro):
          def html_element(self, contents:WikklySource):
             return '<blockquote> . . .

          def tsearch_data(self, contents:to_tsearch_data):
             return [ . . .

    Type hints must be callables and will be passed the string paramter
    as input. Should the type hint (which is a callable) itself have
    parameters with type hints that point to Context, the current context
    will be supplied. A function like:

        def to_html(source, context:Context):
             . . .

    will have the current context as 2nd parameter. The same holds true for
    parameters hinted as WikklyMacro
    """
    def tag_params(self, *args, **kw):
        """
        Return a dict object mapping HTML attributes to values. These will
        be used to open an HTML tag in these contexts:
        - bockquotes <<<macro . . . >>>
        - Table captions |macro Caption    |
        - Table cells    |macro Contents | next call |
        - @@macro: . . . @@ inline markup
        """
        raise NotImplementedError()

    @property
    def tag(self):
        if self.environment == "block":
            return "div"
        else:
            return "span"

    def start_tag(self, *args, **kw):
        return html_start_tag(
            self.tag, **self.tag_params(*args, **kw)) + self.end

    @property
    def end_tag(self):
        return f'</{self.tag}>'


    def html_element(self, *args, **kw):
        """
        Return a complete HTML element inserted into the compiler’s output
        on macro call.
        """
        return self.start_tag(*args, **kw) + self.end_tag

eols_re = re.compile(lextokens.t_EOLS.__doc__)
class WikklySource(object):
    def __init__(self, source, context:Context, macro:WikklyMacro):
        self.source = source
        self.context = context
        self.macro = macro

    def html(self):
        if self.macro.environment == "block":
            return to_html(self.source, context=self.context)
        else:
            return to_inline_html(self.source, context=self.context)

    __str__ = html

    def has_paras(self):
        """
        Return whether the source contains multiple Wikkly Paragraphs
        """
        result = eols_re.search(self.source)
        if result is not None:
            value = result.group()
            return (value.count("\n") > 1)

        return False

############################################################
## Misc. Macro base classes

class DecoratorMacro(WikklyMacro):
    """
    Baseclass for those macros that take a single wikkly source parameter
    and “decorate” the resulting HTML in some way depening on their name.
    """
    def html_element(self, contents:WikklySource):
        """
        Return a complete HTML element inserted into the compiler’s output
        on macro call.
        """
        return self.start_tag() + contents.html() + self.end_tag

class LanguageMacro(DecoratorMacro):
    """
    Base class for the languages used in a context. The macro’s name
    should be an ISO language code.
    """
    def tag_params(self):
        return { "lang": self.get_name(), }

class ClassMacro(DecoratorMacro):
    """
    This will set the resulting HTML element’s class= attribute to the
    macro’s name.

    <<subdued 'Grey text'>> → <span class="subdued">Grey text</span>
    """
    def css_class(self):
        return self.get_name()

    def tag_params(self):
        return { "class": self.css_class(), }
