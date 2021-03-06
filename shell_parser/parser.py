from typing import Optional

from .ast import Word, File
from .ast import RedirectionInput, RedirectionOutput, RedirectionAppend, OperatorAnd, OperatorOr
from .ast import DescriptorRead, DescriptorWrite, CommandFileDescriptor, CommandDescriptor
from .ast import Command, CommandBuilder


WHITESPACE = frozenset((" ", "\t"))
NUMBERS = frozenset(("0", "1", "2", "3", "4", "5", "6", "7", "8", "9"))


def isdigit(s: str) -> bool:
    for char in s:
        if char not in NUMBERS:
            return False
    return True


class Parser(object):
    """
    The main parser class, responsible for taking in the command line string
    and outputting the command AST.
    """

    def parse(self, statement: str) -> Command:
        """
        Parses the command line string.

        :param statement: The full command-line string to be parsed.
        :type statement: str
        :returns: A fully processed Command AST object.
        :rtype: Command
        """

        statement = statement.strip()
        statement_len = len(statement)
        if statement_len == 0:
            raise EmptyInputException("Input statement was empty or contained only whitespace.")

        pos = 0
        cur_word = ""

        cmd_builder = CommandBuilder()
        first_cmd_builder: CommandBuilder = cmd_builder
        prev_cmd_builder: Optional[CommandBuilder] = None
        pipe_first_cmd_builder: CommandBuilder = cmd_builder
        pipe_prev_cmd_builder: Optional[CommandBuilder] = None

        prev_char: Optional[str] = None
        quote_mode: Optional[str] = None
        was_quote_mode = False
        redirect_mode: Optional[str] = None
        just_terminated = False
        expecting_new_statement = False
        current_descriptor: Optional[int] = None
        modifying_descriptor = False

        def WRITE_CHAR(char: str):
            nonlocal cur_word
            cur_word += char

        def NEXT_CHAR(*, fail_if_end: bool = True) -> Optional[str]:
            next_char: Optional[str]
            try:
                next_char = statement[pos + 1]
            except IndexError:
                next_char = None

            if next_char is None and fail_if_end:
                raise UnexpectedStatementFinishParserFailure("Unexpected end of statement while parsing.", pos=pos)
            else:
                return next_char

        def END_WORD():
            nonlocal cur_word, was_quote_mode, cmd_builder, redirect_mode, current_descriptor, modifying_descriptor
            if redirect_mode is not None:
                if not cur_word:
                    raise EmptyRedirectParserFailure("No redirect filename provided.", pos=pos)
                if redirect_mode == "<":
                    descriptor_mode = DescriptorRead()
                    redirect_operator = RedirectionInput()
                elif redirect_mode == ">":
                    descriptor_mode = DescriptorWrite()
                    redirect_operator = RedirectionOutput()
                elif redirect_mode == ">>":
                    descriptor_mode = DescriptorWrite()
                    redirect_operator = RedirectionAppend()
                if modifying_descriptor:
                    if cur_word == "-":
                        cmd_builder.descriptors.close_descriptor(current_descriptor)
                    elif isdigit(cur_word):
                        cmd_builder.descriptors.duplicate_descriptor(int(cur_word), current_descriptor)
                    else:
                        raise AmbiguousRedirectParserFailure("", pos=pos)
                else:
                    descriptor = CommandDescriptor(
                        mode=descriptor_mode,
                        descriptor=CommandFileDescriptor(
                            target=File(cur_word),
                            operator=redirect_operator,
                        ),
                    )
                    cmd_builder.descriptors.set_descriptor(current_descriptor, descriptor)

                cur_word = ""
                redirect_mode = None
                current_descriptor = None
                modifying_descriptor = False
            else:
                if cur_word or was_quote_mode:
                    cmd_builder.words.append(Word(cur_word))
                    cur_word = ""

        def END_CMDARGS():
            nonlocal was_quote_mode
            was_quote_mode = False

        def END_STMT():
            nonlocal cmd_builder, prev_cmd_builder, pipe_first_cmd_builder, pipe_prev_cmd_builder
            if pipe_prev_cmd_builder is not None:
                pipe_prev_cmd_builder.pipe_command = cmd_builder
                if prev_cmd_builder:
                    prev_cmd_builder.next_command = pipe_first_cmd_builder
                prev_cmd_builder = pipe_first_cmd_builder
            elif prev_cmd_builder is not None:
                prev_cmd_builder.next_command = cmd_builder
                prev_cmd_builder = cmd_builder
            else:
                prev_cmd_builder = cmd_builder
            cmd_builder = CommandBuilder()
            pipe_first_cmd_builder = cmd_builder
            pipe_prev_cmd_builder = None

        while pos < statement_len:
            char = statement[pos]
            if just_terminated and char not in WHITESPACE:
                just_terminated = False
                expecting_new_statement = False

            if quote_mode == '"':
                if char == '"':
                    if prev_char == "\\":
                        WRITE_CHAR(char)
                    else:
                        quote_mode = None
                elif char == "\\":
                    pass
                else:
                    if prev_char == "\\":
                        if char not in ("\\", "$"):
                            WRITE_CHAR(prev_char)
                    WRITE_CHAR(char)
                prev_char = char
                pos += 1
                continue
            elif quote_mode == "'":
                if char == "'":
                    quote_mode = None
                else:
                    WRITE_CHAR(char)
                prev_char = char
                pos += 1
                continue

            if char == '"' or char == "'":
                if prev_char == "\\":
                    WRITE_CHAR(char)
                else:
                    quote_mode = char
                    was_quote_mode = True

            elif char == "\\":
                if prev_char == "\\":
                    WRITE_CHAR(char)

            elif char == ";":
                if prev_char == "\\":
                    WRITE_CHAR(char)
                else:
                    if len(cmd_builder.words) == 0 and not cur_word:
                        raise EmptyStatementParserFailure(
                            "Statement terminator found without any preceding statement.",
                            pos=pos,
                        )

                    END_WORD()
                    END_CMDARGS()

                    END_STMT()
                    just_terminated = True

            elif char == ">":
                if prev_char == "\\":
                    WRITE_CHAR(char)
                else:
                    if redirect_mode is not None and not cur_word:
                        raise EmptyRedirectParserFailure(
                            "No redirect filename provided.",
                            pos=pos,
                        )

                    END_WORD()
                    was_quote_mode = False

                    if current_descriptor is None:
                        current_descriptor = 1

                    next_char = NEXT_CHAR()
                    if next_char == ">":
                        redirect_mode = ">>"
                        pos += 1
                        next_char = NEXT_CHAR()
                        if next_char == "&":
                            raise InvalidRedirectionParserFailure(
                                "Cannot duplicate descriptor with append operator.",
                                pos=pos,
                            )
                    else:
                        redirect_mode = ">"
                        if next_char == "&":
                            modifying_descriptor = True
                            pos += 1
                            next_char = NEXT_CHAR()

                    while next_char in WHITESPACE:
                        pos += 1
                        next_char = NEXT_CHAR()

            elif char == "<":
                if prev_char == "\\":
                    WRITE_CHAR(char)
                else:
                    if redirect_mode is not None:
                        raise EmptyRedirectParserFailure(
                            "No redirect filename provided.",
                            pos=pos,
                        )

                    END_WORD()
                    was_quote_mode = False

                    if current_descriptor is None:
                        current_descriptor = 0

                    redirect_mode = "<"
                    next_char = NEXT_CHAR()
                    if next_char == "&":
                        modifying_descriptor = True
                        pos += 1
                        next_char = NEXT_CHAR()

                    while next_char in WHITESPACE:
                        pos += 1
                        next_char = NEXT_CHAR()

            elif char == "&":
                if prev_char == "\\":
                    WRITE_CHAR(char)
                else:
                    if len(cmd_builder.words) == 0 and not cur_word:
                        raise EmptyStatementParserFailure(
                            "Statement terminator found without any preceding statement.",
                            pos=pos,
                        )

                    END_WORD()
                    END_CMDARGS()

                    next_char = NEXT_CHAR()
                    if next_char == "&":
                        pipe_first_cmd_builder.next_command_operator = OperatorAnd()
                        pos += 1
                        expecting_new_statement = True
                    else:
                        cmd_builder.asynchronous = True

                    END_STMT()
                    just_terminated = True

            elif char == "|":
                if prev_char == "\\":
                    WRITE_CHAR(char)
                else:
                    if len(cmd_builder.words) == 0 and not cur_word:
                        raise EmptyStatementParserFailure(
                            "Statement terminator found without any preceding statement.",
                            pos=pos,
                        )

                    END_WORD()
                    END_CMDARGS()

                    next_char = NEXT_CHAR()
                    if next_char == "|":
                        pipe_first_cmd_builder.next_command_operator = OperatorOr()
                        pos += 1
                        END_STMT()
                        just_terminated = True
                        expecting_new_statement = True
                    else:
                        if pipe_prev_cmd_builder:
                            pipe_prev_cmd_builder.pipe_command = cmd_builder
                        pipe_prev_cmd_builder = cmd_builder
                        cmd_builder = CommandBuilder()

            elif char == "-":
                if prev_char == "\\":
                    WRITE_CHAR(char)
                elif modifying_descriptor and not cur_word:
                    WRITE_CHAR(char)
                    END_WORD()
                else:
                    WRITE_CHAR(char)

            elif char in NUMBERS:
                if prev_char == "\\":
                    WRITE_CHAR(char)
                elif not cur_word and redirect_mode is None:
                    possible_descriptor = char
                    next_char = NEXT_CHAR(fail_if_end=False)
                    pos += 1
                    while True:
                        if next_char == ">" or next_char == "<":
                            current_descriptor = int(possible_descriptor)
                            break
                        elif next_char in NUMBERS:
                            possible_descriptor += next_char
                        else:
                            WRITE_CHAR(possible_descriptor)
                            break
                        next_char = NEXT_CHAR(fail_if_end=False)
                        pos += 1
                    continue
                else:
                    WRITE_CHAR(char)

            elif char in WHITESPACE:
                if prev_char == "\\":
                    WRITE_CHAR(char)
                else:
                    END_WORD()
                    was_quote_mode = False

            else:
                WRITE_CHAR(char)

            prev_char = char
            pos += 1

        if quote_mode:
            raise UnclosedQuoteParserFailure("End of statement reached with open quote.", pos=pos)

        if just_terminated:
            if expecting_new_statement:
                raise EmptyStatementParserFailure("Follow-on statement not found.", pos=pos)
        else:
            END_WORD()
            END_CMDARGS()
            END_STMT()

        return first_cmd_builder.create()


