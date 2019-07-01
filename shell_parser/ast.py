from dataclasses import dataclass, field
from shlex import quote as shlex_quote
from types import MappingProxyType
from typing import Collection, Dict, List, Mapping, Optional, Union


COMMAND_TYPE = Union['Command', 'NestedCommandList']
COMMANDBUILDER_TYPE = Union['CommandBuilder', 'NestedCommandListBuilder']

DESCRIPTOR_DEFAULT_INDEX_STDIN = 0
DESCRIPTOR_DEFAULT_INDEX_STDOUT = 1
DESCRIPTOR_DEFAULT_INDEX_STDERR = 2


@dataclass(frozen=True)
class Word(object):
    word: str

    def __str__(self):
        return self.word

    def __repr__(self):
        return "<{0} word={1}>".format(
            self.__class__.__name__,
            self.word
        )


@dataclass(frozen=True)
class File(object):
    name: str

    def __str__(self):
        return self.name

    def __repr__(self):
        return "<{0} name={1}>".format(
            self.__class__.__name__,
            self.name
        )

    def duplicate(self) -> 'File':
        return File(name=self.name)


@dataclass(frozen=True)
class StdinTarget(object):
    def __str__(self):
        return "stdin"

    def __repr__(self):
        return "<StdinTarget>"


@dataclass(frozen=True)
class StdoutTarget(object):
    def __str__(self):
        return "stdout"

    def __repr__(self):
        return "<StdoutTarget>"


@dataclass(frozen=True)
class StderrTarget(object):
    def __str__(self):
        return "stderr"

    def __repr__(self):
        return "<StderrTarget>"


@dataclass(frozen=True)
class DefaultFile(object):
    target: Union[StdinTarget, StdoutTarget, StderrTarget]

    def __str__(self):
        return str(self.target)

    def __repr__(self):
        return "<DefaultFile target={0}>".format(self.target)

    def duplicate(self) -> 'DefaultFile':
        return DefaultFile(target=self.target)

    @property
    def is_stdin(self) -> bool:
        return isinstance(self.target, StdinTarget)

    @property
    def is_stdout(self) -> bool:
        return isinstance(self.target, StdoutTarget)

    @property
    def is_stderr(self) -> bool:
        return isinstance(self.target, StderrTarget)


@dataclass(frozen=True)
class RedirectionInput(object):
    def __str__(self):
        return "<"

    def __repr__(self):
        return "<RedirectionInput>"


@dataclass(frozen=True)
class RedirectionOutput(object):
    def __str__(self):
        return ">"

    def __repr__(self):
        return "<RedirectionOutput>"


@dataclass(frozen=True)
class RedirectionAppend(object):
    def __str__(self):
        return ">>"

    def __repr__(self):
        return "<RedirectionAppend>"


@dataclass(frozen=True)
class OperatorAnd(object):
    def __str__(self):
        return "&&"

    def __repr__(self):
        return "<OperatorAnd>"


@dataclass(frozen=True)
class OperatorOr(object):
    def __str__(self):
        return "||"

    def __repr__(self):
        return "<OperatorOr>"


@dataclass(frozen=True)
class DescriptorRead(object):
    pass


@dataclass(frozen=True)
class DescriptorWrite(object):
    pass


@dataclass(frozen=True)
class CommandDescriptorClosed(object):
    def duplicate(self) -> 'CommandDescriptorClosed':
        # There is no state to duplicate.
        return self


@dataclass(frozen=True)
class CommandFileDescriptor(object):
    target: Union[File, DefaultFile]
    operator: Union[RedirectionInput, RedirectionOutput, RedirectionAppend]

    def duplicate(self) -> 'CommandFileDescriptor':
        return CommandFileDescriptor(
            target=self.target.duplicate(),
            operator=self.operator,
        )

    @property
    def is_default_file(self) -> bool:
        return isinstance(self.target, DefaultFile)


