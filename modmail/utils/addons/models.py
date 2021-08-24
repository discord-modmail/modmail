from enum import Enum, auto
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from modmail.utils.addons.sources import AddonSource


class AddonType(Enum):
    """Supported addon types."""

    PLUGIN = auto()


class Addon:
    """Base class of an addon which make the bot extendable."""

    name: str
    description: Optional[str]
    source: AddonSource
    min_version: str

    def __init__(
        self,
        name: str,
        source: AddonSource,
        type: AddonType,
        description: str = None,
        min_version: str = None,
    ) -> None:
        self.name = name
        self.source = source
        self.description = description
        self.min_version = min_version
        self.type: AddonType = type
