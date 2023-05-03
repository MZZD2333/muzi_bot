import asyncio
import random
import re
from pathlib import Path

from PIL import Image, ImageDraw

from libs.fonts import DEFAULT_1
from libs.PixivAPP import PIXIVAPP
from muzi import Bot, CQcode, Message, Trigger, get_bot
from muzi.event import GroupMessageEvent, MessageEvent, PrivateMessageEvent


# PIXIVAPP.set_download_proxy('i.pixiv.re')

def get_dir_size(path: Path):
    if path.is_file():
        return path.stat().st_size
    else:
        return sum(get_dir_size(p)for p in path.iterdir())

bot = get_bot()


icon_bookmark = Image.open(bot.config.data_path+'/icons/36px/bookmark.png')
icon_pid = Image.open(bot.config.data_path+'/icons/36px/pid.png')
icon_size = Image.open(bot.config.data_path+'/icons/36px/size.png')
icon_uid = Image.open(bot.config.data_path+'/icons/36px/uid.png')
icon_user  = Image.open(bot.config.data_path+'/icons/36px/user.png')
icon_view  = Image.open(bot.config.data_path+'/icons/36px/view.png')
bar_gradient = Image.open(bot.config.data_path+'/icons/bar.png')


SAVE_PATH = Path(bot.config.data_path+'/pixiv/imgs')
TEMP_PATH = Path(bot.config.data_path+'/pixiv/temp')
SAVE_PATH.mkdir(exist_ok=True, parents=True)
TEMP_PATH.mkdir(exist_ok=True, parents=True)

STORAGE_LIM = 1024*1024*1024*2
CURRENT_USE = get_dir_size(SAVE_PATH)
EXISTS_FILE = sorted([p for p in SAVE_PATH.iterdir()], key=lambda p: p.stat().st_mtime)

SINGLE_MAX_PAGES = 64

RISK = False

SUB_KEYWORD = {
    '-AI': '-AI -NovelAI -AI绘画 -AI绘图 -AIイラスト',
    'r18': 'R-18',
    'r-18': 'R-18',
}

COLOR_RGBA = [
    (255, 240, 245, 255), (174, 238, 238, 255), (250, 235, 215, 255), (255, 255, 204, 255), (193, 255, 193, 255),
    ( 64, 224, 208, 255), (230, 230, 250, 255), (135, 206, 250, 255), (202, 255, 112, 255), (255, 228, 225, 255),
    ]

class Args:
    text: str = ''
    origin: str = ''
    keywords: str = ''
    pages: int = 12
    show_detail: bool = False
    r18: bool = False
    private: bool = False
    friend: bool = False
    user_id: int = 0
    group_id: int = 0
    
    def __init__(self, text, event: MessageEvent|PrivateMessageEvent|GroupMessageEvent) -> None:
        self.origin = text
        self.user_id = event.user_id
        if isinstance(event, PrivateMessageEvent):
            self.private = True
            self.friend = event.sub_type == 'friend'
        else:
            self.group_id = event.group_id
        if page := re.search(r'(\d+)张', text):
            self.pages = int(page.group(1))
            text = re.sub(r'(\d+)张', '', text)
        if '#' in text:
            self.show_detail = True
            text = text.replace('#', '')
        for old, new in SUB_KEYWORD.items():
            text = re.sub(old, new, text, re.I)
        self.text = text

        if not re.search(r'[-\s]R-18', text):
            text += ' -R-18'
        elif re.search(r'\sR-18', text):
            self.r18 = True

        self.keywords = text
        
        self.pages = SINGLE_MAX_PAGES if self.pages>SINGLE_MAX_PAGES else self.pages

async def pixiv_login(trigger: Trigger, bot: Bot, args: Args):
    login_in = await PIXIVAPP.login(args.origin.strip())
    if login_in:
        url = PIXIVAPP.User.profile_image_urls['px_170x170']
        file_name = url.split('/')[-1]
        if not Path(SAVE_PATH / file_name).is_file():
            await PIXIVAPP._download(url, SAVE_PATH, file_name, timeout=10)
        img = Image.new('RGBA', (480, 210), random.choice(COLOR_RGBA))
        draw = ImageDraw.Draw(img)
        bar = Image.new('RGBA', (640, 40), [(0, 151, 250), (253, 158, 22)][PIXIVAPP.User.is_premium])
        img.paste(bar, (0, 0), mask=bar)
        if Path(SAVE_PATH / file_name).is_file():
            img.paste(Image.open(SAVE_PATH / file_name), (0, 40))
        _icon_user = icon_user.resize((24, 24))
        _icon_uid  = icon_uid.resize((24, 24))
        img.paste(_icon_user, (195,  74), mask=_icon_user)
        img.paste(_icon_uid , (195, 154), mask=_icon_uid )
        draw.text((230,  70), f'''{PIXIVAPP.User.name}   ''', font=DEFAULT_1.size_24, fill=(0, 0, 0))
        draw.text((230, 150), f'''{PIXIVAPP.User.id}     ''', font=DEFAULT_1.size_24, fill=(0, 0, 0))
        await trigger.send(Message(CQcode.image(img.convert('RGB'))))
    else:
        await trigger.send(Message('登陆失败'))

