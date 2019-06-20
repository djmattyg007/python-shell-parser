import pytest

import dataclasses
import re

from shell_parser.ast import *
from shell_parser.formatter import Formatter
from shell_parser.parser import *
from typing import Mapping, Set, Tuple, Union


def assert_single_cmd(cmd: Command):
    assert cmd.pipe_command is None
    assert cmd.next_command is None
    assert cmd.next_command_operator is None


def make_descriptor(target: Union[File, DefaultFile], operator: Union[RedirectionInput, RedirectionOutput, RedirectionAppend]) -> CommandDescriptor:
    file_descriptor = CommandFileDescriptor(
        target=target,
        operator=operator,
    )
    if isinstance(operator, RedirectionInput):
        return CommandDescriptor(
            mode=DescriptorRead(),
            descriptor=file_descriptor,
        )
    else:
        return CommandDescriptor(
            mode=DescriptorWrite(),
            descriptor=file_descriptor,
        )


DEFAULT_DESCRIPTOR_STDIN = make_descriptor(DefaultFile(target=StdinTarget()), operator=RedirectionInput())
DEFAULT_DESCRIPTOR_STDOUT = make_descriptor(DefaultFile(target=StdoutTarget()), operator=RedirectionOutput())
DEFAULT_DESCRIPTOR_STDERR = make_descriptor(DefaultFile(target=StderrTarget()), operator=RedirectionOutput())


def assert_descriptors(
        cmd: Command,
        *,
        defaults: Set[int] = frozenset((0, 1, 2)),
        files: Mapping[int, CommandDescriptor] = None,
        closed: Set[int] = frozenset()
    ):
    descriptors = cmd.descriptors.descriptors
    checked_fds = set()

    not_set_defaults = defaults - closed
    if files is not None:
        not_set_defaults -= files.keys()

    for default_fd in not_set_defaults:
        assert descriptors[default_fd].descriptor.is_default_file == True
        checked_fds.add(default_fd)

    if files is not None:
        for file_fd, descriptor in files.items():
            assert descriptors[file_fd] == descriptor
            checked_fds.add(file_fd)

    for closed_fd in closed:
        assert isinstance(descriptors[closed_fd], CommandDescriptorClosed)
        checked_fds.add(closed_fd)

    assert checked_fds == descriptors.keys()


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
    assert_single_cmd(first_cmd)
    assert first_cmd.asynchronous == False


@pytest.mark.parametrize("before_space_count", range(0, 4))
@pytest.mark.parametrize("after_space_count", range(0, 4))
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
def test_single_word_manually_terminated(parser: Parser, manual: str, nonmanual: str, before_space_count: int, after_space_count: int):
    before_spaces = " " * before_space_count
    after_spaces = " " * after_space_count
    _manual = manual.replace(";", before_spaces + ";" + after_spaces)
    manual_first_cmd = parser.parse(_manual)
    nonmanual_first_cmd = parser.parse(nonmanual)
    assert manual_first_cmd == nonmanual_first_cmd
    assert_single_cmd(manual_first_cmd)
    assert manual_first_cmd.asynchronous == False


@pytest.mark.parametrize("line,command_word,args_words", (
    ("cmd arg1", Word("cmd"), (Word("arg1"),)),
    ("cmd arg1 arg2", Word("cmd"), (Word("arg1"), Word("arg2"))),
    ("cmd arg1 arg2 arg3", Word("cmd"), (Word("arg1"), Word("arg2"), Word("arg3"))),
    ("'cmd' 'arg1 arg2' arg3", QuotedWord("cmd"), (QuotedWord("arg1 arg2"), Word("arg3"))),
    ('"cmd" "arg1" "arg2 arg3"', QuotedWord("cmd"), (QuotedWord("arg1"), QuotedWord("arg2 arg3"))),
    ("cmd  arg1   arg2", Word("cmd"), (Word("arg1"), Word("arg2"))),
    ("'cmd'   arg1  '   arg2'", QuotedWord("cmd"), (Word("arg1"), QuotedWord("   arg2"))),
    ("cmd 1arg 2arg", Word("cmd"), (Word("1arg"), Word("2arg"))),
))
def test_multiple_words(parser: Parser, line: str, command_word: Word, args_words: Tuple[Word, ...]):
    first_cmd = parser.parse(line)
    assert first_cmd.command == command_word
    assert first_cmd.args == args_words
    assert_single_cmd(first_cmd)
    assert_descriptors(first_cmd)


