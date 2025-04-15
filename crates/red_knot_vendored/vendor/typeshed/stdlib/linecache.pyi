from collections.abc import Callable
from typing import Any
from typing_extensions import TypeAlias

__all__ = ["getline", "clearcache", "checkcache", "lazycache"]

_ModuleGlobals: TypeAlias = dict[str, Any]
_ModuleMetadata: TypeAlias = tuple[int, float | None, list[str], str]

_SourceLoader: TypeAlias = tuple[Callable[[], str | None]]

cache: dict[str, _SourceLoader | _ModuleMetadata]  # undocumented

def getline(filename: str, lineno: int, module_globals: _ModuleGlobals | None = None) -> str: ...
def clearcache() -> None: ...
def getlines(filename: str, module_globals: _ModuleGlobals | None = None) -> list[str]: ...
def checkcache(filename: str | None = None) -> None: ...
def updatecache(filename: str, module_globals: _ModuleGlobals | None = None) -> list[str]: ...
def lazycache(filename: str, module_globals: _ModuleGlobals) -> bool: ...
