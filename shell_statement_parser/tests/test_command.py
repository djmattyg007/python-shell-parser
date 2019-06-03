import pytest

import dataclasses
import re

from shell_statement_parser.ast import Command, InvalidCommandDataException, Word, File, RedirectionOutput, RedirectionAppend, OperatorAnd, OperatorOr


def test_missing_compulsory_data():
    with pytest.raises(TypeError, match=re.escape("__init__() missing 1 required positional argument: 'command'")):
        Command()


def test_invalid_redirect_data():
    with pytest.raises(InvalidCommandDataException, match=re.escape("Redirection file set, but no redirection operator set.")):
        Command(command=Word("cmd1"), redirect_to=File("file1.txt"))

    with pytest.raises(InvalidCommandDataException, match=re.escape("Redirection operator set, but no redirection file set.")):
        Command(command=Word("cmd2"), redirect_to_operator=RedirectionOutput())
    with pytest.raises(InvalidCommandDataException, match="Redirection operator set, but no redirection file set."):
        Command(command=Word("cmd3"), redirect_to_operator=RedirectionAppend())


def test_invalid_next_command_data():
    with pytest.raises(InvalidCommandDataException, match=re.escape("Next command operator set, but no next command set.")):
        Command(command=Word("cmd1"), next_command_operator=OperatorAnd())
    with pytest.raises(InvalidCommandDataException, match=re.escape("Next command operator set, but no next command set.")):
        Command(command=Word("cmd2"), next_command_operator=OperatorOr())


def test_immutability():
    cmd = Command(command=Word("cmd1"))
    with pytest.raises(dataclasses.FrozenInstanceError):
        cmd.command = Word("cmd2")
    with pytest.raises(dataclasses.FrozenInstanceError):
        cmd.args = tuple("arg1")
    with pytest.raises(dataclasses.FrozenInstanceError):
        cmd.redirect_to = File("file1.txt")
    with pytest.raises(dataclasses.FrozenInstanceError):
        cmd.redirect_to_operator = None
    with pytest.raises(dataclasses.FrozenInstanceError):
        cmd.pipe_command = None
    with pytest.raises(dataclasses.FrozenInstanceError):
        cmd.next_command = None
    with pytest.raises(dataclasses.FrozenInstanceError):
        cmd.next_command_operator = None
    with pytest.raises(dataclasses.FrozenInstanceError):
        cmd.asynchronous = True
