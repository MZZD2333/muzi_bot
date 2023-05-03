import math

from PIL import Image, ImageDraw

from ._typing import Color, ColorMode


class BaseGraph:

    def __init__(self, width: int = 100, height: int = 100, mode: ColorMode = 'RGBA', color: Color = (0, 0, 0, 255)) -> None:
        self.width = width
        self.height = height
        self.mode = mode
        self.color = color

    def export(self) -> Image.Image:
        return Image.new(self.mode, (self.width, self.height))

    @property
    def image(self) -> Image.Image:
        return self.export()


class Rectangle(BaseGraph):

    def __init__(self, width: int = 100, height: int = 100, mode: ColorMode = 'RGBA', color: Color = (0, 0, 0, 255), radius: int = 0) -> None:
        super().__init__(width, height, mode, color)
        self.radius = radius

    def export(self) -> Image.Image:
        img = Image.new(self.mode, (self.width, self.height))
        draw = ImageDraw.Draw(img)
        if self.radius:
            draw.rectangle((self.radius, 0, self.width-self.radius, self.height), fill=self.color)
            draw.rectangle((0, self.radius, self.width, self.height-self.radius), fill=self.color)
            draw.pieslice(((0, 0), (self.radius*2, self.radius*2)), start=180, end=270, fill=self.color)
            draw.pieslice(((self.width-self.radius*2, 0), (self.width, self.radius*2)), start=270, end=360, fill=self.color)
            draw.pieslice(((0, self.height-self.radius*2), (self.radius*2, self.height)), start= 90, end=180, fill=self.color)
            draw.pieslice(((self.width-self.radius*2, self.height-self.radius*2), (self.width, self.height)), start=0, end=90, fill=self.color)
        else:
            draw.rectangle((0, 0, self.width, self.height), fill=self.color)
        
        return img

class Ellipses(BaseGraph):
    def __init__(self, width: int = 100, height: int = 100, mode: ColorMode = 'RGBA', color: Color = (0, 0, 0, 255), ratio: float = 0, fill: Color = (0, 0, 0, 0)) -> None:
        super().__init__(width, height, mode, color)
        self.ratio = ratio
        self.fill = fill

        

    def export(self) -> Image.Image:
        img = Image.new(self.mode, (self.width, self.height))
        draw = ImageDraw.Draw(img)
        draw.ellipse((0, 0, self.width, self.height), fill=self.color)
        if self.ratio != 0:
            draw.ellipse((int(self.width*(1-self.ratio)/2), int(self.height*(1-self.ratio)/2), int(self.width*(1+self.ratio)/2), int(self.height*(1+self.ratio)/2)), self.fill)
        
        return img

class Sector(BaseGraph):
    
    def __init__(self, radius: int = 100, mode: ColorMode = 'RGBA', color: Color = (0, 0, 0, 255), deg: float = 270, start: float = 0, ratio: float = 0, fill: Color = (0, 0, 0, 0), corner: bool = False) -> None:
        super().__init__(2*radius, 2*radius, mode, color)
        self.radius = radius
        self.deg = deg
        self.start = start
        self.ratio = ratio
        self.fill = fill
        self.corner = corner

    def export(self) -> Image.Image:
        img = Image.new(self.mode, (self.width, self.height))
        draw = ImageDraw.Draw(img)
        if self.corner:
            r1 = self.radius*self.ratio
            r2 = (self.radius-r1)*0.5
            s_rad = math.radians(self.start)
            e_rad = math.radians(self.start+self.deg)
            x_s = self.radius+(r1+r2)*math.cos(s_rad)
            y_s = self.radius+(r1+r2)*math.sin(s_rad)
            x_e = self.radius+(r1+r2)*math.cos(e_rad)
            y_e = self.radius+(r1+r2)*math.sin(e_rad)
            draw.pieslice(((0, 0), (self.width, self.height)), start=self.start, end=self.start+self.deg, fill=self.color)
            draw.ellipse((x_s-r2, y_s-r2, x_s+r2, y_s+r2), fill=self.color)
            draw.ellipse((x_e-r2, y_e-r2, x_e+r2, y_e+r2), fill=self.color)
        else:
            draw.pieslice(((0, 0), (self.width, self.height)), start=self.start, end=self.start+self.deg, fill=self.color)
        if self.ratio != 0:
            draw.ellipse((int(self.width*(1-self.ratio)/2), int(self.height*(1-self.ratio)/2), int(self.width*(1+self.ratio)/2), int(self.height*(1+self.ratio)/2)), fill=self.fill)
        
        return img


__all__ = [
    'Rectangle',
    'Ellipses',
    'Sector'
]