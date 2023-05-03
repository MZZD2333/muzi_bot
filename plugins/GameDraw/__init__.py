import re

from muzi import Bot, CQcode, get_bot, on_regex
from muzi.event import MessageEvent

from .arknights import ARKNIGHTS
from .db import DB

bot = get_bot()

game_draw = on_regex(r'^(?P<game>[^一二三四五六七八九十单\d]+)\s*(?P<times>[\d一二三四五六七八九十单]+)\s*[连发抽]', flags=re.I, priority=1)

@game_draw.excute()
async def e_game_draw(bot: Bot, event: MessageEvent, data: dict):
    game = data['matched_groupdict']['game']
    times = data['matched_groupdict']['times']
    if times.isdigit():
        times = int(times)
    else:
        if len(times) == 1:
            times = ('一二三四五六七八九十单'.index(times)+1)%10
        else:
            times = 10
    match game:
        case '明日方舟'|'方舟'|'Arknights':
            result = await DB.execute('''SELECT n FROM Arknights WHERE id = ?;''', (event.user_id, ))
            if fetch := await result.fetchone():
                n = fetch[0]
            else:
                await DB.execute('''INSERT OR IGNORE INTO Arknights (id, n) VALUES(?, ?);''', (event.user_id, 0))
                n = 0
            img, n = ARKNIGHTS.draw(times, n)
            await DB.execute('''UPDATE Arknights SET n = ? WHERE id = ?;''', (n, event.user_id))
            await game_draw.send(CQcode.image(img))
    
    await DB.commit()