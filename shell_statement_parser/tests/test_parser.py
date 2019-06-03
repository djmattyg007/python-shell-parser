import pytest

import dataclasses
import re

from shell_statement_parser.ast import *
from shell_statement_parser.formatter import Formatter
from shell_statement_parser.parser import *
from typing import Tuple


# TODO: check for removal
def strip_quotes(arg: str) -> str:
    if len(arg) > 1 and arg[0] == arg[-1] and arg[0] in ("'", '"'):
        arg = arg[1:-1]
    return arg


def assert_no_redirections(cmd: Command):
    assert cmd.redirect_to is None
    assert cmd.redirect_to_operator is None


def assert_single_cmd(cmd: Command):
    assert cmd.pipe_command is None
    assert cmd.next_command is None
    assert cmd.next_command_operator is None


@pytest.fixture(scope="module")
def parser() -> Parser:
    return Parser()


@pytest.fixture(scope="module")
def formatter() -> Formatter:
    return Formatter()


def test_empty_string(parser: Parser):
    with pytest.raises(EmptyInputException, match=re.escape("Input statement was empty or contained only whitespace.")):
        parser.parse("")


@pytest.mark.parametrize("line", (
    " ",
    "  ",
    "   ",
    "\n",
    "\t",
    "\t\t",
    " \t ",
    "\t \t",
    "   \t\t\t",
))
def test_only_whitespace(parser: Parser, line: str):
    with pytest.raises(EmptyInputException, match=re.escape("Input statement was empty or contained only whitespace.")):
        parser.parse(line)


@pytest.mark.parametrize("line,expected_str", (
    ("plainword", Word("plainword")),
    ("'one word'", QuotedWord("one word")),
    ('"one word"', QuotedWord("one word")),
    ("' one word '", QuotedWord(" one word ")),
    ('" one word "', QuotedWord(" one word ")),
    (" plainword ", Word("plainword")),
    (" 'one word' ", QuotedWord("one word")),
    (' " one word " ', QuotedWord(" one word ")),
    (r"plain\word", Word("plainword")),
    (r"plain\ word", Word("plain word")),
    (r"'one\word'", QuotedWord(r"one\word")),
    (r'"one\word"', QuotedWord(r"one\word")),
    (r"'one\ word'", QuotedWord(r"one\ word")),
    (r'"one\ word"', QuotedWord(r"one\ word")),
))
def test_single_word(parser: Parser, line: str, expected_str: Word):
    first_cmd = parser.parse(line)
    assert first_cmd.command == expected_str
    assert len(first_cmd.args) == 0
    assert_no_redirections(first_cmd)
    assert_single_cmd(first_cmd)
    assert first_cmd.asynchronous == False


@pytest.mark.parametrize("manual,nonmanual", (
    ("plainword;", "plainword"),
    ("plainword ;", "plainword "),
    ("'one word';", "'one word'"),
    ("'one word' ;", "'one word'"),
    ('"one word";', '"one word"'),
    ('"one word" ;', '"one word"'),
    (r"plain\word;", r"plain\word"),
    (r"plain\ word;", r"plain\ word"),
    (r"'one\word';", r"'one\word'"),
    (r'"one\word";', r'"one\word"'),
    (r"'one\ word';", r"'one\ word'"),
    (r'"one\ word";', r'"one\ word"'),
))
def test_single_word_manually_terminated(parser: Parser, manual: str, nonmanual: str):
    def check(_manual, _nonmanual):
        manual_first_cmd = parser.parse(_manual)
        nonmanual_first_cmd = parser.parse(_nonmanual)
        assert manual_first_cmd == nonmanual_first_cmd
        assert_no_redirections(manual_first_cmd)
        assert_single_cmd(manual_first_cmd)
        assert manual_first_cmd.asynchronous == False

    check(manual, nonmanual)
    for before_space_count in range(0, 5):
        before_spaces = " " * before_space_count
        for after_space_count in range(0, 5):
            after_spaces = " " * after_space_count
            check(manual.replace(";", before_spaces + ";" + after_spaces), nonmanual)


@pytest.mark.parametrize("line,command_word,args_words", (
    ("cmd arg1", Word("cmd"), (Word("arg1"),)),
    ("cmd arg1 arg2", Word("cmd"), (Word("arg1"), Word("arg2"))),
    ("cmd arg1 arg2 arg3", Word("cmd"), (Word("arg1"), Word("arg2"), Word("arg3"))),
    ("'cmd' 'arg1 arg2' arg3", QuotedWord("cmd"), (QuotedWord("arg1 arg2"), Word("arg3"))),
    ('"cmd" "arg1" "arg2 arg3"', QuotedWord("cmd"), (QuotedWord("arg1"), QuotedWord("arg2 arg3"))),
    ("cmd  arg1   arg2", Word("cmd"), (Word("arg1"), Word("arg2"))),
    ("'cmd'   arg1  '   arg2'", QuotedWord("cmd"), (Word("arg1"), QuotedWord("   arg2"))),
))
def test_multiple_words(parser: Parser, line: str, command_word: Word, args_words: Tuple[Word, ...]):
    first_cmd = parser.parse(line)
    assert first_cmd.command == command_word
    assert first_cmd.args == args_words
    assert_no_redirections(first_cmd)
    assert_single_cmd(first_cmd)


