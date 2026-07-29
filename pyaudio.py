"""
Compatibility shim so libraries expecting ``pyaudio`` can use ``pyaudiowpatch``.
"""

from pyaudiowpatch import *  # noqa: F401,F403
from pyaudiowpatch import __version__  # noqa: F401