async def pixiv_search_illust(trigger: Trigger, bot: Bot, args: Args):
    data = await PIXIVAPP.search_illust(word=args.keywords.strip())
    illusts: list[dict] = data['illusts']
    illusts.extend(await _request_next_url(data['next_url'], int(24-256/(args.pages+16)), 'illusts'))
    await _send_thumbnail(trigger, _max_bookmarks_illusts(illusts, args.pages, 3))

async def pixiv_illust_detail(trigger: Trigger, bot: Bot, args: Args):
    data = [await PIXIVAPP.illust_detail(illust_id=int(i.strip())) for i in args.text.split()[:10]]
    illusts: list[dict] = [i['illust'] for i in data if i.get('illust', None)]
    await _send_illusts(trigger, bot, args, illusts)

async def pixiv_illust_new(trigger: Trigger, bot: Bot, args: Args):
    data = await PIXIVAPP.illust_new()
    illusts: list[dict] = data['illusts']
    illusts.extend(await _request_next_url(data['next_url'], int(24-256/(args.pages+16)), 'illusts'))
    await _send_thumbnail(trigger, _max_bookmarks_illusts(illusts, args.pages, 3))

async def pixiv_illust_ranking(trigger: Trigger, bot: Bot, args: Args):
    mode = {'日榜':'day', '日榜R18':'day_r18', '男性向':'day_male', '女性向':'day_female', '周榜':'week', '周榜R18':'week_r18', '原创':'week_original', '新人':'week_rookie', '月榜':'month'}.get(args.text.strip(), 'day')
    data = await PIXIVAPP.illust_ranking(mode=mode)
    illusts: list[dict] = data['illusts']
    await _send_thumbnail(trigger, _max_bookmarks_illusts(illusts, args.pages, 1))

async def pixiv_illust_recommended(trigger: Trigger, bot: Bot, args: Args):
    data = await PIXIVAPP.illust_recommended()
    illusts: list[dict] = data['illusts']
    illusts.extend(await _request_next_url(data['next_url'], int(24-256/(args.pages+16)), 'illusts'))
    await _send_thumbnail(trigger, _max_bookmarks_illusts(illusts, args.pages, 3))

async def pixiv_illust_related(trigger: Trigger, bot: Bot, args: Args):
    data = await PIXIVAPP.illust_detail(illust_id=int(args.text))
    if data.get('illust', None):
        data = await PIXIVAPP.illust_related(illust_id=int(args.text))
        illusts: list[dict] = data['illusts']
        illusts.extend(await _request_next_url(data['next_url'], int(24-256/(args.pages+16)), 'illusts'))
        await _send_thumbnail(trigger, _max_bookmarks_illusts(illusts, args.pages, 3))
    else:
        pass

async def pixiv_search_user(trigger: Trigger, bot: Bot, args: Args):
    data = await PIXIVAPP.search_user(word=args.keywords.strip())
    users: list[dict] = data['user_previews']
    await _send_users(trigger, users)

async def pixiv_user_bookmarks_illust(trigger: Trigger, bot: Bot, args: Args):
    data = await PIXIVAPP.user_bookmarks_illust(user_id=int(args.text.strip()))
    illusts: list[dict] = data['illusts']
    illusts.extend(await _request_next_url(data['next_url'], int(24-256/(args.pages+16)), 'illusts'))
    illusts = _fliter_tags(illusts, ['R-18']) if not args.r18 else illusts
    await _send_thumbnail(trigger, _max_bookmarks_illusts(illusts, args.pages, 3))

