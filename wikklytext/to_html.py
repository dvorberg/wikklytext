import re, html
from io import StringIO

from .compiler import Context, WikklyCompiler
from .macros import BlockLevelMacro
from .exceptions import WikklyError, RestrictionError

def to_html(wikkly, context:Context=None):
    compiler = HTMLCompiler(context)
    return compiler.compile(wikkly)

def to_inline_html(wikkly, context:Context=None):
    compiler = InlineHTMLCompiler(context)
    return compiler.compile(wikkly)

class TableCell(object):
    def __init__(self, header:bool, classes:set):
        self.header = header
        if header:
            self.tag = "th"
        else:
            self.tag = "td"
        self.classes = classes
        self.output = StringIO()


    def get_html(self):
        if self.classes:
            cls = f' class="{" ".join(self.classes)}"'
        else:
            cls = ""

        start_tag = f'<{self.tag}{cls}>'
        end_tag = f'</{self.tag}>'

        return start_tag + self.output.getvalue().strip() + end_tag

class Table(object):
    def __init__(self, compiler):
        self.compiler = compiler
        self.original_output = compiler.output
        self.caption = None
        self.classes = {"table"}
        self._rows = []
        self.compiler.tag_stack.append("--in-table--")

    @property
    def current_row(self):
        return self._rows[-1]

    def set_caption(self, caption:str, classes:set):
        self.caption = caption.strip()
        self.classes |= classes

    def make_row(self):
        self._rows.append([])

    def make_cell(self, header:bool, align:str="left"):
        cell = TableCell(header, align)
        self.current_row.append(cell)
        self.compiler.output = cell.output

    def write_table(self):
        print = self.compiler.print
        open = self.compiler.open
        close = self.compiler.close

        def is_head_row(row):
            """
            Return whether a row has all header cells in it.
            """
            for cell in row:
                if not cell.header:
                    return False

            return True

        def print_rows(rows):
            for row in rows:
                open("tr")
                for cell in row:
                    print(cell.get_html())
                close("tr")

        open("table", class_=" ".join(self.classes))
        if self.caption:
            print(f'<caption>{self.caption}</caption>')

        # Split table head and body.
        thead = []
        tbody = self._rows
        while tbody:
            if is_head_row(self._rows[0]):
                thead.append(self._rows[0])
                del self._rows[0]
            else:
                break

        if thead:
            open("thead")
            print_rows(thead)
            close("thead")

        if tbody:
            open("tbody")
            print_rows(tbody)
            close("tbody")

        close("table")

    def finalize(self):
        assert self.compiler.tag_stack.pop() == "--in-table--", WikklyError

        self.compiler.output = self.original_output

        if self._rows:
            # This uses self.compiler.print()
            # which, after the line above, directy
            # to the original output.
            self.write_table()


def needs_paragraph(f):
    def call_it(self, *args):
        if not self.tag_stack:
            self.open("p")

        f(self, *args)

    return call_it


class HTMLCompiler(WikklyCompiler):
    block_level_tags = { "div", "p", "ol", "ul", "li", "blockquote", "code",
                         "table", "tbody", "thead", "tr", "td",
                         "dl", "dt", "dd",
                         "h1", "h2", "h3", "h4", "h5", "h6", }

    # Tags that like to stand on a line by themselves.
    loner_tags = { "ol", "ul", "code", "table", "tbody", "thead", "tr", "dl",}

    paragraph_break_re = re.compile("\n\n+")

    def __init__(self, context=None):
        super().__init__(context)
        self._table = None

    def compile(self, source):
        self.output = StringIO()
        self.tag_stack = []
        super().compile(source)
        return self.output.getvalue()

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
        if self._table:
            self.endTable()

        while self.tag_stack:
            self.close(self.tag_stack[-1])

    def beginDoc(self):
        pass
        #self.open("p")

    def endDoc(self):
        self.close_all()

    @needs_paragraph
    def beginBold(self): self.open("b")
    def endBold(self): self.close("b")

    @needs_paragraph
    def beginItalic(self): self.open("i")
    def endItalic(self): self.close("i")

    @needs_paragraph
    def beginStrikethrough(self): self.open("s")
    def endStrikethrough(self): self.close("s")

    @needs_paragraph
    def beginUnderline(self): self.open("u")
    def endUnderline(self): self.close("u")

    @needs_paragraph
    def beginSuperscript(self): self.open("sup")
    def endSuperscript(self): self.close("sup")

    @needs_paragraph
    def beginSubscript(self): self.open("sub")
    def endSubscript(self): self.close("sub")

    @needs_paragraph
    def beginHighlight(self, style=None):
        #print("beginHighlight, style=%s" % repr(style))
        self.open("span", class_="wikkly-highlight")
    def endHighlight(self): self.close("span")

    @needs_paragraph
    def beginCodeInline(self):
        print("beginCodeInline")

    def endCodeInline(self):
        print("endCodeInline")

    @needs_paragraph
    def characters(self, txt):
        self.print(txt, end="")


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

    def beginTable(self):
        self._table = Table(self)

    def endTable(self):
        self._table.finalize()
        self._table = None

    def setTableCaption(self, caption:str, classes:set):
        self._table.set_caption(caption, classes)

    def beginTableRow(self):
        self._table.make_row()

    def endTableRow(self):
        pass

    def beginTableCell(self, header:bool, classes:set):
        self._table.make_cell(header, classes)

    def endTableCell(self):
        pass

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

    def call_macro(self, macro, args, kw):
        try:
            result = macro.html(args, kw)
        except WikklyError as exc:
            exc.location = self.location
            raise exc1

        if isinstance(macro, BlockLevelMacro):
            self.close_all()
            self.print("\n", result)
        else:
            self.print(result, end="")


    def callStartTagMacro(self, macro, args, kw):
        self.open("span", **macro.span_params(args, kw))

    def endStartTagMacro(self):
        self.close("span")


class InlineHTMLCompiler(HTMLCompiler):
    def beginDoc(self):
        # Do no create the top-level "p".
        pass

    def endDoc(self):
        # Conversely to characters() not opening a top-level "p",
        # there is no need to close it.
        pass

    def beginTable(self):
        raise RestrictionError("You may not use tables in inline markup.",
                               location=self.location)

    def characters(self, txt):
        self.print(txt, end="")

    def open(self, tag, **params):
        if tag in self.block_level_tags:
            raise RestrictionError("You may only use inline markup "
                                   "in this context.",
                                   location=self.location)
        super().open(tag, **params)
