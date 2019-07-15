============
Shell Parser
============

Shell Parser is designed to parse strings that you would pass on the command
line to your shell (eg. bash). It will turn the string into a set of objects
designed to provide you with all the necessary information about the string
entered by the user. It also contains a formatter, whose job is to convert the
output of the parser back into a string using a canonical formatting.

.. contents::
   :local:
   :depth: 2

Installation
============

Shell Parser can be found on PyPI, and installed with pip:

.. code-block:: sh

   $ pip install shell-parser

At the moment, Shell Parser only supports Python 3.7 and above.

Example
=======

Parsing
-------

The `Parser` class has a single method named `parse`:

.. code-block:: python

   from shell_parser.parser import Parser

   parser = Parser()
   first_cmd = parser.parse("cmd arg1 arg2 > stdout.txt 2> stderr.txt")

   # Access the name of the command
   print(first_cmd.command)  # prints 'cmd'
   # Access the arguments for the command
   for arg in first_cmd.args:
       print(arg)  # prints 'arg1', then 'arg2'

   # Check the file descriptors
   descriptors = first_cmd.descriptors.descriptors
   # Standard In (stdin) should point to the default stdin descriptor
   print(descriptors[0].descriptor.is_default_file)  # prints 'True'
   print(descriptors[0].descriptor.target)  # prints 'stdin'
   # Standard Out (stdout) should point to the file stdout.txt
   print(descriptors[1].descriptor.is_default_file)  # prints 'False'
   print(descriptors[1].descriptor.target)  # prints 'stdout.txt'
   # Standard Error (stderr) should point to the file stderr.txt
   print(descriptors[2].descriptor.is_default_file)  # prints 'False'
   print(descriptors[2].descriptor.target)  # prints 'stderr.txt'

Formatting
----------

When you know for certain that your input only contains a single statement,
or you don't care about follow-up statements for some reason, you would use
the `format_statement` method on the `Formatter` class:

.. code-block:: python

   from shell_parser.parser import Parser
   from shell_parser.formatter import Formatter

   parser = Parser()
   formatter = Formatter()

   first_cmd = parser.parse("cmd arg1 >stdout.txt arg2")
   print(formatter.format_statement(first_cmd))  # prints 'cmd arg1 arg2 > stdout.txt'

Most of the time, you'll need to deal with the fact that the input contains
multiple statements, some of which may be chained together. For this, you can
use the `format_statements` method:

.. code-block:: python

   from shell_parser.parser import Parser
   from shell_parser.formatter import Formatter

   parser = Parser()
   formatter = Formatter()

   first_cmd = parser.parse("cmd1 arg1 | cmd2 arg2 arg3 && cmd3; cmd4 || cmd5 arg4")
   print(formatter.format_statements(first_cmd))

This will output a tuple with each distinct statement in its own string:

.. code-block:: python

   ('cmd1 arg1 | cmd2 arg2 arg3 && cmd3', 'cmd4 || cmd5 arg4')

License
=======

This project is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License Version 3 as published by the Free
Software Foundation. No other version currently applies to this project. This
project is distributed without any warranty. Please see LICENSE.txt for the
full text of the license.
