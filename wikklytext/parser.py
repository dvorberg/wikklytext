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
from .exceptions import WikklyError, ParseError, UnknownMacro
from .lexer import WikklyLexer, whitespace_re
from .macros import BlockLevelMacro, MacroLibrary

class WikklyParser(object):
    """
    Base class for content parser showing the required API.

    You can also instantiate this by itself to show a trace of the
    tokens from the lexer.
    """
    def __init__(self, macro_library:MacroLibrary):
        self.macro_library = macro_library

    @property
    def location(self):
        if not hasattr(self, "lexer"):
            raise ValueError("location only available when calling parse().")
        return self.lexer.location

    def parse(self, source, compiler):
        # flags:
        #   * need to use re.M so beginning-of-line matches will
        #     work as expected
        #   * use re.I for case-insensitive as well
        #   * use re.S so '.' will match newline also

        # state vars - most of these are local context only, but some are set
        # into self if they are needed above
        self.lexer = WikklyLexer()

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
        in_strip_ccomment = 0 # inside /*** ... ***/ block
        in_html_comment = 0 # inside <!--- ... ---> block
        # since CSS blocks can nest, this is a list of currently open
        # blocks, by CSS name
        css_stack = []
        start_tag_macro_stack = []
        # allow <html> blocks to nest
        #in_html_block = 0
        #in_code = 0

        in_table = 0
        in_tablerow = 0

        self.in_tablecell = False
        table_cell_source_re = re.compile(
            r"^(?P<clasdecl>\((?P<classes>[-\w ]+)\):\s*)?"
            r"(?P<lead_spc>\s*)"
            r"(?P<excl>!?)\s*[^\|\n]*?\s*\|")
        def beginTableCell():
            if self.in_tablecell:
                compiler.endTableCell()

            match = table_cell_source_re.match(compiler.parser.lexer.remainder)
            if match is None:
                raise ParseError("Missing closing “|” for table cell.",
                                 location=self.location)
            else:
                groups = match.groupdict()
                compiler.parser.lexer.base.lexpos += len(groups["lead_spc"])

                if groups["excl"] == "!":
                    header = True
                    compiler.parser.lexer.base.lexpos += 1
                else:
                    header = False

                classes = groups["classes"]
                if classes is None:
                    classes = set()
                else:
                    compiler.parser.lexer.base.lexpos += len(groups["clasdecl"])
                    classes = set(whitespace_re.split(classes))

                compiler.beginTableCell( header, classes )
                self.in_tablecell = True

        def endTableCell():
            if self.in_tablecell:
                compiler.endTableCell()
                self.in_tablecell = False

        last_token = (None,None)  # type,value

        compiler.beginDoc()

        for tok in self.lexer.tokenize(source):
            # print(tok)

            # check for EOF or over time limit
            if tok is None:
                # close any open lists
                while list_stack[-1][0] in "NU":
                    kind,n = list_stack.pop()
                    if kind == 'N':
                        compiler.endNListItem()
                        compiler.endNList()
                    else:
                        compiler.endUListItem()
                        compiler.endUList()

                # close any open tables
                endTableCell()
                if in_tablerow:
                    compiler.endTableRow()
                if in_table:
                    compiler.endTable()

                # close any opened line-indents
                while in_line_indent:
                    compiler.endLineIndent()
                    in_line_indent -= 1

                # close any open definition list
                if in_defterm:
                    compiler.endDefinitionTerm()

                if in_defdef:
                    compiler.endDefinitionDef()

                if in_deflist:
                    compiler.endDefinitionList()

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
                    #(in_html_block, "<html> ... </html>"),
                    #(in_code, "{{{ ... }}}")]:
                    ]:
                        if v:
                            raise ParseError("Input ended inside %s" % s,
                                             location=compiler.location)

            # while in blockquote, hand parser raw chars
            #if in_blockquote and tok.type != 'BLOCKQUOTE':
            #   if hasattr(tok,'rawtext'):
            #       compiler.characters(tok.rawtext)
            #   else:
            #       compiler.characters(tok.value)
            #
            #   continue

            # while in code, hand parser raw chars
            #if in_code and tok.type != 'CODE_END':
            #   if hasattr(tok,'rawtext'):
            #       compiler.characters(tok.rawtext)
            #   else:
            #       compiler.characters(tok.value)
            #
            #   continue

            # while in <html>, hand parser raw chars, checking for nesting
            #if in_html_block:
            #   if tok.type == 'HTML_END':
            #       in_html_block -= 1
            #   elif tok.type == 'HTML_START':
            #       in_html_block += 1
            #   else:
            #       if hasattr(tok,'rawtext'):
            #           val = tok.rawtext
            #       else:
            #           val = tok.value
            #
            #       compiler.characters(val)
            #
            #   continue

            # if just ended a line, and inside a table, and NOT starting a new tablerow, end table
            #if last_token[0] == 'EOLS' and in_table:
            #   if tok.type != 'TABLEROW_START' or len(last_token[1]) > 1:
            #       compiler.endTable()
            #       in_table = 0

            # if just ended a line, and inside a definition list,
            # and NOT starting a new definition item, end list
            if last_token[0] == 'EOLS' and in_deflist:
                if tok.type not in['D_TERM','D_DEFINITION'] \
                   or len(last_token[1]) > 1:
                    compiler.endDefinitionList()
                    in_deflist = 0

            # if just saw TABLEROW_END or TABLEROW_CAPTION and next token not
            # TABLEROW_CAPTION or TABLEROW_START, then end table
            if in_table \
               and last_token[0] in ['TABLEROW_END', 'TABLEROW_CAPTION'] \
               and tok.type not in ['TABLEROW_CAPTION', 'TABLEROW_START']:
               endTableCell()

               if in_tablerow:
                   compiler.endTableRow()
                   in_tablerow = 0

               compiler.endTable()
               in_table = 0

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
                            compiler.endNListItem()
                            compiler.endNList()
                        else:
                            compiler.endUListItem()
                            compiler.endUList()

            if tok.type in { 'WORD', 'TEXT' }:
                #compiler.characters(compiler.no_tags(tok.value))
                compiler.characters(tok.value)

            #elif tok.type == 'RAWTEXT':
            # internally generated type that tells me not to escape text
            #   compiler.characters(tok.value)

            #elif tok.type == 'HTML_START':
            #   in_html_block += 1

            elif tok.type == 'BOLD':
                if in_bold:
                    compiler.endBold()
                    in_bold = 0
                else:
                    compiler.beginBold()
                    in_bold = 1

            elif tok.type == 'ITALIC':
                if in_italic:
                    compiler.endItalic()
                    in_italic = 0
                else:
                    compiler.beginItalic()
                    in_italic = 1

            elif tok.type == 'STRIKETHROUGH':
                if in_strikethrough:
                    compiler.endStrikethrough()
                    in_strikethrough = 0
                else:
                    compiler.beginStrikethrough()
                    in_strikethrough = 1

            elif tok.type == 'UNDERLINE':
                if in_underline:
                    compiler.endUnderline()
                    in_underline = 0
                else:
                    compiler.beginUnderline()
                    in_underline = 1

            elif tok.type == 'SUPERSCRIPT':
                if in_superscript:
                    compiler.endSuperscript()
                    in_superscript = 0
                else:
                    compiler.beginSuperscript()
                    in_superscript = 1

            elif tok.type == 'SUBSCRIPT':
                if in_subscript:
                    compiler.endSubscript()
                    in_subscript = 0
                else:
                    compiler.beginSubscript()
                    in_subscript = 1

            elif tok.type == 'BLOCKQUOTE':
                if in_block_indent:
                    compiler.endBlockquote()
                    in_block_indent = 0
                else:
                    compiler.beginBlockquote()
                    in_block_indent = 1

            elif tok.type == 'HTML_ESCAPE':
                m = re.match(compiler.t_HTML_ESCAPE, tok.value, re.M|re.I|re.S)
                compiler.beginRawHTML()
                compiler.characters(m.group(1))
                compiler.endRawHTML()

            elif tok.type == 'WIKI_ESCAPE':
                m = re.match(compiler.t_WIKI_ESCAPE, tok.value, re.M|re.I|re.S)
                # <nowiki> gets its own Text type to prevent camelwording
                compiler.beginNoWiki()
                compiler.characters(m.group(1))
                compiler.endNoWiki()

            elif tok.type == 'D_TERM':
                if not in_deflist:
                    compiler.beginDefinitionList()
                    in_deflist = 1

                compiler.beginDefinitionTerm()
                in_defterm = 1

            elif tok.type == 'D_DEFINITION':
                if not in_deflist:
                    compiler.beginDefinitionList()
                    in_deflist = 1

                if in_defterm:
                    compiler.endDefinitionTerm()
                    in_defterm = False

                compiler.beginDefinitionDef()
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
                    compiler.endNListItem()
                    compiler.beginNListItem(tok.value)

                # case 2:
                elif list_stack[-1][1] < len(tok.value):
                    compiler.beginNList()
                    compiler.beginNListItem(tok.value)
                    list_stack.append( ('N',len(tok.value)) )

                # case 3:
                elif list_stack[-1][1] > len(tok.value):
                    while (not(list_stack[-1][0] == 'N' \
                               and list_stack[-1][1] == len(tok.value))) \
                               and list_stack[-1][0] in 'NU':
                            # watch for end of stack as well

                        # close TOS list
                        if list_stack[-1][0] == 'N':
                            compiler.endNListItem()
                            compiler.endNList()
                        else:
                            compiler.endUListItem()
                            compiler.endUList()

                        list_stack.pop()

                    # did I empty the stack?
                    if list_stack[-1][0] != 'N':
                        # yes, start new list
                        compiler.beginNList()
                    else:
                        # close current item
                        compiler.endNListItem()

                    compiler.beginNListItem(tok.value)

                    # do NOT push to stack since TOS is already correct

                # case 4:
                elif list_stack[-1][0] == 'U' \
                     and list_stack[-1][1] == len(tok.value):

                    # close current list & pop TOS
                    compiler.endUListItem()
                    compiler.endUList()
                    list_stack.pop()

                    # start new list & item
                    compiler.beginNList()
                    compiler.beginNListItem(tok.value)

                    list_stack.append( ('N',len(tok.value)) )

                else:
                    # cannot reach ... if my logic is correct :-)
                    raise WikklyError("** INTERNAL ERROR in N_LISTITEM **",
                                      location=compiler.location)

            elif tok.type == 'U_LISTITEM':
                # (see comments in N_LISTITEM)

                #print "U_LISTITEM, VALUE ",tok.value, "STACK ",list_stack

                # case 1:
                if list_stack[-1][0] == 'U' \
                   and list_stack[-1][1] == len(tok.value):
                    compiler.endUListItem()
                    compiler.beginUListItem(tok.value)

                # case 2:
                elif list_stack[-1][1] < len(tok.value):
                    compiler.beginUList()
                    compiler.beginUListItem(tok.value)
                    list_stack.append( ('U',len(tok.value)) )

                # case 3:
                elif list_stack[-1][1] > len(tok.value):
                    while (not(list_stack[-1][0] == 'U' \
                               and list_stack[-1][1] == len(tok.value))) \
                               and list_stack[-1][0] in 'NU':
                            # watch for end of stack as well

                        # close TOS list
                        if list_stack[-1][0] == 'U':
                            compiler.endUListItem()
                            compiler.endUList()
                        else:
                            compiler.endNListItem()
                            compiler.endNList()

                        list_stack.pop()

                    # did I empty the stack?
                    if list_stack[-1][0] != 'U':
                        # yes, start new list
                        compiler.beginUList()
                    else:
                        # close current item
                        compiler.endUListItem()

                    compiler.beginUListItem(tok.value)

                    # do NOT push to stack since TOS is already correct

                # case 4:
                elif list_stack[-1][0] == 'N' \
                     and list_stack[-1][1] == len(tok.value):

                    # close current list & pop TOS
                    compiler.endNListItem()
                    compiler.endNList()
                    list_stack.pop()

                    # start new list & item
                    compiler.beginUList()
                    compiler.beginUListItem(tok.value)

                    list_stack.append( ('U',len(tok.value)) )

                else:
                    # cannot reach ... if my logic is correct :-)
                    raise WikklyError("** INTERNAL ERROR in N_LISTITEM **",
                                      location=compiler.location)

            elif tok.type == 'HEADING':
                # inside a table, this is a regular char
                # (so parser can see it and
                # know to switch to <th>, etc.)
                if in_table:
                    #print "RAWTEXT HEADING"
                    compiler.characters(tok.rawtext)
                    continue

                compiler.beginHeading(len(tok.value))
                in_heading = 1

            elif tok.type == 'LINK_AB':
                compiler.handleLink(tok.value[0], tok.value[1])

            elif tok.type == 'LINK_A':
                compiler.handleLink(tok.value)

            elif tok.type in ['IMGLINK_TFU', 'IMGLINK_TF',
                              'IMGLINK_FU', 'IMGLINK_F']:
                compiler.handleImgLink(*tok.value)

            elif tok.type == 'CSS_BLOCK_START':
                name = tok.match.groupdict()["css_block_class"]
                # push on stack
                css_stack.append(name)

                try:
                    macro_class = compiler.context.macro_library.get(name)
                except UnknownMacro as exc:
                    exc.location = compiler.location
                    raise exc
                else:
                    macro = macro_class(compiler.context)
                    if isinstance(macro, BlockLevelMacro):
                        raise ParseError("CSS block syntax not allowed for "
                                         "block level macros.",
                                         location=compiler.location)
                    compiler.callStartTagMacro(macro, args, kw)

                # inform parser
                # compiler.beginCSSBlock(name)

            elif tok.type == 'CSS_BLOCK_END':
                if css_stack:
                    # pop name and inform parser
                    name = css_stack.pop()
                    compiler.endStartTagMacro()
                else:
                    raise ParseError("Unexpected end of “{{{”-style CSS block.",
                                     location=compiler.location)

            elif tok.type == 'C_COMMENT_START':
                #print "******** C_COMMENT_START"
                if in_strip_ccomment:
                    # already in C-comment, treat as normal chars
                    compiler.characters(tok.value)
                else:
                    # begin C-comment (strip comment markers)
                    in_strip_ccomment = 1

            #elif tok.type == 'C_COMMENT_END':
            #   print "************* C_COMMENT_END"
            #   if not in_strip_comment:
            #       # not in C-comment, treat as normal chars
            #       compiler.characters(tok.value)
            #   else:
            #       in_strip_comment = 0

            elif tok.type == 'HTML_COMMENT_START':
                #print "******** C_COMMENT_START"
                if in_html_comment:
                    # already in HTML comment, treat as normal chars
                    compiler.characters(tok.value)
                else:
                    # begin HTML comment (strip comment markers)
                    in_html_comment = 1

            elif tok.type == 'HTML_COMMENT_END':
                #print "************* C_COMMENT_END"
                if not in_html_comment:
                    # not in HTML-comment, treat as normal chars
                    compiler.characters(tok.value)
                else:
                    # strip end markers
                    in_html_comment = 0

            elif tok.type == 'CODE_BLOCK':
                # regex grabs entire block since no nesting allowed
                m = re.match(compiler.lexer.t_CODE_BLOCK,
                             tok.value, re.M|re.I|re.S)
                text = m.group(1)

                compiler.handle_codeblock(text)

            elif tok.type == 'CODE_BLOCK_CSS':
                # regex grabs entire block since no nesting allowed
                m = re.match(compiler.lexer.t_CODE_BLOCK_CSS, tok.value,
                             re.M|re.I|re.S)
                text = m.group(1)

                compiler.handle_codeblock(text)

            elif tok.type == 'CODE_BLOCK_CPP':
                # regex grabs entire block since no nesting allowed
                m = re.match(compiler.lexer.t_CODE_BLOCK_CPP, tok.value,
                             re.M|re.I|re.S)
                text = m.group(1)

                compiler.handle_codeblock(text)

            elif tok.type == 'CODE_BLOCK_HTML':
                # regex grabs entire block since no nesting allowed
                m = re.match(compiler.lexer.t_CODE_BLOCK_HTML, tok.value,
                             re.M|re.I|re.S)
                text = m.group(1)

                compiler.handle_codeblock(text)


            #elif tok.type == 'CODE_START':
            #   # note: while in code, nothing else comes here (see above),
            #   # so don't have to test for nesting
            #   compiler.beginCode()
            #   in_code = 1

            #elif tok.type == 'CODE_END':
            #   # is it a code block?
            #   if in_code:
            #       compiler.endCode()
            #       in_code = 0
            #   # else, might be a CSS block ending
            #   elif len(css_stack):
            #       # pop name and inform parser
            #       name = css_stack.pop()
            #       compiler.endCSSBlock(name)
            #   # otherwise, it's just regular text
            #   else:
            #       compiler.characters(tok.value)

            elif tok.type == 'TABLEROW_START':
                if not in_table:
                    compiler.beginTable()
                    in_table = 1

                compiler.beginTableRow()
                in_tablerow = 1

                beginTableCell()

            elif tok.type == 'TABLEROW_END':
                if not in_table:
                    # split | portion from "\n" portion
                    m = re.match(compiler.lexer.t_TABLEROW_END,
                                 tok.value, re.M|re.I|re.S)
                    compiler.characters(m.group(1))
                    # feed \n back to parser
                    txt = compiler.parser.lexer.remainder
                    compiler.parser.lexer.base.input('\n' + txt)
                else:
                    endTableCell()
                    compiler.endTableRow()
                    in_tablerow = False

            elif tok.type == 'TABLE_END':
                if not in_table:
                    # split | portion from "\n" portion
                    m = re.match(compiler.lexer.t_TABLE_END, tok.value,
                                 re.M|re.I|re.S)
                    compiler.characters(m.group(1))
                    # feed \n's back to parser
                    txt = compiler.parser.lexer.remainder
                    compiler.parser.lexer.base.input(m.group(2) + txt)
                else:
                    endTableCell()

                    compiler.endTableRow()
                    in_tablerow = 0
                    compiler.endTable()
                    in_table = 0

            elif tok.type == 'TABLEROW_CAPTION':
                # watch for caption as first row of table
                if not in_table:
                    compiler.beginTable()
                    in_table = 1

                groups = tok.match.groupdict()

                classes = groups["tab_cap_cls"]
                if classes is not None:
                    classes = set(whitespace_re.split(classes))
                else:
                    classes = set()

                compiler.setTableCaption( caption = groups["tab_cap"],
                                          classes = classes)

                txt = compiler.parser.lexer.remainder

                # have to check for table ending since I grabbed the \n
                if re.match(r"[\t ]*[\n]", txt):
                    compiler.endTable()
                    in_table = 0

            elif tok.type == 'PIPECHAR':
                if in_table:
                    beginTableCell()
                else:
                    compiler.characters(tok.value)

            elif tok.type == 'SEPARATOR':
                compiler.separator()

            elif tok.type == 'CATCH_URL':
                # turn bare URL into link like: [[URL|URL]]
                compiler.handleLink(tok.value, tok.value)

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
                        compiler.characters('&#x200b;')
                    else:
                        compiler.characters(unichr(hex2int(m.group(1))))

                    continue

                # check for decimal entity
                m = re.match(r'\#([0-9]+)', s, re.M|re.I|re.S)
                if m:
                    compiler.characters(unichr(int(m.group(1))))
                    continue

                # see if name defined in htmlentitydefs
                import htmlentitydefs as hed
                if hed.name2codepoint.has_key(s):
                    compiler.characters(unichr(hed.name2codepoint[s]))
                else:
                    # else, return as raw text (will be escaped in final output)
                    compiler.characters(u'&' + s + addsemi)

            #elif tok.type == 'HTML_HEX_ENTITY':
            #   # reparse hex part
            #   m = re.match(compiler.lexer.t_HTML_HEX_ENTITY,
            #    tok.value, re.M|re.I|re.S)

            elif tok.type in { 'MACRO', 'START_TAG_MACRO_START' }:
                # macro has already run, insert text ...
                #compiler.characters(compiler.no_tags(tok.value))
                #compiler.characters(tok.value)
                name, args, kw = tok.value
                try:
                    macro_class = compiler.context.macro_library.get(name)
                except UnknownMacro as exc:
                    exc.location = compiler.location
                    raise exc
                else:
                    macro = macro_class(compiler.context)
                    block_level = isinstance(macro, BlockLevelMacro)
                    last_type, last_value = last_token
                    if tok.type == "MACRO":
                        if block_level and \
                           not ( last_type == "EOLS" and \
                                 last_value.count("\n") >= 2):
                            raise ParseError("Block level macros must have "
                                             "a paragraph of their own with "
                                             "leading and trailing double "
                                             "newlines with no extra "
                                             "whitespace.",
                                             location=compiler.location)
                        compiler.call_macro(macro, args, kw)
                    elif tok.type == "START_TAG_MACRO_START":
                        if block_level:
                            raise ParseError("At-at syntax not allowed for "
                                             "block level macros.",
                                             location=compiler.location)
                        compiler.callStartTagMacro(macro, args, kw)
                        start_tag_macro_stack.append(name)

            elif tok.type == "START_TAG_MACRO_END":
                if start_tag_macro_stack:
                    compiler.endStartTagMacro()
                    start_tag_macro_stack.pop()
                else:
                    ParseError("Unexpected end of “@@”-style start tag macro.")


            elif tok.type == 'PYTHON_EMBED':
                pass
                # if compiler.wcontext.restricted_mode:
                #     compiler.wcontext.compiler.error(
                #             "Not allowed to define macros in Safe Mode",
                #             tok.rawtext, '')

                # else:
                #     compiler.beginPyCode()
                #     compiler.characters(tok.value)
                #     compiler.endPyCode()

            #elif tok.type == 'RAWHTML':
            #   print "** RAWHTML **",tok.value
            #   compiler.characters(tok.value)

            elif tok.type == "HTML_BREAK":
                compiler.linebreak()

            elif tok.type == 'EOLS':
                # Do NOT handle lists here -
                # they have complex nesting rules so must be
                # handled separately (above)

                if in_heading:
                    compiler.endHeading()
                    in_heading = 0

                #if in_tablerow:
                #   compiler.endTableRow()
                #   in_tablerow = 0

                #if not in_table:
                compiler.EOLs(tok.value)

                if in_defdef:
                    compiler.endDefinitionDef()
                    in_defdef = 0

                if in_defterm:
                    compiler.endDefinitionTerm()
                    in_defterm = 0

            # remember for next pass
            last_token = (tok.type,tok.value)

        compiler.endDoc()
