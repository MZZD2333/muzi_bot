from typing import Callable

from .coordinate import Coordinates


class Position:
    def __init__(self, func: Callable[..., tuple[int, int]]) -> None:
        self.func = func

    def prase(self, canvas, layer):
        return Coordinates(self.func(canvas, layer))

CENTER = Position(lambda c, l: (int(0.5*(c.width-l.width)), int(0.5*(c.height-l.height))))
TOP_LEFT = Position(lambda c, l: (0, 0))
TOP_RIGHT = Position(lambda c, l: (c.width-l.width, 0))
TOP_MIDDLE = Position(lambda c, l: (int(0.5*(c.width-l.width)), 0))
BOTTOM_LEFT = Position(lambda c, l: (0, c.height-l.height))
BOTTOM_RIGHT = Position(lambda c, l: (c.width-l.width, c.height-l.height))
BOTTOM_MIDDLE = Position(lambda c, l: (int(0.5*(c.width-l.width)), c.height-l.height))
LEFT_MIDDLE = Position(lambda c, l: (0, int(0.5*(c.height-l.height))))
RIGHT_MIDDLE = Position(lambda c, l: (c.width-l.width, int(0.5*(c.height-l.height))))
