import asyncio
import os
import re
from collections import deque
from datetime import datetime
from pathlib import Path
from random import choice

import httpx
import psutil
from PIL import Image, ImageFilter

from libs.drawing import Canvas, Layer, LineChart, Rectangle, Sector, position
from libs.fonts import DEFAULT_1, DEFAULT_2
from muzi import Bot, CQcode, get_bot, on_regex
from muzi.condition import SUPERUSER
from muzi.event import GroupMessageEvent, MessageEvent
from muzi.plugin import Plugin, Trigger

bot = get_bot()

BG_IMAGE_PATH = Path(bot.config.data_path+'/backgrounds')
BG_IMAGE_PATH.mkdir(parents=True, exist_ok=True)

INTERVAL = 3

BOT_PROCESS = psutil.Process(os.getpid())
BOT_STARTUP = BOT_PROCESS.create_time()

MEM_USAGE = deque([.0]*40, maxlen=40)
CPU_PERCENT = deque([.0]*40, maxlen=40)


helper = on_regex(r'^(菜单|帮助|help)\s*(?P<pid>\d+)?', flags=re.I, priority=1, block=True)
admin = on_regex(r'^#\s*(?P<cmd>\S+)\s*(?P<arg>.+)?', condition=SUPERUSER, flags=re.I, priority=1, block=True)


@helper.excute()
async def e_helper(bot: Bot, event: MessageEvent, data: dict):
    pid = data['matched_groupdict']['pid']
    await f_help(pid, False, bot, event, helper)

@admin.excute()
async def e_admin(bot: Bot, event: MessageEvent, data: dict):
    cmd = data['matched_groupdict']['cmd']
    arg = data['matched_groupdict']['arg']
    match cmd:
        case 'help':
            await f_help(arg, True, bot, event, admin)
        case 'plugin':
            await f_plugin(arg, bot, event, admin)
        case 'status'|'state'|'状态':
            await f_status(bot, admin)
        case 'reboot'|'重启':
            await f_reboot(arg, bot, event)
        
async def f_help(arg, superuser: bool, bot: Bot, event: MessageEvent, trigger: Trigger):
    if superuser:
        plugins = bot.plugins
    else:
        plugins = [p for p in bot.plugins if p.enable and not p.metadata.hide]
    if arg is not None:
        if arg.isdigit():
            plugin_id = int(arg)
            if 0 < plugin_id <= len(bot.plugins):
                await trigger.done(CQcode.image(draw_usage(plugins[plugin_id-1])))
            await trigger.done(f'插件[{plugin_id}]不存在')
        await trigger.done(f'不合法的插件id[{arg}]请使用数字表示插件id')
    await trigger.done(CQcode.image(draw_plugins(plugins, event, superuser)))

async def f_plugin(arg, bot: Bot, event: MessageEvent, trigger: Trigger):
    arg = arg if arg is not None else ''
    if match_ := re.search(r'(?P<cmd>\S+)\s*(?P<pid>.+)?', arg):
        data = match_.groupdict()
        cmd = data['cmd']
        pid = data['pid']
        tpid = [p.metadata.name for p in bot.plugins].index(PLUGIN_NAME)
        pct = len(bot.plugins)
        if pid is None:
            await trigger.done(f'缺少插件id')
        if 'all' in pid:
            pids = list(range(pct))
        else:
            pids = list(map(lambda i: int(i)-1, filter(lambda i: i.isdigit() and 0<=int(pid)-1<pct, pid.split())))
        if not pids:
            await trigger.done('请使用数字或者all表示插件id')
        if tpid in pids:
            pids.remove(tpid)

        match cmd:
            case 'disable':
                if not pids:
                    await trigger.send(f'muzi的基础功能依赖于此插件[{PLUGIN_NAME}] 此插件不支持{cmd}操作')
                for i in pids:
                    bot.plugins[i].disable()
            case 'enable':
                for i in pids:
                    bot.plugins[i].disable(False)
            case 'reload':
                for i in pids:
                    bot.plugins[i].reload()
            case None:
                await trigger.done(CQcode.image(draw_plugins(bot.plugins, event, True)))
    else:
        await trigger.done(CQcode.image(draw_plugins(bot.plugins, event, True)))