@pytest.mark.parametrize("line,expected_str", (
    ("cmd1 arg\\ 1", "cmd1 'arg 1'"),
    ("cmd\\ 1", "'cmd 1'"),
    ("cmd\\ 1 arg\\ 1\\ arg\\ 2", "'cmd 1' 'arg 1 arg 2'"),
    ("cmd\\ 1\\;", "'cmd 1;'"),
    ("cmd\\;\\ 1 arg\\$1", "'cmd; 1' 'arg$1'"),
    ("cmd1 \\\\arg1", "cmd1 '\\arg1'"),
    ("cmd1 \\'", "cmd1 ''\"'\"''"),
    ("cmd1 \\'\"\"", "cmd1 ''\"'\"''"),
    ("cmd1 \"\"\\'", "cmd1 ''\"'\"''"),
    ("cmd1 \\\"", "cmd1 '\"'"),
    ("cmd1 \\\"''", "cmd1 '\"'"),
    ("cmd1 ''\\\"", "cmd1 '\"'"),
    ("cmd1 \\>", "cmd1 '>'"),
    ("cmd1 \\>\\>", "cmd1 '>>'"),
    ("cmd1 \\> arg2", "cmd1 '>' arg2"),
    ("cmd1 \\>\\> arg2", "cmd1 '>>' arg2"),
    ("cmd1 \\>arg1", "cmd1 '>arg1'"),
    ("cmd1 \\>\\ arg1", "cmd1 '> arg1'"),
    ("cmd1 \\>\\>arg1", "cmd1 '>>arg1'"),
    ("cmd1 \\&", "cmd1 '&'"),
    ("cmd1 \\&\\&", "cmd1 '&&'"),
    ("cmd1 \\& arg2", "cmd1 '&' arg2"),
    ("cmd1 \\&\\& arg2", "cmd1 '&&' arg2"),
    ("cmd1 \\&\\ arg2", "cmd1 '& arg2'"),
    ("cmd1 \\&\\&\\ arg2", "cmd1 '&& arg2'"),
    ("cmd1 \\|", "cmd1 '|'"),
    ("cmd1 \\|\\|", "cmd1 '||'"),
    ("cmd1 \\| arg2", "cmd1 '|' arg2"),
    ("cmd1 \\|\\| arg2", "cmd1 '||' arg2"),
    ("cmd1 \\|\\ arg2", "cmd1 '| arg2'"),
    ("cmd1 \\|\\|\\ arg2", "cmd1 '|| arg2'"),
))
def test_escaping_outside_quotes(parser: Parser, line: str, expected_str: str):
    def check(_line: str):
        first_cmd = parser.parse(_line)
        assert str(first_cmd) == expected_str
        assert_no_redirections(first_cmd)
        assert_single_cmd(first_cmd)
        assert first_cmd.asynchronous == False

    check(line)
    check(line + ";")


@pytest.mark.parametrize("line,expected_str", (
    ("cmd1 'arg\\1'", "cmd1 'arg\\1'"),
    ("cmd1 '$arg1'", "cmd1 '$arg1'"),
    ("cmd1 '\\$arg1'", "cmd1 '\\$arg1'"),
    ("cmd1 '\\a'", "cmd1 '\\a'"),
    ("cmd1 '\\'a", "cmd1 '\\a'"),
    ("cmd1 ' \\\" '", "cmd1 ' \\\" '"),
    ("cmd1 '\\\\'", "cmd1 '\\\\'"),
))
def test_escaping_inside_single_quotes(parser: Parser, line: str, expected_str: str):
    first_cmd = parser.parse(line)
    assert str(first_cmd) == expected_str
    assert_no_redirections(first_cmd)
    assert_single_cmd(first_cmd)
    assert first_cmd.asynchronous == False


@pytest.mark.parametrize("line,expected_str", (
    ('cmd1 "arg\\1"', "cmd1 'arg\\1'"),
    ('cmd1 "arg\\"1"', "cmd1 'arg\"1'"),
    ('cmd1 "arg\\"\\$\\1"', "cmd1 'arg\"$\\1'"),
    ('cmd1 "arg1" "arg\\\\2"', "cmd1 arg1 'arg\\2'"),
))
def test_escaping_inside_double_quotes(parser: Parser, line: str, expected_str: str):
    first_cmd = parser.parse(line)
    assert str(first_cmd) == expected_str
    assert_no_redirections(first_cmd)
    assert_single_cmd(first_cmd)
    assert first_cmd.asynchronous == False


