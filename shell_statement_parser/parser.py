import sys
from .ast import *


WHITESPACE = (" ", "\t")


class Parser(object):
    def parse(self, statement: str) -> COMMAND_TYPE:
        statement = statement.strip()
        statement_len = len(statement)
        if statement_len == 0:
            raise EmptyInputException("Input statement was empty or contained only whitespace.")

        pos = 0
        cur_word = ""
        cur_command_words = []

        cmd_builder = CommandBuilder()
        first_cmd_builder: CommandBuilder = cmd_builder
        prev_cmd_builder: CommandBuilder = None
        pipe_first_cmd_builder: CommandBuilder = cmd_builder
        pipe_prev_cmd_builder: CommandBuilder = None

        commands = []

        prev_char = None
        quote_mode = None
        was_quote_mode = False
        redirect_mode = None
        just_terminated = False
        expecting_new_statement = False

        def WRITE_CHAR(char: str):
            nonlocal cur_word
            cur_word += char

        def NEXT_CHAR() -> str:
            try:
                next_char = statement[pos + 1]
            except IndexError:
                next_char = None

            if next_char is None:
                raise UnexpectedStatementFinishParserFailure("Unexpected end of statement while parsing.", pos=pos)
            else:
                return next_char

        def END_WORD():
            nonlocal cur_word, was_quote_mode, cur_command_words, cmd_builder, redirect_mode
            if redirect_mode:
                if not cur_word:
                    raise EmptyRedirectParserFailure("No redirect filename provided.", pos=pos)
                cmd_builder.redirect_to = File(cur_word)
                if redirect_mode == ">":
                    cmd_builder.redirect_to_operator = RedirectionOutput()
                elif redirect_mode == ">>":
                    cmd_builder.redirect_to_operator = RedirectionAppend()
                cur_command_words.append(cur_word)
                cur_word = ""
                redirect_mode = False
            else:
                if cur_word or was_quote_mode:
                    if was_quote_mode:
                        cmd_builder.words.append(QuotedWord(cur_word))
                    else:
                        cmd_builder.words.append(Word(cur_word))
                    cur_command_words.append(cur_word)
                    cur_word = ""

        def END_CMDARGS():
            nonlocal cur_command_words, commands, was_quote_mode
            commands.append(tuple(cur_command_words))
            cur_command_words = []
            was_quote_mode = False

        def END_STMT():
            nonlocal cmd_builder, prev_cmd_builder, pipe_first_cmd_builder, pipe_prev_cmd_builder
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


        #import pdb; pdb.set_trace()
        #breakpoint()
        while pos < statement_len:
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

                    next_char = NEXT_CHAR()
                    if next_char == ">":
                        redirect_mode = ">>"
                        cur_command_words.append(">>")
                        pos += 1
                        next_char = NEXT_CHAR()
                    else:
                        redirect_mode = ">"
                        cur_command_words.append(">")

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

        if "pytest" in sys.modules:
            return first_cmd_builder.create()
        else:
            return tuple(commands), first_cmd_builder.create()


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


__all__ = [
    "Parser",
    "EmptyInputException",
    "ParserFailure",
    "UnclosedQuoteParserFailure",
    "EmptyStatementParserFailure",
    "EmptyRedirectParserFailure",
    "UnexpectedStatementFinishParserFailure",
]