async def f_status(bot: Bot, trigger: Trigger):
    layer_1_cont = Rectangle(width=1020, height=1860, color=(0, 0, 0, 24), radius=24).image
    layer_1_mask = Rectangle(width=1020, height=1860, color=255, radius=24, mode='L').image
    bar_bg_1 = Rectangle(width=960, height=60, color=(255, 255, 255, 191), radius=12).image
    bar_bg_2 = Rectangle(width=477, height=60, color=(255, 255, 255, 191), radius=12).image
    bg = random_background((1080, 1920))
    canvas = Canvas(width=1080, height=1920)
    layer_0 = Layer.image(bg, pos=position.CENTER)
    layer_1 = Layer.image(layer_1_cont, coord=(30, 30), apply=ImageFilter.GaussianBlur(6), mask=layer_1_mask)
    canvas.add_layers([layer_0, layer_1])

    title_layer = Canvas(Rectangle(width=960, height=120, color=(255, 255, 255, 191), radius=12).image)
    title_layer.add_layer(Layer.text('状态监测', font=DEFAULT_2.size_64, lmt_height=64, pos=position.CENTER))
    canvas.add_layer(Layer.image(title_layer.image, coord=(60, 60)))

    color = [(49, 225, 247, 207), (40, 223, 153, 207), (255, 217, 61, 207), (253, 180, 75, 207), (255, 109, 96, 207), (177, 175, 255, 207), (68, 142, 246, 207), (117, 113, 121, 207)]
    storge = Canvas(Rectangle(width=960, height=508, color=(255, 255, 255, 191), radius=12).image)
    consumption = storge_consumption()
    total = sum([t[1] for t in consumption])
    start_deg = -90
    for i, t in enumerate(consumption[:7]):
        deg = t[1]/total*360
        storge.add_layer(Layer.image(Sector(radius=210, color=color[i], ratio=0.75, start=start_deg, deg=deg).image, pos=position.LEFT_MIDDLE, move=(44, 0)))
        storge.add_layer(Layer.image(Rectangle(width=90, height=180, color=color[i], radius=40).image.resize((18, 36)), coord=(513, 40+i*56)))
        storge.add_layer(Layer.text(t[0], font=DEFAULT_1.size_24, lmt_width=180, lmt_height=32, move=(543, 40+i*56)))
        storge.add_layer(Layer.text(get_storge(t[1]), font=DEFAULT_1.size_24, lmt_height=32, pos=position.TOP_RIGHT, move=(-20, 40+i*56)))
        start_deg += deg
    if len(consumption) > 7 or len(consumption) == 0:
        storge.add_layer(Layer.image(Sector(radius=210, color=color[-1], ratio=0.75, start=start_deg, deg=270-start_deg).image, pos=position.LEFT_MIDDLE, move=(44, 0)))
        storge.add_layer(Layer.image(Rectangle(width=90, height=180, color=color[-1], radius=40).image.resize((18, 36)), coord=(513, 432)))
        storge.add_layer(Layer.text('其他文件', font=DEFAULT_1.size_24, lmt_height=32, move=(543, 432)))
        storge.add_layer(Layer.text(get_storge(sum([t[1] for t in consumption[7:]])), font=DEFAULT_1.size_24, lmt_height=32, pos=position.TOP_RIGHT, move=(-20, 432)))
    storge.add_layer(Layer.text('已用存储', font=DEFAULT_1.size_36, lmt_height=48, pos=position.LEFT_MIDDLE, move=(184, -30)))
    storge.add_layer(Layer.text(get_storge(total), font=DEFAULT_1.size_32, lmt_height=40, pos=position.RIGHT_MIDDLE, move=(-628, 30)))
    canvas.add_layer(Layer.image(storge.image, coord=(60, 210)))

    groups = await bot.get_group_list()
    friends = await bot.get_friend_list()
    friend = Canvas(bar_bg_2)
    friend.add_layer(Layer.text('好友数', font=DEFAULT_1.size_32, lmt_height=40, pos=position.LEFT_MIDDLE, move=(20, 0)))
    friend.add_layer(Layer.text(f'{len(friends)}', font=DEFAULT_1.size_32, lmt_height=40, pos=position.RIGHT_MIDDLE, move=(-20, 0)))
    group = Canvas(bar_bg_2)
    group.add_layer(Layer.text('群聊数', font=DEFAULT_1.size_32, lmt_height=40, pos=position.LEFT_MIDDLE, move=(20, 0)))
    group.add_layer(Layer.text(f'{len(groups)}' , font=DEFAULT_1.size_32, lmt_height=40, pos=position.RIGHT_MIDDLE, move=(-20, 0)))
    canvas.add_layers([Layer.image(friend.image, coord=(60, 724)), Layer.image(group.image, coord=(543, 724))])

    plugin = Canvas(bar_bg_1)
    icon_1 = Rectangle(width=36, height=36, radius=12, color=( 87, 213,  85, 207)).image
    icon_2 = Rectangle(width=36, height=36, radius=12, color=(255, 140,  63, 207)).image
    icon_3 = Rectangle(width=36, height=36, radius=12, color=(241,  27,  27, 207)).image
    status = [0, 0, 0]
    for p in bot.plugins:
        if not p.enable or not p.metadata.available:
            status[2] += 1
        elif p.metadata.risk:
            status[1] += 1
        else:
            status[0] += 1
    plugin.add_layer(Layer.text('插件', font=DEFAULT_1.size_32, lmt_height=40, pos=position.LEFT_MIDDLE, move=(20, 0)))
    plugin.add_layer(Layer.text(f'{status[0]}', font=DEFAULT_1.size_32, lmt_height=40, pos=position.RIGHT_MIDDLE, move=(-260, 0)))
    plugin.add_layer(Layer.text(f'{status[1]}', font=DEFAULT_1.size_32, lmt_height=40, pos=position.RIGHT_MIDDLE, move=(-140, 0)))
    plugin.add_layer(Layer.text(f'{status[2]}', font=DEFAULT_1.size_32, lmt_height=40, pos=position.RIGHT_MIDDLE, move=( -20, 0)))
    plugin.add_layer(Layer.image(icon_1, coord=(600, 12)))
    plugin.add_layer(Layer.image(icon_2, coord=(720, 12)))
    plugin.add_layer(Layer.image(icon_3, coord=(840, 12)))
    canvas.add_layer(Layer.image(plugin.image, coord=(60, 790)))

    date = Canvas(bar_bg_1)
    date.add_layer(Layer.text('运行时长', font=DEFAULT_1.size_32, lmt_height=40, pos=position.LEFT_MIDDLE, move=(20, 0)))
    date.add_layer(Layer.text(str(datetime.now()-bot.bootdate)[:-7], font=DEFAULT_1.size_32, lmt_height=40, pos=position.RIGHT_MIDDLE, move=(-20, 0)))
    canvas.add_layer(Layer.image(date.image, coord=(60, 856)))

    chart_mask = Rectangle(width=960, height=400, color=255, radius=12, mode='L').image
    config = {
        'bgcolor': (255, 255, 255, 191),
        'padding_Top': 0,
        'padding_Left': 120,
        'padding_Right': 120,
        'padding_Bottom': 0,
        'border_width': 0,
        'H_grid': True,
        'H_grid_div': 4,
        'H_grid_color': (0, 255, 144, 255),
        'avg_line': True,
        'avg_line_color': (0, 144, 255, 255),
        'H_grid_label_color': (0, 0, 0, 255),
        'line_width': 14,
        'font_path': './data/fonts/consola.ttf',
    }
    config_ram = dict(**config, **{'fgcolor': (239, 120, 239, 220)})
    config_cpu = dict(**config, **{'fgcolor': (255, 144,   0, 220)})
    chart_cpu = LineChart(list(CPU_PERCENT), width=2400, height=1000, **config_cpu).image.resize((960, 400))
    chart_cpu = Layer.image(chart_cpu, mask=chart_mask, coord=(60, 988))
    title_cpu = Canvas(bar_bg_1)
    title_cpu.add_layer(Layer.text('CPU 使用率', font=DEFAULT_1.size_32, lmt_height=40, pos=position.LEFT_MIDDLE, move=(20, 0)))
    title_cpu.add_layer(Layer.text(f'平均  {sum(CPU_PERCENT)/40:.4f} %', font=DEFAULT_1.size_32, lmt_height=40, pos=position.RIGHT_MIDDLE, move=(-20, 0)))
    layer_cpu = Layer.image(title_cpu.image, coord=(60, 922))
    chart_ram = LineChart(list(MEM_USAGE), width=2400, height=1000, **config_ram).image.resize((960, 400))
    chart_ram = Layer.image(chart_ram, mask=chart_mask, coord=(60, 1460))
    title_ram = Canvas(bar_bg_1)
    title_ram.add_layer(Layer.text('RAM 占用', font=DEFAULT_1.size_32, lmt_height=40, pos=position.LEFT_MIDDLE, move=(20, 0)))
    title_ram.add_layer(Layer.text(f'平均  {sum(MEM_USAGE)/40:.4f} MB', font=DEFAULT_1.size_32, lmt_height=40, pos=position.RIGHT_MIDDLE, move=(-20, 0)))
    layer_ram = Layer.image(title_ram.image, coord=(60, 1394))

    canvas.add_layers([layer_cpu, chart_cpu, layer_ram, chart_ram])

    await trigger.done(CQcode.image(canvas.image.convert('RGB')))

