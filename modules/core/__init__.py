import os
import sys
import time
import traceback

import psutil
import ujson as json

from core.component import on_command
from core.elements import MessageSession, Command, PrivateAssets, Image, Plain
from core.loader import ModulesManager
from core.parser.command import CommandParser, InvalidHelpDocTypeError
from core.tos import pardon_user, warn_user
from core.utils.image_table import ImageTable, image_table_render, web_render
from database import BotDBUtil

module = on_command('module',
                    base=True,
                    alias={'enable': 'module enable', 'disable': 'module disable'},
                    developers=['OasisAkari'],
                    required_admin=True
                    )


@module.handle(['enable (<module>...|all) {开启一个/多个或所有模块}',
                'disable (<module>...|all) {关闭一个/多个或所有模块}'], exclude_from=['QQ|Guild'])
async def _(msg: MessageSession):
    await config_modules(msg)


@module.handle(['enable (<module>...|all) [-g] {开启一个/多个或所有模块}',
                'disable (<module>...|all) [-g] {关闭一个/多个或所有模块\n [-g] - 为文字频道内全局操作}'],
               available_for=['QQ|Guild'])
async def _(msg: MessageSession):
    await config_modules(msg)


async def config_modules(msg: MessageSession):
    alias = ModulesManager.return_modules_alias_map()
    modules_ = ModulesManager.return_modules_list_as_dict(targetFrom=msg.target.targetFrom)
    wait_config = msg.parsed_msg['<module>']
    wait_config_list = []
    for module_ in wait_config:
        if module_ not in wait_config_list:
            if module_ in alias:
                wait_config_list.append(alias[module_])
            else:
                wait_config_list.append(module_)
    query = BotDBUtil.Module(msg)
    msglist = []
    recommend_modules_list = []
    recommend_modules_help_doc_list = []
    if msg.parsed_msg['enable']:
        enable_list = []
        if wait_config_list == ['all']:
            for function in modules_:
                if function[0] == '_':
                    continue
                if isinstance(modules_[function], Command) and (
                    modules_[function].base or modules_[function].required_superuser):
                    continue
                enable_list.append(function)
        else:
            for module_ in wait_config_list:
                if module_ not in modules_:
                    msglist.append(f'失败：“{module_}”模块不存在')
                else:
                    if modules_[module_].required_superuser and not msg.checkSuperUser():
                        msglist.append(f'失败：你没有打开“{module_}”的权限。')
                    elif isinstance(modules_[module_], Command) and modules_[module_].base:
                        msglist.append(f'失败：“{module_}”为基础模块。')
                    else:
                        enable_list.append(module_)
                        recommend = modules_[module_].recommend_modules
                        if recommend is not None:
                            for r in recommend:
                                recommend_modules_list.append(r)
        if '-g' in msg.parsed_msg and msg.parsed_msg['-g']:
            get_all_channel = await msg.get_text_channel_list()
            for x in get_all_channel:
                query = BotDBUtil.Module(f'{msg.target.targetFrom}|{x}')
                query.enable(enable_list)
            for x in enable_list:
                msglist.append(f'成功：为所有文字频道打开“{x}”模块')
        else:
            if query.enable(enable_list):
                for x in enable_list:
                    msglist.append(f'成功：打开模块“{x}”')
        if recommend_modules_list:
            for m in recommend_modules_list:
                if m not in enable_list:
                    try:
                        hdoc = CommandParser(modules_[m], msg=msg).return_formatted_help_doc()
                        recommend_modules_help_doc_list.append(f'模块{m}的帮助信息：')
                        if modules_[m].desc is not None:
                            recommend_modules_help_doc_list.append(modules_[m].desc)
                        recommend_modules_help_doc_list.append(hdoc)
                    except InvalidHelpDocTypeError:
                        pass
    elif msg.parsed_msg['disable']:
        disable_list = []
        if wait_config_list == ['all']:
            for function in modules_:
                if function[0] == '_':
                    continue
                if isinstance(modules_[function], Command) and (
                    modules_[function].base or modules_[function].required_superuser):
                    continue
                disable_list.append(function)
        else:
            for module_ in wait_config_list:
                if module_ not in modules_:
                    msglist.append(f'失败：“{module_}”模块不存在')
                else:
                    disable_list.append(module_)
        if '-g' in msg.parsed_msg and msg.parsed_msg['-g']:
            get_all_channel = await msg.get_text_channel_list()
            for x in get_all_channel:
                query = BotDBUtil.Module(f'{msg.target.targetFrom}|{x}')
                query.disable(disable_list)
            for x in disable_list:
                msglist.append(f'成功：为所有文字频道关闭“{x}”模块')
        else:
            if query.disable(disable_list):
                for x in disable_list:
                    msglist.append(f'成功：关闭模块“{x}”')
    if msglist is not None:
        await msg.sendMessage('\n'.join(msglist))
    if recommend_modules_help_doc_list and ('-g' not in msg.parsed_msg or not msg.parsed_msg['-g']):
        confirm = await msg.waitConfirm('建议同时打开以下模块：\n' +
                                        '\n'.join(recommend_modules_list) + '\n\n' +
                                        '\n'.join(recommend_modules_help_doc_list) +
                                        '\n是否一并打开？')
        if confirm:
            query = BotDBUtil.Module(msg)
            if query.enable(recommend_modules_list):
                msglist = []
                for x in recommend_modules_list:
                    msglist.append(f'成功：打开模块“{x}”')
                await msg.sendMessage('\n'.join(msglist))


