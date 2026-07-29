"""
Minimal aifc compatibility shim for Python 3.14+.

SpeechRecognition imports ``aifc`` at module import time, but voice typing in this
application only uses live microphone capture rather than AIFF file parsing.
This shim provides the small surface area needed for the import to succeed.
"""

import wave

Error = wave.Error


def open(file, mode="rb"):
    return wave.open(file, mode)