@pytest.mark.parametrize("line,command_word,args_words", (
    ("cmd 1", Word("cmd"), (Word("1"),)),
    ("cmd 1 arg2", Word("cmd"), (Word("1"), Word("arg2"))),
    ("cmd 1 2", Word("cmd"), (Word("1"), Word("2"))),
    ("cmd 1 2 arg3", Word("cmd"), (Word("1"), Word("2"), Word("arg3"))),
    ("cmd 1 arg2 3", Word("cmd"), (Word("1"), Word("arg2"), Word("3"))),
    ("cmd 1 2 arg3 4", Word("cmd"), (Word("1"), Word("2"), Word("arg3"), Word("4"))),
    ("cmd 11 222", Word("cmd"), (Word("11"), Word("222"))),
    ("cmd 11 222 arg3", Word("cmd"), (Word("11"), Word("222"), Word("arg3"))),
    ("cmd 11 arg2 333", Word("cmd"), (Word("11"), Word("arg2"), Word("333"))),
    ("cmd 11 222 arg3 4444", Word("cmd"), (Word("11"), Word("222"), Word("arg3"), Word("4444"))),
))
def test_multiple_word_with_numeric_only_args(parser: Parser, line: str, command_word: Word, args_words: Tuple[Word, ...]):
    first_cmd = parser.parse(line)
    assert first_cmd.command == command_word
    assert first_cmd.args == args_words
    assert_single_cmd(first_cmd)
    assert_descriptors(first_cmd)


@pytest.mark.parametrize("line,expected_str", (
    ("cmd1 arg\\ 1", "cmd1 'arg 1'"),
    ("cmd\\ 1", "'cmd 1'"),
    ("cmd\\ 1a", "'cmd 1a'"),
    ("cmd\\ 12", "'cmd 12'"),
    ("cmd\\ 12a", "'cmd 12a'"),
    ("cmd\\ 12ab", "'cmd 12ab'"),
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
    assert_single_cmd(first_cmd)
    assert_descriptors(first_cmd)
    assert first_cmd.asynchronous == False


@pytest.mark.parametrize("line,expected_cmd_count,expected_strs", (
    ("cmd1 arg1; cmd2 arg1", 2, ("cmd1 arg1", "cmd2 arg1")),
    ("cmd1  arg1 ; cmd2 'arg1'", 2, ("cmd1 arg1", "cmd2 arg1")),
    ("cmd1 ' arg1 ' ;cmd2 arg1", 2, ("cmd1 ' arg1 '", "cmd2 arg1")),
    ("cmd1 arg1;cmd2 arg1", 2, ("cmd1 arg1", "cmd2 arg1")),
    ("cmd1 'arg1';cmd2 arg1", 2, ("cmd1 arg1", "cmd2 arg1")),
    ("cmd1 arg1;cmd2 'arg1'", 2, ("cmd1 arg1", "cmd2 arg1")),
    ("cmd1;cmd2;cmd3", 3, ("cmd1", "cmd2", "cmd3")),
    ("'cmd1';'cmd2';'cmd3'", 3, ("cmd1", "cmd2", "cmd3")),
    ("'cmd1' 'arg1';'cmd2' 'arg2';'cmd3' 'arg3'", 3, ("cmd1 arg1", "cmd2 arg2", "cmd3 arg3")),
    ("cmd1; cmd2; cmd3", 3, ("cmd1", "cmd2", "cmd3")),
    ("'cmd1'; 'cmd2'; 'cmd3'", 3, ("cmd1", "cmd2", "cmd3")),
    ("'cmd1';' cmd2';' cmd3'", 3, ("cmd1", "' cmd2'", "' cmd3'")),
    ("cmd1; cmd2;", 2, ("cmd1", "cmd2")),
    ("cmd1 'arg;1'; cmd2 \";;;'\" ;", 2, ("cmd1 'arg;1'", "cmd2 ';;;'\"'\"''")),
))
def test_multiple_plain_commands(parser: Parser, formatter: Formatter, line: str, expected_cmd_count: int, expected_strs: Tuple[str, ...]):
    first_cmd = parser.parse(line)
    assert first_cmd.next_command_operator is None
    assert_descriptors(first_cmd)

    actual_cmd_count = 1
    cur_cmd = first_cmd.next_command
    while cur_cmd:
        actual_cmd_count += 1
        assert cur_cmd.next_command_operator is None
        assert_descriptors(cur_cmd)

        cur_cmd = cur_cmd.next_command

    assert actual_cmd_count == expected_cmd_count

    formatted_statements = formatter.format_statements(first_cmd)
    assert formatted_statements == expected_strs
    assert len(formatted_statements) == expected_cmd_count


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
    assert first_cmd.next_command is None
    assert first_cmd.next_command_operator is None
    assert_descriptors(first_cmd)

    actual_cmd_count = 1
    cur_cmd = first_cmd.pipe_command
    while cur_cmd:
        actual_cmd_count += 1
        assert cur_cmd.next_command is None
        assert cur_cmd.next_command_operator is None
        assert_descriptors(cur_cmd)

        cur_cmd = cur_cmd.pipe_command

    assert actual_cmd_count == expected_cmd_count
    assert formatter.format_statement(first_cmd) == expected_str


@pytest.mark.parametrize("space_count", range(-1, 4))
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
    ("cmd1 'arg1 arg2'>testfile.txt", "cmd1 'arg1 arg2' > testfile.txt"),
    ("cmd1 'arg1 arg2'xx>testfile.txt", "cmd1 'arg1 arg2xx' > testfile.txt"),
    ("cmd1 'arg1 arg2'3>testfile.txt", "cmd1 'arg1 arg23' > testfile.txt"),
    ("cmd1 'arg1 arg2'>testfile.txt arg3", "cmd1 'arg1 arg2' arg3 > testfile.txt"),
    ("cmd1 'arg1 arg2'xx>testfile.txt arg3", "cmd1 'arg1 arg2xx' arg3 > testfile.txt"),
    ("cmd1 'arg1 arg2'3>testfile.txt arg3", "cmd1 'arg1 arg23' arg3 > testfile.txt"),
))
def test_redirect_output(parser: Parser, line: str, expected_str: str, space_count: int):
    # todo add escaped appends
    file_descriptor = make_descriptor(File("testfile.txt"), RedirectionOutput())
    def check(_line: str):
        first_cmd = parser.parse(_line)
        assert_single_cmd(first_cmd)

        assert str(first_cmd.command) == "cmd1"
        assert str(first_cmd) == expected_str
        assert_descriptors(first_cmd, files={DESCRIPTOR_DEFAULT_INDEX_STDOUT: file_descriptor})

    if space_count < 0:
        check(line)
        return

    spaces = " " * space_count
    check(line.replace("> ", spaces + ">" + spaces))
    check(line.replace(" >", spaces + ">" + spaces))
    check(line.replace(" > ", spaces + ">" + spaces))


