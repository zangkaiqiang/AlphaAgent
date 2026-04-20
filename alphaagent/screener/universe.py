"""Universe abstractions: where the candidate symbols come from.

Three implementations:
- ``StaticUniverse``: a fixed list from yaml.
- ``AkshareIndexUniverse``: current index components via akshare (free,
  has survivorship bias).
- ``TushareIndexUniverse``: historical monthly snapshots via tushare's
  ``index_weight`` (planned for v2; raises NotImplementedError now).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date


class Universe(ABC):
    """Stock pool. ``get_symbols`` returns the pool as of a given date."""

    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def get_symbols(self, as_of: date) -> list[str]: ...


class StaticUniverse(Universe):
    """Fixed list of symbols, ignores ``as_of``."""

    def __init__(self, symbols: list[str], name: str = "static"):
        if not symbols:
            raise ValueError("StaticUniverse requires at least one symbol")
        self._symbols = list(symbols)
        self._name = name

    def name(self) -> str:
        return self._name

    def get_symbols(self, as_of: date) -> list[str]:
        return list(self._symbols)


class AkshareIndexUniverse(Universe):
    """Current components of an A-share index via akshare.

    ``index_code`` examples: "000300" (CSI 300), "000016" (SSE 50),
    "000905" (CSI 500), "000852" (CSI 1000).

    NOTE: returns the *current* component list for any ``as_of`` — has
    survivorship bias. For historical-accurate components, use
    ``TushareIndexUniverse`` (v2).
    """

    def __init__(self, index_code: str):
        self._index_code = index_code

    def name(self) -> str:
        return f"akshare_index:{self._index_code}"

    def get_symbols(self, as_of: date) -> list[str]:
        import akshare as ak

        df = ak.index_stock_cons_csindex(symbol=self._index_code)
        col = "成分券代码" if "成分券代码" in df.columns else "code"
        return [str(s).zfill(6) for s in df[col].tolist()]


class TushareIndexUniverse(Universe):
    """Historical monthly index components via tushare ``index_weight``.

    Requires Tushare 2000 points. Planned for v2.
    """

    def __init__(self, index_code: str):
        self._index_code = index_code

    def name(self) -> str:
        return f"tushare_index:{self._index_code}"

    def get_symbols(self, as_of: date) -> list[str]:
        raise NotImplementedError(
            "TushareIndexUniverse requires Tushare 2000 points; planned for v2. "
            "Use AkshareIndexUniverse for now (current components, has survivorship bias)."
        )