async def f_reboot(arg, bot: Bot, event: MessageEvent):
    arg = arg if arg is not None else ''
    if args := re.findall(r'-([^-]+)', arg):
        if 'plugin' in args:
            @bot.on_connect(temp=True)
            def _reload_plugins():
                for p in bot.plugins:
                    p.reload()

    @bot.on_connect(temp=True)
    async def _msg(bot: Bot):
        if isinstance(event, GroupMessageEvent):
            await bot.send_msg(message='重启成功', group_id=event.group_id)
        else:
            await bot.send_msg(message='重启成功', user_id=event.sender.user_id)

    bot.reboot()

def draw_plugins(plugins: list[Plugin], event: MessageEvent, superuser: bool = False):
    session_available = lambda t: t in (0, 1) if isinstance(event, GroupMessageEvent) else t in (0, 2)

    state_1 = Rectangle(width=36, height=36, radius=12, color=( 87, 213,  85, 207)).image
    state_2 = Rectangle(width=36, height=36, radius=12, color=(255, 140,  63, 207)).image
    state_3 = Rectangle(width=36, height=36, radius=12, color=(100, 106, 121, 207)).image
    state_4 = Rectangle(width=36, height=36, radius=12, color=(241,  27,  27, 207)).image

    if superuser:
        layer_1_cont = Rectangle(width=1020, height=540+66*len(plugins), color=(0, 0, 0, 24), radius=24).image
        layer_1_mask = Rectangle(width=1020, height=540+66*len(plugins), color=255, radius=24, mode='L').image
        bg = random_background((1080, 600+66*len(plugins)))
        canvas = Canvas(width=1080, height=600+66*len(plugins))
        layer_0 = Layer.image(bg, pos=position.CENTER)
        layer_1 = Layer.image(layer_1_cont, coord=(30, 30), apply=ImageFilter.GaussianBlur(6), mask=layer_1_mask)
        canvas.add_layers([layer_0, layer_1])
        # title layer
        title_layer = Canvas(Rectangle(width=960, height=120, color=(255, 255, 255, 191), radius=12).image)
        title_layer.add_layer(Layer.text('插件菜单(管理员)', font=DEFAULT_2.size_64, lmt_height=64, pos=position.CENTER))
        canvas.add_layer(Layer.image(title_layer.image, coord=(60, 60)))
        # description layer
        description_layer = Canvas(Rectangle(width=960, height=300, color=(255, 255, 255, 191), radius=12).image)
        for i in range(5):
            description_layer.add_layer(Layer.text(f'{i+1}', font=DEFAULT_1.size_24, coord=(670, 212), move=(i*60, 0)))
            description_layer.add_layer(Layer.image([state_3, state_2, state_4, state_3, state_4][i], coord=(660, 252), move=(i*60, 0)))
        description = \
        '发送 #help 插件id 可查看插件具体用法\n\n'\
        '1. [会话不可用]  插件在当前群聊/私聊中不可用\n'\
        '2. [处于风控中]  插件部分功能可能受限\n'\
        '3. [插件异常]  插件绝大部分功能不可用\n'\
        '4. [插件被隐藏]  功能不受限\n'\
        '5. [插件被禁用]  全部交互功能被禁用\n\n'\
        f'当前存在插件 [{len(plugins)}] 个'
        description_layer.add_layer(Layer.text('插件状态栏', font=DEFAULT_1.size_24, lmt_width=500, lmt_height=30, coord=(660, 162)))
        description_layer.add_layer(Layer.text(description, font=DEFAULT_1.size_24, lmt_width=500, lmt_height=270, coord=(30, 12)))
        canvas.add_layer(Layer.image(description_layer.image, coord=(60, 210)))
        # plugin layer
        p_layer_0 = Rectangle(width=960, height=60, color=(255, 255, 255, 191), radius=12).image
        for i, p in enumerate(plugins):
            plugin_layer = Canvas(p_layer_0)
            p_layer_1 = Layer.image([state_3, state_1][session_available(p.metadata.type)], coord=(660, 12))
            p_layer_2 = Layer.image([state_1, state_2][p.metadata.risk], coord=(720, 12))
            p_layer_3 = Layer.image([state_4, state_1][p.metadata.available], coord=(780, 12))
            p_layer_4 = Layer.image([state_1, state_3][p.metadata.hide], coord=(840, 12))
            p_layer_5 = Layer.image([state_4, state_1][p.enable], coord=(900, 12))
            p_layer_6 = Layer.text(f'{i+1}', font=DEFAULT_1.size_36, lmt_width=64, lmt_height=48, pos=position.LEFT_MIDDLE, move=(24, 0))
            p_layer_7 = Layer.text(p.metadata.name[:12], font=DEFAULT_1.size_36, lmt_width=432, lmt_height=48, pos=position.LEFT_MIDDLE, move=(100, 0))
            plugin_layer.add_layers([p_layer_1, p_layer_2, p_layer_3, p_layer_4, p_layer_5, p_layer_6, p_layer_7])
            canvas.add_layer(Layer.image(plugin_layer.image, coord=(60, 540), move=(0, i*66)))
        return canvas.image.convert('RGB')
    else:
        layer_1_cont = Rectangle(width=1020, height=480+66*len(plugins), color=(0, 0, 0, 24), radius=24).image
        layer_1_mask = Rectangle(width=1020, height=480+66*len(plugins), color=255, radius=24, mode='L').image
        bg = random_background((1080, 540+66*len(plugins)))
        canvas = Canvas(width=1080, height=540+66*len(plugins))
        layer_0 = Layer.image(bg, pos=position.CENTER)
        layer_1 = Layer.image(layer_1_cont, coord=(30, 30), apply=ImageFilter.GaussianBlur(6), mask=layer_1_mask)
        canvas.add_layers([layer_0, layer_1])
        # title layer
        title_layer = Canvas(Rectangle(width=960, height=120, color=(255, 255, 255, 191), radius=12).image)
        title_layer.add_layer(Layer.text('插件菜单', font=DEFAULT_2.size_64, lmt_height=64, pos=position.CENTER))
        canvas.add_layer(Layer.image(title_layer.image, coord=(60, 60)))
        # description layer
        description_layer = Canvas(Rectangle(width=960, height=240, color=(255, 255, 255, 191), radius=12).image)
        for i in range(3):
            description_layer.add_layer(Layer.text(f'{i+1}', font=DEFAULT_1.size_24, coord=(790, 152), move=(i*60, 0)))
            description_layer.add_layer(Layer.image([state_3, state_2, state_4][i], coord=(780, 192), move=(i*60, 0)))
        description = \
        '发送 help 插件id 可查看插件具体用法\n\n'\
        '1. [会话不可用]  插件在当前群聊/私聊中不可用\n'\
        '2. [处于风控中]  插件部分功能可能受限\n'\
        '3. [插件异常]  插件绝大部分功能不可用\n\n'\
        f'当前存在可用插件 [{len(plugins)}] 个'
        description_layer.add_layer(Layer.text('插件状态栏', font=DEFAULT_1.size_24, lmt_width=120, lmt_height=30, coord=(780, 102)))
        description_layer.add_layer(Layer.text(description, font=DEFAULT_1.size_24, lmt_width=500, lmt_height=210, coord=(30, 12)))
        canvas.add_layer(Layer.image(description_layer.image, coord=(60, 210)))
        # plugin layer
        p_layer_0 = Rectangle(width=960, height=60, color=(255, 255, 255, 191), radius=12).image
        for i, p in enumerate(plugins):
            plugin_layer = Canvas(p_layer_0)
            p_layer_1 = Layer.image([state_3, state_1][session_available(p.metadata.type)], coord=(780, 12))
            p_layer_2 = Layer.image([state_1, state_2][p.metadata.risk], coord=(840, 12))
            p_layer_3 = Layer.image([state_4, state_1][p.metadata.available], coord=(900, 12))
            p_layer_4 = Layer.text(f'{i+1}', font=DEFAULT_1.size_36, lmt_width=64, lmt_height=48, pos=position.LEFT_MIDDLE, move=(24, 0))
            p_layer_5 = Layer.text(p.metadata.name[:12], font=DEFAULT_1.size_36, lmt_width=432, lmt_height=48, pos=position.LEFT_MIDDLE, move=(100, 0))
            plugin_layer.add_layers([p_layer_1, p_layer_2, p_layer_3, p_layer_4, p_layer_5])
            canvas.add_layer(Layer.image(plugin_layer.image, coord=(60, 480), move=(0, i*66)))
        return canvas.image.convert('RGB')

