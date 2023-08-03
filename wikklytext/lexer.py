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
#   {{{ ... }}}  : Code
#   ^/*{{{*/$ ... ^/*}}}*/ : Code
#   ^//{{{$ ... ^//}}} : Code
#   ^<!--{{{-->$ ... ^<!--}}}--> : Code
#   ^/***$ : Begin C-comment (markers removed, inner text processed)
#   ^***/$ : End C-comment
#   ^<!---$ : Begin HTML comment (markers removed, inner text processed)
#   ^--->$ : End HTML comment
#   {{class{  : old: “CSS block begin” now: “inline macro call without params”
#   }}}   : old: “CSS block end”, new: see above.
#   ----  : Separator line
#   ^\s*| : Begins table row (no leading text allowed per TiddlyWiki)
#   EOLS  : One or more newlines, possibly with intermixed spaces
#   [http|file|..etc..]://  : Automatic URLs
#   <html> .. </html> : Inner text is passed through to parser.
#   <br>  : HTML <br>
#   \s--\s : &mdash;
#   /% .. %/ : Comment
#   ~Name : WikiWord escape
#  ^.$ : Nothing
#  &#DeleteMe; : EXTENSION - Deleted in lexer
#  &#NNN;  : Converted to plain text char
#  &#xHHH; : Converted to plain text char
#   .     : Any other character
#

import sys, time, re

from .exceptions import SyntaxError, Location
#from ply.lex import lex
from .baselexer import lex

whitespace_re = re.compile(r"\s+")

