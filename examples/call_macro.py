import time
from io import StringIO

from wikklytext.to_html import to_html, to_inline_html, Context
from wikklytext.macro import WikklyMacro, MacroLibrary, WikklySource

class Bild(WikklyMacro):
    name = "bild"

    def html_element(self, filename):
        return f'<figure><img src="{filename}" /></figure>'

class red(WikklyMacro):
    def tag_params(self):
        return { "style": "color: red; font-weight: bold"}

    def html_element(self, contents:WikklySource):
        return self.start_tag() + contents.html() + self.end_tag

macro_library = MacroLibrary(Bild, red)
    #NamedLanguageMacro,
    # German, English, Bild, TestMacro)

# Hallo Welt!
#
# <<bild "hallo.jpg">>

wikkly = """\
Ich bin ein Absatz mit {{red{rotem, fettem}}} Text drin. Ich bin auch
<<red "rot und fett">>, aber mit dem anderen Syntax.

<<red "Ich bin roter, fetter Text mit meinem eigenen Absatz.">>

<<red "Ich bin roter, fetter Text mit meinem eigenen Absatz.">> Doch hinter
mir steht normaler Text.

<<red '''
Mehrere rote

Absätze.
'''>>

"""




# Ende.


def main():
    t = time.time()
    html = to_html(wikkly, Context(macro_library))
    print("%.4fsec" % (time.time() - t))

    print("*"*60)
    print(html)


main()
