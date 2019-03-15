from __future__ import absolute_import
from __future__ import unicode_literals

from inspect import getmembers, isclass, getdoc

from docopt import docopt
from docopt import DocoptExit

from .commands import COMMANDS

def docopt_full_help(docstring, *args, **kwargs):
    try:
        return docopt(docstring, *args, **kwargs)
    except DocoptExit:
        raise SystemExit(docstring)


class DocoptDispatcher(object):

    def __init__(self, command_class, options):
        self.command_class = command_class
        self.options = options

    def parse(self, argv):
        command_help = getdoc(self.command_class)
        options = docopt_full_help(command_help, argv, **self.options)
        command = options['COMMAND']

        if command is None:
            raise SystemExit(command_help)

        handler = get_handler(self.command_class, command)
        docstring = getdoc(handler)

        if docstring is None:
            raise NoSuchCommand(command, self)

        command_options = docopt_full_help(docstring, options['ARGS'], options_first=True)
        return options, handler, command_options


def get_handler(command_class, command):
    command = command.replace('-', '_')
    # we certainly want to have "exec" command, since that's what docker client has
    # but in python exec is a keyword
    if command == "exec":
        command = "exec_command"

    if not COMMANDS.get(command, None):
        raise NoSuchCommand(command, command_class)

    return COMMANDS.get(command)


class NoSuchCommand(Exception):
    def __init__(self, command, supercommand):
        super(NoSuchCommand, self).__init__("No such command: %s" % command)

        self.command = command
        self.supercommand = supercommand
