from typing import  Union


class Coordinates:
    def __init__(self, coord: Union[tuple[int, int], 'Coordinates']):
        self.x = coord[0]
        self.y = coord[1]

    def __getitem__(self, index) -> int:
        return [self.x, self.y][index]

    def __invert__(self) -> 'Coordinates':
        self.x, self.y = self.y, self.x
        return self

    def __neg__(self) -> 'Coordinates':
        self.x = -self.x
        self.y = -self.y
        return self

    def __add__(self, coord) -> 'Coordinates':
        self.x = int(self.x+coord[0])
        self.y = int(self.y+coord[1])
        return self

    def __sub__(self, coord) -> 'Coordinates':
        self.x = int(self.x-coord[0])
        self.y = int(self.y-coord[1])
        return self

    def __mul__(self, coord) -> 'Coordinates':
        self.x = int(self.x*coord[0])
        self.y = int(self.y*coord[1])
        return self

    def __truediv__(self, coord) -> 'Coordinates':
        self.x = int(self.x/coord[0])
        self.y = int(self.y/coord[1])
        return self

    def __and__(self, coord) -> 'Coordinates':
        self.x = int((self.x+coord[0])/2)
        self.y = int((self.y+coord[1])/2)
        return self

    def __repr__(self) -> str:
        return f'Coordinates({self.x}, {self.y})'

    @property
    def value(self) -> tuple[int, int]:
        return (self.x, self.y)
