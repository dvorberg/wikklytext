class Macro(object):
    def __init__(self, parser):
        self.parser = parser

    def html(self, *args, **kw):
        return None

    def tsearch(self, *args, **kw):
        return None

class BlockElementMacro(Macro):
    pass

class InlineElementMacro(Macro):
    pass
