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

import inspect
from tinymarkup.exceptions import MarkupError, ErrorInMacroCall
from tinymarkup.context import Context
from tinymarkup.compiler import Compiler
from tinymarkup.writer import Writer
from tinymarkup.macro import Macro

empty = inspect.Parameter.empty

class WikklyCompiler(Compiler):
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

    def beginList(self, listtype):
        print("begin list", listtype)

    def endList(self, listtype):
        print("end list", listtype)

    def beginListItem(self, listtype):
        print("begin-listitem ", listtype)

    def endListItem(self, listtype):
        print("end listitem", listtype)

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

    def word(self, txt):
        print("word: ", repr(txt))

    def other_characters(self, txt):
        print("other_chars: ", repr(txt))

    def call_macro(self, environment, macro_class, args, kw):
        print("macro: ", repr(environment), repr(macro_class), args, kw)

    def startStartTagMacro(self, macro_class, args, kw):
        print("startStartTagMacro: ", repr(macro_class), args, kw)

    def endStartTagMacro(self, macro_class):
        print("end start tag macro")

    def call_macro_method(self, method, args, kw, location=None):
        """
        Wrap a macro’s html() or tsearch() function in such a way that
        the arguments provided by

            <<mymacro 'a' 1.2 filename='test.jpg'>>

        are mapped correctly to a Python function as

        class MyMacro:
            def html(self, letter, length, filename=None, color='default')

        If the method raises an exception that is not a WikklyError
        it will be wrapped in a ErrorInMacroCall. In any case,
        the “location” information will be provided, if present.
        """
        parameters_by_name = inspect.signature(method).parameters
        parameters = list(parameters_by_name.values())

        def convert_maybe(value, param):
            """
            Provided a value from lexer.parse_macro_parameter_list_from()
            as a string, this function will attempt to cast it to the
            type indicated by the function parameter annotation.
            """
            if param.annotation is not empty:
                kw = {}

                # If the param.annotation is callable and accepts a
                # context parameter, provide it.
                if callable(param.annotation):
                    try:
                        sig = inspect.signature(param.annotation)
                    except ValueError:
                        pass
                    else:
                        for pp in sig.parameters.values():
                            if issubclass(pp.annotation, Context):
                                kw[pp.name] = method.__self__.context
                            if issubclass(pp.annotation, Writer):
                                kw[pp.name] = self.writer
                            elif issubclass(pp.annotation, Macro):
                                kw[pp.name] = method.__self__

                try:
                    if isinstance(value, param.annotation):
                        return value
                    else:
                        return param.annotation(value, **kw)
                except MarkupError as exc:
                    if exc.location:
                        exc.location.lineno += location.lineno - 1
                    raise exc
                #ErrorInMacroCall(f"Error in wikkly for {param.name}.",
                #                           location=location) from exc
            else:
                # These will be provided as strings by
                # parse_macro_pa_list_from()
                # except for `self`.
                return value

        # These are provided as positional arguments.
        positional = parameters[:len(args)]
        # These came with identifier= keywords.
        throughkw = parameters[len(args):]

        # Convert the positional arguments.
        args = [ convert_maybe(arg, param)
                 for arg, param in zip(args, positional) ]

        # Convert the keyword arguments.
        kw = dict([ (name, convert_maybe(value, parameters_by_name[name]),)
                    for name, value in kw.items() ])

        # Fill up the **kw dict to have the provided default values
        # in it.
        for param in throughkw:
            if not param.name in kw:
                if param.default is not empty:
                    kw[param.name] = param.default
                elif issubclass(param.annotation, Context):
                    kw[param.name] = method.__self__.context
                elif issubclass(param.annotation, Writer):
                    kw[param.name] = self.writer
                elif issubclass(param.annotation, Macro):
                    kw[param.name] = method.__self__

        # Call the method.
        try:
            if "location" in kw and not "location" in parameters_by_name:
                del kw["location"]

            return method(*args, **kw)
        except Exception as exc:
            if not isinstance(exc, MarkupError):
                raise ErrorInMacroCall(f"Error calling {method}",
                                       location=location) from exc
            else:
                exc.location = location
                raise exc