@pytest.mark.parametrize("line,expected_str", (
    ("cmd1 'a'\"b\"", "cmd1 ab"),
    ("cmd1 \"ab \"' cd'", "cmd1 'ab  cd'"),
    ("cmd1 'a b '\"c d\"", "cmd1 'a b c d'"),
    ("cmd1 \"abc \"\\ ' def'", "cmd1 'abc   def'"),
))
def test_mixing_quotes(parser: Parser, line: str, expected_str: str):
    first_cmd = parser.parse(line)
    assert str(first_cmd) == expected_str
    assert_no_redirections(first_cmd)
    assert_single_cmd(first_cmd)
    assert first_cmd.asynchronous == False


@pytest.mark.parametrize("line", (
    "cmd1 \"\"",
    "cmd1 ''",
    "cmd1 \"\"''",
    "cmd1 ''\"\"",
    "cmd1 \"\"''\"\"''",
    "cmd1 ''\"\"''\"\"",
    "cmd1 ''''",
    "cmd1 \"\"\"\"",
    "cmd1 ''''''",
    "cmd1 \"\"\"\"\"\"",
))
def test_empty_string_args(parser: Parser, line: str):
    first_cmd = parser.parse(line)
    assert str(first_cmd) == "cmd1 ''"
    assert_no_redirections(first_cmd)
    assert_single_cmd(first_cmd)
    assert first_cmd.asynchronous == False


@pytest.mark.parametrize("line,expected_cmd_count", (
    ("cmd1 arg1; cmd2 arg1", 2),
    ("cmd1  arg1 ; cmd2 'arg1'", 2),
    ("cmd1 ' arg1 ' ;cmd2 arg1", 2),
    ("cmd1 arg1;cmd2 arg1", 2),
    ("cmd1;cmd2;cmd3", 3),
    ("cmd1; cmd2; cmd3", 3),
    ("cmd1; cmd2;", 2),
    ("cmd1 'arg;1'; cmd2 \";;;'\" ;", 2),
))
def test_multiple_plain_commands(parser: Parser, line: str, expected_cmd_count: int):
    first_cmd = parser.parse(line)
    assert_no_redirections(first_cmd)
    assert first_cmd.next_command_operator is None

    actual_cmd_count = 1
    cur_cmd = first_cmd.next_command
    while cur_cmd:
        actual_cmd_count += 1
        assert_no_redirections(first_cmd)
        assert cur_cmd.next_command_operator is None

        cur_cmd = cur_cmd.next_command

    assert actual_cmd_count == expected_cmd_count


@pytest.mark.parametrize("line,expected_cmd_count,expected_str", (
    ("cmd1 | cmd2", 2, "cmd1 | cmd2"),
    ("cmd1 arg1 | cmd2 arg1", 2, "cmd1 arg1 | cmd2 arg1"),
    ("'cmd1' arg1 | cmd2 'arg1' | cmd3", 3, "cmd1 arg1 | cmd2 arg1 | cmd3"),
    ("cmd1|cmd2", 2, "cmd1 | cmd2"),
    ("cmd1|cmd2|cmd3|cmd4", 4, "cmd1 | cmd2 | cmd3 | cmd4"),
    ("cmd1| cmd2| cmd3", 3, "cmd1 | cmd2 | cmd3"),
    ("cmd1 |cmd2 |cmd3 |cmd4", 4, "cmd1 | cmd2 | cmd3 | cmd4"),
    ("cmd1| cmd2 |cmd3", 3, "cmd1 | cmd2 | cmd3"),
))
def test_pipe_commands(parser: Parser, formatter: Formatter, line: str, expected_cmd_count: int, expected_str: str):
    first_cmd = parser.parse(line)
    assert_no_redirections(first_cmd)
    assert first_cmd.next_command is None
    assert first_cmd.next_command_operator is None

    actual_cmd_count = 1
    cur_cmd = first_cmd.pipe_command
    while cur_cmd:
        actual_cmd_count += 1
        assert_no_redirections(first_cmd)
        assert cur_cmd.next_command is None
        assert cur_cmd.next_command_operator is None

        cur_cmd = cur_cmd.pipe_command

    assert actual_cmd_count == expected_cmd_count
    assert formatter.format_statement(first_cmd) == expected_str


