import asyncio

from muzi.plugin import Trigger
from muzi.event import MessageEvent
from muzi.message import Message


def PixivAPP_CallLimits(max_call_times: float = 5, time_limit: float = 10, prompt: str|Message|None= None):

    USERS: dict[str, int] = {}
    
    async def _PixivAPP_CallLimits(trigger: Trigger, event: MessageEvent):
        user = f'{event.user_id}'
        count = USERS.get(user, 0)
        if count >= max_call_times:
            if prompt:
                await trigger.done()
            else:
                await trigger.done(Message(prompt))
        else:
            USERS[user] = count + 1
            def call_later():
                USERS[user] = USERS[user] - 1
                if not USERS[user]:
                    USERS.pop(user)
            loop = asyncio.get_running_loop()
            loop.call_later(time_limit, call_later)
    
    return _PixivAPP_CallLimits
