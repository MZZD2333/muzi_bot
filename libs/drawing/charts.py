import math
from dataclasses import dataclass
from typing import Sequence

from PIL import Image, ImageDraw, ImageFont


@dataclass
class ChartConfig:
    padding: int = 20
    padding_Top: int|None = None
    padding_Left: int|None = None
    padding_Right: int|None = None
    padding_Bottom: int|None = None

    border_width: int = 1
    border_Top_width: int|None = None
    border_Left_width: int|None = None
    border_Right_width: int|None = None
    border_Bottom_width: int|None = None
    border_color: tuple[int, int, int, int] = (0, 0, 0, 255)
    border_Top_color: tuple[int, int, int, int]|None = None
    border_Left_color: tuple[int, int, int, int]|None = None
    border_Right_color: tuple[int, int, int, int]|None = None
    border_Bottom_color: tuple[int, int, int, int]|None = None

    bgcolor: tuple[int, int, int, int] = (255, 255, 255, 0)
    fgcolor: tuple[int, int, int, int] = (0, 0, 0, 255)
    font_path: str|None = None

    # LineChart
    line_width: int = 2

    H_grid: bool = False
    V_grid: bool = False
    H_grid_color: tuple[int, int, int, int] = (0, 0, 0, 255)
    V_grid_color: tuple[int, int, int, int] = (0, 0, 0, 255)
    H_grid_div: int = 5
    H_grid_label_color: tuple[int, int, int, int]|None = None
    avg_line: bool = False
    avg_line_color: tuple[int, int, int, int] = (0, 0, 0, 255)


    def init(self):
        self.padding_Top = self.padding if self.padding_Top is None else self.padding_Top
        self.padding_Left = self.padding if self.padding_Left is None else self.padding_Left
        self.padding_Right = self.padding if self.padding_Right is None else self.padding_Right
        self.padding_Bottom = self.padding if self.padding_Bottom is None else self.padding_Bottom
        self.border_Top_width = self.border_width if self.border_Top_width is None else self.border_Top_width
        self.border_Left_width = self.border_width if self.border_Left_width is None else self.border_Left_width
        self.border_Right_width = self.border_width if self.border_Right_width is None else self.border_Right_width
        self.border_Bottom_width = self.border_width if self.border_Bottom_width is None else self.border_Bottom_width
        self.border_Top_color = self.border_color if self.border_Top_color is None else self.border_Top_color
        self.border_Left_color = self.border_color if self.border_Left_color is None else self.border_Left_color
        self.border_Right_color = self.border_color if self.border_Right_color is None else self.border_Right_color
        self.border_Bottom_color = self.border_color if self.border_Bottom_color is None else self.border_Bottom_color
        self.H_grid_label_color = (255-self.fgcolor[0], 255-self.fgcolor[1], 255-self.fgcolor[2], self.fgcolor[3]) if self.H_grid_label_color is None else self.H_grid_label_color

    def updata(self, kwargs):
        self.__dict__.update(kwargs)

