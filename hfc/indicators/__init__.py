from .fcs import FCSIndicator
from .rcsi import rCSIIndicator
from .hdds import HDDSIndicator
from .demo import DemoIndicator
from .housing import HousingIndicator
from .lcs import LCSIndicator
from .hhexp import HHExpFIndicator, HHExpNF1MIndicator, HHExpNF6MIndicator
from .timing import TimingIndicator

_REGISTRY = {
    "FCS":      FCSIndicator,
    "rCSI":     rCSIIndicator,
    "HDDS":     HDDSIndicator,
    "Demo":     DemoIndicator,
    "Housing":  HousingIndicator,
    "LCS":      LCSIndicator,
    "HHExpF":   HHExpFIndicator,
    "HHExpNF1M": HHExpNF1MIndicator,
    "HHExpNF6M": HHExpNF6MIndicator,
    "Timing":   TimingIndicator,
}


def get_indicator_class(name: str):
    cls = _REGISTRY.get(name)
    if cls is None:
        raise KeyError(f"Unknown indicator '{name}'. Available: {list(_REGISTRY)}")
    return cls
