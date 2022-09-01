from os import path
import os


from typing import TYPE_CHECKING, Set

import pytest
from nonebug import App

if TYPE_CHECKING:
    from nonebot.plugin import Plugin


@pytest.fixture
def load_plugins(nonebug_init: None) -> Set["Plugin"]:
    import nonebot  # 这里的导入必须在函数内

    # 加载插件
    return nonebot.load_plugins("..")

@pytest.mark.asyncio
async def test_clanbattle(app: App, load_plugins):
    from .. import clanbattle_qq
    from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message
    from nonebot.adapters.onebot.v11.event import Sender


    #加入公会测试
    async with app.test_matcher(clanbattle_qq.create_clan) as ctx:
        bot = ctx.create_bot()
        msg = Message("创建台服公会")
        event = GroupMessageEvent(message=msg, group_id=114514,user_id=114514, self_id= 0, message_id=0,time=114514,post_type="message",sub_type="1",message_type="group",raw_message="创建台服公会",font=0,sender=Sender())
        ctx.receive_event(bot, event)
        ctx.should_call_api("get_group_info",{"group_id":114514,"no_cache": True},{"group_name","下北泽乐园"})
        ctx.should_call_api("get_group_member_list",{"group_id":114514},[{
            "role": "admin",
            "user_id": 114514,
            "nickname": "先辈"
        },{
            "role": "member",
            "user_id": 114515,
            "nickname": "先辈2号"
        }])
        ctx.should_call_send(event, "公会创建成功，请发送“帮助”查看使用说明", True)
        ctx.should_call_send(event, "已经将全部群成员加入公会", True)
        