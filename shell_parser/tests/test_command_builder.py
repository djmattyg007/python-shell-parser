import pytest

import re

from shell_parser.ast import CommandBuilder, CommandBuilderCreateException


def make_match(msg: str) -> str:
    return "^" + re.escape(msg) + "$"


def test_no_words():
    builder = CommandBuilder()
    with pytest.raises(CommandBuilderCreateException, match=make_match("No command words added.")):
        builder.create()