async def pixiv_user_illusts(trigger: Trigger, bot: Bot, args: Args):
    data = await PIXIVAPP.user_illusts(user_id=int(args.text.strip()))
    illusts: list[dict] = data['illusts']
    illusts.extend(await _request_next_url(data['next_url'], int(24-256/(args.pages+16)), 'illusts'))
    illusts = _fliter_tags(illusts, ['R-18']) if not args.r18 else illusts
    await _send_thumbnail(trigger, _max_bookmarks_illusts(illusts, args.pages, 3))

async def pixiv_user_related(trigger: Trigger, bot: Bot, args: Args):
    data = await PIXIVAPP.user_related(seed_user_id=int(args.text.strip()))
    users: list[dict] = data['user_previews']
    img = await _send_users(trigger, users)

def _max_bookmarks_illusts(illusts: list[dict], n: int = 10, rand: float = 2):
    length = len(illusts)
    n = n if n < length else length
    result = sorted(illusts, key=lambda d: d['total_view'] / (d['total_bookmarks'] + 1))[:int(n*rand)]
    random.shuffle(result)
    return result[:n]

def _fliter_tags(illusts: list[dict], fliter_tags: list[str] = []):
    _illusts: list[dict] = []
    for illust in illusts:
        tags = [tag['name'] for tag in illust['tags']]
        if not set(tags) & set(fliter_tags):
            _illusts.append(illust)
    return _illusts

def _clean(exceed: int):
    global CURRENT_USE, EXISTS_FILE
    size = 0
    while size < exceed:
        file = EXISTS_FILE.pop(0)
        size += file.stat().st_size
        file.unlink(missing_ok=True)
    CURRENT_USE -= size
    
async def _request_next_url(next_url: str, n: int, request_data: str):
    result: list[dict] = []
    for i in range(n):
        if not next_url:
            break
        await asyncio.sleep(0.2)
        try:
            resp = await PIXIVAPP.get(next_url, timeout=2)
            data = resp.json()
            result.extend(data[request_data])
            next_url = data['next_url']
        except:
            continue
    return result

async def _send_illusts(trigger: Trigger, bot: Bot, args: Args, illusts: list[dict]):
    global STORAGE_LIM, CURRENT_USE, EXISTS_FILE, RISK
    r18 = False
    _illusts: list[dict] = []
    download_illusts: list[dict] = []
    for illust in illusts:
        if illust['meta_single_page']:
            url = illust['meta_single_page']['original_image_url']
        elif illust['meta_pages']:
            url = illust['meta_pages'][0]['image_urls']['original']
        else:
            continue
        file_name = url.split('/')[-1]
        illust_info = {
            'id' : illust['id'],
            'url': url, 
            'file_name': file_name,
            'title': illust['title'],
            'tags': [tag['name'] for tag in illust['tags']],
            'user_id': illust['user']['id'],
            'user_name': illust['user']['name'],
            'view': illust['total_view'],
            'bookmarks': illust['total_bookmarks'],
        }
        if not Path(SAVE_PATH / file_name).is_file():
            download_illusts.append(illust_info)
        if 'R-18' in illust_info['tags']:
            r18 = True
        _illusts.append(illust_info)
    result = await PIXIVAPP.download([(illust['url'], SAVE_PATH, illust['file_name']) for illust in download_illusts], timeout=60)
    CURRENT_USE += sum(result)
    EXISTS_FILE.extend([SAVE_PATH / download_illusts[i]['file_name'] for i, size in enumerate(result) if size])
    if CURRENT_USE > STORAGE_LIM:
        _clean(CURRENT_USE-STORAGE_LIM)

    if args.friend or not r18:
        for illust in _illusts:
            if not Path(SAVE_PATH / illust['file_name']).is_file():
                continue
            detail = f'''画师: {illust['user_name']} ID: {illust['user_id']}\n作品 ID: {illust['id']}\nTags: ''' + ' '.join(illust['tags']) if args.show_detail else ''
            cqimg = CQcode.image(SAVE_PATH / illust['file_name'])
            try:
                if RISK:
                    await trigger.send(Message(cqimg))
                    if detail:
                        await trigger.send(Message(detail))
                else:
                    await trigger.send(Message(detail+cqimg))
            except Exception as e:
                RISK = True
                await trigger.send(Message(cqimg))
                if detail:
                    await trigger.send(Message(detail))
    else:
        # api = 'upload_private_file' if args.private else 'upload_group_file'
        # file_path = [Path(SAVE_PATH / i['file_name']) for i in _illusts if Path(SAVE_PATH / i['file_name']).is_file()]
        # if not args.private:
        #     info = await bot.call_api('get_group_file_system_info', group_id=args.group_id)
        #     if sum([p.stat().st_size for p in file_path])>int(info['total_space'])-int(info['used_space']):
        #         await trigger.done(Message('群文件剩余空间不足'))
        # zipfile_path = twice_zip(TEMP_PATH / f'{args.text}.zip', file_path)
        # await bot.call_api(api=api, group_id=args.group_id, file=zipfile_path.absolute().__str__(), name=f'{args.text}.zip')
        # zipfile_path.unlink(missing_ok=True)
        pass

