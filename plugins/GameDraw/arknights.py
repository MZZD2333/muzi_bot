import asyncio
import json
import re
from pathlib import Path
from random import choice, choices

from httpx import AsyncClient
from lxml import etree
from PIL import Image

from libs.drawing import Canvas, Layer, position
from libs.fonts import DEFAULT_1
from muzi import get_bot

bot = get_bot()


PATH = Path(bot.config.data_path+'/game_draw/Arknights')

DATA = PATH/'data.json'
RESOURCE = PATH/'resource'
ROLES = RESOURCE/'roles'

RESOURCE.mkdir(exist_ok=True, parents=True)
ROLES.mkdir(exist_ok=True, parents=True)

NR = {

}

class Arknights:
    roles: dict[str, dict] = dict()
    role_6: list = list()
    role_5: list = list()
    role_4: list = list()
    role_3: list = list()
    role_up_6: list = list()
    role_up_5: list = list()
    role_up_4: list = list()
    role_up_x: list = list()

    enable: bool = True
    missing_file_info: list = list()

    _img_size: tuple[int, int] = (1920, 1080)
    img_scale: float = 0.533333

    def __init__(self, data: dict|None = None) -> None:
        if data:
            self.set(data)

    def set(self, data: dict[str, dict]):
        if pool_info := data.get('latest_pool', None):
            self.role_up_x = pool_info.get('x', list())
            self.role_up_6 = pool_info.get('6', list())
            self.role_up_5 = pool_info.get('5', list())
            self.role_up_4 = pool_info.get('4', list())
        if roles := data.get('roles', None):
            self.roles = roles
            for name in list(set(roles.keys())-set(self.role_up_x)-set(self.role_up_6)-set(self.role_up_5)-set(self.role_up_4)):
                info = roles[name]
                if '标准' not in info['approach']:
                    continue
                rarity = info['rarity']
                if rarity == '5':
                    self.role_6.append(name)
                elif rarity == '4':
                    self.role_5.append(name)
                elif rarity == '3':
                    self.role_4.append(name)
                elif rarity == '2':
                    self.role_3.append(name)
        else:
            self.enable = False

    def get_resource(self, role):
        bg_img = Image.open(RESOURCE/f'role_bg_{role[1]}.png').convert('RGBA')
        rarity_img = Image.open(RESOURCE/f'star_{role[1]}.png').convert('RGBA')
        if (role_img_path := ROLES/f'{role[0]}.png').is_file():
            role_img = Image.open(role_img_path).convert('RGBA')
        else:
            canvas = Canvas(width=360, height=180, bgcolor=(255, 255, 255, 255))
            canvas.add_layer(Layer.text(role[0], font=DEFAULT_1.size_32, lmt_height=40, pos=position.CENTER))
            role_img = canvas.image.transpose(4)
        if role[0] in self.roles:
            class_img = Image.open(RESOURCE/f"{self.roles[role[0]]['class']}.png").convert('RGBA')
        else:
            class_img = Image.open(RESOURCE/'未知.png').convert('RGBA')        
        return bg_img, role_img, class_img, rarity_img

    def image(self, result: list, length: int):
        bg = Image.open(RESOURCE/'bg.png').convert('RGBA') if (RESOURCE/'bg.png').is_file() else Image.new('RGBA', (1280, 720), (0, 0, 0, 255))
        if length <= 10:
            canvas = Canvas(bg)
            x_s = int((1920-length*182)/2)
            for i, role in enumerate(result):
                bg_img, role_img, class_img, rarity_img = self.get_resource(role)
                canvas.add_layer(Layer.image(bg_img, coord=(x_s+i*182, 80)))
                canvas.add_layer(Layer.image(role_img, coord=(x_s+i*182, 320)))
                canvas.add_layer(Layer.image(class_img, coord=(x_s+i*182+36, 640)))
                canvas.add_layer(Layer.image(rarity_img, coord=(x_s+i*182, 296)))
            canvas.add_layer(Layer.image(canvas.image))
            img = canvas.image
            return canvas.image.convert('RGB').resize((1024, 576))
        else:
            img = bg

        if self.img_scale < 1:
            return img.convert('RGB').resize((round(self._img_size[0]*self.img_scale), round(self._img_size[0]*self.img_scale)))
        else:
            return img.convert('RGB')


    def _draw_once(self, n: int = 0):
        if n > 50:
            k = n-50
            rarity = choices([6, 5, 4, 3], [0.02+k*0.02, 0.08, 0.5-k*0.005, 0.4-k*0.015])[0]
        else:
            rarity = choices([6, 5, 4, 3], [0.02, 0.08, 0.5, 0.4])[0]
        if rarity == 6:
            n = 0
        else:
            n += 1
        if rarity == 6:
            if self.role_up_x:
                role = choice(choices([self.role_up_x, self.role_up_6], [0.3, 0.7])[0])
            elif self.role_up_6:
                role = choice(choices([self.role_6, self.role_up_6], [0.5, 0.5])[0])
            else:
                role = choice(self.role_6)
        elif rarity == 5:
            if self.role_up_5:
                role = choice(choices([self.role_5, self.role_up_5], [0.5, 0.5])[0])
            else:
                role = choice(self.role_5)
        elif rarity == 4:
            if self.role_up_4:
                role = choice(choices([self.role_4, self.role_up_4], [0.8, 0.2])[0])
            else:
                role = choice(self.role_4)
        else:
            role = choice(self.role_3)

        return role, rarity, n
    
    def draw(self, times, n):
        result = list()
        for i in range(times):
            role, rarity, n = self._draw_once(n)
            result.append((role, rarity))
        return self.image(result, times), n


