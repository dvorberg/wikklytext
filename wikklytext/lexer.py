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
import sys, time, re, copy

import ply.lex

from .exceptions import SyntaxError, Location
from . import tokens

wikkly_base_lexer = ply.lex.lex(module=tokens,
                                reflags=re.M|re.I|re.S,
                                optimize=False,
                                lextab=None)


class WikklyLexer(object):
    def __init__(self):
        self.base = copy.copy(wikkly_base_lexer)

    def tokenize(self, source):
        self._source = source
        self.base.input(source.lstrip())

        while True:
            token = self.base.token()
            if not token:
                break
            else:
                yield token

    @property
    def location(self):
        return Location.from_baselexer(self.base)

    @property
    def remainder(self):
        return tokens._get_remainder(self.base)

    @property
    def lexpos(self):
        return self.base.lexpos

    @lexpos.setter
    def lexpos(self, lexpos):
        self.base.lexpos = lexpos

    @remainder.setter
    def remainder(self, remainder):
        tokens._set_remainder(self.base, remainder)


parbreak_re = re.compile(tokens.t_EOLS.__doc__)
def starts_with_parbreak(remainder):
    match = parbreak_re.match(remainder)
    return (match is not None and match.group().count("\n") >= 2)
