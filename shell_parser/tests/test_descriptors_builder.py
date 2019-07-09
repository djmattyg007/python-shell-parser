import pytest

from dataclasses import FrozenInstanceError
import re

from shell_parser.ast import CommandDescriptorsBuilder, CommandDescriptor, CommandFileDescriptor, File
from shell_parser.ast import RedirectionOutput, DescriptorWrite
from shell_parser.ast import BadFileDescriptorException, InvalidFileDescriptorException
from shell_parser.ast import (
    DESCRIPTOR_DEFAULT_INDEX_STDIN, DESCRIPTOR_DEFAULT_INDEX_STDOUT, DESCRIPTOR_DEFAULT_INDEX_STDERR
)


DEFAULT_DESCRIPTOR_FDS = frozenset((
    DESCRIPTOR_DEFAULT_INDEX_STDIN,
    DESCRIPTOR_DEFAULT_INDEX_STDOUT,
    DESCRIPTOR_DEFAULT_INDEX_STDERR,
))


def make_match(msg: str) -> str:
    return "^" + re.escape(msg) + "$"


def test_default_init():
    builder = CommandDescriptorsBuilder()
    assert builder.descriptors.keys() == DEFAULT_DESCRIPTOR_FDS
    
    stdin = builder.descriptors[DESCRIPTOR_DEFAULT_INDEX_STDIN]
    assert stdin.for_reading == True
    assert stdin.for_writing == False
    assert stdin.descriptor.is_default_file == True
    assert stdin.descriptor.target.is_stdin == True
    assert stdin.descriptor.target.is_stdout == False
    assert stdin.descriptor.target.is_stderr == False

    stdout = builder.descriptors[DESCRIPTOR_DEFAULT_INDEX_STDOUT]
    assert stdout.for_reading == False
    assert stdout.for_writing == True
    assert stdout.descriptor.is_default_file == True
    assert stdout.descriptor.target.is_stdin == False
    assert stdout.descriptor.target.is_stdout == True
    assert stdout.descriptor.target.is_stderr == False

    stderr = builder.descriptors[DESCRIPTOR_DEFAULT_INDEX_STDERR]
    assert stderr.for_reading == False
    assert stderr.for_writing == True
    assert stderr.descriptor.is_default_file == True
    assert stderr.descriptor.target.is_stdin == False
    assert stderr.descriptor.target.is_stdout == False
    assert stderr.descriptor.target.is_stderr == True


@pytest.mark.parametrize("fds", (
    frozenset((0,)),
    frozenset((1,)),
    frozenset((2,)),
    frozenset((0, 1)),
    frozenset((0, 2)),
    frozenset((1, 2)),
    frozenset((0, 1, 2)),
))
def test_custom_init(fds):
    descriptors = dict()
    for fd in fds:
        descriptors[fd] = CommandDescriptor(
            mode=DescriptorWrite(),
            descriptor=CommandFileDescriptor(
                target=File("test{0}.txt".format(fd)),
                operator=RedirectionOutput(),
            )
        )

    builder = CommandDescriptorsBuilder(descriptors=descriptors)
    for fd in fds:
        assert builder.descriptors[fd].descriptor.is_default_file == False
        assert builder.descriptors[fd].descriptor.target.name == "test{0}.txt".format(fd)

    default_fds = DEFAULT_DESCRIPTOR_FDS - fds
    for fd in default_fds:
        assert builder.descriptors[fd].descriptor.is_default_file == True


def test_default_create():
    builder = CommandDescriptorsBuilder()
    descriptor_container = builder.create()
    with pytest.raises(FrozenInstanceError):
        descriptor_container.descriptors = {}


def test_non_equality():
    builder1 = CommandDescriptorsBuilder()
    builder2 = CommandDescriptorsBuilder()
    assert builder1 != builder2


@pytest.mark.parametrize("fd", (
    -1,
    -2,
    -100,
    -75,
))
def test_negative_descriptor_fds_set(fd: int):
    builder = CommandDescriptorsBuilder()
    with pytest.raises(InvalidFileDescriptorException, match=make_match("File descriptors cannot be negative")):
        descriptor = CommandDescriptor(
            mode=DescriptorWrite(),
            descriptor=CommandFileDescriptor(
                target=File(name="test.txt"),
                operator=RedirectionOutput(),
            )
        )
        builder.set_descriptor(fd, descriptor)


@pytest.mark.parametrize("src_fd,dest_fd", (
    (-1, 1),
    (1, -1),
    (-2, -3),
    (-100, 50),
    (200, -75),
))
def test_negative_descriptor_fds_duplicate(src_fd: int, dest_fd: int):
    builder = CommandDescriptorsBuilder()
    with pytest.raises(InvalidFileDescriptorException, match=make_match("File descriptors cannot be negative")):
        builder.duplicate_descriptor(src_fd, dest_fd)


@pytest.mark.parametrize("fd", (
    -1,
    -2,
    -100,
    -75,
))
def test_negative_descriptor_fds_close(fd: int):
    builder = CommandDescriptorsBuilder()
    with pytest.raises(InvalidFileDescriptorException, match=make_match("File descriptors cannot be negative")):
        builder.close_descriptor(fd)
