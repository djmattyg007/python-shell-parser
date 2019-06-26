import pytest

import re

from shell_parser.ast import CommandDescriptorsBuilder
from shell_parser.ast import BadFileDescriptorException, InvalidFileDescriptorException
from shell_parser.ast import DESCRIPTOR_DEFAULT_INDEX_STDIN, DESCRIPTOR_DEFAULT_INDEX_STDOUT, DESCRIPTOR_DEFAULT_INDEX_STDERR


DEFAULT_DESCRIPTOR_FDS = frozenset((
    DESCRIPTOR_DEFAULT_INDEX_STDIN,
    DESCRIPTOR_DEFAULT_INDEX_STDOUT,
    DESCRIPTOR_DEFAULT_INDEX_STDERR,
))


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
