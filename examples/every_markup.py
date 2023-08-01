from wikklytext.to_html import WikklyToHTML

def main():
    wcontext = None
    converter = WikklyToHTML(wcontext)

    with open("every_markup.wikkly") as fp:
        converter.parse(fp.read())

    print('<!DOCTYPE html>')
    print('<html>',
          '<head>',
          '<meta charset="utf-8">',
          '</head>',
          '<body>',
          sep="\n")
    print(converter.output.getvalue())
    print('</body>', '</html>', sep="\n")


main()
