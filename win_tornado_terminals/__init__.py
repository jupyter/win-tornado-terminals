"""
This packages contains and implements a simple terminal server.

Creates virtual terminals via pexpect and websockets.
"""

from .manager import TermManager
from .websockets import MainSocket

VERSION_INFO = (0, 1, 0, 'dev0')
__version__ = '.'.join(map(str, VERSION_INFO))
