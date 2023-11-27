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

import re, copy
import ply.lex

from tinymarkup.exceptions import (InternalError, ParseError,
                                   UnknownMacro, Location)
from tinymarkup.macro import MacroLibrary
from tinymarkup.parser import Parser

from . import lextokens
from .compiler import WikklyCompiler

wikkly_base_lexer = ply.lex.lex(module=lextokens,
                                reflags=re.MULTILINE|re.IGNORECASE|re.DOTALL,
                                optimize=False,
                                lextab=None)

paragraph_break_re = re.compile("\n\n+")
class WikklyParser(Parser):
    """
    Base class for content parser showing the required API.

    You can also instantiate this by itself to show a trace of the
    tokens from the lexer.
    """
    def __init__(self):
        super().__init__(wikkly_base_lexer)

    def parse(self, source:str, compiler:WikklyCompiler):
        # flags:
        #   * need to use re.M so beginning-of-line matches will
        #     work as expected
        #   * use re.I for case-insensitive as well
        #   * use re.S so '.' will match newline also

        # state vars - most of these are local context only, but some are set
        # into self if they are needed above
        self.in_bold = 0
        self.in_italic = 0
        self.in_strikethrough = 0
        self.in_underline = 0
        self.in_superscript = 0
        self.in_subscript = 0
        self.in_blockquote = 0
        # the top of stack is the _currently_ opened listitem + level
        # e.g. for <ul>, item "###" is ('U',3), for <ol>, item '##' is ('N',2)
        list_stack = [('X',0)] # no currently opened list
        in_heading = 0
        self.in_deflist = 0 # tiddlywiki does not let DL/DT/DD nest apparently, so don't worry about it
        in_defterm = 0 # in <DT>?
        in_defdef = 0  # in <DD>?
        in_strip_ccomment = 0 # inside /*** ... ***/ block
        in_html_comment = 0 # inside <!--- ... ---> block
        # since CSS blocks can nest, this is a list of currently open
        # blocks, by CSS name
        self.inline_block_stack = []
        start_tag_macro_stack = []
        # allow <html> blocks to nest

        in_table = 0
        in_tablerow = 0

        def on_root_level():
            return (not self.in_paragraph
                    and not in_heading
                    and not self.in_deflist
                    and not in_table
                    and len(list_stack) == 1)

        self.in_paragraph = False
        def assure_paragraph():
            if on_root_level():
                compiler.beginParagraph()
                self.in_paragraph = True

        def end_current_block():
            for flag, construct in [
                    (self.in_bold, "'' ... ''"),
                    (self.in_italic, "// ... //"),
                    (self.in_strikethrough, "-- ... --"),
                    (self.in_underline, "__ .. .__"),
                    (self.in_superscript, "^^ ... ^^"),
                    (self.in_subscript, "~~ ... ~~"),
                    (self.inline_block_stack, "{{…{ ... }}}"),
            ]:
                if flag:
                    raise ParseError(f"Input ended in {construct}.",
                                     location=self.location)

            if self.in_deflist:
                compiler.endDefinitionList()
                self.in_deflist = False

            if self.in_paragraph:
                compiler.endParagraph()
                self.in_paragraph = False

        def close_any_open_list():
            while list_stack[-1][0] in "NU":
                kind,n = list_stack.pop()
                if kind == 'N':
                    compiler.endNListItem()
                    compiler.endNList()
                else:
                    compiler.endUListItem()
                    compiler.endUList()

        def get_macro_for(macro_name, macro_end):
            """
            Parse macro calls in Wikkly constructs that allow for a
            syntax as

                macro_name(params):
            """
            args = []
            kw = {}

            if macro_name is None:
                macro = None
            else:
                if macro_end == "(":
                    remainder, args, kw = \
                        lextokens.parse_macro_parameter_list_from(
                            self.location, lexer.remainder, "):")
                    lexer.remainder = remainder

                macro_class = compiler.context.macro_library.get(
                    macro_name, self.location)
                macro = macro_class(compiler.context,
                                    list(macro_class.environments)[0])

            return (macro, args, kw)

        table_cell_source_re = re.compile(
            r"^(?P<excl>!?)" # Exclamation point or not.
            r"(?:" # Non-capturing group: Optionsl macro call start.
            r"(?P<macroname>[^\d\W][\w]*)" # Macro name
            r"(?P<macroend>[\(:])"         # opening of macro params or “:”
            r")?"  # close non-capturing group of optional macro start
            r".*?\|") # The end of the cell must be there in any case.
        self.in_tablecell = False
        def beginTableCell():
            if self.in_tablecell:
                compiler.endTableCell()

            match = table_cell_source_re.match(self.lexer.remainder)
            if match is None:
                raise ParseError("Missing closing “|” for table cell.",
                                 location=self.location)

            groups = match.groupdict()

            if groups["excl"] == "!":
                header = True

                # Advance the lexer to point right after the “!”.
                self.lexer.lexpos += 1
            else:
                header = False

            macro, args, kw = get_macro_for(groups["macroname"],
                                            groups["macroend"])
            if groups["macroname"] is not None \
               and groups["macroend"] == ":":
                self.lexpos += len(groups["macroname"]) + 1

            compiler.beginTableCell( header, macro, args, kw )
            self.in_tablecell = True


        def endTableCell():
            if self.in_tablecell:
                compiler.endTableCell()
                self.in_tablecell = False

        last_token = (None,None)  # type,value

        compiler.begin_document(self.lexer)

        for tok in self.lexer.tokenize(source):
            #ic(tok)

            # ply.lex.lex() puts the regex match object in
            # lexer.lexmatch if the token has an associated
            # function.
            lexmatch = getattr(self.lexer.base, "lexmatch", None)

            # check for EOF or over time limit
            if tok is None:
                # close any open lists
                close_any_open_list()

                # close any open tables
                endTableCell()
                if in_tablerow:
                    compiler.endTableRow()
                if in_table:
                    compiler.endTable()

                # close any open definition list
                if in_defterm:
                    compiler.endDefinitionTerm()
                    in_defterm = False

                if in_defdef:
                    compiler.endDefinitionDef()
                    in_defdef = False

                if self.in_deflist:
                    compiler.endDefinitionList()
                    self.in_deflist = False

            # if just ended a line, and inside a definition list,
            # and NOT starting a new definition item, end list
            if last_token[0] == 'EOLS' and self.in_deflist:
                if tok.type not in['D_TERM','D_DEFINITION'] \
                   or len(last_token[1]) > 1:
                    if in_defdef:
                        compiler.endDefinitionDef()
                        in_defdef = False

                    compiler.endDefinitionList()
                    self.in_deflist = False

            # if just saw TABLEROW_END or TABLE_CAPTION and next token not
            # TABLE_CAPTION or TABLEROW_START, then end table
            if in_table \
               and last_token[0] in ['TABLEROW_END', 'TABLE_CAPTION'] \
               and tok.type not in ['TABLE_CAPTION', 'TABLEROW_START']:
               endTableCell()

               if in_tablerow:
                   compiler.endTableRow()
                   in_tablerow = False

               compiler.endTable()
               in_table = False

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

            if tok.type == 'WORD':
                assure_paragraph()
                compiler.word(tok.value)

            elif tok.type == 'OTHER_CHARACTERS':
                assure_paragraph()
                compiler.other_characters(tok.value)

            elif tok.type == 'BOLD':
                assure_paragraph()
                if self.in_bold:
                    compiler.endBold()
                    self.in_bold = 0
                else:
                    compiler.beginBold()
                    self.in_bold = 1

            elif tok.type == 'ITALIC':
                assure_paragraph()
                if self.in_italic:
                    compiler.endItalic()
                    self.in_italic = 0
                else:
                    compiler.beginItalic()
                    self.in_italic = 1

            elif tok.type == 'STRIKETHROUGH':
                assure_paragraph()
                if self.in_strikethrough:
                    compiler.endStrikethrough()
                    self.in_strikethrough = 0
                else:
                    compiler.beginStrikethrough()
                    self.in_strikethrough = 1

            elif tok.type == 'UNDERLINE':
                assure_paragraph()
                if self.in_underline:
                    compiler.endUnderline()
                    self.in_underline = 0
                else:
                    compiler.beginUnderline()
                    self.in_underline = 1

            elif tok.type == 'SUPERSCRIPT':
                assure_paragraph()
                if self.in_superscript:
                    compiler.endSuperscript()
                    self.in_superscript = 0
                else:
                    compiler.beginSuperscript()
                    self.in_superscript = 1

            elif tok.type == 'SUBSCRIPT':
                assure_paragraph()
                if self.in_subscript:
                    compiler.endSubscript()
                    self.in_subscript = 0
                else:
                    compiler.beginSubscript()
                    self.in_subscript = 1

            elif tok.type == 'BLOCKQUOTE_START':
                if self.in_blockquote:
                    raise ParseError("Blockquotes can’t nest.",
                                     location=self.location)

                groups = lexmatch.groupdict()
                macro, args, kw = get_macro_for(
                    groups["blockquote_macro_start"],
                    groups["blockquote_macro_end"])
                compiler.beginBlockquote(macro, args, kw)
                self.in_blockquote = True

            elif tok.type == "BLOCKQUOTE_END":
                if not self.in_blockquote:
                    raise ParseError("Missing beginning of blockquote.",
                                     location=self.location)

                end_current_block()
                close_any_open_list()

                compiler.endBlockquote()
                self.in_blockquote = False

            elif tok.type == 'D_TERM':
                if not self.in_deflist:
                    compiler.beginDefinitionList()
                    self.in_deflist = True

                compiler.beginDefinitionTerm()
                in_defterm = True

            elif tok.type == 'D_DEFINITION':
                if not self.in_deflist:
                    compiler.beginDefinitionList()
                    self.in_deflist = True

                if in_defterm:
                    compiler.endDefinitionTerm()
                    in_defterm = False

                compiler.beginDefinitionDef()
                in_defdef = True

            elif tok.type == 'N_LISTITEM':
                end_current_block()

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
                    raise InternalError("** INTERNAL ERROR in N_LISTITEM **",
                                        location=self.location)

            elif tok.type == 'U_LISTITEM':
                end_current_block()
                # (see comments in N_LISTITEM)

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
                    raise InternalError("** INTERNAL ERROR in N_LISTITEM **",
                                        location=self.location)

            elif tok.type == 'HEADING':
                # inside a table, this is a regular char
                # (so parser can see it and
                # know to switch to <th>, etc.)
                if in_table:
                    #print "RAWTEXT HEADING"
                    compiler.word(tok.rawtext)
                    continue

                compiler.beginHeading(len(tok.value))
                in_heading = 1

            elif tok.type == 'LINK_AB':
                assure_paragraph()
                text, target = tok.value
                compiler.handleLink(text, target)

            elif tok.type == 'LINK_A':
                assure_paragraph()
                compiler.handleLink(tok.value)

            elif tok.type == 'INLINE_BLOCK_START':
                assure_paragraph()
                name = lexmatch.groupdict()["inlblk_macro_name"]

                macro_class = compiler.context.macro_library.get(
                    name, self.location)
                # push on stack
                self.inline_block_stack.append(macro_class)
                compiler.startStartTagMacro(macro_class, (), {})

            elif tok.type == 'INLINE_BLOCK_END':
                if self.inline_block_stack:
                    # pop name and inform parser
                    macro_class = self.inline_block_stack.pop()
                    compiler.endStartTagMacro(macro_class)
                else:
                    raise ParseError("Unexpected end of “{{{”-style CSS block.",
                                     location=self.location)

            elif tok.type == 'HTML_COMMENT_START':
                #print "******** C_COMMENT_START"
                if in_html_comment:
                    # already in HTML comment, treat as normal chars
                    compiler.word(tok.value)
                else:
                    # begin HTML comment (strip comment markers)
                    in_html_comment = 1

            elif tok.type == 'HTML_COMMENT_END':
                #print "************* C_COMMENT_END"
                if not in_html_comment:
                    # not in HTML-comment, treat as normal chars
                    compiler.word(tok.value)
                else:
                    # strip end markers
                    in_html_comment = 0

            # elif tok.type == 'CODE_BLOCK':
            #     # regex grabs entire block since no nesting allowed
            #     m = re.match(self.lexer.t_CODE_BLOCK,
            #                  tok.value, re.M|re.I|re.S)
            #     text = m.group(1)

            #     compiler.handle_codeblock(text)

            # elif tok.type == 'CODE_BLOCK_CSS':
            #     # regex grabs entire block since no nesting allowed
            #     m = re.match(self.lexer.t_CODE_BLOCK_CSS, tok.value,
            #                  re.M|re.I|re.S)
            #     text = m.group(1)

            #     compiler.handle_codeblock(text)

            # elif tok.type == 'CODE_BLOCK_CPP':
            #     # regex grabs entire block since no nesting allowed
            #     m = re.match(self.lexer.t_CODE_BLOCK_CPP, tok.value,
            #                  re.M|re.I|re.S)
            #     text = m.group(1)

            #     compiler.handle_codeblock(text)

            # elif tok.type == 'CODE_BLOCK_HTML':
            #     # regex grabs entire block since no nesting allowed
            #     m = re.match(self.lexer.t_CODE_BLOCK_HTML, tok.value,
            #                  re.M|re.I|re.S)
            #     text = m.group(1)

            #     compiler.handle_codeblock(text)


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
            #   elif len(self.inline_block_stack):
            #       # pop name and inform parser
            #       name = self.inline_block_stack.pop()
            #       compiler.endCSSBlock(name)
            #   # otherwise, it's just regular text
            #   else:
            #       compiler.characters(tok.value)

            elif tok.type == 'TABLEROW_START':
                if not in_table:
                    compiler.beginTable()
                    in_table = True

                compiler.beginTableRow()
                in_tablerow = 1

                beginTableCell()

            elif tok.type == 'TABLEROW_END':
                if not in_table:
                    # split | portion from "\n" portion
                    m = re.match(self.lexer.t_TABLEROW_END,
                                 tok.value, re.M|re.I|re.S)
                    compiler.word(m.group(1))
                    # feed \n back to parser

                    # Does this even word? Should this not talk back
                    # the remainder to the last \n
                    self.lexer.remainder = "\n" + self.lexer.remainder
                else:
                    endTableCell()
                    compiler.endTableRow()
                    in_tablerow = False

            elif tok.type == 'TABLE_END':
                if not in_table:
                    # split | portion from "\n" portion
                    m = re.match(self.lexer.t_TABLE_END, tok.value,
                                 re.M|re.I|re.S)
                    compiler.word(m.group(1))
                    # feed \n's back to parser
                    self.lexer.remainder = m.group(2) + self.lexer.remainder
                else:
                    endTableCell()

                    compiler.endTableRow()
                    in_tablerow = False
                    compiler.endTable()
                    in_table = False

            elif tok.type == 'TABLE_CAPTION':
                # Table caption starts a table.
                if not in_table:
                    compiler.beginTable()
                    in_table = True

                groups = lexmatch.groupdict()

                macro, args, kw = get_macro_for(groups["tabcap_macroname"],
                                                groups["tabcap_macroend"])

                compiler.setTableCaption(groups["tabcap"].strip(),
                                         macro, args, kw)

            elif tok.type == 'PIPECHAR':
                if in_table:
                    beginTableCell()
                else:
                    compiler.other_characters(tok.value)

            elif tok.type == 'SEPARATOR':
                compiler.separator()

            elif tok.type == 'CATCH_URL':
                # turn bare URL into link like: [[URL|URL]]
                compiler.handleLink(tok.value, tok.value)

            elif tok.type == 'NULLDOT':
                pass # nothing

            elif tok.type == "MACRO":
                name, args, kw = tok.value
                macro_class = compiler.context.macro_library.get(
                    name, self.location, )

                parbreak_before = on_root_level()
                parbreak_after = ( starts_with_parbreak(self.lexer.remainder)
                                   or self.lexer.remainder.lstrip() == "" )

                environment = "inline"
                if parbreak_before and parbreak_after:
                    if ( "block" not in macro_class.environments
                         and "inline" in macro_class.environments ):
                        environment = "inline"
                    else:
                        environment = "block"

                if environment == "inline":
                    assure_paragraph()

                compiler.call_macro(environment,
                                    macro_class, args, kw,
                                    Location.from_lextoken(tok))


            elif tok.type == "START_TAG_MACRO_START":
                name, args, kw = tok.value
                macro_class = compiler.context.macro_library.get(
                    name, self.location, )
                start_tag_macro_stack.push(macro_class)
                compiler.startStartTagMacro(macro_class, args, kw)

            elif tok.type == "START_TAG_MACRO_END":
                if start_tag_macro_stack:
                    macro_class = start_tag_macro_stack.pop()
                    compiler.endStartTagMacro(macro_class)
                else:
                    ParseError("Unexpected end of “@@”-style start tag macro.")

            elif tok.type == "HTML_BREAK":
                compiler.linebreak()

            elif tok.type == 'EOLS':
                # Do NOT handle lists here -
                # they have complex nesting rules so must be
                # handled separately (above)

                if in_heading:
                    compiler.endHeading()
                    in_heading = False

                #if in_tablerow:
                #   compiler.endTableRow()
                #   in_tablerow = 0

                if in_defdef:
                    compiler.endDefinitionDef()
                    in_defdef = False

                if in_defterm:
                    compiler.endDefinitionTerm()
                    in_defterm = False

                if paragraph_break_re.match(tok.value) is not None:
                    end_current_block()
                else:
                    compiler.other_characters(" ")

            # remember for next pass
            last_token = (tok.type,tok.value)

        compiler.end_document()

parbreak_re = re.compile(lextokens.t_EOLS.__doc__)
def starts_with_parbreak(remainder):
    match = parbreak_re.match(remainder)
    return (match is not None and match.group().count("\n") >= 2)
