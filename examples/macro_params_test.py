from wikklytext.lexer import parse_macro_parameter_list_from

source = ''' 12
             'Single single quote string' \'\'\'Tripple single quote string
                   with possible newlines in it\'\'\' "Single double quote string" """Tritpple double quote string""" identifyer fn=filename.jpg length=12.21 url='http://www.prima.de'):'''

remainder, args, kw = parse_macro_parameter_list_from(
    1, source, end_marker="):")

print("Args")
for arg in args:
    print(repr(arg))
print()

print("kw")
for name, value in kw.items():
    print(name, "=", repr(value))
print()

print("remainder")
print(remainder)
