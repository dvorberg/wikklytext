"""
Copyright (C) 2023 Diedrich Vorberg

Contact: diedrich@tux4web.de

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.
"""
from tinymarkup.exceptions import UnsuitableMacro
from tinymarkup.writer import TSearchWriter
from tinymarkup.context import Context

from .parser import WikklyParser
from .compiler import WikklyCompiler
from .to_html import CmdlineTool

class TSearchCompiler(WikklyCompiler):
    def __init__(self, context, output):
        WikklyCompiler.__init__(self, context)
        self.writer = TSearchWriter(output, self.context.root_language)

    # characters() and end_document() are implemented by
    # TSearchCompiler_mixin. No need to repeat them here.

    def word(self, s:str):
        self.writer.word(s)

    def other_characters(self, s:str):
        pass

    def endDocument(self):
        self.writer.finish_tsearch()
    end_document = endDocument

    def beginParagraph(self): pass
    def endParagraph(self): self.writer.tsvector_break()
    def beginBold(self): pass
    def endBold(self): pass
    def beginItalic(self): pass
    def endItalic(self): pass
    def beginStrikethrough(self): pass
    def endStrikethrough(self): pass
    def beginUnderline(self): pass
    def endUnderline(self): pass
    def beginSuperscript(self): pass
    def endSuperscript(self): pass
    def beginSubscript(self): pass
    def endSubscript(self): pass
    def beginHighlight(self, style=None): self.writer.push_weight("C")
    def endHighlight(self): self.writer.pop_weight()
    def beginNList(self): pass
    def endNList(self): pass
    def beginNListItem(self, txt): pass
    def endNListItem(self): pass
    def beginUList(self): pass
    def endUList(self): pass
    def beginUListItem(self, txt): pass
    def endUListItem(self): pass

    def beginHeading(self, level):
        if level < 3:
            self.writer.push_weight("B")
        else:
            self.writer.push_weight("C")

    def endHeading(self):
        self.writer.pop_weight()

    def beginBlockquote(self, macro, args, kw):
        self._blockquote_macro = macro
        if macro is not None:
            params = self.call_macro_method(
                macro.add_searchable_text,
                [self.writer,] + args, kw,
                self.parser.location)

    def endBlockquote(self):
        if self._blockquote_macro is not None:
            params = self.call_macro_method(
                self._blockquote_macro.finish_searchable_text,
                [self.writer], {},
                self.parser.location)
            self._blockquote_macro = None

    def beginLineIndent(self): pass
    def endLineIndent(self): pass

    def handleLink(self, target, text=None):
        if not target.startswith("#"):
            self.word(text or target)

    def beginCodeBlock(self): pass
    def endCodeBlock(self): pass
    def beginCodeInline(self): pass
    def endCodeInline(self): pass
    def beginTable(self): pass
    def endTable(self):
        self.writer.reset_to_root_language()

    def setTableCaption(self, caption:str, macro, args, kw):
        self.writer.push_weight("C")

        if macro is not None:
            params = self.writer.call_macro_method(
                macro.add_searchable_text,
                [self,] + args, kw,
                self.parser.location)

        self.writer.word(caption)

        if macro is not None:
            params = self.writer.call_macro_method(
                macro.finish_searchable_text,
                [self.writer], kw, self.parser.location)

        self.writer.pop_weight()


    def beginTableRow(self):  pass
    def endTableRow(self): pass

    def beginTableCell(self, header:bool, macro, args, kw):
        if header:
            self.writer.push_weight("C")
            self._table_cell_was_header = True
        else:
            self._table_cell_was_header = False

        if macro is not None:
            self.call_macro_method( macro.add_searchable_text,
                                    [self.writer,] + args, kw,
                                    self.parser.location )


    def endTableCell(self):
        if macro is not None:
            self.call_macro_method( macro.finish_searchable_text,
                                    [self.writer], {},
                                    self.parser.location )

        if self._table_cell_was_header:
            self.writer.pop_weight()

    def beginDefinitionList(self): pass
    def endDefinitionList(self): pass
    def beginDefinitionTerm(self): pass
    def endDefinitionTerm(self): pass
    def beginDefinitionDef(self): pass
    def endDefinitionDef(self): pass
    def beginInlineBlock(self, classname): pass
    def endInlineBlock(self): pass

    # standalone tokens
    def separator(self): pass

    def close_paragraph(self):
        self.writer.tsvector_break()

    def linebreak(self): pass

    def call_macro(self, environment, macro_class, args, kw, location):
        try:
            macro = macro_class(self.context, environment)
        except UnsuitableMacro as exc:
            exc.location = location
            raise

        self.call_macro_method(macro.add_searchable_text,
                               [ self.writer, ] + args, kw,
                               location=location)

    def startStartTagMacro(self, macro_class, args, kw):
        macro = macro_class(self.context, "inline")
        self.call_macro_method( macro.add_searchable_text,
                                [ self.writer, ] + list(args), kw,
                                location=self.parser.location )

    def endStartTagMacro(self, macro_class):
        macro = macro_class(self.context, "inline")
        self.call_macro_method( macro.finish_searchable_text,
                                [self.writer], {},
                                location=self.parser.location )


class CmdlineTool(CmdlineTool):
    def to_tsearch(self, outfile, source):
        parser = WikklyParser()
        compiler = TSearchCompiler(self.context, outfile)
        compiler.compile(parser, source)

    to_html = to_tsearch
    def begin_html(self): pass
    def end_html(self): pass

def cmdline_main(context:Context=None):
    cmdline_tool = CmdlineTool(context)
    cmdline_tool()

if __name__ == "__main__":
    print("SELECT ")
    cmdline_main()
