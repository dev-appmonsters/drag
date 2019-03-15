from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import functools
import logging
import sys

from inspect import getmembers, isclass, getdoc
from docopt import docopt

from .commands.base import Base
from .command_parser import NoSuchCommand, DocoptDispatcher
from .. import __version__ as VERSION

from compose.cli import signals
from compose.cli import errors
from compose.cli.main import TopLevelCommand, setup_logging
from compose.cli.main import setup_console_handler, setup_parallel_logger, console_handler, log, parse_doc_section

from compose.service import OperationFailedError, BuildError, NeedsBuildError
from compose.cli.command import project_from_options
from compose.project import ProjectError, NoSuchService
from compose.cli.errors import UserError
from compose.config import ConfigurationError
from compose.progress_stream import StreamOutputError
from compose.errors import StreamParseError


def main():
    signals.ignore_sigpipe()
    try:
        command = dispatch()
        command()
    except (KeyboardInterrupt, signals.ShutdownException):
        log.error("Aborting.")
        sys.exit(1)
    except (UserError, NoSuchService, ConfigurationError,
            ProjectError, OperationFailedError) as e:
        log.error(e.msg)
        sys.exit(1)
    except BuildError as e:
        log.error("Service '%s' failed to build: %s" % (e.service.name, e.reason))
        sys.exit(1)
    except StreamOutputError as e:
        log.error(e)
        sys.exit(1)
    except NeedsBuildError as e:
        log.error("Service '%s' needs to be built, but --no-build was passed." % e.service.name)
        sys.exit(1)
    except NoSuchCommand as e:
        commands = "\n".join(parse_doc_section("commands:", getdoc(e.supercommand)))
        log.error("No such command: %s\n\n%s", e.command, commands)
        sys.exit(1)
    except (errors.ConnectionError, StreamParseError):
        sys.exit(1)


def dispatch():
    setup_logging()
    dispatcher = DocoptDispatcher(Base, {'options_first': True, 'version': VERSION})

    options, handler, command_options = dispatcher.parse(sys.argv[1:])
    setup_console_handler(console_handler,
                          options.get('--verbose'),
                          options.get('--no-ansi'),
                          options.get("--log-level"))
    setup_parallel_logger(options.get('--no-ansi'))
    if options.get('--no-ansi'):
        command_options['--no-color'] = True
    return functools.partial(perform_command, options, handler, command_options)


def perform_command(options, handler, command_options):
    if options['COMMAND'] in ('help', 'version'):
        # Skip looking up the compose file.
        handler(command_options).run()
        return

    project = project_from_options('.', options)
    command = handler(project=project, options=command_options)
    with errors.handle_connection_errors(project.client):
        command.run()