async def _send_thumbnail(trigger: Trigger, illusts: list[dict]):
    global STORAGE_LIM, CURRENT_USE, EXISTS_FILE, COLOR_RGBA
    _illusts: list[dict] = []
    download_illusts: list[dict] = []
    for illust in illusts:
        url = illust['image_urls']['square_medium']
        file_name = url.split('/')[-1]
        info = {
            'id' : illust['id'],
            'url': url, 
            'file_name': file_name,
            'title': illust['title'],
            'tags': [tag['name'] for tag in illust['tags']],
            'user_id': illust['user']['id'],
            'user_name': illust['user']['name'],
            'view': illust['total_view'],
            'bookmarks': illust['total_bookmarks'],
            'size': f'''W: {illust['width']}px  H: {illust['height']}px''',
            'page_count': illust['page_count']
        }
        if not Path(SAVE_PATH / file_name).is_file():
            download_illusts.append(info)
        _illusts.append(info)
    result = await PIXIVAPP.download([(illust['url'], SAVE_PATH, illust['file_name']) for illust in download_illusts], timeout=60)
    CURRENT_USE += sum(result)
    EXISTS_FILE.extend([SAVE_PATH / download_illusts[i]['file_name'] for i, size in enumerate(result) if size])
    if CURRENT_USE > STORAGE_LIM:
        _clean(CURRENT_USE-STORAGE_LIM)

    illusts = [i for i in _illusts if Path(SAVE_PATH / i['file_name']).is_file()]
    count = len(illusts)
    img = Image.new('RGBA', (1080, 100+count*365), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)
    for i in range(5):
        draw.rectangle(((i*50, 0), ((i+1)*50, 100)), fill=random.choice(COLOR_RGBA))
    draw.text((360,  18), f'Pixiv illusts  > {count} <' , font=DEFAULT_1.size_48, fill=(  0,   0,   0))
    for row, info in enumerate(illusts):
        illust = Image.open(SAVE_PATH / info['file_name']).convert('RGBA')
        bar = Image.new('RGBA', (720, 360), random.choice(COLOR_RGBA))
        img.paste(illust       , (  0, 100+row*365    ), mask=illust       )
        img.paste(bar          , (360, 100+row*365    ), mask=bar          )
        img.paste(icon_bookmark, (650, 100+row*365+243), mask=icon_bookmark)
        img.paste(icon_size    , (400, 100+row*365+293), mask=icon_size    )
        img.paste(icon_pid     , (400, 100+row*365+ 93), mask=icon_pid     )
        img.paste(icon_uid     , (400, 100+row*365+193), mask=icon_uid     )
        img.paste(icon_user    , (400, 100+row*365+143), mask=icon_user    )
        img.paste(icon_view    , (400, 100+row*365+243), mask=icon_view    )
        draw.text((400, 100+row*365+ 30), f'''{info['title']}'''    , font=DEFAULT_1.size_36, fill=(  0,   0,   0))
        draw.text((450, 100+row*365+ 90), f'''{info['id']}'''       , font=DEFAULT_1.size_32, fill=(  0,   0,   0))
        draw.text((450, 100+row*365+140), f'''{info['user_name']}''', font=DEFAULT_1.size_32, fill=(  0,   0,   0))
        draw.text((450, 100+row*365+190), f'''{info['user_id']}'''  , font=DEFAULT_1.size_32, fill=(  0,   0,   0))
        draw.text((450, 100+row*365+240), f'''{info['view']}'''     , font=DEFAULT_1.size_32, fill=(120, 120, 120))
        draw.text((700, 100+row*365+240), f'''{info['bookmarks']}''', font=DEFAULT_1.size_32, fill=(120, 120, 120))
        draw.text((450, 100+row*365+290), f'''{info['size']}'''     , font=DEFAULT_1.size_32, fill=(120, 120, 120))
        if info['page_count'] > 1:
            img.paste(bar_gradient, (810, 100+row*365+300), mask=bar_gradient)
            draw.text((1030-len(str(info['page_count']))*30, 100+row*365+305), f'''{info['page_count']} P''', font=DEFAULT_1.size_36, fill=(120, 120, 120))

    await trigger.send(Message(CQcode.image(img.convert('RGB'))))

