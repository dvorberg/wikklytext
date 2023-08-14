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

from tinymarkup.macro import Macro
from tinymarkup.utils import html_start_tag
from .to_html import to_html, to_inline_html

class ByNameMacro(Macro):
    name = None

    def tag_params(self):
        raise NotImplementedError()

    def _html(self, tag, content):
        return html_start_tag(tag, **self.tag_params()) + content + f"</{tag}>"

    def block_html(self, contents:to_html):
        return self._html("div", contents)

    def inline_html(self, contents:to_inline_html):
        return self._html("span", contents)

class LanguageMacro(ByNameMacro):
    """
    To mark blocks as belonging to a certain language.
    """
    def tag_params(self):
        return { "lang": self.name or self.__class__.__name__}

class ClassMacro(ByNameMacro):
    """
    Use a CSS class name to construct a span (inline) or div (block).
    """
    def tag_params(self):
        return { "class_": self.name or self.__class__.__name__}