@pytest.mark.parametrize("line,expected_str", (
    ("cmd1 > testfile.txt", "cmd1 > testfile.txt"),
    ("cmd1 arg1 > testfile.txt", "cmd1 arg1 > testfile.txt"),
    ("cmd1 arg1 > 'testfile.txt'", "cmd1 arg1 > testfile.txt"),
    ("cmd1 arg1 'arg2' > testfile.txt", "cmd1 arg1 arg2 > testfile.txt"),
    ("'cmd1' arg1 > testfile.txt", "cmd1 arg1 > testfile.txt"),
    ("cmd1 'arg1 arg2' > testfile.txt", "cmd1 'arg1 arg2' > testfile.txt"),
    ("cmd1 'arg1' 'arg2' > 'testfile.txt'", "cmd1 arg1 arg2 > testfile.txt"),
    ("cmd1 'arg1' > \"testfile.txt\"", "cmd1 arg1 > testfile.txt"),
    ("cmd1 > testfile.txt arg1", "cmd1 arg1 > testfile.txt"),
    ("cmd1 > 'testfile.txt'", "cmd1 > testfile.txt"),
    ("> testfile.txt cmd1 arg1", "cmd1 arg1 > testfile.txt"),
    ("> \"testfile.txt\" cmd1 'arg1 arg2'", "cmd1 'arg1 arg2' > testfile.txt"),
))
def test_redirect_output(parser: Parser, line: str, expected_str: str):
    # todo add escaped appends
    def check(_line: str):
        first_cmd = parser.parse(_line)
        assert_single_cmd(first_cmd)

        assert str(first_cmd.command) == "cmd1"
        assert str(first_cmd) == expected_str
        assert first_cmd.redirect_to == File("testfile.txt")
        assert isinstance(first_cmd.redirect_to_operator, RedirectionOutput)

    # We check the vanilla statement as provided by the fixture, but we also
    # check the same statement with whitespace removed from one or both sides
    # of the operator. They should all produce identical results.
    check(line)
    for space_count in range(0, 5):
        spaces = " " * space_count
        check(line.replace("> ", spaces + ">" + spaces))
        check(line.replace(" >", spaces + ">" + spaces))
        check(line.replace(" > ", spaces + ">" + spaces))


@pytest.mark.parametrize("line,expected_str", (
    ("cmd1 >> testfile.txt", "cmd1 >> testfile.txt"),
    ("cmd1 arg1 >> testfile.txt", "cmd1 arg1 >> testfile.txt"),
    ("cmd1 arg1 >> 'testfile.txt'", "cmd1 arg1 >> testfile.txt"),
    ("cmd1 arg1 'arg2' >> testfile.txt", "cmd1 arg1 arg2 >> testfile.txt"),
    ("'cmd1' arg1 >> testfile.txt", "cmd1 arg1 >> testfile.txt"),
    ("cmd1 'arg1 arg2' >> testfile.txt", "cmd1 'arg1 arg2' >> testfile.txt"),
    ("cmd1 'arg1' 'arg2' >> 'testfile.txt'", "cmd1 arg1 arg2 >> testfile.txt"),
    ("cmd1 'arg1' >> \"testfile.txt\"", "cmd1 arg1 >> testfile.txt"),
    ("cmd1 >> testfile.txt arg1", "cmd1 arg1 >> testfile.txt"),
    ("cmd1 >> 'testfile.txt'", "cmd1 >> testfile.txt"),
    (">> testfile.txt cmd1 arg1", "cmd1 arg1 >> testfile.txt"),
    (">> \"testfile.txt\" cmd1 'arg1 arg2'", "cmd1 'arg1 arg2' >> testfile.txt"),
))
def test_redirect_append(parser: Parser, line: str, expected_str: str):
    # todo add escaped outputs 
    def check(_line: str):
        first_cmd = parser.parse(line)
        assert_single_cmd(first_cmd)

        assert str(first_cmd.command) == "cmd1"
        assert str(first_cmd) == expected_str
        assert first_cmd.redirect_to == File("testfile.txt")
        assert isinstance(first_cmd.redirect_to_operator, RedirectionAppend)

    # We check the vanilla statement as provided by the fixture, but we also
    # check the same statement with whitespace removed from one or both sides
    # of the operator. They should all produce identical results.
    check(line)
    for space_count in range(0, 5):
        spaces = " " * space_count
        check(line.replace(">> ", spaces + ">>" + spaces))
        check(line.replace(" >>", spaces + ">>" + spaces))
        check(line.replace(" >> ", spaces + ">>" + spaces))


@pytest.mark.parametrize("line,expected_str", (
    ("cmd1 arg1 > file1.txt | cmd2 arg1 arg2", "cmd1 arg1 > file1.txt | cmd2 arg1 arg2"),
    ("cmd1 'arg1 arg2' > file1.txt | cmd2 arg1 ", "cmd1 'arg1 arg2' > file1.txt | cmd2 arg1"),
    ("> file1.txt cmd1 | cmd2  \"arg1 arg2 \"", "cmd1 > file1.txt | cmd2 'arg1 arg2 '"),
    ("'cmd1' | ' cmd2 ' > file2.txt", "cmd1 | ' cmd2 ' > file2.txt"),
    ("cmd1 | > file2.txt cmd2 arg1", "cmd1 | cmd2 arg1 > file2.txt"),
))
def test_pipe_and_redirect_output_one_side_only(parser: Parser, formatter: Formatter, line: str, expected_str: str):
    def check(_line):
        first_cmd = parser.parse(_line)
        assert first_cmd.next_command is None
        assert first_cmd.next_command_operator is None
        assert formatter.format_statement(first_cmd) == expected_str

        assert str(first_cmd.command) == "cmd1"
        assert isinstance(first_cmd.pipe_command, Command)

        second_cmd = first_cmd.pipe_command
        assert str(second_cmd.command).strip() == "cmd2"

        if first_cmd.redirect_to_operator:
            assert first_cmd.redirect_to == File("file1.txt")
            assert isinstance(first_cmd.redirect_to_operator, RedirectionOutput)
        else:
            assert second_cmd.redirect_to == File("file2.txt")
            assert isinstance(second_cmd.redirect_to_operator, RedirectionOutput)

    check(line)
    for pipe_space_count in range(0, 5):
        pipe_spaces = " " * pipe_space_count
        for redirect_space_count in range(0, 5):
            redirect_spaces = " " * redirect_space_count
            for pipe_chars in ("| ", " |", " | "):
                _line = line.replace(pipe_chars, pipe_spaces + "|" + pipe_spaces)
                check(_line)
                check(_line.replace("> ", redirect_spaces + ">" + redirect_spaces))
                check(_line.replace(" >", redirect_spaces + ">" + redirect_spaces))
                check(_line.replace(" > ", redirect_spaces + ">" + redirect_spaces))