@pytest.mark.parametrize("space_count", range(-1, 4))
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
    ("cmd1 'arg1 arg2'>>testfile.txt", "cmd1 'arg1 arg2' >> testfile.txt"),
    ("cmd1 'arg1 arg2'xx>>testfile.txt", "cmd1 'arg1 arg2xx' >> testfile.txt"),
    ("cmd1 'arg1 arg2'3>>testfile.txt", "cmd1 'arg1 arg23' >> testfile.txt"),
    ("cmd1 'arg1 arg2'>>testfile.txt arg3", "cmd1 'arg1 arg2' arg3 >> testfile.txt"),
    ("cmd1 'arg1 arg2'xx>>testfile.txt arg3", "cmd1 'arg1 arg2xx' arg3 >> testfile.txt"),
    ("cmd1 'arg1 arg2'3>>testfile.txt arg3", "cmd1 'arg1 arg23' arg3 >> testfile.txt"),
))
def test_redirect_append(parser: Parser, line: str, expected_str: str, space_count: int):
    # todo add escaped outputs 
    file_descriptor = make_descriptor(File("testfile.txt"), RedirectionAppend())
    def check(_line: str):
        first_cmd = parser.parse(line)
        assert_single_cmd(first_cmd)

        assert str(first_cmd.command) == "cmd1"
        assert str(first_cmd) == expected_str
        assert_descriptors(first_cmd, files={DESCRIPTOR_DEFAULT_INDEX_STDOUT: file_descriptor})

    if space_count < 0:
        check(line)
        return

    spaces = " " * space_count
    check(line.replace(">> ", spaces + ">>" + spaces))
    check(line.replace(" >>", spaces + ">>" + spaces))
    check(line.replace(" >> ", spaces + ">>" + spaces))


