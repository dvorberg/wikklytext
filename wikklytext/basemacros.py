from .base import Macro, html_start_tag
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
