import aiosqlite
from muzi import get_bot


bot = get_bot()

DB = aiosqlite.connect(bot.config.data_path+'/game_draw/data.db')

@bot.on_connect()
async def init_database():
    await DB
    await DB.execute(
        '''
        CREATE TABLE IF NOT EXISTS Arknights (
        id             INT,
        n              INT         DEFAULT 0,
        UNIQUE(id));'''
    )