@pytest.mark.parametrize("line,expected_str", (
    ("cmd1 arg1 > file1.txt | cmd2 arg1 arg2 > file2.txt", "cmd1 arg1 > file1.txt | cmd2 arg1 arg2 > file2.txt"),
    ("cmd1 'arg1 arg2' > file1.txt | cmd2 arg1 > file2.txt", "cmd1 'arg1 arg2' > file1.txt | cmd2 arg1 > file2.txt"),
    ("> file1.txt cmd1 | cmd2 > file2.txt \"arg1 arg2 \"", "cmd1 > file1.txt | cmd2 'arg1 arg2 ' > file2.txt"),
    ("> file1.txt 'cmd1' | ' cmd2 ' > file2.txt", "cmd1 > file1.txt | ' cmd2 ' > file2.txt"),
    ("cmd1 arg1 > file1.txt | > file2.txt cmd2", "cmd1 arg1 > file1.txt | cmd2 > file2.txt"),
))
def test_pipe_and_redirect_output_both_sides(parser: Parser, formatter: Formatter, line: str, expected_str: str):
    def check(_line):
        first_cmd = parser.parse(_line)
        assert first_cmd.next_command is None
        assert first_cmd.next_command_operator is None
        assert formatter.format_statement(first_cmd) == expected_str

        assert str(first_cmd.command) == "cmd1"
        assert isinstance(first_cmd.pipe_command, Command)
        assert first_cmd.redirect_to == File("file1.txt")
        assert isinstance(first_cmd.redirect_to_operator, RedirectionOutput)

        second_cmd = first_cmd.pipe_command
        assert str(second_cmd.command).strip() == "cmd2"
        assert second_cmd.redirect_to == File("file2.txt")
        assert isinstance(second_cmd.redirect_to_operator, RedirectionOutput)

    check(line)
    for pipe_space_count in range(0, 5):
        pipe_spaces = " " * pipe_space_count
        for redirect_space_count in range(0, 5):
            redirect_spaces = " " * redirect_space_count
            for pipe_chars in ("| ", " |", " | "):
                _line = line.replace(pipe_chars, pipe_spaces + "|" + pipe_spaces)
                check(_line)
                check(_line.replace("> ", redirect_spaces + ">" + redirect_spaces))
                check(_line.replace(" >", redirect_spaces + ">" + redirect_spaces))
                check(_line.replace(" > ", redirect_spaces + ">" + redirect_spaces))


@pytest.mark.parametrize("line,expected_str", (
    ("cmd1 arg1 >> file1.txt | cmd2 arg1 arg2", "cmd1 arg1 >> file1.txt | cmd2 arg1 arg2"),
    ("cmd1 'arg1 arg2' >> file1.txt | cmd2 arg1 ", "cmd1 'arg1 arg2' >> file1.txt | cmd2 arg1"),
    (">> file1.txt cmd1 | cmd2  \"arg1 arg2 \"", "cmd1 >> file1.txt | cmd2 'arg1 arg2 '"),
    ("'cmd1' | ' cmd2 ' >> file2.txt", "cmd1 | ' cmd2 ' >> file2.txt"),
    ("cmd1 | >> file2.txt cmd2 arg1", "cmd1 | cmd2 arg1 >> file2.txt"),
))
def test_pipe_and_redirect_append_one_side_only(parser: Parser, formatter: Formatter, line: str, expected_str: str):
    def check(_line):
        first_cmd = parser.parse(_line)
        assert first_cmd.next_command is None
        assert first_cmd.next_command_operator is None
        assert formatter.format_statement(first_cmd) == expected_str

        assert str(first_cmd.command) == "cmd1"
        assert isinstance(first_cmd.pipe_command, Command)

        second_cmd = first_cmd.pipe_command
        assert str(second_cmd.command).strip() == "cmd2"

        if first_cmd.redirect_to_operator:
            assert first_cmd.redirect_to == File("file1.txt")
            assert isinstance(first_cmd.redirect_to_operator, RedirectionAppend)
        else:
            assert second_cmd.redirect_to == File("file2.txt")
            assert isinstance(second_cmd.redirect_to_operator, RedirectionAppend)

    check(line)
    for pipe_space_count in range(0, 5):
        pipe_spaces = " " * pipe_space_count
        for redirect_space_count in range(0, 5):
            redirect_spaces = " " * redirect_space_count
            for pipe_chars in ("| ", " |", " | "):
                _line = line.replace(pipe_chars, pipe_spaces + "|" + pipe_spaces)
                check(_line)
                check(_line.replace(">> ", redirect_spaces + ">>" + redirect_spaces))
                check(_line.replace(" >>", redirect_spaces + ">>" + redirect_spaces))
                check(_line.replace(" >> ", redirect_spaces + ">>" + redirect_spaces))


