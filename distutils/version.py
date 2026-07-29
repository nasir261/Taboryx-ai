"""
Compatibility shim for ``distutils.version``.
"""

import re
from functools import total_ordering


def _normalize_version(value):
    parts = []
    for token in re.split(r"[._+-]", str(value)):
        if token == "":
            continue
        if token.isdigit():
            parts.append((0, int(token)))
        else:
            parts.append((1, token.lower()))
    return tuple(parts)


@total_ordering
class LooseVersion:
    def __init__(self, version):
        self.version = str(version)
        self._normalized = _normalize_version(version)

    def __eq__(self, other):
        if not isinstance(other, LooseVersion):
            other = LooseVersion(other)
        return self._normalized == other._normalized

    def __lt__(self, other):
        if not isinstance(other, LooseVersion):
            other = LooseVersion(other)
        return self._normalized < other._normalized

    def __repr__(self):
        return f"LooseVersion ('{self.version}')"


class StrictVersion(LooseVersion):
    pass


__all__ = ["LooseVersion", "StrictVersion"]
