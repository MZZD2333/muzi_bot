from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .._typing import Color
from .coordinate import Coordinates
from .position import Position


class Layer:

    __slots__ = ('img', 'mask', 'coord', 'pos', 'move', 'opacity', 'apply', 'width', 'height')

    def __init__(
        self,
        img: Image.Image, 
        mask: Image.Image|None,
        coord: Coordinates|None,
        pos: Position|None,
        move: tuple[int, int]|None,
        opacity: float,
        apply: ImageFilter.Filter|None
        ) -> None:

        self.img = img
        self.mask = mask
        self.coord = coord
        self.pos = pos
        self.move = move
        self.opacity = opacity
        self.apply = apply
        
        self.width = img.width
        self.height = img.height

    @staticmethod
    def text(
        text: str,
        font: ImageFont.FreeTypeFont,
        color: Color = (0, 0, 0),
        spacing: float = 4,
        lmt_width: int|None = None,
        lmt_height: int|None = None,
        mask: Image.Image|None = None,
        coord: tuple[int, int]|Coordinates|None = None,
        pos: Position|None = None,
        move: tuple[int, int]|None = None,
        opacity: float = 1,
        apply: ImageFilter.Filter|None = None
        ) -> 'Layer':
        
        if lmt_width is not None and lmt_height is not None:
            size = (lmt_width, lmt_height)
        else:
            _size = font.getsize_multiline(text, spacing=spacing)
            if lmt_width is not None:
                size = (lmt_width, _size[1])
            elif lmt_height is not None:
                size = (_size[0], lmt_height)
            else:
                size = _size
        img = Image.new('RGBA', size)
        draw = ImageDraw.Draw(img)
        draw.multiline_text((0, 0), text=text, font=font, spacing=spacing, fill=color)

        if isinstance(coord, tuple):
            coord = Coordinates(coord)
        
        return Layer(img, mask, coord, pos, move, opacity, apply)

    @staticmethod
    def image(
        img: Image.Image, 
        mask: Image.Image|None = None,
        coord: tuple[int, int]|Coordinates|None = None,
        pos: Position|None = None,
        move: tuple[int, int]|None = None,
        opacity: float = 1,
        apply: ImageFilter.Filter|None = None
        ) -> 'Layer':
        
        if isinstance(coord, tuple):
            coord = Coordinates(coord)
        
        return Layer(img, mask, coord, pos, move, opacity, apply)

