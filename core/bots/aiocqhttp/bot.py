import asyncio
import logging
import os
import re

from aiocqhttp import Event

from config import Config
from core.bots.aiocqhttp.client import bot
from core.bots.aiocqhttp.message import MessageSession, FetchTarget
from core.bots.aiocqhttp.tasks import MessageTaskManager, FinishedTasks
from core.elements import MsgInfo, Session, StartUp, Schedule, EnableDirtyWordCheck, PrivateAssets
from core.loader import ModulesManager
from core.parser.message import parser
from core.scheduler import Scheduler
from core.utils import init, load_prompt

PrivateAssets.set(os.path.abspath(os.path.dirname(__file__) + '/assets'))
EnableDirtyWordCheck.status = True
init()


@bot.on_startup
async def startup():
    gather_list = []
    Modules = ModulesManager.return_modules_list_as_dict()
    for x in Modules:
        if isinstance(Modules[x], StartUp):
            gather_list.append(asyncio.ensure_future(Modules[x].function(FetchTarget)))
        elif isinstance(Modules[x], Schedule):
            Scheduler.add_job(func=Modules[x].function, trigger=Modules[x].trigger, args=[FetchTarget])
    await asyncio.gather(*gather_list)
    Scheduler.start()
    logging.getLogger('apscheduler.executors.default').setLevel(logging.WARNING)
    bot.logger.setLevel(logging.WARNING)


@bot.on_websocket_connection
async def _(event: Event):
    await load_prompt(FetchTarget)


@bot.on_message('group', 'private')
async def _(event: Event):
    if event.detail_type == 'private':
        if event.sub_type == 'group':
            return await bot.send(event, '请先添加好友后再进行命令交互。')
    filter_msg = re.match(r'.*?\[CQ:(?:json|xml).*?].*?|.*?<\?xml.*?>.*?', event.message)
    if filter_msg:
        return
    all_tsk = MessageTaskManager.get()
    user_id = event.user_id
    if user_id in all_tsk:
        FinishedTasks.add_task(user_id, event.message)
        all_tsk[user_id].set()
        MessageTaskManager.del_task(user_id)
    targetId = 'QQ|' + (f'Group|{str(event.group_id)}' if event.detail_type == 'group' else str(event.user_id))
    msg = MessageSession(MsgInfo(targetId=targetId,
                                 senderId=f'QQ|{str(event.user_id)}',
                                 targetFrom='QQ|Group' if event.detail_type == 'group' else 'QQ',
                                 senderFrom='QQ', senderName=''), Session(message=event,
                                                                          target=event.group_id if event.detail_type == 'group' else event.user_id,
                                                                          sender=event.user_id))
    await parser(msg)


qq_host = Config("qq_host")
if qq_host:
    host, port = qq_host.split(':')
    bot.run(host=host, port=port, debug=False)
