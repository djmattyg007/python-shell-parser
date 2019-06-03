import pytest

import re

from shell_statement_parser.ast import CommandBuilder, CommandBuilderCreateException


def test_no_words():
    builder = CommandBuilder()
    with pytest.raises(CommandBuilderCreateException, match=re.escape("No command words added.")):
        builder.create()
