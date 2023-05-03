from PIL import Image

from .._typing import Color, ColorMode
from .coordinate import Coordinates
from .layer import Layer


class Canvas:

    __slots__ = ('width', 'height', 'mode', 'bgcolor', 'layers', '_image0')

    def __init__(self, image: Image.Image|None = None, width: int|None = None, height: int|None = None, mode: ColorMode = 'RGBA', bgcolor: Color|None = None):
        if image is None:
            self._image0 = None
            self.width = 100 if width is None else width
            self.height = 100 if height is None else height
        else:
            if image.mode != 'RGBA':
                image = image.convert('RGBA')
            self._image0 = image.copy()
            self.width = image.width
            self.height = image.height
        self.mode = mode
        self.bgcolor = bgcolor
        self.layers: list[Layer] = list()

    def export(self):
        if self._image0:
            IMAGE = self._image0
        else:
            if self.bgcolor is None:
                IMAGE = Image.new(self.mode, (self.width, self.height))
            else:
                IMAGE = Image.new(self.mode, (self.width, self.height), self.bgcolor)
        
        def draw_layer(layer: Layer):
            if layer.coord is not None:
                _coord = layer.coord
            elif layer.pos is not None:
                _coord = layer.pos.prase(self, layer)
            else:
                _coord = Coordinates((0, 0))
            if layer.move is not None:
                _coord += layer.move
            
            img = layer.img
            coord = _coord.value

            if layer.opacity < 1:
                img.putalpha(int(layer.opacity*255))
            if layer.mask is None:
                IMAGE.paste(img, coord, mask=img)
            else:
                sampled = IMAGE.crop(coord+(img.width+coord[0], img.height+coord[1]))
                if layer.apply is not None:
                    sampled = sampled.filter(layer.apply)
                sampled.paste(img, mask=img)
                IMAGE.paste(sampled, coord, mask=layer.mask)

        for layer in self.layers:
            if layer.img.mode != 'RGBA':
                layer.img = layer.img.convert('RGBA')
            draw_layer(layer)
        if IMAGE.mode != self.mode:
            return IMAGE.convert(self.mode)
        return IMAGE


    def add_layer(self, layer: 'Layer', layer_index: int|None = None):
        index = layer_index if not layer_index == None else len(self.layers)
        self.layers.insert(index, layer)

    def add_layers(self, layers: list['Layer'], insert_index: int|None = None):
        index = insert_index if not insert_index == None else len(self.layers)
        self.layers = self.layers[:index]+layers+self.layers[index:]

    def replace_layer(self, layer: 'Layer', layer_index: int) -> None:
        self.layers[layer_index] = layer
        

    @property
    def image(self):
        return self.export()
