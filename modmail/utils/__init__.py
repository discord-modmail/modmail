from typing import Any


class _MissingSentinel:
    def __eq__(self, other: Any):
        return False

    def __bool__(self):
        return False

    def __repr__(self):
        return "..."


MISSING: Any = _MissingSentinel()