@pytest.mark.parametrize("pipe_space_count", range(-1, 4))
@pytest.mark.parametrize("redirect_space_count", range(0, 4))
@pytest.mark.parametrize("pipe_chars", ("| ", " |", " | "))
@pytest.mark.parametrize("line,expected_str", (
    ("cmd1 arg1 > file1.txt | cmd2 arg1 arg2", "cmd1 arg1 > file1.txt | cmd2 arg1 arg2"),
    ("cmd1 'arg1 arg2' > file1.txt | cmd2 arg1 ", "cmd1 'arg1 arg2' > file1.txt | cmd2 arg1"),
    ("> file1.txt cmd1 | cmd2  \"arg1 arg2 \"", "cmd1 > file1.txt | cmd2 'arg1 arg2 '"),
))
def test_pipe_and_redirect_output_left_side_only(parser: Parser, formatter: Formatter, line: str, expected_str: str, pipe_space_count: int, redirect_space_count: int, pipe_chars: str):
    file_descriptor = make_descriptor(File("file1.txt"), RedirectionOutput())
    def check(_line):
        first_cmd = parser.parse(_line)
        assert first_cmd.next_command is None
        assert first_cmd.next_command_operator is None
        assert formatter.format_statement(first_cmd) == expected_str

        assert str(first_cmd.command) == "cmd1"
        assert isinstance(first_cmd.pipe_command, Command)
        assert_descriptors(first_cmd, files={DESCRIPTOR_DEFAULT_INDEX_STDOUT: file_descriptor})

        second_cmd = first_cmd.pipe_command
        assert str(second_cmd.command).strip() == "cmd2"
        assert_single_cmd(second_cmd)
        assert_descriptors(second_cmd)

    if pipe_space_count < 0:
        check(line)
        return

    pipe_spaces = " " * pipe_space_count
    redirect_spaces = " " * redirect_space_count
    redirect_chars = redirect_spaces + ">" + redirect_spaces

    _line = line.replace(pipe_chars, pipe_spaces + "|" + pipe_spaces)
    check(_line)
    check(_line.replace("> ", redirect_chars))
    check(_line.replace(" >", redirect_chars))
    check(_line.replace(" > ", redirect_chars))


@pytest.mark.parametrize("pipe_space_count", range(-1, 4))
@pytest.mark.parametrize("redirect_space_count", range(0, 4))
@pytest.mark.parametrize("pipe_chars", ("| ", " |", " | "))
@pytest.mark.parametrize("line,expected_str", (
    ("'cmd1' | ' cmd2 ' > file2.txt", "cmd1 | ' cmd2 ' > file2.txt"),
    ("cmd1 | > file2.txt cmd2 arg1", "cmd1 | cmd2 arg1 > file2.txt"),
    ("cmd1 | cmd2 2arg > file2.txt", "cmd1 | cmd2 2arg > file2.txt"),
))
def test_pipe_and_redirect_output_right_side_only(parser: Parser, formatter: Formatter, line: str, expected_str: str, pipe_space_count: int, redirect_space_count: int, pipe_chars: str):
    file_descriptor = make_descriptor(File("file2.txt"), RedirectionOutput())
    def check(_line):
        first_cmd = parser.parse(_line)
        assert first_cmd.next_command is None
        assert first_cmd.next_command_operator is None
        assert formatter.format_statement(first_cmd) == expected_str

        assert str(first_cmd.command) == "cmd1"
        assert isinstance(first_cmd.pipe_command, Command)
        assert_descriptors(first_cmd)

        second_cmd = first_cmd.pipe_command
        assert str(second_cmd.command).strip() == "cmd2"
        assert_single_cmd(second_cmd)
        assert_descriptors(second_cmd, files={DESCRIPTOR_DEFAULT_INDEX_STDOUT: file_descriptor})

    if pipe_space_count < 0:
        check(line)
        return

    pipe_spaces = " " * pipe_space_count
    redirect_spaces = " " * redirect_space_count
    redirect_chars = redirect_spaces + ">" + redirect_spaces

    _line = line.replace(pipe_chars, pipe_spaces + "|" + pipe_spaces)
    check(_line)
    check(_line.replace("> ", redirect_chars))
    check(_line.replace(" >", redirect_chars))
    check(_line.replace(" > ", redirect_chars))


