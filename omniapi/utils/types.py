from pathlib import Path
from typing import Optional, Union, Sequence

numeric = Union[int, float]

PathType = Optional[Union[str, Path]]

StringSequence = Union[str, Sequence[str]]
OptionalDictSequence = Optional[Union[Sequence[dict], dict]]
