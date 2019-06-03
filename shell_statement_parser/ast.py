from dataclasses import dataclass, field
from shlex import quote as shlex_quote
from typing import Collection, List, Optional, Union


COMMAND_TYPE = Union['Command', 'NestedCommandList']
COMMANDBUILDER_TYPE = Union['CommandBuilder', 'NestedCommandListBuilder']


@dataclass(frozen=True)
class Word(object):
    word: str

    def __str__(self):
        return self.word


@dataclass(frozen=True)
class QuotedWord(Word):
    pass


@dataclass(frozen=True)
class File(object):
    name: str

    def __str__(self):
        return self.name


class Pipe(object):
    def __str__(self):
        return "|"


class RedirectionOutput(object):
    def __str__(self):
        return ">"

    def __repr__(self):
        return "<RedirectionOutput>"


class RedirectionAppend(object):
    def __str__(self):
        return ">>"

    def __repr__(self):
        return "<RedirectionAppend>"


class OperatorAnd(object):
    def __str__(self):
        return "&&"

    def __repr__(self):
        return "<OperatorAnd>"


class OperatorOr(object):
    def __str__(self):
        return "||"

    def __repr__(self):
        return "<OperatorOr>"


@dataclass(frozen=True)
class Command(object):
    command: Word
    args: Collection[Word] = field(default_factory=tuple)
    redirect_to: Optional[File] = None
    redirect_to_operator: Optional[Union[RedirectionOutput, RedirectionAppend]] = None
    pipe_command: Optional[COMMAND_TYPE] = None
    next_command: Optional[COMMAND_TYPE] = None
    next_command_operator: Union[None, OperatorAnd, OperatorOr] = None
    asynchronous: bool = False

    def __post_init__(self):
        if self.redirect_to and not self.redirect_to_operator:
            raise InvalidCommandDataException("Redirection file set, but no redirection operator set.")
        if not self.redirect_to and self.redirect_to_operator:
            raise InvalidCommandDataException("Redirection operator set, but no redirection file set.")
        if self.next_command_operator and not self.next_command:
            raise InvalidCommandDataException("Next command operator set, but no next command set.")

    @property
    def command_line(self) -> str:
        command_line = shlex_quote(str(self.command))
        if self.args:
            command_line += " " + " ".join((shlex_quote(str(arg)) for arg in self.args))
        if self.redirect_to:
            command_line += " " + str(self.redirect_to_operator) + " " + shlex_quote(str(self.redirect_to))
        return command_line

    def __str__(self):
        return self.command_line


class InvalidCommandDataException(Exception):
    pass


@dataclass(eq=False)
class CommandBuilder(object):
    words: List[Word] = field(default_factory=list)
    redirect_to: Optional[File] = None
    redirect_to_operator: Optional[Union[RedirectionOutput, RedirectionAppend]] = None
    pipe_command: Optional[COMMANDBUILDER_TYPE] = None
    next_command: Optional[COMMANDBUILDER_TYPE] = None
    next_command_operator: Union[None, OperatorAnd, OperatorOr] = None
    asynchronous: bool = False

    def create(self) -> Command:
        if len(self.words) == 0:
            raise CommandBuilderCreateException("No command words added.")
        elif len(self.words) == 1:
            command = self.words[0]
            args = tuple()
        else:
            command = self.words[0]
            args = tuple(self.words[1:])

        if self.pipe_command:
            pipe_command = self.pipe_command.create()
        else:
            pipe_command = None

        if self.next_command:
            next_command = self.next_command.create()
        else:
            next_command = None

        return Command(
            command=command,
            args=args,
            pipe_command=pipe_command,
            redirect_to=self.redirect_to,
            redirect_to_operator=self.redirect_to_operator,
            next_command=next_command,
            next_command_operator=self.next_command_operator,
            asynchronous=self.asynchronous,
        )


@dataclass(frozen=True)
class NestedCommandList(object):
    first_command: COMMAND_TYPE
    pipe_command: Optional[COMMAND_TYPE] = None
    redirect_to: Optional[str] = None
    redirect_to_operator: Optional[Union[RedirectionOutput, RedirectionAppend]] = None
    next_command: Optional[COMMAND_TYPE] = None
    next_command_operator: Union[None, OperatorAnd, OperatorOr] = None
    asynchronous: bool = False


class CommandBuilderCreateException(Exception):
    pass


__all__ = [
    "COMMAND_TYPE",
    "Word",
    "QuotedWord",
    "File",
    "Pipe",
    "RedirectionOutput",
    "RedirectionAppend",
    "OperatorAnd",
    "OperatorOr",
    "Command",
    "InvalidCommandDataException",
    "CommandBuilder",
    "CommandBuilderCreateException",
    "NestedCommandList",
]