@pytest.mark.parametrize("pipe_space_count", range(-1, 4))
@pytest.mark.parametrize("redirect_space_count", range(0, 4))
@pytest.mark.parametrize("pipe_chars", ("| ", " |", " | "))
@pytest.mark.parametrize("line,expected_str", (
    ("cmd1 arg1 > file1.txt | cmd2 arg1 arg2 > file2.txt", "cmd1 arg1 > file1.txt | cmd2 arg1 arg2 > file2.txt"),
    ("cmd1 'arg1 arg2' > file1.txt | cmd2 arg1 > file2.txt", "cmd1 'arg1 arg2' > file1.txt | cmd2 arg1 > file2.txt"),
    ("> file1.txt cmd1 | cmd2 > file2.txt \"arg1 arg2 \"", "cmd1 > file1.txt | cmd2 'arg1 arg2 ' > file2.txt"),
    ("> file1.txt 'cmd1' | ' cmd2 ' > file2.txt", "cmd1 > file1.txt | ' cmd2 ' > file2.txt"),
    ("cmd1 arg1 > file1.txt | > file2.txt cmd2", "cmd1 arg1 > file1.txt | cmd2 > file2.txt"),
))
def test_pipe_and_redirect_output_both_sides(parser: Parser, formatter: Formatter, line: str, expected_str: str, pipe_space_count: int, redirect_space_count: int, pipe_chars: str):
    file1_descriptor = make_descriptor(File("file1.txt"), RedirectionOutput())
    file2_descriptor = make_descriptor(File("file2.txt"), RedirectionOutput())
    def check(_line):
        first_cmd = parser.parse(_line)
        assert first_cmd.next_command is None
        assert first_cmd.next_command_operator is None
        assert formatter.format_statement(first_cmd) == expected_str

        assert str(first_cmd.command) == "cmd1"
        assert isinstance(first_cmd.pipe_command, Command)
        assert_descriptors(first_cmd, files={DESCRIPTOR_DEFAULT_INDEX_STDOUT: file1_descriptor})

        second_cmd = first_cmd.pipe_command
        assert str(second_cmd.command).strip() == "cmd2"
        assert_single_cmd(second_cmd)
        assert_descriptors(second_cmd, files={DESCRIPTOR_DEFAULT_INDEX_STDOUT: file2_descriptor})

    if pipe_space_count < 0:
        check(line)
        return

    pipe_spaces = " " * pipe_space_count
    redirect_spaces = " " * redirect_space_count
    redirect_chars = redirect_spaces + ">" + redirect_spaces

    _line = line.replace(pipe_chars, pipe_spaces + "|" + pipe_spaces)
    check(_line)
    check(_line.replace("> ", redirect_chars))
    check(_line.replace(" >", redirect_chars))
    check(_line.replace(" > ", redirect_chars))


@pytest.mark.parametrize("pipe_space_count", range(-1, 4))
@pytest.mark.parametrize("redirect_space_count", range(0, 4))
@pytest.mark.parametrize("pipe_chars", ("| ", " |", " | "))
@pytest.mark.parametrize("line,expected_str", (
    ("cmd1 arg1 >> file1.txt | cmd2 arg1 arg2", "cmd1 arg1 >> file1.txt | cmd2 arg1 arg2"),
    ("cmd1 'arg1 arg2' >> file1.txt | cmd2 arg1 ", "cmd1 'arg1 arg2' >> file1.txt | cmd2 arg1"),
    (">> file1.txt cmd1 | cmd2  \"arg1 arg2 \"", "cmd1 >> file1.txt | cmd2 'arg1 arg2 '"),
))
def test_pipe_and_redirect_append_left_side_only(parser: Parser, formatter: Formatter, line: str, expected_str: str, pipe_space_count: int, redirect_space_count: int, pipe_chars: str):
    file_descriptor = make_descriptor(File("file1.txt"), RedirectionAppend())
    def check(_line):
        first_cmd = parser.parse(_line)
        assert first_cmd.next_command is None
        assert first_cmd.next_command_operator is None
        assert formatter.format_statement(first_cmd) == expected_str

        assert str(first_cmd.command) == "cmd1"
        assert isinstance(first_cmd.pipe_command, Command)
        assert_descriptors(first_cmd, files={DESCRIPTOR_DEFAULT_INDEX_STDOUT: file_descriptor})

        second_cmd = first_cmd.pipe_command
        assert str(second_cmd.command).strip() == "cmd2"
        assert_single_cmd(second_cmd)
        assert_descriptors(second_cmd)

    if pipe_space_count < 0:
        check(line)
        return

    pipe_spaces = " " * pipe_space_count
    redirect_spaces = " " * redirect_space_count
    redirect_chars = redirect_spaces + ">>" + redirect_spaces

    _line = line.replace(pipe_chars, pipe_spaces + "|" + pipe_spaces)
    check(_line)
    check(_line.replace(">> ", redirect_chars))
    check(_line.replace(" >>", redirect_chars))
    check(_line.replace(" >> ", redirect_chars))