@pytest.mark.parametrize("line,expected_str", (
    ("cmd1 arg1 >> file1.txt | cmd2 arg1 arg2 >> file2.txt", "cmd1 arg1 >> file1.txt | cmd2 arg1 arg2 >> file2.txt"),
    ("cmd1 'arg1 arg2' >> file1.txt | cmd2 arg1 >> file2.txt", "cmd1 'arg1 arg2' >> file1.txt | cmd2 arg1 >> file2.txt"),
    (">> file1.txt cmd1 | cmd2 >> file2.txt \"arg1 arg2 \"", "cmd1 >> file1.txt | cmd2 'arg1 arg2 ' >> file2.txt"),
    (">> file1.txt 'cmd1' | ' cmd2 ' >> file2.txt", "cmd1 >> file1.txt | ' cmd2 ' >> file2.txt"),
    ("cmd1 arg1 >> file1.txt | >> file2.txt cmd2", "cmd1 arg1 >> file1.txt | cmd2 >> file2.txt"),
))
def test_pipe_and_redirect_append_both_sides(parser: Parser, formatter: Formatter, line: str, expected_str: str):
    def check(_line):
        first_cmd = parser.parse(_line)
        assert first_cmd.next_command is None
        assert first_cmd.next_command_operator is None
        assert formatter.format_statement(first_cmd) == expected_str

        assert str(first_cmd.command) == "cmd1"
        assert isinstance(first_cmd.pipe_command, Command)
        assert first_cmd.redirect_to == File("file1.txt")
        assert isinstance(first_cmd.redirect_to_operator, RedirectionAppend)

        second_cmd = first_cmd.pipe_command
        assert str(second_cmd.command).strip() == "cmd2"
        assert second_cmd.redirect_to == File("file2.txt")
        assert isinstance(second_cmd.redirect_to_operator, RedirectionAppend)

    check(line)
    for pipe_space_count in range(0, 5):
        pipe_spaces = " " * pipe_space_count
        for redirect_space_count in range(0, 5):
            redirect_spaces = " " * redirect_space_count
            for pipe_chars in ("| ", " |", " | "):
                _line = line.replace(pipe_chars, pipe_spaces + "|" + pipe_spaces)
                check(_line)
                check(_line.replace(">> ", redirect_spaces + ">>" + redirect_spaces))
                check(_line.replace(" >>", redirect_spaces + ">>" + redirect_spaces))
                check(_line.replace(" >> ", redirect_spaces + ">>" + redirect_spaces))


@pytest.mark.parametrize("line,expected_cmd_count,expected_str", (
    ("cmd1 arg1 | cmd2 arg1 | cmd3 arg1", 3, "cmd1 arg1 | cmd2 arg1 | cmd3 arg1"),
    ("cmd1 'arg1 arg2' | cmd2 \"arg1 arg2\" arg3", 2, "cmd1 'arg1 arg2' | cmd2 'arg1 arg2' arg3"),
    ("cmd1 'arg1' 'arg2' 'arg3' | cmd2 | cmd3 \"\\arg1'\"", 3, "cmd1 arg1 arg2 arg3 | cmd2 | cmd3 '\\arg1'\"'\"''"),
    ("cmd1 | cmd2 | cmd3 | cmd4 | cmd5", 5, "cmd1 | cmd2 | cmd3 | cmd4 | cmd5"),
))
def test_multiple_pipes(parser: Parser, formatter: Formatter, line: str, expected_cmd_count: int, expected_str: str):
    def check(_line):
        first_cmd = parser.parse(_line)
        assert_no_redirections(first_cmd)
        assert first_cmd.next_command is None
        assert first_cmd.next_command_operator is None

        actual_cmd_count = 1
        cur_cmd = first_cmd.pipe_command
        while cur_cmd:
            actual_cmd_count += 1
            assert_no_redirections(cur_cmd)
            assert cur_cmd.next_command is None
            assert cur_cmd.next_command_operator is None
            cur_cmd = cur_cmd.pipe_command

        assert actual_cmd_count == expected_cmd_count

        actual_str = formatter.format_statement(first_cmd)
        assert actual_str == expected_str

    check(line)
    for pipe_space_count in range(0, 5):
        pipe_spaces = " " * pipe_space_count
        check(line.replace("| ", pipe_spaces + "|" + pipe_spaces))
        check(line.replace(" |", pipe_spaces + "|" + pipe_spaces))
        check(line.replace(" | ", pipe_spaces + "|" + pipe_spaces))


