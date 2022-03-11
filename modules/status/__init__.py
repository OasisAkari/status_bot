import asyncio
import random
import string

from core.bots.aiocqhttp.tasks import MessageTaskManager
from core.component import on_schedule
from core.elements import FetchTarget, IntervalTrigger
from core.bots.aiocqhttp.client import bot


bot_id = 2314163511
send_ = False


@on_schedule('bot_status', IntervalTrigger(minutes=5))
async def _(target: FetchTarget):
    nonlocal send_
    command = '~echo ' + ''.join(random.sample(string.ascii_letters + string.digits, 8))
    send = await bot.send_private_msg(user_id=bot_id, message=command)
    flag = asyncio.Event()
    MessageTaskManager.add_task(bot_id, flag)
    await asyncio.sleep(30)
    all_tsk = MessageTaskManager.get()
    if bot_id in all_tsk:
        if not send_:
            await target.post_message('bot_status', '警告：小可服务状态异常，可能存在冻结或软件问题。')
            send_ = True
    else:
        send_ = False