ARKNIGHTS = Arknights()


async def update_arknights():
    client = AsyncClient(timeout=10)
    game_data = json.loads(DATA.read_text(encoding='UTF-8')) if DATA.is_file() else dict()
    game_data_new = dict()
    # 获取最新卡池信息
    if (resp := await client.get('https://ak.hypergryph.com/news.html')).is_success:
        html = etree.HTML(resp.text, etree.HTMLParser(encoding='UTF-8'))
        hrefs = html.xpath('//ol[@class="articleList" and @data-category-key="ACTIVITY"]/li/a/@href')
        for url in ['https://ak.hypergryph.com'+n for n in hrefs[:6]]:
            if (res := await client.get(url)).is_success:
                doc = etree.HTML(res.text, etree.HTMLParser(encoding='UTF-8'))
                text = doc.xpath('string(//div[@class="article-content"])')
                if '寻访开启' not in text:
                    continue
                elif ol := re.findall(r'★{4,6}[：:]([^★]+)[（\(]占(\d)★出率的\d+%', text):
                    latest_pool = dict()
                    for t in ol:
                        latest_pool[t[1]] = t[0].replace('\\', '').replace('/', '').replace('[限定]', '').split()
                    if m :=re.search(r'\d+%.*★{6}[：:](.+)[（\(].*剩余出率.*5倍权值', text):
                        latest_pool['x'] = m.group(1).replace('\\', '').replace('/', '').replace('[限定]', '').split()
                    game_data_new['latest_pool'] = latest_pool
                    break
    # 获取干员信息
    if (resp := await client.get('https://prts.wiki/w/干员一览')).is_success:
        html = etree.HTML(resp.text, etree.HTMLParser(encoding='UTF-8'))
        divs = html.xpath('//div[@id="mw-content-text"]//div[@class="smwdata"]')
        roles_data = dict()
        for div in divs:
            data = div.attrib
            roles_data[data['data-cn']] = {
                'name_en': data['data-en'],
                'class': data['data-class'],
                'rarity': data['data-rarity'],
                'approach': data['data-approach'],
                'img_url': 'https:' + data['data-half'].replace('/thumb', '').split('.png')[0] + '.png'}
        game_data_new['roles'] = roles_data
    if game_data_new and game_data != game_data_new:
        DATA.write_text(json.dumps(game_data_new, indent=4, ensure_ascii=False), encoding='UTF-8')
    roles = game_data_new['roles']
    if missing := check_resource_Arknights(roles):
        async def task(url: str, name: str):
            if (resp := await client.get(url)).is_success:
                (ROLES/name).write_bytes(resp.content)
        for i in range(0, len(missing), 8):
            await asyncio.wait([task(roles[role]['img_url'], f'{role}.png') for role in missing[i: i+8]])
        missing_file = len(check_resource_Arknights(roles))
    
    return game_data

def check_resource_Arknights(roles: dict):
    return list(set(roles.keys())-set([p.stem for p in ROLES.rglob('*.png')]))

@bot.on_connect()
async def updata():
    data = await update_arknights()
    ARKNIGHTS.set(data)