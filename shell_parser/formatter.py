from typing import Optional, Sequence

from .ast import Command


class Formatter(object):
    """
    The main formatter class, responsible for taking in :class:`Command`
    objects and converting them into their canonical string representation.
    """

    def format_statements(self, first_cmd: Command) -> Sequence[str]:
        """
        Converts a series of commands into their string representations.
        Adjoining statements connected by an operator (such as ``&&`` or
        ``||``) will be part of the same string. Adjoining statements
        connected by other terminators (such as ``;``) will be part of
        separate strings.

        :param first_cmd: The first command to be converted.
        :type first_cmd: Command
        :returns: The sequence of strings representing the sequence of
                  supplied commands.
        :rtype: Sequence[str]
        """

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

    def format_statement(self, first_cmd: Command) -> str:
        """
        Converts a single command into its string representation. If the
        command pipes its output into another command, these subsequent
        commands will be included.

        :param first_cmd: The command to be converted.
        :type first_cmd: Command
        :returns: The string form of the supplied command object.
        :rtype: str
        """

        statement = str(first_cmd)
        cur_pipe_cmd = first_cmd.pipe_command
        while cur_pipe_cmd is not None:
            statement += " | " + str(cur_pipe_cmd)
            cur_pipe_cmd = cur_pipe_cmd.pipe_command
        return statement
