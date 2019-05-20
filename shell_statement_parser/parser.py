from .ast import *


class Parser(object):
    def parse(self, statement: str) -> COMMAND_TYPE:
        statement_len = len(statement)
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

        def WRITE_CHAR(char):
            nonlocal cur_word
            cur_word += char

        def END_WORD():
            nonlocal cur_word, was_quote_mode, cur_command_words, cmd_builder, redirect_mode
            if redirect_mode:
                if not cur_word:
                    raise Exception(str(cur_command_words))
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
                    cmd_builder.words.append(cur_word)
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
        while pos < statement_len:
            char = statement[pos]

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
                    # TODO: Make sure there is at least one word
                    if redirect_mode and not cur_word:
                        raise Exception()

                    END_WORD()
                    END_CMDARGS()

                    END_STMT()

            elif char == ">":
                if prev_char == "\\":
                    WRITE_CHAR(char)
                else:
                    if redirect_mode:
                        raise Exception()

                    END_WORD()

                    next_char = statement[pos + 1]
                    if next_char == ">":
                        redirect_mode = ">>"
                        cur_command_words.append(">>")
                        pos += 1
                        next_char = statement[pos + 1]
                    else:
                        redirect_mode = ">"
                        cur_command_words.append(">")

                    while next_char in (" ", "\t"):
                        pos += 1
                        next_char = statement[pos + 1]

            elif char == "&":
                if prev_char == "\\":
                    WRITE_CHAR(char)
                else:
                    # TODO: Make sure there is at least one word
                    if redirect_mode and not cur_word:
                        raise Exception()

                    END_WORD()
                    END_CMDARGS()

                    next_char = statement[pos + 1]
                    if next_char == "&":
                        cmd_builder.next_command_operator = OperatorAnd()
                        pos += 1
                    else:
                        cmd_builder.asynchronous = True

                    END_STMT()

            elif char == "|":
                if prev_char == "\\":
                    WRITE_CHAR(char)
                else:
                    # TODO: Make sure there is at least one word
                    if redirect_mode and not cur_word:
                        raise Exception()

                    END_WORD()
                    END_CMDARGS()

                    next_char = statement[pos + 1]
                    if next_char == "|":
                        cmd_builder.next_command_operator = OperatorOr()
                        pos += 1
                        END_STMT()
                    else:
                        if pipe_prev_cmd_builder:
                            pipe_prev_cmd_builder.pipe_command = cmd_builder
                        pipe_prev_cmd_builder = cmd_builder
                        cmd_builder = CommandBuilder()

            elif char in (" ", "\t"):
                if prev_char == "\\":
                    WRITE_CHAR(char)
                else:
                    END_WORD()
                    was_quote_mode = False

            else:
                WRITE_CHAR(char)

            prev_char = char
            pos += 1

        END_WORD()
        END_CMDARGS()
        END_STMT()

        return tuple(commands), first_cmd_builder.create()
