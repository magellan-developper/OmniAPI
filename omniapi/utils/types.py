from pathlib import Path
from typing import Optional, Union, Sequence

PathType = Optional[Union[str, Path]]

StringSequence = Union[str, Sequence[str]]
OptionalDictSequence = Optional[Union[Sequence[dict], dict]]