@dataclass(frozen=True)
class CommandDescriptor(object):
    mode: Union[DescriptorRead, DescriptorWrite]
    descriptor: CommandFileDescriptor

    def __post_init__(self):
        if isinstance(self.mode, DescriptorRead):
            if not isinstance(self.descriptor.operator, RedirectionInput):
                raise InvalidDescriptorDataException()
        elif isinstance(self.mode, DescriptorWrite):
            if not isinstance(self.descriptor.operator, (RedirectionOutput, RedirectionAppend)):
                raise InvalidDescriptorDataException()
        else:
            raise InvalidDescriptorDataException()

    def duplicate(self) -> 'CommandDescriptor':
        return CommandDescriptor(
            mode=self.mode,
            descriptor=self.descriptor.duplicate(),
        )

    @property
    def for_reading(self) -> bool:
        return isinstance(self.mode, DescriptorRead)

    @property
    def for_writing(self) -> bool:
        return isinstance(self.mode, DescriptorWrite)


@dataclass(frozen=True)
class CommandDescriptors(object):
    descriptors: Mapping[int, Union[CommandDescriptor, CommandDescriptorClosed]]

    def __post_init__(self):
        for fd in self.descriptors.keys():
            if type(fd) is not int:
                raise InvalidFileDescriptorException("File descriptors must be integers")
            if fd < 0:
                raise InvalidFileDescriptorException("File descriptors must not be negative")

    @property
    def command_line(self) -> str:
        descriptors = self.descriptors
        fds = sorted(descriptors)
        args = []
        for fd in fds:
            if isinstance(descriptors[fd], CommandDescriptorClosed):
                if fd == DESCRIPTOR_DEFAULT_INDEX_STDOUT:
                    args.append(">&-")
                else:
                    args.append(str(fd) + ">&-")
                continue

            arg = ""
            if fd == DESCRIPTOR_DEFAULT_INDEX_STDIN:
                if descriptors[fd].descriptor.is_default_file and descriptors[fd].descriptor.target.is_stdin:
                    continue
                if not isinstance(descriptors[fd].mode, DescriptorRead):
                    arg += str(fd)
            elif fd == DESCRIPTOR_DEFAULT_INDEX_STDOUT:
                if descriptors[fd].descriptor.is_default_file and descriptors[fd].descriptor.target.is_stdout:
                    continue
                if not isinstance(descriptors[fd].mode, DescriptorWrite):
                    arg += str(fd)
            elif fd == DESCRIPTOR_DEFAULT_INDEX_STDERR:
                if descriptors[fd].descriptor.is_default_file and descriptors[fd].descriptor.target.is_stderr:
                    continue
                arg += str(fd)
            else:
                arg += str(fd)

            descriptor = descriptors[fd].descriptor
            arg += str(descriptor.operator) + " "

            target = descriptor.target
            if isinstance(target, DefaultFile):
                file_target = target.target
                if isinstance(file_target, StdinTarget):
                    file_arg = "/dev/stdin"
                elif isinstance(file_target, StdoutTarget):
                    file_arg = "/dev/stdout"
                elif isinstance(file_target, StderrTarget):
                    file_arg = "/dev/stderr"
                else:
                    raise Exception()
            else:
                file_arg = str(target)

            arg += shlex_quote(file_arg)
            args.append(arg)

        return " ".join(args)


@dataclass(frozen=True)
class Command(object):
    command: Word
    descriptors: CommandDescriptors
    args: Collection[Word] = field(default_factory=tuple)
    pipe_command: Optional[COMMAND_TYPE] = None
    next_command: Optional[COMMAND_TYPE] = None
    next_command_operator: Union[None, OperatorAnd, OperatorOr] = None
    asynchronous: bool = False

    def __post_init__(self):
        if self.next_command_operator and not self.next_command:
            raise InvalidCommandDataException("Next command operator set, but no next command set.")

    @property
    def command_line(self) -> str:
        command_line = shlex_quote(str(self.command))
        if self.args:
            command_line += " " + " ".join((shlex_quote(str(arg)) for arg in self.args))

        descriptors = self.descriptors.command_line
        if len(descriptors) > 0:
            command_line += " " + descriptors

        return command_line

    def __str__(self):
        return self.command_line


class InvalidCommandDataException(Exception):
    pass


