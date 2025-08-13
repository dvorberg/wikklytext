"""
wikklytext/lexer.py: WikklyText lexer. Part of the WikklyText suite.

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

#
# Supported markup:
#
#   ''  : Bold start/end
#   //  : Italic start/end
#   --  : Strikethrough start/end
#   __  : Underlined start/end
#   ^^  : Superscript start/end
#   ~~  : Subscript start/end
#   @@  : Highlight start/end
#   ^[#]+ : Numbered list item
#   ^[*]+ : Unnumbered list item
#   ^[!]+ : Heading
#   ^[;]+ : Term (dt)
#   ^[:]+ : Definition (dd)
#   ^<<<  : Block-indent start/end
#   ^[>]+ : Line-indent
#   <<name : Macro call
#   [[A|B]] : Link
#   [[A]] : Link
####   {{{ ... }}}  : Code
#   {{class{  : old: “CSS block begin” now: “inline macro call without params”
#   }}}   : old: “CSS block end”, new: see above.
#   ----  : Separator line
#   ^\s*| : Begins table row (no leading text allowed per TiddlyWiki)
#   EOLS  : One or more newlines, possibly with intermixed spaces
#   <br>  : HTML <br>
#   /% .. %/ : Comment


import re
from tinymarkup.exceptions import Location, SyntaxError, LexerSetupError

macro_parameter_re = re.compile(r"""
    ^\s+                 # Every param, including the first, has leading space.
      (?:([^\d\W]\w*)=)? # Optional “identifyer=”. No whitespace around the “=”.
      (?:'''(.*?)''' |       # a
         \"\"\"(.*?)\"\"\" | # b
         '(.*?)' |           # c
         "(.*?)" |           # d
         ([^'">:\)\s]+)      # e
                         # All the string literal types …
      ) |                # … OR …
    ^\s*(>>|\):)         # the end of the macro/@@id(): construct.
    """, re.DOTALL | re.VERBOSE)
def parse_macro_parameter_list_from(location:Location,
                                    source:str, end_marker:str):
    """
    Return a tipplet as (args, kw, remainder,)
    """
    args = []
    kw = {}
    while True:
        match = macro_parameter_re.search(source)

        if match is None:
            raise SyntaxError("Syntax error in macro paramter",
                              location=location)
        else:
            found = len(match.group(0))
            keyword, a, b, c, d, e, end = match.groups()

            if end:
                if end != end_marker:
                    raise SyntaxError(f"Syntax error, can’t parse “{end}” in "
                                      f"macro parameter list.",
                                      location=location)
                source = source[len(end):]
                break

            arg = a or b or c or d or e

            if keyword is None:
                if kw:
                    raise SyntaxError("Syntax error: positional argument "
                                      "follows named argument.",
                                      location=location)
                args.append(arg)
            else:
                kw[keyword] = arg

            source = source[found:]

    return source, args, kw,


tokens = (
    'BOLD',
    'ITALIC',
    'STRIKETHROUGH',
    'UNDERLINE',
    'SUPERSCRIPT',
    'SUBSCRIPT',
    'SEPARATOR',
    'LISTITEM',
    'HEADING',
    'D_TERM',
    'D_DEFINITION',
    'MACRO',
    'START_TAG_MACRO_START',
    'START_TAG_MACRO_END',
    'BLOCKQUOTE_START',
    'BLOCKQUOTE_END',
    'LINK_AB',
    'LINK_A',
    #'IMGSTART',
    'INLINE_BLOCK_START',
    'INLINE_BLOCK_END',
    #'CODE_START',
    #'CODE_END',
    #'CODE_BLOCK',
    #'CODE_BLOCK_CSS',
    #'CODE_BLOCK_CPP',
    #'CODE_BLOCK_HTML',
    'C_COMMENT_START',
    #'C_COMMENT_END',
    'HTML_COMMENT_START',
    'HTML_COMMENT_END',
    'TABLEROW_START',
    'TABLEROW_END',
    'TABLE_END',
    'TABLE_CAPTION',
    'EOLS',
    # NOTE: this never becomes a token - it turns into TEXT below
    # I'm leaving this as a comment so the length with match with
    # the list above.
    'CATCH_URL',
    #'HTML_START',
    #'HTML_END',
    'COMMENT',
    # NOTE: this never becomes a token - it turns into TEXT below
    # I'm leaving this as a comment so the length with match with
    # the list above.
    #'WIKIWORD_ESC',
    'HTML_BREAK',
    'PIPECHAR',
    'NULLDOT',
    #'DELETE_ME',
    # for internal use only - keep the lexer from matching BOL as needed
    'WORD',
    'OTHER_CHARACTERS',
    # internally-generated, but still has to be in this list ...
    #'RAWTEXT',
)

t_HTML_COMMENT_START = r'^<!---\n'
t_HTML_COMMENT_END = r'^--->\n'

# TABLES
#
# A table cell may be marked as a header (<th>-element) with an
# exclemation point as the first character of its contents like so:
#
# | Phonebook              |c
# |! Name      |! Phone    |
# | Bugs Bunny | +49 12345 |
#
# Note the “c” for “caption” as the last character of the first line.
#
# A table cel lmay carry (CSS-) class information after the “|” like so
#
# |! Name                        |! Phone     |
# |(table-danger): Elmer J. Fudd | +1 876 432 |
#
# Headers may also carry a class. It must go before the “!” as in:
#
# |(table-success): ! Green heading | …
#
t_TABLEROW_START = r"^\s*\|"
t_TABLEROW_END = r"(\|\s*)\n" # normal end of table row
t_TABLE_END = r"(\|\s*)(\n[\t ]*\n)" # blank line after table row =
                                     #   table end.
#
# The table caption may carry (CSS-) class information like so:
#
#  |(table-dark): I am the caption |c
#
# The class is meant for the <table> element. An empty caption
# will be ignored but not its class.
def t_TABLE_CAPTION(t):
    (
        r"^\|"
        r"(?:" # Non-capturing group: Optionsl macro call start.
        r"(?P<tabcap_macroname>[^\d\W][\w]*)" # Macro name
        r"(?P<tabcap_macroend>[\(:])"         # opening of macro params or “:”
        r")?"  # close non-capturing group of optional macro start
        r"(?P<tabcap>.*?)\|c" # Terminating “|”
        r"\s*\n" # The newline must be consumed by this re, or a EOLs will
        # cause the parser to end the table prematurely.
    )
    return t

t_SEPARATOR = r"^---[-]+[ \t]*\n"

t_BOLD = r"''"
t_ITALIC = r"//"
t_STRIKETHROUGH = r"--"
t_UNDERLINE = r"__"
t_SUPERSCRIPT = r"\^\^"
t_SUBSCRIPT = r"~~"
# @@prop1: style 1 here; prop2: style 2 here; ... ;
# (sync regex w/wikklytext.buildXML.py)
# careful on matching - easy to mix up with the other @@ forms
# (this is not the full set of property names allowed by CSS, but
# should cover most real uses)
#t_IMGSTART = r"\[img\["

# Inline blocks as {{macro-name{Arbitrary contents}}} The macro’s
# tag_params() method is called to supply parameters
# for a <span . . .></span>.
def t_INLINE_BLOCK_START(t):
    r"\{\{\s*(?P<inlblk_macro_name>[^\d\W]\w+)\s*\{"
    return t

t_INLINE_BLOCK_END = r"\}\}\}"
#t_CODE_BLOCK = r"\{\{\{(.*?)\}\}\}"
#t_CODE_BLOCK_CSS = r'^\/\*{{{\*\/(\n.*?\n)\/\*}}}\*\/'
#t_CODE_BLOCK_CPP = r'^\/\/{{{(\n.*?\n)\/\/}}}'
#t_CODE_BLOCK_HTML = r'^<!--{{{-->(\n.*?\n)<!--}}}-->'
# note optional semicolon - need to catch for XSS filter

t_COMMENT = r"[\s\n]*/%.*?%/[\s\n]*"
# grab any leading & trailing whitespace so it doesn't cause a gap

t_C_COMMENT_START = r'^\/\*\*\*\n'
# this is caught as a special case of ^*
#t_C_COMMENT_END = r'^\*\*\*\/\n'

t_HTML_BREAK = r"<\s*br\s*[/]?\s*>[ ]*\n?"
#t_HTML_START = r"<html>"
#t_HTML_END = r"</html>"
# TiddlyWiki does not allow nesting, so grab all at once

t_PIPECHAR = r"\|"
t_NULLDOT = r"^\s*\.\s*$"
# extension: a lone dot causes the line to be ignored

t_WORD = r"[^\W_]+" # \w has the _ in it which is for underline.
t_OTHER_CHARACTERS = r"."

roman_numeral_re = re.compile("[Ⅰ-ↁ]")
def t_LISTITEM(t):
    r"^[\t ]*[\*\#•Ⅰ-ↁ]+[ \t]*"
    # No “-” here. Overlaps with SEPARATOR AND STRIKETHROUGH.
    t.rawtext = t.value
    t.value = t.value.strip()

    # t.list_types contains a list of characters:
    # "U" for an unnumbered list
    # "N" for a numbered list
    # "R" for a numbered list with roman numerals
    def listtype(s):
        if s in "*•":
            return "U"
        elif s == "#":
            return "N"
        elif roman_numeral_re.match(s) is not None:
            return "R"
        else:
            raise NotImplementedError() # Can’t reach here.

    t.listtypes = [ listtype(s) for s in t.value ]
    return t

def t_HEADING(t):
    r"^\s*[\!]+\s*"
    t.rawtext = t.value
    t.value = t.value.strip()
    return t

def t_D_TERM(t):
    r"^\s*[;]+\s*"
    t.rawtext = t.value
    t.value = t.value.strip()
    return t

def t_D_DEFINITION(t):
    r"^\s*[:]+\s*"
    t.rawtext = t.value
    t.value = t.value.strip()
    return t

# link: [[A]]
def t_LINK_A(t):
    r"\[\[(?P<link_a>[^\|]+?)\]\]"
    t.value = t.lexer.lexmatch.groupdict()["link_a"]
    return t

# link: [[A|B]]
def t_LINK_AB(t):
    r"\[\[(?P<link_b_text>.+?)\|(?P<link_b_target>.*?)\]\]"
    groupdict = t.lexer.lexmatch.groupdict()
    t.value = ( groupdict["link_b_text"], groupdict["link_b_target"], )
    return t


# These functions provide a mechanism to access a copy of the base lexer
# (a ply.lex.Lexer() object) to set its current position in the input
# by accessing it through the LexToken object.

def _get_remainder(lexer):
    return lexer.lexdata[lexer.lexpos:]

def _set_remainder(lexer, remainder):
    if not lexer.lexoptimize:
        assert lexer.lexdata.endswith(remainder)
    lexer.lexpos = len(lexer.lexdata)-len(remainder)

def _get_location(lexer):
    return Location.from_baselexer(lexer)

def t_MACRO(t):
    # Macro call - IMPORTANT - only grab the beginning - trying to catch
    # ">>" here would be wrong since ">>" could be inside a quoted string
    # argument. So, just catch the start and pass it off
    # to wikklytext.macro to do the full parsing.
    # Do NOT allow leading inner space, so things like " << " are
    # not accidentally matched.
    r"<<[a-z_]+"

    macro_name = t.value[2:]
    remainder, args, kw = parse_macro_parameter_list_from(
        _get_location(t.lexer), _get_remainder(t.lexer), ">>")
    _set_remainder(t.lexer, remainder)

    t.value = macro_name, args, kw
    return t

def t_START_TAG_MACRO_START(t):
    # The syntax is
    #
    #     @@identifier: more Wikkly@@.
    #
    # The identifier may be accompanied by a parameter list in parentheses:
    #
    #     @@identifyer('Something'): more Wikkly@@.
    #
    # Leading whitespace from the text content will be removed. To prevent
    # “word:” to be used as macro name, put a space after the opening
    # “@@”.
    #
    r"@@([^\d\W][\w]*)(\(?)"

    macro_name = t.value[2:]
    if macro_name.endswith("("):
        macro_name = macro_name[:-1]

        source = " " + _get_remainder(t.lexer)
        remainder, args, kw = parse_macro_parameter_list_from(
            _get_location(t.lexer), source, "):")
        _set_remainder(t.lexer, remainder.lstrip())
    else:
        if t.lexer.lexdata[t.lexer.lexpos] != ":":
            raise SyntaxError("Missing “:” in start tag macro call.",
                              location=_get_location(t.lexer))
        else:
            t.lexer.lexpos += 1
            # lstrip() the lexdata
            while t.lexer.lexdata[t.lexer.lexpos] in " \t":
                t.lexer.lexpos += 1

        args = ()
        kw = {}

    t.value = macro_name, args, kw
    return t

t_START_TAG_MACRO_END = r"@@"

def t_BLOCKQUOTE_START(t):
    (
        r"^<<<"
        r"(?:"
        r"(?P<blockquote_macro_start>[^\d\W][\w]*)"
        r"(?P<blockquote_macro_end>[\):])"
        r")?"
        r"\s+"
    )
    return t

t_BLOCKQUOTE_END = r">>>[ \t]*(\n|$)"


def t_CATCH_URL(t):
    r"((http|https|file|ftp|gopher|mms|news|nntp|telnet)://[a-zA-Z0-9~\$\-_\.\#\+\!%/\?\=&]+(:?\:[0-9]+)?(?:[a-zA-Z0-9~\$\-_\.\#\+\!%/\?\=&]+)?)|(mailto:[a-zA-Z\._@]+)"
    # common parts of RFC 1738 - I left out "(),'*" because they might be legitimate markup and I never
    # (or rarely) see those used in URLs
    # NOTE -- if changing this, sync with wiki/render.py
    return t

def t_EOLS(t):
    r"\n([\t ]*[\n])*"
    # group one or more \n chars possibly intermixed with whitespace.
    # delete whitespace so value is just a set of \n chars.
    t.value = t.value.replace(' ','').replace('\t','')

    return t

def t_error(t):
    raise LexerSetupError(repr(t), location=Location.from_baselexer(t.lexer))