class BaseChart:
    def __init__(self, width: int = 100, height: int = 100, config: ChartConfig|None = None, **kwargs) -> None:
        self.width = width
        self.height = height
        if config is None:
            self.config = ChartConfig(**kwargs)
        else:
            self.config = config
            config.updata(kwargs)
        self.config.init()
        
    def export(self) -> Image.Image:
        chart_width = self.width + self.config.padding_Left + self.config.padding_Right # type: ignore
        chart_height = self.height + self.config.padding_Top + self.config.padding_Bottom # type: ignore
        img = Image.new('RGBA', (chart_width, chart_height), self.config.bgcolor)
        draw = ImageDraw.Draw(img)

        self.draw(draw)

        if self.config.border_Top_width > 0: # type: ignore
            draw.line((self.config.padding_Left, self.config.padding_Top, chart_width-self.config.padding_Right, self.config.padding_Top), fill=self.config.border_Top_color, width=self.config.border_Top_width) # type: ignore
        if self.config.border_Left_width > 0: # type: ignore
            draw.line((self.config.padding_Left, self.config.padding_Top, self.config.padding_Left, chart_height-self.config.padding_Bottom), fill=self.config.border_Left_color, width=self.config.border_Left_width) # type: ignore
        if self.config.border_Right_width > 0: # type: ignore
            draw.line((chart_width-self.config.padding_Right, self.config.padding_Top, chart_width-self.config.padding_Right, chart_height-self.config.padding_Bottom), fill=self.config.border_Right_color, width=self.config.border_Right_width) # type: ignore
        if self.config.border_Bottom_width > 0: # type: ignore
            draw.line((self.config.padding_Left, chart_height-self.config.padding_Bottom, chart_width-self.config.padding_Right, chart_height-self.config.padding_Bottom), fill=self.config.border_Bottom_color, width=self.config.border_Bottom_width) # type: ignore
        
        return img
    
    def draw(self, draw: ImageDraw.ImageDraw):
        pass        

    @property
    def image(self) -> Image.Image:
        return self.export()


class LineChart(BaseChart):
    def __init__(self, Y_data: Sequence[float], X_data: Sequence[float]|None = None, width: int = 100, height: int = 100, **config) -> None:
        super().__init__(width, height, **config)
        dl = len(Y_data)
        if dl == 0:
            raise ValueError
        if X_data is None:
            self.X_data = list(range(dl))
        elif len(X_data) != dl:
            raise ValueError
        self.X_data = X_data
        self.Y_data = Y_data

    def draw(self, draw: ImageDraw.ImageDraw):
        dl = len(self.Y_data)
        mx = int(self.width/dl)
        my = int(self.height/self.config.H_grid_div)
        px = self.config.padding_Left
        py = self.config.padding_Top
        sx = int((self.width-(dl-1)*mx)/2)+px # type: ignore
        sy = int((self.height-(self.config.H_grid_div-1)*my)/2)+py # type: ignore
        ch = (self.config.H_grid_div-1)*my
        dmin = min(self.Y_data)
        dmax = max(self.Y_data)
        dy = dmax - dmin
        
        lw = self.config.line_width
        lw_1_2 = math.ceil(lw/2)
        lw_2_3 = math.ceil(lw*2/3)

        if self.config.V_grid:
            for i in range(dl):
                draw.line((sx+i*mx, py, sx+i*mx, py+self.height), fill=self.config.V_grid_color, width=lw_1_2) # type: ignore
        if self.config.H_grid:
            for i in range(self.config.H_grid_div):
                draw.line((px, sy+my*i, px+self.width, sy+my*i), fill=self.config.H_grid_color, width=lw_1_2) # type: ignore
        for i, y in enumerate(self.Y_data[:-1]):
            ddc = y-dmin
            ddn = self.Y_data[i+1]-dmin
            pc = ddc/dy if ddc != 0 else 0
            pn = ddn/dy if ddn != 0 else 0
            draw.line((sx+i*mx, sy+ch*(1-pc), sx+(i+1)*mx, sy+ch*(1-pn)), fill=self.config.fgcolor, width=lw)
        if self.config.avg_line:
            avg = sum(self.Y_data)/dl
            dda = avg-dmin
            pa = dda/dy if dda != 0 else 0
            draw.line((px, sy+ch*(1-pa), px+self.width, sy+ch*(1-pa)), fill=self.config.avg_line_color, width=lw_2_3) # type: ignore
        if self.config.font_path is not None:
            font = ImageFont.truetype(self.config.font_path, size=lw*5)
            for i in range(self.config.H_grid_div):
                draw.text((px+lw, sy+my*i-lw*5), f'{dmax-dy/self.config.H_grid_div*(i+1):.3f}', font=font, fill=self.config.H_grid_label_color) # type: ignore

__all__ = [
    'LineChart'
]