@dataclass(eq=False)
class CommandDescriptorsBuilder(object):
    descriptors: Dict[int, Union[CommandDescriptor, CommandDescriptorClosed]] = field(default_factory=dict)

    def __post_init__(self):
        if DESCRIPTOR_DEFAULT_INDEX_STDIN not in self.descriptors:
            self.descriptors[DESCRIPTOR_DEFAULT_INDEX_STDIN] = CommandDescriptor(
                mode=DescriptorRead(),
                descriptor=CommandFileDescriptor(
                    target=DefaultFile(target=StdinTarget()),
                    operator=RedirectionInput()
                )
            )

        if DESCRIPTOR_DEFAULT_INDEX_STDOUT not in self.descriptors:
            self.descriptors[DESCRIPTOR_DEFAULT_INDEX_STDOUT] = CommandDescriptor(
                mode=DescriptorWrite(),
                descriptor=CommandFileDescriptor(
                    target=DefaultFile(target=StdoutTarget()),
                    operator=RedirectionOutput()
                )
            )

        if DESCRIPTOR_DEFAULT_INDEX_STDERR not in self.descriptors:
            self.descriptors[DESCRIPTOR_DEFAULT_INDEX_STDERR] = CommandDescriptor(
                mode=DescriptorWrite(),
                descriptor=CommandFileDescriptor(
                    target=DefaultFile(target=StderrTarget()),
                    operator=RedirectionOutput()
                )
            )

    def set_descriptor(self, fd: int, descriptor: CommandDescriptor):
        if fd < 0:
            raise InvalidFileDescriptorException("File descriptors cannot be negative")
        self.descriptors[fd] = descriptor

    def duplicate_descriptor(self, src_fd: int, dest_fd: int):
        if src_fd < 0 or dest_fd < 0:
            raise InvalidFileDescriptorException("File descriptors cannot be negative")
        success = False
        try:
            src_descriptor = self.descriptors[src_fd].duplicate()
            if isinstance(src_descriptor, CommandDescriptor):
                self.descriptors[dest_fd] = src_descriptor
                success = True
        except KeyError:
            pass

        if not success:
            raise BadFileDescriptorException("Bad file descriptor {0}".format(src_fd))

    def close_descriptor(self, fd: int):
        if fd < 0:
            raise InvalidFileDescriptorException("File descriptors cannot be negative")
        self.descriptors[fd] = CommandDescriptorClosed()

    def create(self) -> CommandDescriptors:
        return CommandDescriptors(descriptors=MappingProxyType(self.descriptors.copy()))


class BadFileDescriptorException(Exception):
    pass


class InvalidDescriptorDataException(Exception):
    pass


class InvalidFileDescriptorException(Exception):
    pass


@dataclass(eq=False)
class CommandBuilder(object):
    words: List[Word] = field(default_factory=list)
    descriptors: CommandDescriptorsBuilder = field(default_factory=CommandDescriptorsBuilder)
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
            descriptors=self.descriptors.create(),
            pipe_command=pipe_command,
            next_command=next_command,
            next_command_operator=self.next_command_operator,
            asynchronous=self.asynchronous,
        )


@dataclass(frozen=True)
class NestedCommandList(object):
    first_command: COMMAND_TYPE
    pipe_command: Optional[COMMAND_TYPE] = None
    next_command: Optional[COMMAND_TYPE] = None
    next_command_operator: Union[None, OperatorAnd, OperatorOr] = None
    asynchronous: bool = False


class CommandBuilderCreateException(Exception):
    pass


__all__ = [
    "COMMAND_TYPE",
    "DESCRIPTOR_DEFAULT_INDEX_STDIN",
    "DESCRIPTOR_DEFAULT_INDEX_STDOUT",
    "DESCRIPTOR_DEFAULT_INDEX_STDERR",
    "Word",
    "File",
    "StdinTarget",
    "StdoutTarget",
    "StderrTarget",
    "DefaultFile",
    "RedirectionInput",
    "RedirectionOutput",
    "RedirectionAppend",
    "OperatorAnd",
    "OperatorOr",
    "DescriptorRead",
    "DescriptorWrite",
    "CommandDescriptorClosed",
    "CommandFileDescriptor",
    "CommandDescriptor",
    "CommandDescriptors",
    "Command",
    "InvalidCommandDataException",
    "CommandDescriptorsBuilder",
    "BadFileDescriptorException",
    "InvalidDescriptorDataException",
    "InvalidFileDescriptorException",
    "CommandBuilder",
    "CommandBuilderCreateException",
    "NestedCommandList",
]
