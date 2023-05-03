import re

from libs.PixivAPP import PIXIVAPP
from muzi import Bot, get_bot, on_regex
from muzi.event import MessageEvent

from .datasource import *
from .dependence import PixivAPP_CallLimits

__metadata__ = {
    'name': 'Pixiv APP',
    'version': '1.0',
    'usage_text': \
    '指令格式: pixiv  [功能]  [参数]\n'\
    '[功能] 如下 (注: 同一功能可能有不同的名字, 各参数可乱序)\n'\
    '01.登录 | login    用于登录pixiv(注: 仅bot超管可用)\n'\
    '   必填参数 refresh_token\n'\
    '   例: pixiv login XXXXX\n'\
    '02.搜索 | 搜图    用提供的tags搜索图片\n'\
    '   必填参数  tags  可选参数  page(最大为64张默认12张)  R18(默认关闭)\n'\
    '   例: pixiv  搜索  Miku  64张\n'\
    '       pixiv  搜索  Miku  -AI  64张  R-18\n'\
    '       -tag  可以过滤含此tag的搜索结果\n'\
    '       本插件已将  r18  R18  r-18  解析为  R-18\n'\
    '       -AI  解析为  -AI  -NovelAI  -AI绘画  -AI绘图  -AIイラスト\n'\
    '02.作品 | pid | id  用于下载作品\n'\
    '   必填参数  ids(可以多个但需用换行间隔)  可选参数  #(显示详细信息)\n'\
    '   例: pixiv  id  123456789\n'\
    '       pixiv  pid  123456789\n'\
    '       123456790\n'\
    '04.新作    获取pixiv最新发布的作品\n'\
    '   可选参数  page(最大为64张默认12张)\n'\
    '   例: pixiv  新作  24张\n'\
    '05.排行榜 | 榜单    获取pixiv排行榜作品\n'\
    '   可选参数  type(榜单类型:  默认每日)  page(最大为64张默认12张)\n'\
    '   例: pixiv  排行榜  24张\n'\
    '       pixiv  排行榜  周榜  R-18\n'\
    '   榜单类型:\n'\
    '       日榜  日榜R18  男性向  女性向  周榜  周榜R18  原创  新人  月榜\n'\
    '06.推荐 | 随机    获取pixiv随机推荐的作品\n'\
    '   可选参数  page(最大为64张默认12张)\n'\
    '   例: pixiv  推荐  36张\n'\
    '07.相关作品 | 相似作品    获取与之相似的作品\n'\
    '   必填参数  id\n'\
    '   例: pixiv  相关作品  123456789\n'\
    '08.搜索用户 | 搜索画师 | 搜索作者    搜索pixiv的用户\n'\
    '   必填参数  keyword\n'\
    '   例: pixiv  搜索用户  ATDAN\n'\
    '09.用户收藏    获取pixiv用户的收藏的作品\n'\
    '   必填参数  uid  可选参数  page(最大为64张默认12张)\n'\
    '   例: pixiv  用户收藏  123456\n'\
    '10.用户 | 画师 | 作者 | uid    获取pixiv用户的作品\n'\
    '   必填参数  uid  可选参数  page(最大为64张默认12张)\n'\
    '   例: pixiv  uid 123456  36张\n'\
    '11.相关用户 | 相关画师 | 相关作者 | 相似用户 | 相似画师 | 相似作者\n'\
    '   获取与之相似的用户\n'\
    '   必填参数  uid  可选参数\n'\
    '   例: pixiv  相关画师 123456\n'\
    ,
    # usage_image='./help_pixiv.png',
    'status_tracing': get_plugin_status,
    'type': 0
}


pixivapp = on_regex(r'^pixiv\s*(\S+)\s*((?:.|\n)*)?', flags=re.I, priority=1)


@pixivapp.excute(pre_excute=[PixivAPP_CallLimits(max_call_times=3), ])
async def _pixivapp(bot: Bot, event: MessageEvent, data: dict):
    matched: tuple[str] = data['matched_groups']
    args = Args(matched[1], event)
    match matched[0].strip().lower():
        case '登录' | 'login':
            if event.user_id in bot.config.superusers:
                await pixiv_login(trigger=pixivapp, bot=bot, args=args)
            else:
                await pixivapp.done('权限不足')
        case '搜索' | '搜图':
            await pixiv_search_illust(trigger=pixivapp, bot=bot, args=args)
        case '作品' | 'pid' | 'id':
            await pixiv_illust_detail(trigger=pixivapp, bot=bot, args=args)
        case '新作':
            await pixiv_illust_new(trigger=pixivapp, bot=bot, args=args)
        case '排行榜' | '榜单':
            await pixiv_illust_ranking(trigger=pixivapp, bot=bot, args=args)
        case '推荐' | '随机':
            await pixiv_illust_recommended(trigger=pixivapp, bot=bot, args=args)
        case '相关作品' | '相似作品':
            await pixiv_illust_related(trigger=pixivapp, bot=bot, args=args)
        case '搜索用户' | '搜索画师' | '搜索作者':
            await pixiv_search_user(trigger=pixivapp, bot=bot, args=args)
        case '用户收藏':
            await pixiv_user_bookmarks_illust(trigger=pixivapp, bot=bot, args=args)
        case '用户' | '画师' | '作者' | 'uid':
            await pixiv_user_illusts(trigger=pixivapp, bot=bot, args=args)
        case '相关用户' | '相关画师' | '相关作者' | '相似用户' | '相似画师' | '相似作者':
            await pixiv_user_related(trigger=pixivapp, bot=bot, args=args)
        case _:
            await pixivapp.done()


bot = get_bot()

@bot.on_connect
async def _check_refresh_token(bot: Bot):
    refresh_token = '1_dn1hmZWM0lOZ3Aud-Wl88Lpixr2FkHaazu66IhDDI'
    if refresh_token:
        await PIXIVAPP.login(refresh_token=refresh_token)
        if not PIXIVAPP.login_in:
            await bot.send_private_msg(user_id=int(list(bot.config.superusers)[0]), message='Pixiv refresh_token 错误/过期\n可能导致部分相关插件不能正常使用\n发送pixiv token XXXXXXX 使其恢复')
    else:
        await bot.send_private_msg(user_id=int(list(bot.config.superusers)[0]), message='Pixiv refresh_token 缺失\n可能导致部分相关插件不能正常使用\n发送pixiv token XXXXXXX 使其恢复')