@pytest.mark.parametrize("pipe_space_count", range(-1, 4))
@pytest.mark.parametrize("redirect_space_count", range(0, 4))
@pytest.mark.parametrize("pipe_chars", ("| ", " |", " | "))
@pytest.mark.parametrize("line,expected_str", (
    ("'cmd1' | ' cmd2 ' >> file2.txt", "cmd1 | ' cmd2 ' >> file2.txt"),
    ("cmd1 | >> file2.txt cmd2 arg1", "cmd1 | cmd2 arg1 >> file2.txt"),
    ("cmd1 | cmd2 2arg >> file2.txt", "cmd1 | cmd2 2arg >> file2.txt"),
))
def test_pipe_and_redirect_append_right_side_only(parser: Parser, formatter: Formatter, line: str, expected_str: str, pipe_space_count: int, redirect_space_count: int, pipe_chars: str):
    file_descriptor = make_descriptor(File("file2.txt"), RedirectionAppend())
    def check(_line):
        first_cmd = parser.parse(_line)
        assert first_cmd.next_command is None
        assert first_cmd.next_command_operator is None
        assert formatter.format_statement(first_cmd) == expected_str

        assert str(first_cmd.command) == "cmd1"
        assert isinstance(first_cmd.pipe_command, Command)
        assert_descriptors(first_cmd)

        second_cmd = first_cmd.pipe_command
        assert str(second_cmd.command).strip() == "cmd2"
        assert_single_cmd(second_cmd)
        assert_descriptors(second_cmd, files={DESCRIPTOR_DEFAULT_INDEX_STDOUT: file_descriptor})

    if pipe_space_count < 0:
        check(line)
        return

    pipe_spaces = " " * pipe_space_count
    redirect_spaces = " " * redirect_space_count
    redirect_chars = redirect_spaces + ">>" + redirect_spaces

    _line = line.replace(pipe_chars, pipe_spaces + "|" + pipe_spaces)
    check(_line)
    check(_line.replace(">> ", redirect_chars))
    check(_line.replace(" >>", redirect_chars))
    check(_line.replace(" >> ", redirect_chars))


@pytest.mark.parametrize("pipe_space_count", range(-1, 4))
@pytest.mark.parametrize("redirect_space_count", range(0, 4))
@pytest.mark.parametrize("pipe_chars", ("| ", " |", " | "))
@pytest.mark.parametrize("line,expected_str", (
    ("cmd1 arg1 >> file1.txt | cmd2 arg1 arg2 >> file2.txt", "cmd1 arg1 >> file1.txt | cmd2 arg1 arg2 >> file2.txt"),
    ("cmd1 'arg1 arg2' >> file1.txt | cmd2 arg1 >> file2.txt", "cmd1 'arg1 arg2' >> file1.txt | cmd2 arg1 >> file2.txt"),
    (">> file1.txt cmd1 | cmd2 >> file2.txt \"arg1 arg2 \"", "cmd1 >> file1.txt | cmd2 'arg1 arg2 ' >> file2.txt"),
    (">> file1.txt 'cmd1' | ' cmd2 ' >> file2.txt", "cmd1 >> file1.txt | ' cmd2 ' >> file2.txt"),
    ("cmd1 arg1 >> file1.txt | >> file2.txt cmd2", "cmd1 arg1 >> file1.txt | cmd2 >> file2.txt"),
))
def test_pipe_and_redirect_append_both_sides(parser: Parser, formatter: Formatter, line: str, expected_str: str, pipe_space_count: int, redirect_space_count: int, pipe_chars: str):
    file1_descriptor = make_descriptor(File("file1.txt"), RedirectionAppend())
    file2_descriptor = make_descriptor(File("file2.txt"), RedirectionAppend())
    def check(_line):
        first_cmd = parser.parse(_line)
        assert first_cmd.next_command is None
        assert first_cmd.next_command_operator is None
        assert formatter.format_statement(first_cmd) == expected_str

        assert str(first_cmd.command) == "cmd1"
        assert isinstance(first_cmd.pipe_command, Command)
        assert_descriptors(first_cmd, files={DESCRIPTOR_DEFAULT_INDEX_STDOUT: file1_descriptor})

        second_cmd = first_cmd.pipe_command
        assert str(second_cmd.command).strip() == "cmd2"
        assert_single_cmd(second_cmd)
        assert_descriptors(second_cmd, files={DESCRIPTOR_DEFAULT_INDEX_STDOUT: file2_descriptor})

    if pipe_space_count < 0:
        check(line)
        return

    pipe_spaces = " " * pipe_space_count
    redirect_spaces = " " * redirect_space_count
    redirect_chars = redirect_spaces + ">>" + redirect_spaces

    _line = line.replace(pipe_chars, pipe_spaces + "|" + pipe_spaces)
    check(_line)
    check(_line.replace(">> ", redirect_chars))
    check(_line.replace(" >>", redirect_chars))
    check(_line.replace(" >> ", redirect_chars))


