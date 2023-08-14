from wikklytext import to_html, Context, Macro, MacroLibrary

class RedMacro(Macro):
    """
    Example for a simple tag_param()-based macro.
    """
    name = "red"

    def tag_params(self):
        # Yeah, don’t do this. A professional will return
        #
        #    { "class": "red-macro" }
        #
        # and properly define span.red-macro in CSS.
        # Also: A professional chooses a name based on function no just
        # not “red”.
        return { "style": "color: red; font-weight: bold" }

def main():
    with open("every_markup.wikkly") as fp:
        wikkly = fp.read()

    print('<!DOCTYPE html>')
    print('<html>',
          '<head>',
          '<meta charset="utf-8">',
          '</head>',
          '<body>',
          sep="\n")
    print(MacroLibrary.__init__)
    print(to_html(wikkly, Context(MacroLibrary(RedMacro))))
    print('</body>', '</html>', sep="\n")


main()
