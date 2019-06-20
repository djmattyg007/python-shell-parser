import os
from typing import Optional

from .ast import *


WHITESPACE = frozenset((" ", "\t"))
NUMBERS = frozenset((str(x) for x in range(0, 10)))


mydebug = None
def breaker():
    global mydebug
    return
    if mydebug is None:
        import pdb
        mydebug = pdb.Pdb()
        mydebug.rcLines = ['alias stats pp dict(((x, y) for x, y in locals().items() if not isinstance(y, CommandBuilder) and x != "self" and not callable(y)))']
    if os.environ.get("PYTHONBREAKPOINT", "") != "0":
        mydebug.set_trace()


def isdigit(s: str) -> bool:
    for char in s:
        if char not in NUMBERS:
            return False
    return True


class Parser(object):
    def parse(self, statement: str) -> COMMAND_TYPE:
        statement = statement.strip()
        statement_len = len(statement)
        if statement_len == 0:
            raise EmptyInputException("Input statement was empty or contained only whitespace.")

        pos = 0
        cur_word = ""

        cmd_builder = CommandBuilder()
        first_cmd_builder: CommandBuilder = cmd_builder
        prev_cmd_builder: CommandBuilder = None
        pipe_first_cmd_builder: CommandBuilder = cmd_builder
        pipe_prev_cmd_builder: CommandBuilder = None

        prev_char: str = None
        quote_mode: str = None
        was_quote_mode = False
        redirect_mode: str = None
        just_terminated = False
        expecting_new_statement = False
        current_descriptor: int = None
        modifying_descriptor = False

        def WRITE_CHAR(char: str):
            nonlocal cur_word
            cur_word += char

        def NEXT_CHAR(*, fail_if_end: bool = True) -> Optional[str]:
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
            breaker()
            if redirect_mode:
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
                        )
                    )
                    cmd_builder.descriptors.set_descriptor(current_descriptor, descriptor)

                cur_word = ""
                redirect_mode = False
                current_descriptor = None
                modifying_descriptor = False
            else:
                if cur_word or was_quote_mode:
                    if was_quote_mode:
                        cmd_builder.words.append(QuotedWord(cur_word))
                    else:
                        cmd_builder.words.append(Word(cur_word))
                    cur_word = ""

        def END_CMDARGS():
            nonlocal was_quote_mode
            was_quote_mode = False

        def END_STMT():
            nonlocal cmd_builder, prev_cmd_builder, pipe_first_cmd_builder, pipe_prev_cmd_builder
            breaker()
            if pipe_prev_cmd_builder:
                pipe_prev_cmd_builder.pipe_command = cmd_builder
                if prev_cmd_builder:
                    prev_cmd_builder.next_command = pipe_first_cmd_builder
                prev_cmd_builder = pipe_first_cmd_builder
            elif prev_cmd_builder:
                prev_cmd_builder.next_command = cmd_builder
                prev_cmd_builder = cmd_builder
            else:
                prev_cmd_builder = cmd_builder
            cmd_builder = CommandBuilder()
            pipe_first_cmd_builder = cmd_builder
            pipe_prev_cmd_builder = None


        while pos < statement_len:
            breaker()
            char = statement[pos]
            if just_terminated and char not in WHITESPACE:
                just_terminated = False
                expecting_new_statement = False

            if quote_mode == '"':
                if char == '"':
                    if prev_char == "\\":
                        cur_word += char
                    else:
                        quote_mode = None
                elif char == "\\":
                    pass
                else:
                    if prev_char == "\\":
                        if char not in ("\\", "$"):
                            cur_word += prev_char
                    cur_word += char
                prev_char = char
                pos += 1
                continue
            elif quote_mode == "'":
                if char == "'":
                    quote_mode = None
                else:
                    cur_word += char
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
                        raise EmptyStatementParserFailure("Statement terminator found without any preceding statement.", pos=pos)

                    END_WORD()
                    END_CMDARGS()

                    END_STMT()
                    just_terminated = True

            elif char == ">":
                if prev_char == "\\":
                    WRITE_CHAR(char)
                else:
                    if redirect_mode:
                        raise EmptyRedirectParserFailure("No redirect filename provided.", pos=pos)

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
                            raise InvalidRedirectionParserFailure("Cannot duplicate descriptor with append operator.", pos=pos)
                    else:
                        redirect_mode = ">"
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
                    # TODO: Make sure there is at least one word

                    END_WORD()
                    END_CMDARGS()

                    next_char = NEXT_CHAR()
                    if next_char == "&":
                        cmd_builder.next_command_operator = OperatorAnd()
                        pos += 1
                        expecting_new_statement = True
                    else:
                        cmd_builder.asynchronous = True

                    just_terminated = True
                    END_STMT()

            elif char == "|":
                if prev_char == "\\":
                    WRITE_CHAR(char)
                else:
                    # TODO: Make sure there is at least one word

                    END_WORD()
                    END_CMDARGS()

                    next_char = NEXT_CHAR()
                    if next_char == "|":
                        cmd_builder.next_command_operator = OperatorOr()
                        pos += 1
                        just_terminated = True
                        expecting_new_statement = True
                        END_STMT()
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
                elif not cur_word and not redirect_mode:
                    possible_descriptor = char
                    next_char = NEXT_CHAR(fail_if_end=False)
                    pos += 1
                    while True:
                        if next_char == ">":
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
    pass


class ParserFailure(Exception):
    def __init__(self, message: str, pos: int):
        super().__init__(message)
        self.pos = pos


class UnclosedQuoteParserFailure(ParserFailure):
    pass


class EmptyStatementParserFailure(ParserFailure):
    pass


class EmptyRedirectParserFailure(ParserFailure):
    pass


class UnexpectedStatementFinishParserFailure(ParserFailure):
    pass


class InvalidRedirectionParserFailure(ParserFailure):
    pass


class AmbiguousRedirectParserFailure(ParserFailure):
    pass


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
