import datetime
import os
import sys

sys.path.insert(0, os.path.abspath(".."))

from shell_parser import __version__ as shell_parser_version

YEAR = datetime.date.today().strftime("%Y")

extensions = [
    "sphinx.ext.doctest",
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
]

autodoc_member_order = "bysource"

templates_path = ["templates"]

source_suffix = ".rst"

master_doc = "index"

project = "shell-parser"
author = "Matthew Gamble"
copyright = "{0}, {1}".format(YEAR, author)

version = ".".join(shell_parser_version.split(".")[:2])
release = shell_parser_version

language = "en"

exclude_patterns = ["build"]

add_function_parentheses = True

nitpick_ignore = [
    ("py:class", "str"),
]

pygments_style = "sphinx"

html_theme = "sphinx_rtd_theme"
