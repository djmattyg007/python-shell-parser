import bdb
import importlib
import sys

import shell_parser.ast as ast
import shell_parser.parser as parser
import shell_parser.formatter as formatter

try:
    import readline
except:
    pass

while True:
    try:
        statement = input("> ")
    except (EOFError, KeyboardInterrupt):
        sys.stdout.write("\n")
        break
    statement = statement.strip()
    if statement == "q":
        break

    importlib.reload(ast)
    importlib.reload(parser)
    importlib.reload(formatter)

    p = parser.Parser()
    try:
        first_cmd = p.parse(statement)
    except bdb.BdbQuit:
        sys.stderr.write("\n")
        continue
    except parser.ParserFailure as e:
        sys.stderr.write("Parser failure at position {0}\n".format(e.pos))
        sys.stderr.write(statement + "\n")
        sys.stderr.write((" " * e.pos) + "^\n")
        sys.stderr.write("{0}: {1}\n\n".format(e.__class__.__name__, e))
        continue
    print("")

    f = formatter.Formatter()
    formatted_statements = f.format_statements(first_cmd)
    for stmt in formatted_statements:
        print(stmt)

    print("")
