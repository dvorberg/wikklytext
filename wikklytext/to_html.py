import re, html
from io import StringIO

from .parser import WikklyParser

class WikklyToHTML(WikklyParser):
    block_level_tags = { "div", "p", "ol", "ul", "li", "blockquote", "code",
                         "table", "tbody", "thead", "tr", "td",
                         "dl", "dt", "dd",
                         "h1", "h2", "h3", "h4", "h5", "h6", }

    paragraph_break_re = re.compile("\n\n+")

    def __init__(self, wcontext):
        self.wcontext = wcontext
        self.output = StringIO()

        self.tag_stack = []

    def print(self, *args, **kw):
        print(*args, **kw, file=self.output)

    def open(self, tag, **params):
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


        # If we’re in a <p> and we’re opening a block level element,
        # close the <p> first.

        if self.tag_stack and self.tag_stack[-1] == "p" \
           and tag in self.block_level_tags:
            self.close("p")

        self.print(f"<{tag}{params}>", end="")

        self.tag_stack.append(tag)

    def close(self, tag):
        if tag in self.block_level_tags:
            end = "\n"
        else:
            end = ""
        self.print(f"</{tag}>", end=end)

        assert self.tag_stack.pop() == tag, ValueError


    def beginDoc(self):
        pass

    def endDoc(self):
        pass

    def beginBold(self): self.open("b")
    def endBold(self): self.close("b")
    def beginItalic(self): self.open("i")
    def endItalic(self): self.close("i")
    def beginStrikethrough(self): self.open("s")
    def endStrikethrough(self): self.close("s")
    def beginUnderline(self): self.open("u")
    def endUnderline(self): self.close("u")
    def beginSuperscript(self): self.open("sup")
    def endSuperscript(self): self.close("sup")
    def beginSubscript(self): self.open("sub")
    def endSubscript(self): self.close("sub")

    def beginHighlight(self, style=None):
        #print("beginHighlight, style=%s" % repr(style))
        self.open("span", class_="wikkly-highlight")

    def endHighlight(self): self.close("span")

    def beginNList(self): self.open("ol")
    def endNList(self): self.close("ol")

    def beginNListItem(self, txt):
        # print("begin N-listitem:%s:" % txt)
        self.open("li")

    def endNListItem(self):
        # print("end N-listitem")
        self.close("li")

    def beginUList(self): self.open("ul")
    def endUList(self): self.close("ul")

    def beginUListItem(self, txt):
        # print("begin U-listitem:%s:" % txt)
        self.open("li")

    def endUListItem(self):
        self.close("li")

    def beginHeading(self, level):
        # print("beginHeading:%s:" % level)
        level = int(level)
        self._current_heading_level = level

        self.open(f"h{level}")

    def endHeading(self):
        self.close(f"h{self._current_heading_level}")
        self._current_heading_level = None

    def beginBlockIndent(self):
        self.open("blockquote")

    def endBlockIndent(self):
        self.close("blockquote")

    def beginLineIndent(self):
        self.open("div", class_="wikkly-line-indent")

    def endLineIndent(self):
        self.close("div")

    def handleLink(self, A, B=None):
        # print("handleLink A=%s, B=%s" % (A,B))
        self.characters("")
        self.print(f'<a href="{A}">{A}</a>', end="")
        self.characters("")

    def handleImgLink(self, title, filename, url):
        print("handleImgLink title=%s, filename=%s, url=%s" % (
            title, filename, url))

    def beginCodeBlock(self):
        self.open("code")

    def endCodeBlock(self):
        self.close("code")

    def beginCodeInline(self):
        print("beginCodeInline")

    def endCodeInline(self):
        print("endCodeInline")

    def beginTable(self):
        self.open("table", class_="wikkly-table")

    def endTable(self):
        self.close("table")

    def setTableCaption(self, txt):
        # print("TableCaption: ",txt)
        pass

    def beginTableRow(self): self.open("tr")
    def endTableRow(self): self.close("tr")
    def beginTableCell(self): self.open("td")
    def endTableCell(self): self.close("td")

    def beginDefinitionList(self): self.open("dl")
    def endDefinitionList(self): self.close("dl")
    def beginDefinitionTerm(self): self.open("dt")
    def endDefinitionTerm(self): self.close("dt")
    def beginDefinitionDef(self): self.open("dd")
    def endDefinitionDef(self): self.close("dd")

    def beginCSSBlock(self, classname):
        print("beginCSSBlock(%s)" % classname)

    def endCSSBlock(self):
        print("endCSSBlock")

    def beginRawHTML(self):
        print("beginRawHTML")

    def endRawHTML(self):
        print("endRawHTML")

    def beginNoWiki(self):
        print("beginNoWiki")

    def endNoWiki(self):
        print("endNoWiki")

    def beginPyCode(self):
        print("beginPyCode")

    def endPyCode(self):
        print("endPyCode")

    # standalone tokens
    def separator(self):
        self.print("<hr />", end="")

    def EOLs(self, txt):
        # We ignore \n
        # print("**", repr(txt))
        if self.paragraph_break_re.match(txt) is not None:
            if self.tag_stack and self.tag_stack[-1] == "p":
                self.close("p")

    def linebreak(self):
        self.print("<br />", end="")

    def characters(self, txt):
        if len(self.tag_stack) == 0:
            # We’re on top level.
            self.open("p")

        self.print(txt, end="")
