from wikklytext import to_html

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
    print(to_html(wikkly))
    print('</body>', '</html>', sep="\n")


main()