def test_duplicating_descriptors(parser: Parser):
    stmt1 = "cmd arg1 >&2"
    cmd1 = parser.parse(stmt1)
    assert_single_cmd(cmd1)
    assert_descriptors(cmd1, files={DESCRIPTOR_DEFAULT_INDEX_STDOUT: DEFAULT_DESCRIPTOR_STDERR})
    assert str(cmd1) == "cmd arg1 > /dev/stderr"

    stmt2 = "cmd arg1 >&2 2>&-"
    cmd2 = parser.parse(stmt2)
    assert_single_cmd(cmd2)
    assert_descriptors(cmd2, files={DESCRIPTOR_DEFAULT_INDEX_STDOUT: DEFAULT_DESCRIPTOR_STDERR}, closed=frozenset((DESCRIPTOR_DEFAULT_INDEX_STDERR,)))
    assert str(cmd2) == "cmd arg1 > /dev/stderr 2>&-"

    stmt3 = "cmd arg1 22>&2 >33 44>&22"
    cmd3 = parser.parse(stmt3)
    assert_single_cmd(cmd3)
    cmd3_files = {
        DESCRIPTOR_DEFAULT_INDEX_STDOUT: make_descriptor(File(name="33"), RedirectionOutput()),
        22: DEFAULT_DESCRIPTOR_STDERR,
        44: DEFAULT_DESCRIPTOR_STDERR,
    }
    assert_descriptors(cmd3, files=cmd3_files)
    assert str(cmd3) == "cmd arg1 > 33 22> /dev/stderr 44> /dev/stderr"

    stmt4 = "cmd arg1 22>&2 >44 44>&22 2>&-"
    cmd4 = parser.parse(stmt4)
    assert_single_cmd(cmd4)
    cmd4_files = {
        DESCRIPTOR_DEFAULT_INDEX_STDOUT: make_descriptor(File(name="44"), RedirectionOutput()),
        22: DEFAULT_DESCRIPTOR_STDERR,
        44: DEFAULT_DESCRIPTOR_STDERR,
    }
    assert_descriptors(cmd4, files=cmd4_files, closed=frozenset((DESCRIPTOR_DEFAULT_INDEX_STDERR,)))
    assert str(cmd4) == "cmd arg1 > 44 2>&- 22> /dev/stderr 44> /dev/stderr"


@pytest.mark.parametrize("line,descriptors,expected_str", (
    ("cmd arg1 >&-", frozenset((1,)), "cmd arg1 >&-"),
    ("cmd arg1 >& -", frozenset((1,)), "cmd arg1 >&-"),
    ("cmd arg1 2>&- >&-", frozenset((1, 2)), "cmd arg1 >&- 2>&-"),
    ("cmd 'arg1 arg2'>&-", frozenset((1,)), "cmd 'arg1 arg2' >&-"),
    ("cmd 'arg1 arg2'2>&-", frozenset((1,)), "cmd 'arg1 arg22' >&-"),
    ("cmd 'arg1 arg2'2>&-2>&-", frozenset((1, 2)), "cmd 'arg1 arg22' >&- 2>&-"),
    ("cmd 'arg1 arg2'>&- arg3", frozenset((1,)), "cmd 'arg1 arg2' arg3 >&-"),
    ("cmd 'arg1 arg2'2>&- arg3", frozenset((1,)), "cmd 'arg1 arg22' arg3 >&-"),
    ("cmd 'arg1 arg2'2>&-2>&- arg3", frozenset((1, 2)), "cmd 'arg1 arg22' arg3 >&- 2>&-"),
    ("cmd arg1 arg2>&-", frozenset((1,)), "cmd arg1 arg2 >&-"),
    ("cmd arg1 2>&-", frozenset((2,)), "cmd arg1 2>&-"),
    ("cmd arg1 \\2>&-", frozenset((1,)), "cmd arg1 2 >&-"),
    ("cmd arg1 'arg2'>&-'arg3'", frozenset((1,)), "cmd arg1 arg2 arg3 >&-"),
    ("cmd arg1 1000>&-", frozenset((1000,)), "cmd arg1 1000>&-"),
    ("cmd arg1 >&--", frozenset((1,)), "cmd arg1 - >&-"),
))
def test_closing_descriptors(parser: Parser, line: str, descriptors: Set[int], expected_str: str):
    first_cmd = parser.parse(line)
    assert_single_cmd(first_cmd)
    assert_descriptors(first_cmd, closed=descriptors)
    assert str(first_cmd) == expected_str


