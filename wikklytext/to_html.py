import re, html
from io import StringIO

from .parser import Context, WikklyParser
from .macros import BlockLevelMacro
from .exceptions import WikklyError, RestrictionError

def to_html(wikkly, context:Context=None):
    converter = WikklyToHTML(context)
    converter.parse(wikkly)
    return converter.get_html()

def to_inline_html(wikkly, context:Context=None):
    converter = WikklyToInlineHTML(context)
    converter.parse(wikkly)
    return converter.get_html()


class WikklyToHTML(WikklyParser):
    block_level_tags = { "div", "p", "ol", "ul", "li", "blockquote", "code",
                         "table", "tbody", "thead", "tr", "td",
                         "dl", "dt", "dd",
                         "h1", "h2", "h3", "h4", "h5", "h6", }

    # Tags that like to stand on a line by themselves.
    loner_tags = { "ol", "ul", "code", "table", "tbody", "thead", "tr",
                   "dl", }

    paragraph_break_re = re.compile("\n\n+")

    def __init__(self, context=None):
        super().__init__(context)
        self.output = StringIO()
        self.tag_stack = []

    def print(self, *args, **kw):
        print(*args, **kw, file=self.output)

    def get_html(self):
        return self.output.getvalue()

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

        if tag in self.loner_tags:
            end = "\n"
        else:
            end = ""

        self.print(f"<{tag}{params}>", end=end)

        self.tag_stack.append(tag)

    def close(self, tag):
        if tag in self.block_level_tags:
            end = "\n"
        else:
            end = ""

        self.print(f"</{tag}>", end=end)

        if not self.tag_stack or self.tag_stack[-1] != tag:
            raise WikklyError(f"Internal error. HTML nesting failed. "
                              f"Can’t close “{tag}”. "
                              f"Tag stack: {repr(self.tag_stack)}.",
                              location=self.location)
        else:
            self.tag_stack.pop()

    def close_all(self):
        while self.tag_stack:
            self.close(self.tag_stack[-1])

    def beginDoc(self):
        pass
        #self.open("p")

    def endDoc(self):
        self.close_all()

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

    def beginBlockquote(self):
        self.open("blockquote")

    def endBlockquote(self):
        self.close("blockquote")

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
        self.open("table", class_="table wikkly-table")

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
        if self.paragraph_break_re.match(txt) is not None:
            if self.tag_stack and self.tag_stack[-1] == "p":
                self.close("p")

    def linebreak(self):
        self.print("<br />", end="")

    def characters(self, txt):
        if not self.tag_stack:
            self.open("p")

        self.print(txt, end="")

    def call_macro(self, macro, args, kw):
        try:
            result = macro.html(args, kw)
        except WikklyError as exc:
            exc.location = self.location
            raise exc

        if isinstance(macro, BlockLevelMacro):
            self.close_all()
            self.print("\n", result)
        else:
            self.print(result, end="")


    def callStartTagMacro(self, macro, args, kw):
        self.open("span", **macro.span_params(args, kw))

    def endStartTagMacro(self):
        self.close("span")


class WikklyToInlineHTML(WikklyToHTML):
    def beginDoc(self):
        # Do no create the top-level "p".
        pass

    def endDoc(self):
        # Conversely to characters() not opening a top-level "p",
        # there is no need to close it.
        pass

    def characters(self, txt):
        self.print(txt, end="")

    def open(self, tag, **params):
        if tag in self.block_level_tags:
            raise RestrictionError("You may only use inline markup "
                                   "in this context.",
                                   location=self.location)
        super().open(tag, **params)
