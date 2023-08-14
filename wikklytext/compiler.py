from tinymarkup.context import Context
from tinymarkup.macro import Macro, MacroLibrary

from .parser import WikklyParser

class WikklyCompiler(object):
    def __init__(self, context:Context=None):
        if context is None:
            self.context = Context()
        else:
            self.context = context

        self.parser = WikklyParser()

    def compile(self, source):
        self.parser.parse(source, self)

    @property
    def location(self):
        return self.parser.location

    def beginDoc(self):
        print("beginDoc")

    def endDoc(self):
        print("endDoc")

    def beginParagraph(self):
        print("beginParagraph")

    def endParagraph(self):
        print("endParagraph")

    def beginBold(self):
        print("beginBold")

    def endBold(self):
        print("endBold")

    def beginItalic(self):
        print("beginItalic")

    def endItalic(self):
        print("endItalic")

    def beginStrikethrough(self):
        print("beginStrikethrough")

    def endStrikethrough(self):
        print("endStrikethrough")

    def beginUnderline(self):
        print("beginUnderline")

    def endUnderline(self):
        print("endUnderline")

    def beginSuperscript(self):
        print("beginSuperscript")

    def endSuperscript(self):
        print("endSuperscript")

    def beginSubscript(self):
        print("beginSubscript")

    def endSubscript(self):
        print("endSubscript")

    def beginHighlight(self, style=None):
        print("beginHighlight, style=%s" % repr(style))

    def endHighlight(self):
        print("endHighlight")

    def beginNList(self):
        print("begin N-list")

    def endNList(self):
        print("end N-list")

    def beginNListItem(self, txt):
        print("begin N-listitem:%s:" % txt)

    def endNListItem(self):
        print("end N-listitem")

    def beginUList(self):
        print("begin U-list")

    def endUList(self):
        print("end U-list")

    def beginUListItem(self, txt):
        print("begin U-listitem:%s:" % txt)

    def endUListItem(self):
        print("end U-listitem")

    def beginHeading(self, txt):
        print("beginHeading:%s:" % txt)

    def endHeading(self):
        print("endHeading")

    def beginBlockquote(self, macro_name, args, kw):
        print("beginBlockquote")

    def endBlockquote(self):
        print("endBlockquote")

    def beginLineIndent(self):
        print("beginLineIndent")

    def endLineIndent(self):
        print("endLineIndent")

    def handleLink(self, target, text=None):
        print("handleLink target=%s, text=%s" % (target, text))

    def handleImgLink(self, title, filename, url):
        print("handleImgLink title=%s, filename=%s, url=%s" % (
            title,filename,url))

    def beginCodeBlock(self):
        print("beginCodeBlock")

    def endCodeBlock(self):
        print("endCodeBlock")

    def beginCodeInline(self):
        print("beginCodeInline")

    def endCodeInline(self):
        print("endCodeInline")

    def beginTable(self):
        print("beginTable")

    def endTable(self):
        print("endTable")

    def setTableCaption(self, caption:str, macro, args, kw):
        print(f"TableCaption: "
              f"“{caption}” "
              f"with macro: {macro} "
              f"args={args} kw={kw}")

    def beginTableRow(self):
        print("beginTableRow")

    def endTableRow(self):
        print("endTableRow")

    def beginTableCell(self, header:bool, macro, args, kw):
        print("beginTableCell")

    def endTableCell(self):
        print("endTableCell")

    def beginDefinitionList(self):
        print("beginDefinitionList")

    def endDefinitionList(self):
        print("endDefinitionList")

    def beginDefinitionTerm(self):
        print("beginDefinitionTerm")

    def endDefinitionTerm(self):
        print("endDefinitionTerm")

    def beginDefinitionDef(self):
        print("beginDefinitionDef")

    def endDefinitionDef(self):
        print("endDefinitionDef")

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
        print("separator")

    def close_paragraph(self):
        print("close_paragraph")

    def linebreak(self):
        print("linebreak")

    def characters(self, txt):
        print("chars: ", repr(txt))

    def call_macro(self, what, macro, args, kw):
        print("macro: ", repr(what), repr(macro), args, kw)

    def endStartTagMacro(self):
        print("end start tag macro")

    # def handle_codeblock(self, text):
    #     # multi or single line?
    #     if '\n' in text:
    #         # strip leading/trailing newlines
    #         while len(text) and text[0] == '\n':
    #             text = text[1:]

    #         while len(text) and text[-1] == '\n':
    #             text = text[:-1]

    #         self.beginCodeBlock()
    #         self.characters(text)
    #         self.endCodeBlock()
    #     else:
    #         self.beginCodeInline()
    #         self.characters(text)
    #         self.endCodeInline()
