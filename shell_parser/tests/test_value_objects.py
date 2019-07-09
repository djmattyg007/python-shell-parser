import pytest

from dataclasses import FrozenInstanceError

from shell_parser.ast import DefaultFile, File, Word
from shell_parser.ast import StdinTarget, StdoutTarget, StderrTarget
from shell_parser.ast import RedirectionInput, RedirectionOutput, RedirectionAppend
from shell_parser.ast import OperatorAnd, OperatorOr, DescriptorRead, DescriptorWrite


def test_word():
    test_word = Word(word="abc123")
    assert repr(test_word) == "<Word word=abc123>"
    with pytest.raises(FrozenInstanceError):
        test_word.word = "def456"


def test_file():
    test_file = File(name="test.txt")
    assert repr(test_file) == "<File name=test.txt>"
    assert str(test_file) == "test.txt"

    duplicated_test_file = test_file.duplicate()
    assert duplicated_test_file == test_file
    assert duplicated_test_file is not test_file

    with pytest.raises(FrozenInstanceError):
        test_file.name = "test2.txt"


def test_stdin_target():
    test_target = StdinTarget()
    assert repr(test_target) == "<StdinTarget>"
    assert str(test_target) == "stdin"

    with pytest.raises(FrozenInstanceError):
        test_target.newattr = "newattr"


def test_stdout_target():
    test_target = StdoutTarget()
    assert repr(test_target) == "<StdoutTarget>"
    assert str(test_target) == "stdout"

    with pytest.raises(FrozenInstanceError):
        test_target.newattr = "newattr"


def test_stderr_target():
    test_target = StderrTarget()
    assert repr(test_target) == "<StderrTarget>"
    assert str(test_target) == "stderr"

    with pytest.raises(FrozenInstanceError):
        test_target.newattr = "newattr"


def test_default_file():
    test_stdin_file = DefaultFile(target=StdinTarget())
    assert repr(test_stdin_file) == "<DefaultFile target=stdin>"
    assert str(test_stdin_file) == "stdin"
    assert test_stdin_file.is_stdin is True
    assert test_stdin_file.is_stdout is False
    assert test_stdin_file.is_stderr is False

    with pytest.raises(FrozenInstanceError):
        test_stdin_file.target = StdoutTarget()

    test_stdout_file = DefaultFile(target=StdoutTarget())
    assert repr(test_stdout_file) == "<DefaultFile target=stdout>"
    assert str(test_stdout_file) == "stdout"
    assert test_stdout_file.is_stdin is False
    assert test_stdout_file.is_stdout is True
    assert test_stdout_file.is_stderr is False

    with pytest.raises(FrozenInstanceError):
        test_stdout_file.target = StderrTarget()

    test_stderr_file = DefaultFile(target=StderrTarget())
    assert repr(test_stderr_file) == "<DefaultFile target=stderr>"
    assert str(test_stderr_file) == "stderr"
    assert test_stderr_file.is_stdin is False
    assert test_stderr_file.is_stdout is False
    assert test_stderr_file.is_stderr is True

    with pytest.raises(FrozenInstanceError):
        test_stderr_file.target = StdinTarget()


def test_redirection_input():
    test_redirect = RedirectionInput()
    assert repr(test_redirect) == "<RedirectionInput>"
    assert str(test_redirect) == "<"

    with pytest.raises(FrozenInstanceError):
        test_redirect.newattr = "newattr"


def test_redirection_output():
    test_redirect = RedirectionOutput()
    assert repr(test_redirect) == "<RedirectionOutput>"
    assert str(test_redirect) == ">"

    with pytest.raises(FrozenInstanceError):
        test_redirect.newattr = "newattr"


def test_redirection_append():
    test_redirect = RedirectionAppend()
    assert repr(test_redirect) == "<RedirectionAppend>"
    assert str(test_redirect) == ">>"

    with pytest.raises(FrozenInstanceError):
        test_redirect.newattr = "newattr"


def test_operator_and():
    test_operator = OperatorAnd()
    assert repr(test_operator) == "<OperatorAnd>"
    assert str(test_operator) == "&&"

    with pytest.raises(FrozenInstanceError):
        test_operator.newattr = "newattr"


def test_operator_or():
    test_operator = OperatorOr()
    assert repr(test_operator) == "<OperatorOr>"
    assert str(test_operator) == "||"

    with pytest.raises(FrozenInstanceError):
        test_operator.newattr = "newattr"


def test_descriptor_mode_read():
    test_mode = DescriptorRead()

    with pytest.raises(FrozenInstanceError):
        test_mode.newattr = "newattr"


def test_descriptor_mode_write():
    test_mode = DescriptorWrite()

    with pytest.raises(FrozenInstanceError):
        test_mode.newattr = "newattr"
