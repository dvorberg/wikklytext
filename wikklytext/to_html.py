"""
wikklytext.parser.py: Base parser interface to
wikklytext.lexer. Part of the WikklyText suite.

Copyright (C) 2007,2008 Frank McIngvale
Copyright (C) 2023 Diedrich Vorberg

Contact: diedrich@tux4web.de

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.
"""

import sys, re, html, inspect, io
from io import StringIO
from html import escape as escape_html

from tinymarkup.compiler import HTMLCompiler_mixin
from tinymarkup.context import Context
from tinymarkup.exceptions import ( MarkupError, InternalError,
                                    RestrictionError,  UnsuitableMacro, )
from tinymarkup.utils import html_start_tag
from tinymarkup.cmdline import CmdlineTool

from .parser import WikklyParser
from .compiler import WikklyCompiler

def to_html(wikkly, context:Context=None):
    outfile = io.StringIO()
    parser = WikklyParser()
    compiler = HTMLCompiler(context, outfile)
    compiler.compile(parser, wikkly)
    return outfile.getvalue()

def to_inline_html(wikkly, context:Context=None):
    outfile = io.StringIO()
    parser = WikklyParser()
    compiler = InlineHTMLCompiler(context, outfile)
    compiler.compile(parser, wikkly)
    return outfile.getvalue()

class TableCell(object):
    def __init__(self, header:bool, params:dict):
        self.header = header
        if header:
            self.tag = "th"
        else:
            self.tag = "td"
        self.params = params
        self.output = StringIO()

    def write_cell(self, compiler):
        compiler.open(self.tag, **self.params)
        compiler.print(self.output.getvalue().strip(), end="")
        compiler.close(self.tag)

class Table(object):
    def __init__(self, compiler):
        self.compiler = compiler
        self.original_output = compiler.output
        self._caption = None
        self.tag_params = {}
        self._rows = []
        self.compiler.tag_stack.append("--in-table--")

    @property
    def current_row(self):
        return self._rows[-1]

    @property
    def caption(self):
        return self._caption

    @caption.setter
    def caption(self, caption:str):
        self._caption = caption

    def set_tag_params(self, params):
        self.tag_params = params

    def make_row(self):
        self._rows.append([])

    def make_cell(self, header:bool, params:dict):
        cell = TableCell(header, params)
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
                    cell.write_cell(self.compiler)
                close("tr")

        open("table", **self.tag_params)

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
        if self.compiler.tag_stack.pop() != "--in-table--":
            raise InternalError("Internal Error: Table nesting failed.",
                                location=self.compiler.location)

        # Restore the compiler’s output stream.
        self.compiler.output = self.original_output

        if self._rows:
            # This uses self.compiler.print()
            # which, after the line above, is directed
            # to the original output.
            self.write_table()

