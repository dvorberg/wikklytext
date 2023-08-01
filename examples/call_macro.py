import time
from io import StringIO

from wikklytext import to_html, to_inline_html, Context
from wikklytext.macros import (InlineMacro, BlockLevelMacro,
                               MacroLibrary, macromethod)

class LanguageMacro(InlineMacro):
    @macromethod
    def html(self, contents:to_inline_html):
        return f'<span lang="{self.name}">{contents}</span>'

    @macromethod
    def span_params(self):
        return { "lang": self.name, }

class German(LanguageMacro):
    name = "de"

class English(LanguageMacro):
    name = "en"

class NamedLanguageMacro(InlineMacro):
    name = "lang"

    @macromethod
    def html(self, lang, contents:to_inline_html):
        return f'<span lang="{lang}">{contents}</span>'

    @macromethod
    def span_params(self, lang):
        return { "lang": lang, }


class Bild(BlockLevelMacro):
    @macromethod
    def html(self, filename):
        return f'<figure><img src="{filename}" /></figure>'

pprint = print
class TestMacro(BlockLevelMacro):
    @macromethod
    def html(self, *args, **kw):
        fp = StringIO()

        def print(*args):
            pprint(*args, file=fp)

        print("Args")
        for arg in args:
            print(repr(arg))
        print()

        print("kw")
        for name, value in kw.items():
            print(name, "=", repr(value))
        print()

        return f'<pre>{fp.getvalue()}</pre>'

macro_library = MacroLibrary(NamedLanguageMacro,
                             German, English, Bild, TestMacro)

def main():
    #with open("call_macro.wikkly") as fp:
    #    wikkly = fp.read()

    wikkly = """\


Hallo Welt!

<<bild "hallo.jpg">>

Ende.
"""

    t = time.time()
    html = to_html(wikkly, Context(macro_library))
    print("%.4fsec" % (time.time() - t))

    print("*"*60)
    print(html)


main()