def draw_usage(plugin: Plugin):
    canvas_height = 300
    type_layer_height = 60
    usage_layer_height = 60
    usage_image = None
    usage_text = None
    usage_text_height = 0
    if plugin.metadata.usage_image_path:
        if Path(plugin.metadata.usage_image_path).is_file():
            usage_image = Image.open(plugin.metadata.usage_image_path)
            if usage_image.width > 900:
                usage_image = usage_image.resize((900, int(usage_image.height*900/usage_image.width)))
            usage_layer_height += usage_image.height+30
    if plugin.metadata.usage_text:
        usage_text = plugin.metadata.usage_text
        usage_text_height = DEFAULT_1.size_24.getsize_multiline(usage_text)[1]+6
        usage_layer_height += usage_text_height+20

    canvas_height += type_layer_height+usage_layer_height

    layer_1_cont = Rectangle(width=1020, height=canvas_height-60, color=(0, 0, 0, 24), radius=24).image
    layer_1_mask = Rectangle(width=1020, height=canvas_height-60, color=255, radius=24, mode='L').image

    bg = random_background((1080, canvas_height))

    canvas = Canvas(width=1080, height=canvas_height)
    layer_0 = Layer.image(bg, pos=position.CENTER)
    layer_1 = Layer.image(layer_1_cont, coord=(30, 30), apply=ImageFilter.GaussianBlur(6), mask=layer_1_mask)
    canvas.add_layers([layer_0, layer_1])
    # title layer
    title_layer = Canvas(Rectangle(width=960, height=120, color=(255, 255, 255, 191), radius=12).image)
    title_layer.add_layer(Layer.text(plugin.metadata.name, font=DEFAULT_2.size_64, lmt_height=64, pos=position.CENTER))
    canvas.add_layer(Layer.image(title_layer.image, coord=(60, 60)))
    # type layer
    title_layer = Canvas(Rectangle(width=960, height=60, color=(255, 255, 255, 191), radius=12).image)
    title_layer.add_layer(Layer.text('适用会话类型:  '+['群聊 & 私聊', '群聊', '私聊', '非会话'][plugin.metadata.type], font=DEFAULT_2.size_32, lmt_height=32, pos=position.CENTER))
    canvas.add_layer(Layer.image(title_layer.image, coord=(60, 210)))
    # usage layer
    usage_layer = Canvas(Rectangle(width=960, height=usage_layer_height, color=(255, 255, 255, 191), radius=12).image)
    usage_layer.add_layer(Layer.text('使 用 方 法', font=DEFAULT_2.size_32, lmt_height=32, pos=position.TOP_MIDDLE, move=(0, 14)))
    if usage_image:
        usage_layer.add_layer(Layer.image(usage_image, pos=position.TOP_MIDDLE, move=(0, 60)))
    if usage_text:
        usage_layer.add_layer(Layer.text(usage_text, font=DEFAULT_1.size_24, lmt_height=usage_text_height, pos=position.BOTTOM_LEFT, move=(30, -13)))
    canvas.add_layer(Layer.image(usage_layer.image, coord=(60, 300)))
    
    return canvas.image.convert('RGB')