async def _send_users(trigger: Trigger, users: list[dict]):
    global CURRENT_USE, COLOR_RGBA
    some_users: list[dict] = []
    download_illusts: list[dict] = []
    get_filename = lambda url: url.split('/')[-1] if url else ''
    for user in users[:4]:
        avatar_url = user['user']['profile_image_urls'].get('medium', '')
        illusts_url = [i['image_urls'].get('square_medium', '') for i in user.get('illusts', []) if i['type'] == 'illust'][:3]
        file_info = [{'url': url, 'file_name': get_filename(url)} for url in [avatar_url]+illusts_url if url]
        for i in file_info:
            if not Path(SAVE_PATH / i['file_name']).is_file():
                download_illusts.append(i)
        some_users.append({'id': user['user']['id'], 'name': user['user']['name'], 'account': user['user']['account'], 'avatar': get_filename(avatar_url), 'illusts': [get_filename(url) for url in illusts_url]})
    result = await PIXIVAPP.download([(illust['url'], SAVE_PATH, illust['file_name']) for illust in download_illusts], timeout=60)
    CURRENT_USE += sum(result)
    EXISTS_FILE.extend([SAVE_PATH / download_illusts[i]['file_name'] for i, size in enumerate(result) if size])
    if CURRENT_USE > STORAGE_LIM:
        _clean(CURRENT_USE-STORAGE_LIM)

    img = Image.new('RGBA', (1080, 100+480*len(some_users)), (255, 255, 255, 255))
    bar_1 = Image.new('RGBA', (1080,  85), (255, 255, 255, 167))
    draw = ImageDraw.Draw(img)
    for i in range(5):
        draw.rectangle(((i*50, 0), ((i+1)*50, 100)), fill=random.choice(COLOR_RGBA))
    draw.text((400,  27), f'Pixiv User  > {len(some_users)} <' , font=DEFAULT_1.size_36, fill=(  0,   0,   0))
    for row, user in enumerate(some_users):
        if user['avatar']:
            avatar = Image.open(SAVE_PATH / user['avatar']).convert('RGBA')
        else:
            avatar = Image.new('RGBA', (170, 170), (255, 255, 255, 255))
        for col, filename in enumerate(user['illusts']):
            path = Path(SAVE_PATH / filename)
            if path.is_file():
                illust = Image.open(path).convert('RGBA')
            else:
                illust = Image.new('RGBA', (360, 360), (232, 232, 232, 255))
            img.paste(illust, (col*360, 100+row*480), mask=illust)
        bar_2 = Image.new('RGBA', (1080, 115), random.choice(COLOR_RGBA))
        img.paste(bar_1    , (  0, 100+row*480+275), mask=bar_1    )
        img.paste(bar_2    , (  0, 100+row*480+360), mask=bar_2    )
        img.paste(avatar   , (  0, 100+row*480+275), mask=avatar   )
        img.paste(icon_user, (200, 100+row*480+378), mask=icon_user)
        img.paste(icon_uid , (200, 100+row*480+428), mask=icon_uid )
        draw.text((250, 100+row*480+370), f'''{user['name']}    ''', font=DEFAULT_1.size_36, fill=(  0,   0,   0))
        draw.text((600, 100+row*480+425), f'''@{user['account']}''', font=DEFAULT_1.size_32, fill=(120, 120, 120))
        draw.text((250, 100+row*480+425), f'''{user['id']}      ''', font=DEFAULT_1.size_32, fill=(  0,   0,   0))
    
    await trigger.send(Message(CQcode.image(img.convert('RGB'))))

def get_plugin_status():
    status = {
        'available': PIXIVAPP.login_in,
        'risk': RISK,
        'config': {
            'storage_limit': STORAGE_LIM,
            'storage': CURRENT_USE
        }
    }
    return status

__all__ = [
    'Args',
    'get_plugin_status',
    'pixiv_login',
    'pixiv_search_illust',
    'pixiv_illust_detail',
    'pixiv_illust_new',
    'pixiv_illust_ranking',
    'pixiv_illust_recommended',
    'pixiv_illust_related',
    'pixiv_search_user',
    'pixiv_user_bookmarks_illust',
    'pixiv_user_illusts',
    'pixiv_user_related'
]