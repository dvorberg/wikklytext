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

import re
from .lexer import wikkly_lexer

class WikklyParser(object):
    """
    Base class for content parser showing the required API.

    You can also instantiate this by itself to show a trace of the
    tokens from the lexer.
    """
    def beginDoc(self):
        print("beginDoc")

    def endDoc(self):
        print("endDoc")

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

    def beginBlockIndent(self):
        print("beginBlockIndent")

    def endBlockIndent(self):
        print("endBlockIndent")

    def beginLineIndent(self):
        print("beginLineIndent")

    def endLineIndent(self):
        print("endLineIndent")

    def handleLink(self, A, B=None):
        print("handleLink A=%s, B=%s" % (A,B))

    def handleImgLink(self, title, filename, url):
        print("handleImgLink title=%s, filename=%s, url=%s" % (title,filename,url))

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

    def setTableCaption(self, txt):
        print("TableCaption: ",txt)

    def beginTableRow(self):
        print("beginTableRow")

    def endTableRow(self):
        print("endTableRow")

    def beginTableCell(self):
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
        print("separator")

    def EOLs(self, txt):
        print("EOLS (#): ",len(txt))

    def linebreak(self):
        print("linebreak")

    def characters(self, txt):
        print("chars: ", repr(txt))

    def macro(self, name, args, kw):
        print("macro: ", name, args, kw)

    def error(self, message, looking_at=None, trace=None):
        """
        Reports an error to the parser.
        'message': A (usually) short text message describing the error.
        'trace' is a verbose traceback of the error (can be None).

        Both 'message' and 'trace' should be treated as RAW text.

        Note that 'error()' is just another stream event. Parsing will continue after this.
        """
        print("** ERROR **")
        print("Message: ",message)
        print("Trace: ",trace)



    def handle_codeblock(self, text):
        # multi or single line?
        if '\n' in text:
            # strip leading/trailing newlines
            while len(text) and text[0] == '\n':
                text = text[1:]

            while len(text) and text[-1] == '\n':
                text = text[:-1]

            self.beginCodeBlock()
            self.characters(text)
            self.endCodeBlock()
        else:
            self.beginCodeInline()
            self.characters(text)
            self.endCodeInline()

    def parse(self, source):
        # flags:
        #   * need to use re.M so beginning-of-line matches will
        #     work as expected
        #   * use re.I for case-insensitive as well
        #   * use re.S so '.' will match newline also

        # state vars - most of these are local context only, but some are set
        # into self if they are needed above
        in_bold = 0
        in_italic = 0
        in_strikethrough = 0
        in_underline = 0
        in_superscript = 0
        in_subscript = 0
        in_highlight = 0
        in_block_indent = 0
        in_line_indent = 0 # if > 0 this is the nesting level
        # the top of stack is the _currently_ opened listitem + level
        # e.g. for <ul>, item "###" is ('U',3), for <ol>, item '##' is ('N',2)
        list_stack = [('X',0)] # no currently opened list
        #in_Nlistitem = 0
        #in_Ulistitem = 0
        in_heading = 0
        in_deflist = 0 # tiddlywiki does not let DL/DT/DD nest apparently, so don't worry about it
        in_defterm = 0 # in <DT>?
        in_defdef = 0  # in <DD>?
        #in_imglink = 0
        self.in_strip_ccomment = 0 # inside /*** ... ***/ block
        in_html_comment = 0 # inside <!--- ... ---> block
        # since CSS blocks can nest, this is a list of currently open blocks, by CSS name
        css_stack = []
        # allow <html> blocks to nest
        #self.in_html_block = 0
        #self.in_code = 0
        self.in_table = 0
        self.in_tablerow = 0
        self.in_tablecell = 0
        last_token = (None,None)  # type,value

        self.beginDoc()

        for tok in wikkly_lexer.tokenize(source):
            # check for EOF or over time limit
            if tok is None:
                # close any open lists
                while list_stack[-1][0] in "NU":
                    kind,n = list_stack.pop()
                    if kind == 'N':
                        self.endNListItem()
                        self.endNList()
                    else:
                        self.endUListItem()
                        self.endUList()

                # close any open tables
                if self.in_tablecell:
                    self.endTableCell()
                if self.in_tablerow:
                    self.endTableRow()
                if self.in_table:
                    self.endTable()

                # close any opened line-indents
                while in_line_indent:
                    self.endLineIndent()
                    in_line_indent -= 1

                # close any open definition list
                if in_defterm:
                    self.endDefinitionTerm()

                if in_defdef:
                    self.endDefinitionDef()

                if in_deflist:
                    self.endDefinitionList()

                # watch out for ending inside of a structured item
                for v, s in [
                    (in_bold, "'' ... ''"),
                    (in_italic, "// ... //"),
                    (in_strikethrough, "-- ... --"),
                    (in_underline, "__ .. .__"),
                    (in_superscript, "^^ ... ^^"),
                    (in_subscript, "~~ ... ~~"),
                    (in_highlight, "@@ ... @@"),
                    (in_block_indent, "block-indent (<<<)"),
                    #(in_imglink, "[img[ ... ]]"),
                    #(self.in_html_block, "<html> ... </html>"),
                    #(self.in_code, "{{{ ... }}}")]:
                    ]:
                        if v:
                            self.error("ERROR input ended inside %s" % s,
                                         '', '')

                self.endDoc()
                break

            # while in blockquote, hand parser raw chars
            #if self.in_blockquote and tok.type != 'BLOCKQUOTE':
            #   if hasattr(tok,'rawtext'):
            #       self.characters(tok.rawtext)
            #   else:
            #       self.characters(tok.value)
            #
            #   continue

            # while in code, hand parser raw chars
            #if self.in_code and tok.type != 'CODE_END':
            #   if hasattr(tok,'rawtext'):
            #       self.characters(tok.rawtext)
            #   else:
            #       self.characters(tok.value)
            #
            #   continue

            # while in <html>, hand parser raw chars, checking for nesting
            #if self.in_html_block:
            #   if tok.type == 'HTML_END':
            #       self.in_html_block -= 1
            #   elif tok.type == 'HTML_START':
            #       self.in_html_block += 1
            #   else:
            #       if hasattr(tok,'rawtext'):
            #           val = tok.rawtext
            #       else:
            #           val = tok.value
            #
            #       self.characters(val)
            #
            #   continue

            # if just ended a line, and inside a table, and NOT starting a new tablerow, end table
            #if last_token[0] == 'EOLS' and in_table:
            #   if tok.type != 'TABLEROW_START' or len(last_token[1]) > 1:
            #       self.endTable()
            #       in_table = 0

            # if just ended a line, and inside a line-indent,
            # and NOT starting a new
            # line-indent, end indented section
            if last_token[0] == 'EOLS' and in_line_indent:
                if tok.type != 'LINE_INDENT':
                    # close all nested blocks
                    while in_line_indent:
                        self.endLineIndent()
                        in_line_indent -= 1

            # if just ended a line, and inside a definition list,
            # and NOT starting a new definition item, end list
            if last_token[0] == 'EOLS' and in_deflist:
                if tok.type not in['D_TERM','D_DEFINITION'] \
                   or len(last_token[1]) > 1:
                    self.endDefinitionList()
                    in_deflist = 0

            # if just saw TABLEROW_END or TABLEROW_CAPTION and next token not
            # TABLEROW_CAPTION or TABLEROW_START, then end table
            if self.in_table and last_token[0] in ['TABLEROW_END',
                                                   'TABLEROW_CAPTION'] and \
                tok.type not in ['TABLEROW_CAPTION', 'TABLEROW_START']:
                    if self.in_tablecell:
                        self.endTableCell()
                        self.in_tablecell = 0

                    if self.in_tablerow:
                        self.endTableRow()
                        self.in_tablerow = 0

                    self.endTable()
                    self.in_table = 0

            # if I just ended a line, and am inside a listitem,
            # then check next token.
            # if not a listitem, pop & close all currently opened lists
            if last_token[0] == "EOLS" and list_stack[-1][1] >= 1:
                # if new token not a listitem or there were multiple EOLs,
                # close all lists
                if tok.type not in ['N_LISTITEM',
                                    'U_LISTITEM'] or len(last_token[1]) > 1:
                    #print "EOL CLOSE LISTS"
                    #print "STACK ",list_stack

                    # close all open lists
                    while list_stack[-1][0] in "NU":
                        kind,n = list_stack.pop()
                        if kind == 'N':
                            self.endNListItem()
                            self.endNList()
                        else:
                            self.endUListItem()
                            self.endUList()

            if tok.type in { 'WORD', 'TEXT' }:
                #self.characters(self.no_tags(tok.value))
                self.characters(tok.value)

            #elif tok.type == 'RAWTEXT':
            # internally generated type that tells me not to escape text
            #   self.characters(tok.value)

            #elif tok.type == 'HTML_START':
            #   self.in_html_block += 1

            elif tok.type == 'BOLD':
                if in_bold:
                    self.endBold()
                    in_bold = 0
                else:
                    self.beginBold()
                    in_bold = 1

            elif tok.type == 'ITALIC':
                if in_italic:
                    self.endItalic()
                    in_italic = 0
                else:
                    self.beginItalic()
                    in_italic = 1

            elif tok.type == 'STRIKETHROUGH':
                if in_strikethrough:
                    self.endStrikethrough()
                    in_strikethrough = 0
                else:
                    self.beginStrikethrough()
                    in_strikethrough = 1

            elif tok.type == 'UNDERLINE':
                if in_underline:
                    self.endUnderline()
                    in_underline = 0
                else:
                    self.beginUnderline()
                    in_underline = 1

            elif tok.type == 'SUPERSCRIPT':
                if in_superscript:
                    self.endSuperscript()
                    in_superscript = 0
                else:
                    self.beginSuperscript()
                    in_superscript = 1

            elif tok.type == 'SUBSCRIPT':
                if in_subscript:
                    self.endSubscript()
                    in_subscript = 0
                else:
                    self.beginSubscript()
                    in_subscript = 1

            elif tok.type == 'HIGHLIGHT_DEFAULT':
                # can be end of any other "@@" style,
                # or the start of the default style
                if in_highlight:
                    self.endHighlight()
                    in_highlight = 0
                else:
                    # begin default highlight style
                    self.beginHighlight()
                    in_highlight = 1

            elif tok.type in ['HIGHLIGHT_CSS', 'HIGHLIGHT_COLOR',
                              'HIGHLIGHT_BG']:
                #print "TOKEN",tok.type,tok.value
                if in_highlight:
                    # the '@@' is the end of the highlight - reparse remainder
                    txt = self.lexer.lexdata[self.lexer.lexpos:]
                    self.lexer.input(tok.value[2:] + txt)
                    self.endHighlight()
                    in_highlight = 0
                else:
                    # send style to parser so it knows what kind of element
                    # to create
                    self.beginHighlight(tok.value)
                    in_highlight = 1

            #elif tok.type == 'BLOCKQUOTE':
            elif tok.type == 'BLOCK_INDENT':
                if in_block_indent:
                    self.endBlockIndent()
                    in_block_indent = 0
                else:
                    self.beginBlockIndent()
                    in_block_indent = 1

            elif tok.type == 'LINE_INDENT':
                # get >> chars
                m = re.match(wikkly_lexer.t_LINE_INDENT, tok.value)
                # adjust new new nesting level
                nr = len(m.group(1))
                while nr > in_line_indent:
                    self.beginLineIndent()
                    in_line_indent += 1

                while nr < in_line_indent:
                    self.endLineIndent()
                    in_line_indent -= 1

            elif tok.type == 'HTML_ESCAPE':
                m = re.match(self.t_HTML_ESCAPE, tok.value, re.M|re.I|re.S)
                self.beginRawHTML()
                self.characters(m.group(1))
                self.endRawHTML()

            elif tok.type == 'WIKI_ESCAPE':
                m = re.match(self.t_WIKI_ESCAPE, tok.value, re.M|re.I|re.S)
                # <nowiki> gets its own Text type to prevent camelwording
                self.beginNoWiki()
                self.characters(m.group(1))
                self.endNoWiki()

            elif tok.type == 'D_TERM':
                if not in_deflist:
                    self.beginDefinitionList()
                    in_deflist = 1

                self.beginDefinitionTerm()
                in_defterm = 1

            elif tok.type == 'D_DEFINITION':
                if not in_deflist:
                    self.beginDefinitionList()
                    in_deflist = 1

                self.beginDefinitionDef()
                in_defdef = 1

            elif tok.type == 'N_LISTITEM':
                #print "N_LISTITEM, VALUE ",tok.value, "STACK ",list_stack

                # (see file 'stack' for more detailed derivation)
                #
                # remember:
                #    Top of stack is CURRENTLY opened listitem
                #          (the one before me)
                # cases:
                #   1. top of stack is my same type AND level:
                #        Close current listitem and start new one
                #               (leave stack alone)
                #   2. top of stack is LOWER level, ANY type:
                #        I'm a sublist of current item -
                #            open a new list, leaving current list open
                #        Push self to TOS
                #   3. top of stack is HIGHER level, ANY type:
                #        Current item is sublist of MY previous sibling.
                #        Close lists till I find my same type AND level at
                #        TOS (watch for emptying stack!)
                #        Start new item or new list (push to TOS).
                #   4. different type, same level:
                #        Close current list, pop TOS and start new list
                #        (push self to TOS)

                # case 1:
                if list_stack[-1][0] == 'N' \
                   and list_stack[-1][1] == len(tok.value):
                    self.endNListItem()
                    self.beginNListItem(tok.value)

                # case 2:
                elif list_stack[-1][1] < len(tok.value):
                    self.beginNList()
                    self.beginNListItem(tok.value)
                    list_stack.append( ('N',len(tok.value)) )

                # case 3:
                elif list_stack[-1][1] > len(tok.value):
                    while (not(list_stack[-1][0] == 'N' \
                               and list_stack[-1][1] == len(tok.value))) \
                               and list_stack[-1][0] in 'NU':
                            # watch for end of stack as well

                        # close TOS list
                        if list_stack[-1][0] == 'N':
                            self.endNListItem()
                            self.endNList()
                        else:
                            self.endUListItem()
                            self.endUList()

                        list_stack.pop()

                    # did I empty the stack?
                    if list_stack[-1][0] != 'N':
                        # yes, start new list
                        self.beginNList()
                    else:
                        # close current item
                        self.endNListItem()

                    self.beginNListItem(tok.value)

                    # do NOT push to stack since TOS is already correct

                # case 4:
                elif list_stack[-1][0] == 'U' \
                     and list_stack[-1][1] == len(tok.value):

                    # close current list & pop TOS
                    self.endUListItem()
                    self.endUList()
                    list_stack.pop()

                    # start new list & item
                    self.beginNList()
                    self.beginNListItem(tok.value)

                    list_stack.append( ('N',len(tok.value)) )

                else:
                    # cannot reach ... if my logic is correct :-)
                    raise WikError("** INTERNAL ERROR in N_LISTITEM **")

            elif tok.type == 'U_LISTITEM':
                # (see comments in N_LISTITEM)

                #print "U_LISTITEM, VALUE ",tok.value, "STACK ",list_stack

                # case 1:
                if list_stack[-1][0] == 'U' \
                   and list_stack[-1][1] == len(tok.value):
                    self.endUListItem()
                    self.beginUListItem(tok.value)

                # case 2:
                elif list_stack[-1][1] < len(tok.value):
                    self.beginUList()
                    self.beginUListItem(tok.value)
                    list_stack.append( ('U',len(tok.value)) )

                # case 3:
                elif list_stack[-1][1] > len(tok.value):
                    while (not(list_stack[-1][0] == 'U' \
                               and list_stack[-1][1] == len(tok.value))) \
                               and list_stack[-1][0] in 'NU':
                            # watch for end of stack as well

                        # close TOS list
                        if list_stack[-1][0] == 'U':
                            self.endUListItem()
                            self.endUList()
                        else:
                            self.endNListItem()
                            self.endNList()

                        list_stack.pop()

                    # did I empty the stack?
                    if list_stack[-1][0] != 'U':
                        # yes, start new list
                        self.beginUList()
                    else:
                        # close current item
                        self.endUListItem()

                    self.beginUListItem(tok.value)

                    # do NOT push to stack since TOS is already correct

                # case 4:
                elif list_stack[-1][0] == 'N' \
                     and list_stack[-1][1] == len(tok.value):

                    # close current list & pop TOS
                    self.endNListItem()
                    self.endNList()
                    list_stack.pop()

                    # start new list & item
                    self.beginUList()
                    self.beginUListItem(tok.value)

                    list_stack.append( ('U',len(tok.value)) )

                else:
                    # cannot reach ... if my logic is correct :-)
                    raise WikError("** INTERNAL ERROR in N_LISTITEM **")

            elif tok.type == 'HEADING':
                # inside a table, this is a regular char
                # (so parser can see it and
                # know to switch to <th>, etc.)
                if self.in_table:
                    #print "RAWTEXT HEADING"
                    self.characters(tok.rawtext)
                    continue

                self.beginHeading(len(tok.value))
                in_heading = 1

            elif tok.type == 'LINK_AB':
                self.handleLink(tok.value[0], tok.value[1])

            elif tok.type == 'LINK_A':
                self.handleLink(tok.value)

            elif tok.type in ['IMGLINK_TFU', 'IMGLINK_TF',
                              'IMGLINK_FU', 'IMGLINK_F']:
                self.handleImgLink(*tok.value)

            elif tok.type == 'CSS_BLOCK_START':
                m = re.match(wikkly_lexer.t_CSS_BLOCK_START,
                             tok.value, re.M|re.S|re.I)
                name = m.group(1)
                # push on stack
                css_stack.append(name)
                # inform parser
                self.beginCSSBlock(name)

            elif tok.type == 'CSS_BLOCK_END':
                if len(css_stack):
                    # pop name and inform parser
                    name = css_stack.pop()
                    self.endCSSBlock()
                else:
                    # regular chars outside of a CSS block
                    self.characters(tok.value)

            elif tok.type == 'C_COMMENT_START':
                #print "******** C_COMMENT_START"
                if self.in_strip_ccomment:
                    # already in C-comment, treat as normal chars
                    self.characters(tok.value)
                else:
                    # begin C-comment (strip comment markers)
                    self.in_strip_ccomment = 1

            #elif tok.type == 'C_COMMENT_END':
            #   print "************* C_COMMENT_END"
            #   if not self.in_strip_comment:
            #       # not in C-comment, treat as normal chars
            #       self.characters(tok.value)
            #   else:
            #       self.in_strip_comment = 0

            elif tok.type == 'HTML_COMMENT_START':
                #print "******** C_COMMENT_START"
                if in_html_comment:
                    # already in HTML comment, treat as normal chars
                    self.characters(tok.value)
                else:
                    # begin HTML comment (strip comment markers)
                    in_html_comment = 1

            elif tok.type == 'HTML_COMMENT_END':
                #print "************* C_COMMENT_END"
                if not in_html_comment:
                    # not in HTML-comment, treat as normal chars
                    self.characters(tok.value)
                else:
                    # strip end markers
                    in_html_comment = 0

            elif tok.type == 'CODE_BLOCK':
                # regex grabs entire block since no nesting allowed
                m = re.match(wikkly_lexer.t_CODE_BLOCK,
                             tok.value, re.M|re.I|re.S)
                text = m.group(1)

                self.handle_codeblock(text)

            elif tok.type == 'CODE_BLOCK_CSS':
                # regex grabs entire block since no nesting allowed
                m = re.match(wikkly_lexer.t_CODE_BLOCK_CSS, tok.value,
                             re.M|re.I|re.S)
                text = m.group(1)

                self.handle_codeblock(text)

            elif tok.type == 'CODE_BLOCK_CPP':
                # regex grabs entire block since no nesting allowed
                m = re.match(wikkly_lexer.t_CODE_BLOCK_CPP, tok.value,
                             re.M|re.I|re.S)
                text = m.group(1)

                self.handle_codeblock(text)

            elif tok.type == 'CODE_BLOCK_HTML':
                # regex grabs entire block since no nesting allowed
                m = re.match(wikkly_lexer.t_CODE_BLOCK_HTML, tok.value,
                             re.M|re.I|re.S)
                text = m.group(1)

                self.handle_codeblock(text)


            #elif tok.type == 'CODE_START':
            #   # note: while in code, nothing else comes here (see above),
            #   # so don't have to test for nesting
            #   self.beginCode()
            #   self.in_code = 1

            #elif tok.type == 'CODE_END':
            #   # is it a code block?
            #   if self.in_code:
            #       self.endCode()
            #       self.in_code = 0
            #   # else, might be a CSS block ending
            #   elif len(css_stack):
            #       # pop name and inform parser
            #       name = css_stack.pop()
            #       self.endCSSBlock(name)
            #   # otherwise, it's just regular text
            #   else:
            #       self.characters(tok.value)

            elif tok.type == 'TABLEROW_START':
                if not self.in_table:
                    self.beginTable()
                    self.in_table = 1

                self.beginTableRow()
                self.in_tablerow = 1
                self.beginTableCell()
                self.in_tablecell = 1
                #in_tablerow = 1

            elif tok.type == 'TABLEROW_END':
                if not self.in_table:
                    # split | portion from "\n" portion
                    m = re.match(wikkly_lexer.t_TABLEROW_END, tok.value, re.M|re.I|re.S)
                    self.characters(m.group(1))
                    # feed \n back to parser
                    txt = self.lexer.lexdata[self.lexer.lexpos:]
                    self.lexer.input('\n' + txt)
                else:
                    self.endTableCell()
                    self.in_tablecell = 0
                    self.endTableRow()
                    self.in_tablerow = 0

            elif tok.type == 'TABLE_END':
                if not self.in_table:
                    # split | portion from "\n" portion
                    m = re.match(wikkly_lexer.t_TABLE_END, tok.value, re.M|re.I|re.S)
                    self.characters(m.group(1))
                    # feed \n's back to parser
                    txt = self.lexer.lexdata[self.lexer.lexpos:]
                    self.lexer.input(m.group(2) + txt)
                else:
                    self.endTableCell()
                    self.in_tablecell = 0
                    self.endTableRow()
                    self.in_tablerow = 0
                    self.endTable()
                    self.in_table = 0

            elif tok.type == 'TABLEROW_CAPTION':
                # watch for caption as first row of table
                if not self.in_table:
                    self.beginTable()
                    self.in_table = 1

                m = re.match(wikkly_lexer.t_TABLEROW_CAPTION, tok.value, re.M|re.I|re.S)
                self.setTableCaption(m.group(1))

                txt = self.lexer.lexdata[self.lexer.lexpos:]

                # have to check for table ending since I grabbed the \n
                if re.match(r"[\t ]*[\n]", txt):
                    self.endTable()
                    self.in_table = 0

            elif tok.type == 'PIPECHAR':
                if self.in_table:
                    self.endTableCell()

                    # Start next cell UNLESS this is the end of the buffer.
                    # Prevents having a false empty cell at the end of the
                    # table if the row ends in EOF
                    txt = self.lexer.lexdata[self.lexer.lexpos:]
                    match = whitespace_re.match(txt)
                    if match is not None:
                        self.beginTableCell()
                    else:
                        self.in_tablecell = 0

                else:
                    self.characters(tok.value)

            elif tok.type == 'SEPARATOR':
                self.separator()

            elif tok.type == 'CATCH_URL':
                # turn bare URL into link like: [[URL|URL]]
                self.handleLink(tok.value, tok.value)

            elif tok.type == 'NULLDOT':
                pass # nothing

            #elif tok.type == 'DELETE_ME':
            #   pass # nothing

            elif tok.type == 'XHTML_ENTITY':
                s = tok.value
                if s[-1] == ';': # remove ; if present
                    addsemi = u';' # remember to add back (below), if needed
                    s = s[:-1]
                else:
                    addsemi = u''

                s = s[1:] # strip &

                if s == '#DeleteMe':
                    raise Exception("DeleteMe")
                    continue

                # check for hex entity
                m = re.match(r'\#x([0-9a-h]+)', s, re.M|re.I|re.S)
                if m:
                    if m.group(1) in ['200b','200B']:
                        # &#x200b; is special - pass to XML layer
                        self.characters('&#x200b;')
                    else:
                        self.characters(unichr(hex2int(m.group(1))))

                    continue

                # check for decimal entity
                m = re.match(r'\#([0-9]+)', s, re.M|re.I|re.S)
                if m:
                    self.characters(unichr(int(m.group(1))))
                    continue

                # see if name defined in htmlentitydefs
                import htmlentitydefs as hed
                if hed.name2codepoint.has_key(s):
                    self.characters(unichr(hed.name2codepoint[s]))
                else:
                    # else, return as raw text (will be escaped in final output)
                    self.characters(u'&' + s + addsemi)

            #elif tok.type == 'HTML_HEX_ENTITY':
            #   # reparse hex part
            #   m = re.match(wikkly_lexer.t_HTML_HEX_ENTITY, tok.value, re.M|re.I|re.S)

            elif tok.type == 'MACRO':
                # macro has already run, insert text ...
                #self.characters(self.no_tags(tok.value))
                #self.characters(tok.value)
                name, args, kw = tok.value
                self.macro(name, args, kw)

            elif tok.type == 'PYTHON_EMBED':
                pass
                # if self.wcontext.restricted_mode:
                #     self.wcontext.self.error(
                #             "Not allowed to define macros in Safe Mode",
                #             tok.rawtext, '')

                # else:
                #     self.beginPyCode()
                #     self.characters(tok.value)
                #     self.endPyCode()

            #elif tok.type == 'RAWHTML':
            #   print "** RAWHTML **",tok.value
            #   self.characters(tok.value)

            elif tok.type == "HTML_BREAK":
                self.linebreak()

            elif tok.type == 'EOLS':
                # Do NOT handle lists here -
                # they have complex nesting rules so must be
                # handled separately (above)

                if in_heading:
                    self.endHeading()
                    in_heading = 0

                #if in_tablerow:
                #   self.endTableRow()
                #   in_tablerow = 0

                #if not in_table:
                self.EOLs(tok.value)

                if in_defterm:
                    self.endDefinitionTerm()
                    in_defterm = 0

                if in_defdef:
                    self.endDefinitionDef()
                    in_defdef = 0

            # remember for next pass
            last_token = (tok.type,tok.value)

wikkly_parser = WikklyParser()
