import pytest

from typing import Union

from shell_parser.ast import *


def test_word():
    test_word = Word(word="abc123")
    assert repr(test_word) == "<Word word=abc123>"


def test_file():
    test_file = File(name="test.txt")
    assert repr(test_file) == "<File name=test.txt>"
    assert str(test_file) == "test.txt"

    duplicated_test_file = test_file.duplicate()
    assert duplicated_test_file == test_file
    assert duplicated_test_file is not test_file


def test_stdin_target():
    test_target = StdinTarget()
    assert repr(test_target) == "<StdinTarget>"
    assert str(test_target) == "stdin"


def test_stdout_target():
    test_target = StdoutTarget()
    assert repr(test_target) == "<StdoutTarget>"
    assert str(test_target) == "stdout"


def test_stderr_target():
    test_target = StderrTarget()
    assert repr(test_target) == "<StderrTarget>"
    assert str(test_target) == "stderr"


def test_default_file():
    test_stdin_file = DefaultFile(target=StdinTarget())
    assert repr(test_stdin_file) == "<DefaultFile target=stdin>"
    assert str(test_stdin_file) == "stdin"
    assert test_stdin_file.is_stdin
    assert not test_stdin_file.is_stdout
    assert not test_stdin_file.is_stderr

    test_stdout_file = DefaultFile(target=StdoutTarget())
    assert repr(test_stdout_file) == "<DefaultFile target=stdout>"
    assert str(test_stdout_file) == "stdout"
    assert not test_stdout_file.is_stdin
    assert test_stdout_file.is_stdout
    assert not test_stdout_file.is_stderr

    test_stderr_file = DefaultFile(target=StderrTarget())
    assert repr(test_stderr_file) == "<DefaultFile target=stderr>"
    assert str(test_stderr_file) == "stderr"
    assert not test_stderr_file.is_stdin
    assert not test_stderr_file.is_stdout
    assert test_stderr_file.is_stderr


def test_redirection_input():
    test_redirect = RedirectionInput()
    assert repr(test_redirect) == "<RedirectionInput>"
    assert str(test_redirect) == "<"


def test_redirection_output():
    test_redirect = RedirectionOutput()
    assert repr(test_redirect) == "<RedirectionOutput>"
    assert str(test_redirect) == ">"


def test_redirection_append():
    test_redirect = RedirectionAppend()
    assert repr(test_redirect) == "<RedirectionAppend>"
    assert str(test_redirect) == ">>"


def test_operator_and():
    test_operator = OperatorAnd()
    assert repr(test_operator) == "<OperatorAnd>"
    assert str(test_operator) == "&&"


def test_operator_or():
    test_operator = OperatorOr()
    assert repr(test_operator) == "<OperatorOr>"
    assert str(test_operator) == "||"
