"""The base command."""
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

class Base(object):
    """Define and run multi-container applications with Docker.

    Usage:
      drag [-f <arg>...] [options] [COMMAND] [ARGS...]
      drag -h|--help

    Options:
      -f, --file FILE             Specify an alternate compose file

    Commands:
      sync               Pull all images with git subtree hash
      version            Show the drag version information
    """

    def __init__(self, project, options=None):
        self.project = project
        self.options = options or {}

    def run(self, options):
        raise NotImplementedError('You must implement the run() method yourself!')