class HTMLCompiler(WikklyCompiler, HTMLCompiler_mixin):
    block_level_tags = { "div", "p", "ol", "ul", "li", "blockquote", "code",
                         "table", "tbody", "thead", "tr", "td", "th",
                         "dl", "dt", "dd",
                         "h1", "h2", "h3", "h4", "h5", "h6", }

    # Tags that like to stand on a line by themselves.
    loner_tags = { "ol", "ul", "code", "table", "tbody", "thead", "tr", "dl",}

    def __init__(self, context, output):
        WikklyCompiler.__init__(self, context)
        HTMLCompiler_mixin.__init__(self, output)
        self._table = None

    def compile(self, parser, source):
        self.tag_stack = []
        super().compile(parser, source)

    def print(self, *args, **kw):
        print(*args, **kw, file=self.output)

    def get_html(self):
        return self.output.getvalue()

    def open(self, tag, **params):
        # If we’re in a <p> and we’re opening a block level element,
        # close the <p> first.
        #if self.tag_stack and self.tag_stack[-1] == "p" \
        #   and tag in self.block_level_tags:
        #    self.close("p")
        if tag in self.loner_tags:
            end = "\n"
        else:
            end = ""

        self.print(html_start_tag(tag, **params), end=end)
        self.tag_stack.append(tag)

    def close(self, tag):
        if tag in self.block_level_tags:
            end = "\n"
        else:
            end = ""

        self.print(f"</{tag}>", end=end)

        if not self.tag_stack or self.tag_stack[-1] != tag:
            raise InternalError(f"Internal error. HTML nesting failed. "
                                f"Can’t close “{tag}”. "
                                f"Tag stack: {repr(self.tag_stack)}.",
                                location=self.compiler.location)
        else:
            self.tag_stack.pop()

    def begin_document(self, lexer):
        super().begin_document(lexer)
        self.begin_html_document()

    def end_document(self):
        self.close_all()

    def close_all(self):
        if self._table:
            self.endTable()

        while self.tag_stack:
            self.close(self.tag_stack[-1])

    def beginParagraph(self): self.open("p")
    def endParagraph(self): self.close("p")

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

    def beginCodeInline(self):
        print("beginCodeInline")

    def endCodeInline(self):
        print("endCodeInline")

    def characters(self, txt):
        self.print(escape_html(txt), end="")

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

    def beginBlockquote(self, macro, args, kw):
        if macro is not None:
            params = self.call_macro_method(
                macro.tag_params, args, kw,
                self.parser.location)
        else:
            params = {}

        self.open("blockquote", **params)

    def endBlockquote(self):
        self.close("blockquote")

    def handleLink(self, text, target=None):
        self.open("a", href=target or text)
        self.print(text, end="")
        self.close("a")

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

    def setTableCaption(self, caption:str, macro, args, kw):
        self._table.caption = caption
        if macro is not None:
            self._table.tag_params = self.call_macro_method(
                macro.tag_params, args, kw,
                self.parser.location)

    def beginTableRow(self):
        self._table.make_row()

    def endTableRow(self):
        pass

    def beginTableCell(self, header:bool, macro, args, kw):
        if macro is None:
            params = {}
        else:
            params = self.call_macro_method(macro.tag_params, args, kw,
                                            location=self.parser.location)
        self._table.make_cell(header, params)

    def endTableCell(self):
        pass

    def beginDefinitionList(self): self.open("dl")
    def endDefinitionList(self): self.close("dl")
    def beginDefinitionTerm(self): self.open("dt")
    def endDefinitionTerm(self): self.close("dt")
    def beginDefinitionDef(self): self.open("dd")
    def endDefinitionDef(self): self.close("dd")

    def beginInlineBlock(self, classname):
        print("beginInlineBlock(%s)" % classname)

    def endInlineBlock(self):
        print("endInlineBlock")

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
        self.print("<hr />")

    def linebreak(self):
        self.print("<br />", end="")

    def call_macro(self, environment, macro_class, args, kw, location):
        try:
            macro = macro_class(self.context, environment)
        except UnsuitableMacro as exc:
            exc.location = location
            raise

        if environment == "block":
            self.close_all()

        self.print(self.call_macro_method(macro.html_element, args, kw,
                                          location=location),
                   end=macro.end)

    def startStartTagMacro(self, macro_class, args, kw):
        macro = macro_class(self.context, "inline")
        self.open("span", **self.call_macro_method(
            macro.tag_params, args, kw, location=self.parser.location))

    def endStartTagMacro(self):
        self.close("span")


class InlineHTMLCompiler(HTMLCompiler):
    def beginParagraph(self):
        pass

    def endParagraph(self):
        pass

    def beginTable(self):
        raise RestrictionError("You may not use tables in inline markup.",
                               location=self.parser.location)

    def open(self, tag, **params):
        if tag in self.block_level_tags:
            raise RestrictionError("You may only use inline markup "
                                   "in this context.",
                                   location=self.parser.location)
        super().open(tag, **params)

    def call_macro(self, what, macro, args, kw, location):
        if what == "block":
            what = "inline"
        return super().call_macro(what, macro, args, kw, location)



class CmdlineTool(CmdlineTool):
    def default_context(self):
        return Context()

    def to_html(self, outfile, source):
        context = self.default_context()
        parser = WikklyParser()
        compiler = HTMLCompiler(context, outfile)
        compiler.compile(parser, source)


def cmdline_main(context:Context=None):
    cmdline_tool = CmdlineTool(context)
    cmdline_tool()

if __name__ == "__main__":
    cmdline_main()