@pytest.mark.parametrize("line,expected_stmt_count,expected_cmd_count", (
    ("cmd1 | cmd2; cmd3", 2, 3),
    ("cmd1 arg1 | cmd2 arg1 'arg2 arg3' | cmd3 arg1; cmd4 arg1 | cmd5 arg1", 2, 5),
    ("cmd1; cmd2; cmd3 | cmd4", 3, 4),
    ("cmd1; cmd2 | cmd3; cmd4", 3, 4),
    ("cmd1 | cmd2; cmd3; cmd4; cmd5 | cmd6", 4, 6),
    ("cmd1 | cmd2 | cmd3; cmd4 | cmd5 | cmd6 | cmd7; cmd8; cmd9", 4, 9),
))
def test_multiple_statements_with_pipes(parser: Parser, line: str, expected_stmt_count: int, expected_cmd_count: int):
    def check(_line: str):
        first_cmd = parser.parse(_line)
        assert_no_redirections(first_cmd)
        stmt_count = 0
        cmd_count = 0
        cur_cmd = first_cmd
        cur_pipe_cmd = first_cmd
        while cur_cmd:
            assert_no_redirections(cur_cmd)
            assert cur_cmd.next_command_operator is None
            stmt_count += 1
            cmd_count += 1
            cur_pipe_cmd = cur_cmd.pipe_command
            while cur_pipe_cmd:
                assert_no_redirections(cur_pipe_cmd)
                assert cur_pipe_cmd.next_command is None
                assert cur_pipe_cmd.next_command_operator is None
                cmd_count += 1
                cur_pipe_cmd = cur_pipe_cmd.pipe_command
            cur_cmd = cur_cmd.next_command

        assert stmt_count == expected_stmt_count
        assert cmd_count == expected_cmd_count

    check(line)
    check(line + ";")


@pytest.mark.parametrize("line,expected_cmd_count,expected_str", (
    ("cmd1 && cmd2", 2, "cmd1 && cmd2"),
    ("cmd1 && cmd2 && cmd3", 3, "cmd1 && cmd2 && cmd3"),
    ("cmd1 arg1 && cmd2", 2, "cmd1 arg1 && cmd2"),
    ("cmd1 \\&\\&arg1 && cmd2 && cmd3 'arg1'", 3, "cmd1 '&&arg1' && cmd2 && cmd3 arg1"),
    ("cmd1 'arg 1' && cmd2 'arg 1' && cmd3", 3, "cmd1 'arg 1' && cmd2 'arg 1' && cmd3"),
    ("cmd1 && cmd2 && cmd3 && cmd4 arg1", 4, "cmd1 && cmd2 && cmd3 && cmd4 arg1"),
    ("cmd1 > file1.txt && cmd2", 2, "cmd1 > file1.txt && cmd2"),
    ("cmd1 arg1 && cmd2 > file2.txt", 2, "cmd1 arg1 && cmd2 > file2.txt"),
    ("cmd1 > file1.txt && cmd2 > file2.txt && cmd3 > file3.txt", 3, "cmd1 > file1.txt && cmd2 > file2.txt && cmd3 > file3.txt"),
    ("cmd1 \"arg1&&arg2\" && cmd2 > 'file2.txt'", 2, "cmd1 'arg1&&arg2' && cmd2 > file2.txt"),
))
def test_anded_statements(parser: Parser, formatter: Formatter, line: str, expected_cmd_count: int, expected_str: str):
    def check(_line: str):
        first_cmd = parser.parse(_line)
        cur_cmd = first_cmd.next_command
        cmd_count = 1
        while cur_cmd:
            cur_cmd = cur_cmd.next_command
            cmd_count += 1
        assert cmd_count == expected_cmd_count

        formatted_statements = formatter.format_statements(first_cmd)
        assert len(formatted_statements) == 1
        assert formatted_statements[0] == expected_str

    check(line)
    check(line.replace("&& ", "&&"))
    check(line.replace(" &&", "&&"))
    check(line.replace(" && ", "&&"))