class WikklyLexer(object):
    tokens = (
        'BOLD',
        'ITALIC',
        'STRIKETHROUGH',
        'UNDERLINE',
        'SUPERSCRIPT',
        'SUBSCRIPT',
        'N_LISTITEM',
        'U_LISTITEM',
        'HEADING',
        'D_TERM',
        'D_DEFINITION',
        'MACRO',
        'START_TAG_MACRO_START',
        'START_TAG_MACRO_END',
        'BLOCK_INDENT',
        'LINK_AB',
        'LINK_A',
        'IMGLINK_TFU',
        'IMGLINK_TF',
        'IMGLINK_FU',
        'IMGLINK_F',
        #'IMGSTART',
        'CSS_BLOCK_START',
        'CSS_BLOCK_END',
        #'CODE_START',
        #'CODE_END',
        'CODE_BLOCK',
        'CODE_BLOCK_CSS',
        'CODE_BLOCK_CPP',
        'CODE_BLOCK_HTML',
        'C_COMMENT_START',
        #'C_COMMENT_END',
        'HTML_COMMENT_START',
        'HTML_COMMENT_END',
        'SEPARATOR',
        'TABLEROW_START',
        'TABLEROW_END',
        'TABLE_END',
        'TABLEROW_CAPTION',
        'EOLS',
        # NOTE: this never becomes a token - it turns into TEXT below
        # I'm leaving this as a comment so the length with match with
        # the list above.
        'CATCH_URL',
        #'HTML_START',
        #'HTML_END',
        'HTML_ESCAPE',
        'WIKI_ESCAPE',
        'COMMENT',
        # NOTE: this never becomes a token - it turns into TEXT below
        # I'm leaving this as a comment so the length with match with
        # the list above.
        #'WIKIWORD_ESC',
        'HTML_BREAK',
        'PIPECHAR',
        'XHTML_ENTITY',
        'NULLDOT',
        #'DELETE_ME',
        # for internal use only - keep the lexer from matching BOL as needed
        'WORD',
        'TEXT',
        # internally-generated, but still has to be in this list ...
        #'RAWTEXT',
    )

    t_BLOCK_INDENT = r"^<<<\s+|^>>>\s+"
    t_HTML_COMMENT_START = r'^<!---\n'
    t_HTML_COMMENT_END = r'^--->\n'
    t_SEPARATOR = r"^\s*---[-]+\s*"

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
    t_TABLEROW_CAPTION = (r"^\s*\|(\((?P<tab_cap_cls>[-\w ]+)\):\s*)?"
                          r"(?P<tab_cap>[^\n]*)\|c\s*?\n")

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

    # a CSS block ({{class{ .. text ..}}}) is superficially similar to a CODE
    # block. Remember though that a code block puts the lexer into raw
    # character mode, where a CSS class block still does  full parsing of the
    # internal text, so they are very different modes. TiddlyWiki DOES allow a
    # code block to reside inside a CSS block, but not vice versa. Since code
    # blocks are read as raw text, no special check is needed for this since a
    # CSS block won't be recognized in a code block.
    t_CSS_BLOCK_START = r"\{\{\s*(?P<css_block_class>[a-z_-][a-z0-9_-]+)\s*\{"
    t_CSS_BLOCK_END = r"\}\}\}"
    t_CODE_BLOCK = r"\{\{\{(.*?)\}\}\}"
    t_CODE_BLOCK_CSS = r'^\/\*{{{\*\/(\n.*?\n)\/\*}}}\*\/'
    t_CODE_BLOCK_CPP = r'^\/\/{{{(\n.*?\n)\/\/}}}'
    t_CODE_BLOCK_HTML = r'^<!--{{{-->(\n.*?\n)<!--}}}-->'
    t_XHTML_ENTITY = r"&([a-z0-9\x23]+)(;)?"
    # note optional semicolon - need to catch for XSS filter

    t_COMMENT = r"[\s\n]*/%.*?%/[\s\n]*"
    # grab any leading & trailing whitespace so it doesn't cause a gap

    t_C_COMMENT_START = r'^\/\*\*\*\n'
    # this is caught as a special case of ^*
    #t_C_COMMENT_END = r'^\*\*\*\/\n'

    t_HTML_BREAK = r"<\s*br\s*[/]?\s*>"
    #t_HTML_START = r"<html>"
    #t_HTML_END = r"</html>"
    # TiddlyWiki does not allow nesting, so grab all at once

    t_HTML_ESCAPE = r"<html>(.*?)</html>"
    t_WIKI_ESCAPE = r"<nowiki>(.*?)</nowiki>"
    t_PIPECHAR = r"\|"
    t_NULLDOT = r"^\s*\.\s*$"
    # extension: a lone dot causes the line to be ignored

    t_WORD = r"[^\W_]+" # \w has the _ in it which is for underline.
    t_TEXT = r"."

    def __init__(self):
        self.base = lex(object=self, reflags=re.M|re.I|re.S,
                        optimize=True) # optimize?

    def tokenize(self, source):
        self._source = self._remainder = source
        self.base.input(source.lstrip())

        while True:
            token = self.base.token()
            if not token:
                break
            else:
                yield token

            self._remainder = self.base.lexdata[self.base.lexpos:]

    @property
    def location(self):
        idx = self._source.index(self._remainder)
        return Location( lineno = self._source[:idx].count("\n") + 1,
                         looking_at = self._source[idx:idx+30] )

    @property
    def remainder(self):
        return self.base.lexdata[self.base.lexpos:]

    def t_error(self, t):
        #t.lexer.skip(1)
        pass

    def t_N_LISTITEM(self, t):
        r"^\s*[\#]+\s*"
        t.rawtext = t.value
        t.value = t.value.strip()
        return t

    def t_U_LISTITEM(self, t):
        r"^\s*[\*•]+\s*"
        # check for '***/'
        if t.value == '***' \
           and self.base.lexdata[self.base.lexpos] == '/' \
           and self.in_strip_comment:

            self.in_strip_comment = 0
            self.base.input(self.base.lexdata[self.base.lexpos+1:])

            # work done, return an (effectively) NOP token
            t.type = 'TEXT'
            t.value = ''
            return t

        t.rawtext = t.value
        t.value = t.value.strip()
        return t

    def t_HEADING(self, t):
        r"^\s*[\!]+\s*"
        t.rawtext = t.value
        t.value = t.value.strip()
        return t

    def t_D_TERM(self, t):
        r"^\s*[;]+\s*"
        t.rawtext = t.value
        t.value = t.value.strip()
        return t

    def t_D_DEFINITION(self, t):
        r"^\s*[:]+\s*"
        t.rawtext = t.value
        t.value = t.value.strip()
        return t

    # link: [[A]]
    def t_LINK_A(self, t):
        r"\[\[([^\|]+?)\]\]"
        m = re.match(r"\[\[(.+?)\]\]", t.value, re.M|re.I|re.S)
        t.value = m.group(1)
        return t

    # link: [[A|B]]
    def t_LINK_AB(self, t):
        r"\[\[(.+?)\|(.+?)\]\]"
        m = re.match(r"\[\[(.+?)\|(.+?)\]\]", t.value, re.M|re.I|re.S)
        t.value = (m.group(1), m.group(2))
        return t

    # image link forms:
    # [img[FILENAME]]
    def t_IMGLINK_F(self, t):
        r"\[img\[([^\|\[\]]+?)\]\]"
        #print "LEX MATCH IMG F",t.value
        m = re.match(r"\[img\[([^\|\[\]]+?)\]\]", t.value, re.M|re.I|re.S)
        t.value = (None, m.group(1), None)
        return t

    # [img[FILENAME][URL]]
    def t_IMGLINK_FU(self, t):
        r"\[img\[([^\|\[\]]+?)\]\[([^\|\[\]]+?)\]\]"
        #print "LEX MATCH IMG FU",t.value
        m = re.match(r"\[img\[([^\|\[\]]+?)\]\[([^\|\[\]]+?)\]\]",
                     t.value, re.M|re.I|re.S)
        t.value = (None, m.group(1), m.group(2))
        return t

    # [img[TITLE|FILENAME][URL]]
    def t_IMGLINK_TFU(self, t):
        r"\[img\[([^\|\[\]]+?)\|([^\|\[\]]+?)\]\[([^\|\[\]]+?)\]\]"
        #print "LEX MATCH IMG TFU",t.value
        m = re.match(
                r"\[img\[([^\|\[\]]+?)\|([^\|\[\]]+?)\]\[([^\|\[\]]+?)\]\]",
                t.value, re.M|re.I|re.S)
        t.value = (m.group(1), m.group(2), m.group(3))
        return t

    # [img[TITLE|FILENAME]]
    def t_IMGLINK_TF(self, t):
        r"\[img\[([^\|\[\]]+?)\|([^\|\[\]]+?)\]\]"
        m = re.match(r"\[img\[([^\|\[\]]+?)\|([^\|\[\]]+?)\]\]",
                     t.value, re.M|re.I|re.S)
        t.value = (m.group(1), m.group(2), None)
        return t

    #def t_RAWHTML(self, t):
    #   r"<html>.+?</html>" # non-greedy, so it won't grab consecutive html tags
    #   # self.base.lexmatch seems unreliable to me, since it has a lot more groups
    #   # than I defined. so, reparse just to be safe.
    #   t.rawtext = t.value
    #   m = re.match(r"<html>(.+)</html>",t.value,re.I)
    #   t.value = m.group(1)
    #   return t

    def t_MACRO(self, t):
        # Macro call - IMPORTANT - only grab the beginning - trying to catch
        # ">>" here would be wrong since ">>" could be inside a quoted string
        # argument. So, just catch the start and pass it off
        # to wikklytext.macro to do the full parsing.
        # Do NOT allow leading inner space, so things like " << " are
        # not accidentally matched.
        r"<<[a-z_]+"

        macro_name = t.value[2:]
        remainder, args, kw = parse_macro_parameter_list_from(
            self.location, self.base.lexdata[self.base.lexpos:], ">>")
        self.base.input(remainder)

        t.value = macro_name, args, kw
        return t

    def t_START_TAG_MACRO_START(self, t):
        # The syntax is
        #
        #     @@identifier: more Wikkly@@.
        #
        # The identifier may be accompanied by a parameter list in parentheses:
        #
        #     @@identifyer('Something'): more Wikkly@@.
        #
        r"@@([^\d\W][\w]+)(\(?)"

        macro_name = t.value[2:]
        if macro_name.endswith("("):
            macro_name = macro_name[:-1]

            source = " " + self.base.lexdata[self.base.lexpos:]
            remainder, args, kw = parse_macro_parameter_list_from(
                self.location, source, "):")
            self.base.input(remainder.lstrip())
        else:
            if self.base.lexdata[self.base.lexpos] != ":":
                raise SyntaxError("Missing “:” in start tag macro call.",
                                  location=self.location)
            else:
                self.base.lexpos += 1
                # lstrip() the lexdata
                while self.base.lexdata[self.base.lexpos] in " \t":
                    self.base.lexpos += 1

            args = ()
            kw = {}

        t.value = macro_name, args, kw
        return t

    t_START_TAG_MACRO_END = r"@@"


    #def t_WIKIWORD_ESC(self, t):
    #   r"~[a-z][a-z0-9_]+"
    #   # wikiword must begin with a capital and have at least two capitals seperated by a lower or _
    #   if not re.match("~[A-Z].*[a-z_].*[A-Z]", t.value):
    #       # does not appear to be a wikiword escape - skip the "~" and continue parsing from that point
    #       self.base.input(self.base.lexdata[self.base.lexpos-len(t.value)+1:])
    #       # return a 'null' token
    #       #t.type = "RAWHTML"
    #       t.type = "TEXT"
    #       t.value = '~'
    #       return t
    #   else:
    #       # appears to be an escaped wikiword - remove ~ and pass rest as chars
    #       #t.type = 'RAWHTML'
    #       t.type = 'TEXT'
    #       t.rawtext = t.value
    #       t.value = t.value[1:]
    #       return t

    def t_CATCH_URL(self, t):
        r"((http|https|file|ftp|gopher|mms|news|nntp|telnet)://[a-zA-Z0-9~\$\-_\.\#\+\!%/\?\=&]+(:?\:[0-9]+)?(?:[a-zA-Z0-9~\$\-_\.\#\+\!%/\?\=&]+)?)|(mailto:[a-zA-Z\._@]+)"
        # common parts of RFC 1738 - I left out "(),'*" because they might be legitimate markup and I never
        # (or rarely) see those used in URLs
        # NOTE -- if changing this, sync with wiki/render.py
        return t

    def t_EOLS(self, t):
        r"\n([\t ]*[\n])*"
        # group one or more \n chars possibly intermixed with whitespace.
        # delete whitespace so value is just a set of \n chars.
        t.value = t.value.replace(' ','').replace('\t','')

        return t

	# def prepare_input(self, txt):
	# 	# for simplicity in regexes, remove all '\r' chars
	# 	txt = txt.replace('\r','')

	# 	# NO!! This causes all files to end with an extra ' ' at the end
    #     # which screws up things like '<<set' where the variables end up
    #     # with extra padding. Although it is true that some regexes depend
    #     # on a file ending in '\n', the solution is to fix the input,
    #     # not kludge it here.

	# 	# some regexes assume a file will end with '\n',
    #     # so make sure one is present

	# 	#if txt[-1] != '\n':
	# 	#	txt += '\n'

	# 	self.base.input(txt)

	# def test(self, txt):
	# 	self.prepare_input(txt)
	# 	self.previous = []

	# 	while 1:
	# 		tok = self.base.token()
	# 		if not tok:
	# 			break

	# 		print(tok)
	# 		self.previous.append(tok)

    # #def no_tags(self, txt):
	# #	# escape anything like an HTML tag. do NOT escape '&' here.
	# #	# I only modify '<' since '>' can be a colspan symbol
	# #	return txt.replace('<','&lt;')
	# #	#return txt

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
def parse_macro_parameter_list_from(location, source, end_marker):
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
