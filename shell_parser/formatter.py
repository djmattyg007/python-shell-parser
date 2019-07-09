from typing import Optional, Sequence

from .ast import *


class Formatter(object):
    def format_statement(self, first_cmd: Command) -> str:
        statement = str(first_cmd)
        cur_pipe_cmd = first_cmd.pipe_command
        while cur_pipe_cmd is not None:
            statement += " | " + str(cur_pipe_cmd)
            cur_pipe_cmd = cur_pipe_cmd.pipe_command
        return statement

    def format_statements(self, first_cmd: Command) -> Sequence[str]:
        statements = []
        cmd: Optional[Command] = first_cmd
        while cmd:
            if cmd.next_command_operator is not None:
                cur_cmd = cmd
                statement = ""
                while cur_cmd.next_command_operator is not None:
                    statement += self.format_statement(cur_cmd)
                    statement += " " + str(cur_cmd.next_command_operator) + " "
                    cur_cmd = cur_cmd.next_command
                statement += self.format_statement(cur_cmd)
                cmd = cur_cmd.next_command
            else:
                statement = self.format_statement(cmd)
                cmd = cmd.next_command

            statements.append(statement)
        return tuple(statements)