@pytest.mark.parametrize("line,expected_cmd_count,expected_str", (
    ("cmd1 || cmd2", 2, "cmd1 || cmd2"),
    ("cmd1 || cmd2 || cmd3", 3, "cmd1 || cmd2 || cmd3"),
    ("cmd1 arg1 || cmd2", 2, "cmd1 arg1 || cmd2"),
    ("cmd1 \\|\\|arg1 || cmd2 || cmd3 'arg1'", 3, "cmd1 '||arg1' || cmd2 || cmd3 arg1"),
    ("cmd1 'arg 1' || cmd2 'arg 1' || cmd3", 3, "cmd1 'arg 1' || cmd2 'arg 1' || cmd3"),
    ("cmd1 || cmd2 || cmd3 || cmd4 arg1", 4, "cmd1 || cmd2 || cmd3 || cmd4 arg1"),
    ("cmd1 > file1.txt || cmd2", 2, "cmd1 > file1.txt || cmd2"),
    ("cmd1 arg1 || cmd2 > file2.txt", 2, "cmd1 arg1 || cmd2 > file2.txt"),
    ("cmd1 > file1.txt || cmd2 > file2.txt || cmd3 > file3.txt", 3, "cmd1 > file1.txt || cmd2 > file2.txt || cmd3 > file3.txt"),
    ("cmd1 \"arg1||arg2\" || cmd2 > 'file2.txt'", 2, "cmd1 'arg1||arg2' || cmd2 > file2.txt"),
))
def test_ored_statements(parser: Parser, formatter: Formatter, line: str, expected_cmd_count: int, expected_str: str):
    def check(_line: str):
        first_cmd = parser.parse(_line)
        cur_cmd = first_cmd.next_command
        cmd_count = 1
        while cur_cmd:
            cur_cmd = cur_cmd.next_command
            cmd_count += 1
        assert cmd_count == expected_cmd_count

        formatted_statements = formatter.format_statements(first_cmd)
        assert len(formatted_statements) == 1
        assert formatted_statements[0] == expected_str

    check(line)
    check(line.replace("|| ", "||"))
    check(line.replace(" ||", "||"))
    check(line.replace(" || ", "||"))


@pytest.mark.parametrize("line,expected_cmd_count", (
    ("cmd1 arg1 && cmd2 arg2 || cmd3 arg3", 3),
    ("cmd1 arg1 arg2 || cmd2 'arg3 arg4' && cmd3", 3),
    ("cmd1 'arg1 arg2' && cmd2; cmd3 || cmd4", 4),
    ("cmd1 arg1 || cmd2; cmd3", 3),
    ("cmd1 arg1; cmd2 && cmd3 arg2", 3),
    ("cmd1 arg1; cmd2 || cmd3 arg2", 3),
    ("cmd1 arg1; cmd2 && cmd3 arg2 || cmd4 'arg3 arg4'", 4),
    ("cmd1 arg1; cmd2 || cmd3 arg2 && cmd4 'arg3 arg4'; cmd5 && cmd6 arg5", 6),
))
def test_mixed_next_cmd_operators(parser: Parser, formatter: Formatter, line: str, expected_cmd_count: int):
    first_cmd = parser.parse(line)
    formatted_statements = formatter.format_statements(first_cmd)
    assert "; ".join(formatted_statements) == line

    cur_cmd = first_cmd.next_command
    cmd_count = 1
    while cur_cmd:
        cur_cmd = cur_cmd.next_command
        cmd_count += 1
    assert cmd_count == expected_cmd_count


@pytest.mark.parametrize("line", (
    "cmd1 >;",
    "cmd1 > ;",
    "cmd1 > ; cmd2",
    "cmd1 > &",
    "cmd1 > & cmd2",
    "cmd1 > && cmd2",
    "cmd1 > | cmd2",
    "cmd1 > || cmd2",
    "cmd1 > >",
))
def test_empty_redirect_filename(parser: Parser, line: str):
    def check(_line: str):
        with pytest.raises(EmptyRedirectParserFailure, match=re.escape("No redirect filename provided.")):
            parser.parse(_line)

    check(line)
    check(line.replace(">", ">>"))


@pytest.mark.parametrize("line", (
    "cmd1 >",
    "cmd1 >>",
    "cmd1 |",
))
def test_unexpected_statementfinish(parser: Parser, line: str):
    with pytest.raises(UnexpectedStatementFinishParserFailure):
        parser.parse(line)


@pytest.mark.parametrize("line,failure_pos", (
    ("cmd1 ; ;", 7),
    ("cmd1 arg1;;", 10),
    ("cmd1 &&", 7), 
    ("cmd1 ||", 7),
    ("cmd1 'arg1 arg2' && &&", 22),
    ("cmd1 'arg1 || arg2' || ||", 25),
    ("cmd1 'arg1 || arg2' \\|\\| || ||", 30),
))
def test_empty_statement(parser: Parser, line: str, failure_pos: int):
    with pytest.raises(EmptyStatementParserFailure) as excinfo:
        parser.parse(line)
    assert excinfo.value.pos == failure_pos


@pytest.mark.parametrize("line", (
    "cmd1 '",
    'cmd1 "',
    "cmd1 ''\"",
    'cmd1 ""\'',
    "cmd1 '\\''",
    'cmd1 "\\"',
))
def test_unclosed_quotes(parser: Parser, line: str):
    with pytest.raises(UnclosedQuoteParserFailure):
        parser.parse(line)