def random_background(size: tuple[int, int]|None = None):
    global BG_IMAGE_PATH
    bg_path = [p for p in BG_IMAGE_PATH.rglob('*') if p.suffix in ('.jpg', '.png')]
    if len(bg_path) == 0:
        img = Image.new('RGBA', (1000, 2000), (255, 255, 255, 255)) 
    else:
        img = Image.open(choice(bg_path))
    if size is not None:
        pw = img.size[0]/size[0]
        ph = img.size[1]/size[1]
        if pw > ph:
            img = img.resize((int(img.size[0]/ph), size[1]))
        elif pw < ph:
            img = img.resize((size[0], int(img.size[1]/pw)))
        else:
            img = img.resize(size)
    return img

def get_dir_size(path: Path):
    return path.stat().st_size if path.is_file() else sum(get_dir_size(p)for p in path.iterdir())

def storge_consumption():
    return sorted([(p.name, get_dir_size(p)) for p in Path(bot.config.data_path).iterdir()], key=lambda t: t[1], reverse=True)

def get_storge(size):
    pk = (len(bin(size))-2)//10
    unit = ['', 'K', 'M', 'G', 'T', 'P'][pk] + 'B'
    return f'{size/1024**pk:.2f} {unit}'

async def _auto_record_status():
    await asyncio.sleep(INTERVAL)
    await record_status()

@bot.on_startup
async def record_status():
    global BOT_PROCESS, CPU_PERCENT, MEM_USAGE
    CPU_PERCENT.append(BOT_PROCESS.cpu_percent())
    MEM_USAGE.append(BOT_PROCESS.memory_full_info().uss/1024/1024)
    asyncio.run_coroutine_threadsafe(_auto_record_status(), asyncio.get_running_loop())

@bot.on_connect
async def download_avatar():
    url = f'http://q1.qlogo.cn/g?b=qq&nk={bot.qid}&s=640'
    resp = httpx.get(url)
    if resp.status_code == 200:
        with open(bot.config.data_path+'/avatar.jpg', 'wb') as avatar:
            avatar.write(resp.content)


PLUGIN_NAME = '基础功能管理'

__metadata__ = {
    'name': PLUGIN_NAME,
    'hide': True,
}