class EmptyInputException(Exception):
    """
    Raised by the :class:`Parser` class :func:`~Parser.parse()` if the
    ``statement`` input is an empty string, or contains only whitespace.
    """


class ParserFailure(Exception):
    """
    A base class for all failures that can occur during the parsing process,
    typically as the result of a syntax issue in the command-line statement.
    """

    def __init__(self, message: str, pos: int):
        """
        A custom constructor that accepts the position at which the parsing
        failure occurred.

        :param message: The usual exception message parameter accepted by the
                        base class.
        :type message: str
        :param pos: The string index representing the position where the parsing
                    failure was detected.
        :type pos: int
        """
        super().__init__(message)
        self.pos = pos


class UnclosedQuoteParserFailure(ParserFailure):
    """
    Raised by the parser if the end of the input string is reached and a
    quoted string is still open.
    """


class EmptyStatementParserFailure(ParserFailure):
    """
    Raised by the parser if a statement terminator (eg ``;``, ``&``, ``|``)
    is found, and there are no words in that statement. This can also be
    raised if the end of the input string is reached and the same conditions
    apply.
    """


class EmptyRedirectParserFailure(ParserFailure):
    """
    Raised by the parser when a statement terminator or redirection operator
    is found, but the parser was expecting to find a redirection target. This
    can also be raised if the end of the input string is reached and the same
    conditions apply.
    """


class UnexpectedStatementFinishParserFailure(ParserFailure):
    """
    Raised by the parser when the input parsed so far necessitates at least
    one more character to be present in the input string, but the end of the
    input string has been reached.
    """


class InvalidRedirectionParserFailure(ParserFailure):
    """
    Raised by the parser when a redirection operator has been used in an
    incorrect manner. At the moment, it is only raised when attempting to
    duplicate a descriptor with the append redirect operator (``>>``).
    """


class AmbiguousRedirectParserFailure(ParserFailure):
    """
    Raised by the parser when there is an attempt to duplicate a descriptor,
    but the parser is unable to sensibly determine which descriptor should be
    duplicated.
    """


__all__ = [
    "Parser",
    "EmptyInputException",
    "ParserFailure",
    "UnclosedQuoteParserFailure",
    "EmptyStatementParserFailure",
    "EmptyRedirectParserFailure",
    "UnexpectedStatementFinishParserFailure",
    "InvalidRedirectionParserFailure",
    "AmbiguousRedirectParserFailure",
]
