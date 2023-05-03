from PIL import ImageFont


class Font:

    def __init__(self, fontfile_path: str) -> None:
        self.fontfile_path = fontfile_path
        self.size_16 = ImageFont.truetype(self.fontfile_path, size=14)
        self.size_18 = ImageFont.truetype(self.fontfile_path, size=18)
        self.size_24 = ImageFont.truetype(self.fontfile_path, size=24)
        self.size_32 = ImageFont.truetype(self.fontfile_path, size=32)
        self.size_36 = ImageFont.truetype(self.fontfile_path, size=36)
        self.size_48 = ImageFont.truetype(self.fontfile_path, size=48)
        self.size_64 = ImageFont.truetype(self.fontfile_path, size=64)

    def __getattr__(self, size: str):
        builtinsize = self.__dict__.get(size, None)
        if builtinsize:
            return builtinsize
        else:
            return ImageFont.truetype(self.fontfile_path, size=int(size.replace('size_', '')))


DEFAULT_1 = Font('./data/fonts/MicrosoftYaHei.ttc')
DEFAULT_2 = Font('./data/fonts/shaonv.ttf')