

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from .base import Base

class Help(Base):
    """
    Show version informations

    Usage: version [--short]

    Options:
        --short     Shows only Compose's version number.
    """
    # def __init__(self, options):
    #     self.option = options

    def run(self):
        print('Hello, Up world!')
        while True:
            print('in process')