@pytest.mark.parametrize("line", (
    "cmd >&a",
    "cmd >&1a",
    "cmd >&a1",
    "cmd >&1a1",
    "cmd >&a1a",
))
def test_ambiguous_descriptor_redirects(parser: Parser, line: str):
    def check(_line: str):
        with pytest.raises(AmbiguousRedirectParserFailure):
            parser.parse(_line)
        with pytest.raises(AmbiguousRedirectParserFailure):
            parser.parse(_line.replace("cmd", "cmd arg1"))
        with pytest.raises(AmbiguousRedirectParserFailure):
            parser.parse(_line.replace("cmd ", "cmd arg1"))
        with pytest.raises(AmbiguousRedirectParserFailure):
            parser.parse(_line.replace("cmd ", "cmd 'arg1'"))

    check(line)
    check(line.replace(">", "2>"))


@pytest.mark.parametrize("line", (
    "cmd >>&a",
    "cmd >>&1a",
    "cmd >>&a1",
    "cmd >>&1a1",
    "cmd >>&a1a",
))
def test_invalid_redirections(parser: Parser, line: str):
    def check(_line: str):
        with pytest.raises(InvalidRedirectionParserFailure):
            parser.parse(_line)
        with pytest.raises(InvalidRedirectionParserFailure):
            parser.parse(_line.replace("cmd", "cmd arg1"))
        with pytest.raises(InvalidRedirectionParserFailure):
            parser.parse(_line.replace("cmd ", "cmd arg1"))
        with pytest.raises(InvalidRedirectionParserFailure):
            parser.parse(_line.replace("cmd ", "cmd 'arg1'"))

    check(line)
    check(line.replace(">>", "2>>"))


@pytest.mark.parametrize("pipe_space_count", range(-1, 4))
@pytest.mark.parametrize("line,expected_cmd_count,expected_str", (
    ("cmd1 arg1 | cmd2 arg1 | cmd3 arg1", 3, "cmd1 arg1 | cmd2 arg1 | cmd3 arg1"),
    ("cmd1 'arg1 arg2' | cmd2 \"arg1 arg2\" arg3", 2, "cmd1 'arg1 arg2' | cmd2 'arg1 arg2' arg3"),
    ("cmd1 'arg1' 'arg2' 'arg3' | cmd2 | cmd3 \"\\arg1'\"", 3, "cmd1 arg1 arg2 arg3 | cmd2 | cmd3 '\\arg1'\"'\"''"),
    ("cmd1 | cmd2 | cmd3 | cmd4 | cmd5", 5, "cmd1 | cmd2 | cmd3 | cmd4 | cmd5"),
))
def test_multiple_pipes(parser: Parser, formatter: Formatter, line: str, expected_cmd_count: int, expected_str: str, pipe_space_count: int):
    def check(_line):
        first_cmd = parser.parse(_line)
        assert first_cmd.next_command is None
        assert first_cmd.next_command_operator is None
        assert_descriptors(first_cmd)

        actual_cmd_count = 1
        cur_cmd = first_cmd.pipe_command
        while cur_cmd:
            actual_cmd_count += 1
            assert cur_cmd.next_command is None
            assert cur_cmd.next_command_operator is None
            assert_descriptors(cur_cmd)
            cur_cmd = cur_cmd.pipe_command

        assert actual_cmd_count == expected_cmd_count

        actual_str = formatter.format_statement(first_cmd)
        assert actual_str == expected_str

    if pipe_space_count < 0:
        check(line)
        return

    pipe_spaces = " " * pipe_space_count
    pipe_space_chars = pipe_spaces + "|" + pipe_spaces
    check(line.replace("| ", pipe_space_chars))
    check(line.replace(" |", pipe_space_chars))
    check(line.replace(" | ", pipe_space_chars))


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
        stmt_count = 0
        cmd_count = 0
        cur_cmd = first_cmd
        cur_pipe_cmd = first_cmd
        while cur_cmd:
            assert cur_cmd.next_command_operator is None
            assert_descriptors(cur_cmd)
            stmt_count += 1
            cmd_count += 1
            cur_pipe_cmd = cur_cmd.pipe_command
            while cur_pipe_cmd:
                assert cur_pipe_cmd.next_command is None
                assert cur_pipe_cmd.next_command_operator is None
                assert_descriptors(cur_pipe_cmd)
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
    assert_descriptors(first_cmd)
    formatted_statements = formatter.format_statements(first_cmd)
    assert "; ".join(formatted_statements) == line

    cur_cmd = first_cmd.next_command
    cmd_count = 1
    while cur_cmd:
        assert_descriptors(cur_cmd)
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
    "cmd1 >&",
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
