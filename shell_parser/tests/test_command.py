import pytest

import dataclasses
import re

from shell_parser.ast import Command, InvalidCommandDataException, Word, File, RedirectionOutput, RedirectionAppend, OperatorAnd, OperatorOr


def test_missing_compulsory_data():
    with pytest.raises(TypeError, match=re.escape("__init__() missing 2 required positional arguments: 'command' and 'descriptors'")):
        Command()

    with pytest.raises(TypeError, match=re.escape("__init__() missing 1 required positional argument: 'descriptors'")):
        Command(command=Word("cmd"))


def test_invalid_next_command_data():
    with pytest.raises(InvalidCommandDataException, match=re.escape("Next command operator set, but no next command set.")):
        Command(command=Word("cmd1"), descriptors={}, next_command_operator=OperatorAnd())
    with pytest.raises(InvalidCommandDataException, match=re.escape("Next command operator set, but no next command set.")):
        Command(command=Word("cmd2"), descriptors={}, next_command_operator=OperatorOr())


def test_immutability():
    cmd = Command(command=Word("cmd1"), descriptors={})
    with pytest.raises(dataclasses.FrozenInstanceError):
        cmd.command = Word("cmd2")
    with pytest.raises(dataclasses.FrozenInstanceError):
        cmd.descriptors = {}
    with pytest.raises(dataclasses.FrozenInstanceError):
        cmd.args = tuple("arg1")
    with pytest.raises(dataclasses.FrozenInstanceError):
        cmd.pipe_command = None
    with pytest.raises(dataclasses.FrozenInstanceError):
        cmd.next_command = None
    with pytest.raises(dataclasses.FrozenInstanceError):
        cmd.next_command_operator = None
    with pytest.raises(dataclasses.FrozenInstanceError):
        cmd.asynchronous = True
