from typing import Literal, Union


Color = Union[tuple[int, int, int, int], tuple[int, int, int], int]

ColorMode = Literal['RGBA', 'RGB', 'L']
