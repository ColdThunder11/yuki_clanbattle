import asyncio
import imp
from importlib.resources import path
from random import randrange
from typing import Optional
from warnings import resetwarnings
import nonebot
import json
import datetime
import inspect
import os

import pydantic
from peewee import Check, Function
from playhouse.shortcuts import model_to_dict
from typing import ForwardRef, _eval_type  # type: ignore
from typing import Any, List, Dict, Type, Union, Optional, TYPE_CHECKING
from pydantic import BaseModel, conset
from nonebot.adapters.onebot.v11 import Bot, Event, MessageEvent
from nonebot.adapters.onebot.v11.event import PrivateMessageEvent, GroupMessageEvent, PrivateMessageEvent
from nonebot.adapters.onebot.v11.message import Message, MessageSegment
from nonebot.plugin import on, on_command, on_message, MatcherGroup, on_regex
from nonebot.typing import T_State
from nonebot.params import State


from fastapi import FastAPI, Request, Path, Response, Cookie, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from .utils import BossStatus, ClanBattle, ClanBattleData, CommitBattlrOnTreeResult, CommitInProgressResult, CommitRecordResult, CommitSLResult, CommitSubscribeResult, WebAuth
from .utils import Tools


from .exception import WebsocketResloveException, WebsocketAuthException

#from .ws_protocol_pb2 import WsRequestMessage, WsResponseMessage, WsUpdateRequireNotice

driver = nonebot.get_driver()

app: FastAPI = nonebot.get_app()

clanbattle = ClanBattle()

call_api_orig_func = None


VERSION = "0.1.6"
WEB_URL = "https://yukiclanbattle.shikeschedule.cn/"
ENABLE_PRIVATE_HOOK = True


async def call_api_func_hook(self, api: str, **data: Any) -> Any:
    # print(api)
    if ENABLE_PRIVATE_HOOK:
        if api == "send_msg":
            if (not "message_type" in data and "user_id" in data) or ("message_type" in data and data["message_type"] == "private"):
                return
        elif api == "send_private_msg":
            return
    return await call_api_orig_func(self, api, **data)


@driver.on_startup
async def install_call_api_hook():  # 阻止发送私聊消息
    global call_api_orig_func
    call_api_orig_func = Bot.call_api
    Bot.call_api = call_api_func_hook
    # mount static file if exsist
    static_file_path = os.path.join(os.path.dirname(__file__), "dist")
    if os.path.isdir(static_file_path):
        app.mount("/", StaticFiles(directory=static_file_path), name="static")


class WebLoginPost(BaseModel):
    qq_uid: str
    password: str


class WebPostBase(BaseModel):
    clan_gid: str


class WebReportRecord(WebPostBase):
    target_boss: str
    damage: Optional[str]
    is_kill_boss: bool
    froce_use_full_chance: bool
    is_proxy_report: bool
    proxy_report_member: Optional[str]
    comment: Optional[str]


class WebReportQueue(WebPostBase):
    target_boss: str
    comment: Optional[str]


class WebReportSubscribe(WebPostBase):
    target_boss: str
    target_cycle: str
    comment: Optional[str]


class WebReportSL(WebPostBase):
    boss: str
    comment: Optional[str]
    is_proxy_report: bool
    proxy_report_uid: Optional[str]


class WebReportOnTree(WebPostBase):
    boss: str
    comment: Optional[str]


class WebQueryReport(WebPostBase):
    date: Optional[str]
    member: Optional[str]
    boss: Optional[str]
    cycle: Optional[str]


class WebSetClanbattleData(WebPostBase):
    data_num: int


class WebNoticeChallengeForm(WebPostBase):
    notice_member: dict


class WebQueryChallengeStatusForm(WebPostBase):
    date: Optional[str]


class WebRemoveClanMember(WebPostBase):
    remove_member: str


class WebChangeBossStatus(WebPostBase):
    boss: str
    cycle: str
    remain_hp: str


class WebGetRoute:
    @staticmethod
    async def get_joined_clan(uid: str):
        clan_list = clanbattle.get_joined_clan(uid)
        return {"err_code": 0, "clan_list": clan_list}

    @staticmethod
    async def boss_status(uid: str, clan_gid: str):
        clan = clanbattle.get_clan_data(clan_gid)
        boss_status = clan.get_current_boss_state()
        return {"err_code": 0, "boss_status": boss_status}

    @staticmethod
    async def member_list(uid: str, clan_gid: str):
        clan = clanbattle.get_clan_data(clan_gid)
        member_list = clan.get_clan_members_with_info()
        return{"err_code": 0, "member_list": member_list}

    @staticmethod
    async def report_unqueue(uid: str, clan_gid: str):
        clan = clanbattle.get_clan_data(clan_gid)
        result = clan.delete_battle_in_progress(uid)
        if result:
            return{"err_code": 0}
        else:
            return{"err_code": 403, "msg": "取消申请失败，请确认您已经在出刀了喵"}

    @staticmethod
    async def get_in_queue(uid: str, clan_gid: str):
        clan = clanbattle.get_clan_data(clan_gid)
        in_process_list_dict = {}
        for i in range(1, 6):
            in_process_list = []
            in_processes = clan.get_battle_in_progress(boss=i)
            for process in in_processes:
                in_process_list.append(model_to_dict(process))
            in_process_list_dict[str(i)] = in_process_list
        return {"err_code": 0, "queue": in_process_list_dict}

    @staticmethod
    async def on_tree_list(uid: str, clan_gid: str):
        clan = clanbattle.get_clan_data(clan_gid)
        on_tree_list_dict = {}
        for i in range(1, 6):
            on_tree_list = []
            on_trees = clan.get_battle_on_tree(boss=i)
            for on_tree in on_trees:
                on_tree_list.append(model_to_dict(on_tree))
            on_tree_list_dict[str(i)] = on_tree_list
        return {"err_code": 0, "on_tree": on_tree_list_dict}

    @staticmethod
    async def subscribe_list(uid: str, clan_gid: str):
        clan = clanbattle.get_clan_data(clan_gid)
        subscribe_list_dict = {}
        for i in range(1, 6):
            subscribe_list = []
            subscribes = clan.get_battle_subscribe(boss=i)
            for subscribe in subscribes:
                subscribe_list.append(model_to_dict(subscribe))
            subscribe_list_dict[str(i)] = subscribe_list
        return {"err_code": 0, "subscribe": subscribe_list_dict}

    @staticmethod
    async def current_clanbattle_data_num(uid: str, clan_gid: str):
        clan = clanbattle.get_clan_data(clan_gid)
        data_num = clan.get_current_clanbattle_data()
        return{"err_code": 0, "data_num": data_num}


class WebPostRoute:

    async def report_record(item: WebReportRecord, uid: str, clan_gid: str):
        if item.is_proxy_report:
            joined_clan = clanbattle.get_joined_clan(item.proxy_report_member)
            if not item.clan_gid in joined_clan:
                return {"err_code": 403, "msg": "您还没有加入该公会"}
        clan = clanbattle.get_clan_data(item.clan_gid)
        challenge_boss = int(item.target_boss)
        proxy_report_uid = item.proxy_report_member if item.is_proxy_report else None
        comment = item.comment if item.comment else None
        force_use_full_chance = item.froce_use_full_chance
        if not item.is_kill_boss:
            challenge_damage = item.damage
        else:
            boss_status = clan.get_current_boss_state()[challenge_boss-1]
            challenge_damage = str(boss_status.boss_hp)
        if item.is_proxy_report:
            result = await clan.commit_record(proxy_report_uid, challenge_boss, challenge_damage, comment, uid, force_use_full_chance)
            uid = proxy_report_uid
        else:
            result = await clan.commit_record(uid, challenge_boss, challenge_damage, comment, None, force_use_full_chance)
        bot: Bot = list(nonebot.get_bots().values())[0]
        if result == CommitRecordResult.success:
            record = clan.get_recent_record(uid)[0]
            today_status = clan.get_today_record_status(uid)
            boss_status = clan.get_current_boss_state()[challenge_boss-1]
            if today_status.last_is_addition:
                record_type = "补偿刀"
            else:
                record_type = "完整刀"
            await bot.send_group_msg(group_id=item.clan_gid, message="网页上报数据：\n" + MessageSegment.at(uid) + f"对{challenge_boss}王造成了{record.damage}点伤害\n今日第{today_status.today_challenged}刀，{record_type}\n当前{challenge_boss}王第{boss_status.target_cycle}周目，生命值{boss_status.boss_hp}")
            return{"err_code": 0}
        elif result == CommitRecordResult.illegal_damage_inpiut:
            return{"err_code": 403, "msg": "上报的伤害格式不合法"}
        elif result == CommitRecordResult.damage_out_of_hp:
            return{"err_code": 403, "msg": "上报的伤害超出了boss血量，如已击杀请使用尾刀指令"}
        elif result == CommitRecordResult.check_record_legal_failed:
            return{"err_code": 403, "msg": "上报数据合法性检查错误，请检查是否正确上报"}
        elif result == CommitRecordResult.member_not_in_clan:
            return{"err_code": 403, "msg": "您还未加入公会，请发送“加入公会”加入"}

    async def report_queue(item: WebReportQueue, uid: str, clan_gid: str):
        clan = clanbattle.get_clan_data(item.clan_gid)
        challenge_boss = int(item.target_boss)
        comment = item.comment if item.comment else None
        result = clan.commit_battle_in_progress(uid, challenge_boss, comment)
        bot: Bot = list(nonebot.get_bots().values())[0]
        if result == CommitInProgressResult.success:
            await bot.send_group_msg(group_id=item.clan_gid, message=MessageSegment.at(uid) + f"开始挑战{challenge_boss}王")
            return{"err_code": 0}
        elif result == CommitInProgressResult.already_in_battle:
            return{"err_code": 403, "msg": "您已经有正在挑战的boss"}
        elif result == CommitInProgressResult.illegal_target_boss:
            return{"err_code": 403, "msg": "您目前无法挑战这个boss"}
        elif result == CommitInProgressResult.member_not_in_clan:
            return{"err_code": 403, "msg": "您还未加入公会，请发送“加入公会”加入"}

    async def report_subscribe(item: WebReportSubscribe, uid: str, clan_gid: str):
        clan = clanbattle.get_clan_data(item.clan_gid)
        challenge_boss = int(item.target_boss)
        cycle = int(item.target_cycle)
        comment = item.comment if item.comment else None
        result = clan.commit_batle_subscribe(
            uid, challenge_boss, cycle, comment)
        bot: Bot = list(nonebot.get_bots().values())[0]
        if result == CommitSubscribeResult.success:
            await bot.send_group_msg(group_id=item.clan_gid, message=MessageSegment.at(uid) + f"预约了{cycle}周目{challenge_boss}王")
            return{"err_code": 0}
        elif result == CommitSubscribeResult.already_in_progress:
            return{"err_code": 403, "msg": "您已经正在挑战这个boss了"}
        elif result == CommitSubscribeResult.already_subscribed:
            return{"err_code": 403, "msg": "您已经预约了这个boss了"}
        elif result == CommitSubscribeResult.boss_cycle_already_killed:
            return{"err_code": 403, "msg": "boss已经死亡，请刷新页面重新查看"}
        elif result == CommitSubscribeResult.member_not_in_clan:
            return{"err_code": 403, "msg": "您还未加入公会，请发送“加入公会”加入"}

    async def report_unsubscribe(item: WebReportSubscribe, uid: str, clan_gid: str):
        clan = clanbattle.get_clan_data(item.clan_gid)
        challenge_boss = int(item.target_boss)
        cycle = int(item.target_cycle)
        result = clan.delete_battle_subscribe(uid, challenge_boss, cycle)
        if result:
            return{"err_code": 0}
        else:
            return{"err_code": 403, "msg": "取消预约失败，请确认您已经预约该boss喵"}

    async def report_ontree(item: WebReportOnTree, uid: str, clan_gid: str):
        clan = clanbattle.get_clan_data(item.clan_gid)
        boss = int(item.boss)
        comment = item.comment if item.comment else None
        result = clan.commit_battle_on_tree(uid, boss, comment)
        if result == CommitBattlrOnTreeResult.success:
            return{"err_code": 0}
        elif result == CommitBattlrOnTreeResult.already_in_other_boss_progress:
            return{"err_code": 403, "msg": "您正在挑战其他Boss，无法在这里挂树哦"}
        elif result == CommitBattlrOnTreeResult.already_on_tree:
            return{"err_code": 403, "msg": "您已经在树上了，不用再挂了"}
        elif result == CommitBattlrOnTreeResult.member_not_in_clan:
            return{"err_code": 403, "msg": "您还未加入公会，请发送“加入公会”加入"}

    async def report_sl(item: WebReportSL, uid: str, clan_gid: str):
        if item.is_proxy_report:
            joined_clan = clanbattle.get_joined_clan(item.proxy_report_uid)
            if not item.clan_gid in joined_clan:
                return {"err_code": 403, "msg": "您还没有加入该公会"}
        clan = clanbattle.get_clan_data(item.clan_gid)
        boss = int(item.boss)
        proxy_report_uid = item.proxy_report_uid if item.is_proxy_report else None
        comment = item.comment if item.comment else None
        if item.is_proxy_report:
            result = clan.commit_battle_sl(
                proxy_report_uid, boss, comment, uid)
        else:
            result = clan.commit_battle_sl(
                uid, boss, comment, proxy_report_uid)
        if result == CommitSLResult.success:
            return{"err_code": 0}
        elif result == CommitSLResult.illegal_target_boss:
            return{"err_code": 403, "msg": "您还不能在这个boss上sl"}
        elif result == CommitSLResult.already_sl:
            return{"err_code": 403, "msg": "您今天已经使用过SL了"}
        elif result == CommitSLResult.member_not_in_clan:
            return{"err_code": 403, "msg": "您还未加入公会，请发送“加入公会”加入"}

    async def query_record(item: WebQueryReport, uid: str, clan_gid: str):
        clan = clanbattle.get_clan_data(item.clan_gid)
        uid = item.member if item.member != '' else None
        boss = int(item.boss) if item.boss != '' else None
        cycle = int(item.cycle) if item.cycle != '' else None
        if item.date and item.date != '':
            day_data = item.date.split('T')[0]
            detla = datetime.timedelta(
                hours=9) if clan.clan_info.clan_type == "jp" else datetime.timedelta(hours=8)
            now_time_today = datetime.datetime.strptime(
                day_data, "%Y-%m-%d") + datetime.timedelta(days=1)
            start_time = now_time_today + datetime.timedelta(hours=5) - detla
            end_time = now_time_today + datetime.timedelta(hours=29) - detla
        else:
            start_time = None
            end_time = None
        record_list = []
        records = clan.get_record(uid=uid, boss=boss, cycle=cycle,
                                  start_time=start_time, end_time=end_time, time_desc=True)
        if not records:
            return {"err_code": 0, "record": []}
        for record in records:
            record_list.append(model_to_dict(record))
        return {"err_code": 0, "record": record_list}

    async def change_current_clanbattle_data_num(item: WebSetClanbattleData, uid: str, clan_gid: str):
        clan = clanbattle.get_clan_data(item.clan_gid)
        if not clan.check_admin_permission(str(uid)):
            return {"err_code": -2, "msg": "您不是会战管理员，无权切换会战档案"}
        clan.set_current_clanbattle_data(item.data_num)
        bot: Bot = list(nonebot.get_bots().values())[0]
        gid = clan.clan_info.clan_gid
        await bot.send_group_msg(group_id=gid, message=f"会战管理员已经将会战档案切换为{item.data_num}，请注意")
        return {"err_code": 0, "msg": "设置成功"}

    async def battle_status(item: WebQueryChallengeStatusForm, uid: str, clan_gid: str):
        clan = clanbattle.get_clan_data(item.clan_gid)
        status_list = []
        members = clan.get_clan_members()
        for member in members:
            if not item.date:
                status = clan.get_today_record_status(member)
            else:
                day_data = item.date.split('T')[0]
                detla = datetime.timedelta(
                    hours=9) if clan.clan_info.clan_type == "jp" else datetime.timedelta(hours=8)
                now_time_today = datetime.datetime.strptime(
                    day_data, "%Y-%m-%d") + datetime.timedelta(days=1)
                start_time = now_time_today + \
                    datetime.timedelta(hours=5) - detla
                end_time = now_time_today + \
                    datetime.timedelta(hours=29) - detla
                status = clan.get_record_status(member, start_time, end_time)
            status_list.append(status)
        return {"err_code": 0, "status": status_list}

    async def notice_member(item: WebNoticeChallengeForm, uid: str, clan_gid: str):
        clan = clanbattle.get_clan_data(item.clan_gid)
        if not clan.check_admin_permission(str(uid)):
            return {"err_code": -2, "msg": "您不是会战管理员，无权提醒其他成员出刀"}
        notice_list = []
        for key in item.notice_member:
            if item.notice_member[key] == True:
                if clan.check_joined_clan(key):
                    notice_list.append(key)
        bot: Bot = list(nonebot.get_bots().values())[0]
        notice_message = Message("管理员催你快去出刀啦")
        for member in notice_list:
            notice_message += MessageSegment.at(member)
            if len(notice_message) == 20:
                await bot.send_group_msg(group_id=item.clan_gid, message=notice_message)
                notice_message = Message("管理员催你快去出刀啦")
        if len(notice_message) > 1:
            await bot.send_group_msg(group_id=item.clan_gid, message=notice_message)
        return {"err_code": 0}


class PydanticObjectParamCreater:

    @staticmethod
    def parse_item_pydantic_param(func: Function, data_dict: dict) -> Any:
        typed_signature = PydanticObjectParamCreater._get_typed_signature(func)
        pydantic_class = typed_signature.parameters["item"].annotation
        return pydantic_class.parse_obj(data_dict)

    @staticmethod
    def _get_typed_annotation(param: inspect.Parameter,
                              globalns: Dict[str, Any]) -> Any:
        try:
            if isinstance(param.annotation, str):
                return _eval_type(ForwardRef(param.annotation), globalns,
                                  globalns)
            else:
                return param.annotation
        except Exception:
            return param.annotation

    @staticmethod
    def _get_typed_signature(func,
                             follow_wrapped: bool = True) -> inspect.Signature:
        signature = inspect.signature(func, follow_wrapped=follow_wrapped)
        globalns = getattr(func, "__globals__", {})
        typed_params = [
            inspect.Parameter(
                name=param.name,
                kind=param.kind,
                default=param.default,
                annotation=param.annotation if follow_wrapped else
                PydanticObjectParamCreater._get_typed_annotation(
                    param, globalns),
            ) for param in signature.parameters.values()
        ]
        typed_signature = inspect.Signature(typed_params)
        return typed_signature


'''
class WsManager():

    class ws_client_processer():

        uid: str = None
        gid: str = None

        def __init__(self, ws: WebSocket):
            self.ws = ws

        async def get_method_processer(self, request: ws_protocol_pb2.WsRequestMessage) -> dict:
            session = request.session
            api_name = request.route
            clan_gid = request.data
            if not (uid := WebAuth.check_session_valid(session)):
                return {"err_code": -1, "msg": "会话错误，请重新登录"}
            if not hasattr(WebGetRoute, api_name):
                return {"err_code": 404, "msg": "找不到该路由"}
            if api_name in ["get_joined_clan"]:
                ret = await getattr(WebGetRoute, api_name)(uid=uid)
            else:
                joined_clan = clanbattle.get_joined_clan(uid)
                if not clan_gid in joined_clan:
                    return {"err_code": 403, "msg": "您还没有加入该公会"}
                self.gid = clan_gid
                self.uid = uid
                #clan = clanbattle.get_clan_data(clan_gid)
                ret = await getattr(WebGetRoute, api_name)(uid=uid, clan_gid=clan_gid)
            return ret

        async def post_method_processer(self, request: ws_protocol_pb2.WsRequestMessage) -> dict:
            session = request.session
            api_name = request.route
            data = json.loads(request.data)
            clan_gid = data["clan_gid"]
            if not (uid := WebAuth.check_session_valid(session)):
                return {"err_code": -1, "msg": "会话错误，请重新登录"}
            if not hasattr(WebPostRoute, api_name):
                return {"err_code": 404, "msg": "找不到该路由"}
            joined_clan = clanbattle.get_joined_clan(uid)
            if not clan_gid in joined_clan:
                return {"err_code": 403, "msg": "您还没有加入该公会"}
            self.gid = clan_gid
            self.uid = uid
            post_func = getattr(WebPostRoute, api_name)
            item = PydanticObjectParamCreater.parse_item_pydantic_param(
                post_func, data)
            ret = await post_func(item=item, uid=uid, clan_gid=clan_gid)
            return ret

        async def handle_ws_loop(self):
            ws = self.ws
            while True:
                data = await ws.receive()
                if "text" in data:
                    raise WebsocketResloveException()
                elif "bytes" in data:
                    data = data["bytes"]
                if data[0] != 0xf7:
                    raise WebsocketResloveException()
                if data[1] == 0x01:
                    pb_data = data[2:]
                    req: ws_protocol_pb2.WsRequestMessage = ws_protocol_pb2.WsRequestMessage.ParseFromString(
                        pb_data)
                    if req.request_type == 0:
                        ret_dict = await self.get_method_processer(req)
                        header = b'\xf7\x02'
                        ret_msg = ws_protocol_pb2.WsResponseMessage()
                        ret_msg.response_uuid = req.request_uuid
                        ret_msg.data = json.dumps(ret_dict)
                        header += ret_msg.SerializeToString()
                        await asyncio.wait_for(ws.send_bytes(header), timeout=10)
                    elif req.request_type == 1:
                        ret_dict = await self.get_method_processer(req)
                        header = b'\xf7\x02'
                        ret_msg = ws_protocol_pb2.WsResponseMessage()
                        ret_msg.response_uuid = req.request_uuid
                        ret_msg.data = json.dumps(ret_dict)
                        header += ret_msg.SerializeToString()
                        await asyncio.wait_for(ws.send_bytes(header), timeout=10)
                    print(req)
                elif data[1] == 0x04:
                    await asyncio.wait_for(ws.send_bytes(b'\xf7\x04'), timeout=10)
                else:
                    raise WebsocketResloveException()

    active_ws_list = []
    ws_timeout = 10

    async def add_new_ws_connection(self, ws: WebSocket):
        await ws.accept()
        ws_processer = WsManager.ws_client_processer(ws)
        self.active_ws_list.append(ws_processer)
        try:
            await ws_processer.handle_ws_loop()
        except:
            self.active_ws_list.remove(ws_processer)


ws_manager = WsManager()


@app.websocket("/api/clanbattle/websocket/ws")
async def _(websocket: WebSocket):
    await ws_manager.add_new_ws_connection(websocket)
'''


@app.get("/api/clanbattle/{api_name}")
async def _(api_name: str, response: Response, clan_gid: str = None, session: str = Cookie(None)):
    if not (uid := WebAuth.check_session_valid(session)):
        return {"err_code": -1, "msg": "会话错误，请重新登录"}
    if not hasattr(WebGetRoute, api_name):
        response.status_code = 404
        return {"err_code": 404, "msg": "找不到该路由"}
    if api_name in ["get_joined_clan"]:
        ret = await getattr(WebGetRoute, api_name)(uid=uid)
    else:
        joined_clan = clanbattle.get_joined_clan(uid)
        if not clan_gid in joined_clan:
            return {"err_code": 403, "msg": "您还没有加入该公会"}
        #clan = clanbattle.get_clan_data(clan_gid)
        ret = await getattr(WebGetRoute, api_name)(uid=uid, clan_gid=clan_gid)
    return ret


@app.post("/api/clanbattle/login")
async def _(item: WebLoginPost, request: Request, response: Response):
    login_item = WebAuth.login(item.qq_uid, item.password)
    if login_item[0] == 404:
        return {"err_code": 404, "msg": "找不到该用户"}
    elif login_item[0] == 403:
        return {"err_code": 403, "msg": "密码错误，如未设置请查看帮助设置密码"}
    session = login_item[1]
    response.set_cookie(key="session", value=session)
    return {"err_code": 0, "msg": "", "cookie": session}


@app.post("/api/clanbattle/report_record")
async def _(item: WebReportRecord, session: str = Cookie(None)):
    if not (uid := WebAuth.check_session_valid(session)):
        return {"err_code": -1, "msg": "会话错误，请重新登录"}
    joined_clan = clanbattle.get_joined_clan(uid)
    if not item.clan_gid in joined_clan:
        return {"err_code": 403, "msg": "您还没有加入该公会"}
    if item.is_proxy_report:
        joined_clan = clanbattle.get_joined_clan(item.proxy_report_member)
        if not item.clan_gid in joined_clan:
            return {"err_code": 403, "msg": "您还没有加入该公会"}
    clan = clanbattle.get_clan_data(item.clan_gid)
    challenge_boss = int(item.target_boss)
    proxy_report_uid = item.proxy_report_member if item.is_proxy_report else None
    comment = item.comment if item.comment else None
    force_use_full_chance = item.froce_use_full_chance
    if not item.is_kill_boss:
        challenge_damage = item.damage
    else:
        boss_status = clan.get_current_boss_state()[challenge_boss-1]
        challenge_damage = str(boss_status.boss_hp)
    if item.is_proxy_report:
        result = await clan.commit_record(proxy_report_uid, challenge_boss, challenge_damage, comment, uid, force_use_full_chance)
        uid = proxy_report_uid
    else:
        result = await clan.commit_record(uid, challenge_boss, challenge_damage, comment, None, force_use_full_chance)
    bot: Bot = list(nonebot.get_bots().values())[0]
    if result == CommitRecordResult.success:
        record = clan.get_recent_record(uid)[0]
        today_status = clan.get_today_record_status(uid)
        boss_status = clan.get_current_boss_state()[challenge_boss-1]
        if today_status.last_is_addition:
            record_type = "补偿刀"
        else:
            record_type = "完整刀"
        await bot.send_group_msg(group_id=item.clan_gid, message="网页上报数据：\n" + MessageSegment.at(uid) + f"对{challenge_boss}王造成了{Tools.get_num_str_with_dot(record.damage)}点伤害\n今日第{today_status.today_challenged}刀，{record_type}\n当前{challenge_boss}王第{boss_status.target_cycle}周目，生命值{Tools.get_num_str_with_dot(boss_status.boss_hp)}")
        return{"err_code": 0}
    elif result == CommitRecordResult.illegal_damage_inpiut:
        return{"err_code": 403, "msg": "上报的伤害格式不合法"}
    elif result == CommitRecordResult.damage_out_of_hp:
        return{"err_code": 403, "msg": "上报的伤害超出了boss血量，如已击杀请使用尾刀指令"}
    elif result == CommitRecordResult.check_record_legal_failed:
        return{"err_code": 403, "msg": "上报数据合法性检查错误，请检查是否正确上报"}
    elif result == CommitRecordResult.member_not_in_clan:
        return{"err_code": 403, "msg": "您还未加入公会，请发送“加入公会”加入"}


@app.post("/api/clanbattle/report_queue")
async def _(item: WebReportQueue, session: str = Cookie(None)):
    if not (uid := WebAuth.check_session_valid(session)):
        return {"err_code": -1, "msg": "会话错误，请重新登录"}
    joined_clan = clanbattle.get_joined_clan(uid)
    if not item.clan_gid in joined_clan:
        return {"err_code": 403, "msg": "您还没有加入该公会"}
    clan = clanbattle.get_clan_data(item.clan_gid)
    challenge_boss = int(item.target_boss)
    comment = item.comment if item.comment else None
    result = clan.commit_battle_in_progress(uid, challenge_boss, comment)
    bot: Bot = list(nonebot.get_bots().values())[0]
    if result == CommitInProgressResult.success:
        await bot.send_group_msg(group_id=item.clan_gid, message=MessageSegment.at(uid) + f"开始挑战{challenge_boss}王")
        return{"err_code": 0}
    elif result == CommitInProgressResult.already_in_battle:
        return{"err_code": 403, "msg": "您已经有正在挑战的boss"}
    elif result == CommitInProgressResult.illegal_target_boss:
        return{"err_code": 403, "msg": "您目前无法挑战这个boss"}
    elif result == CommitInProgressResult.member_not_in_clan:
        return{"err_code": 403, "msg": "您还未加入公会，请发送“加入公会”加入"}


@app.post("/api/clanbattle/report_subscribe")
async def _(item: WebReportSubscribe, session: str = Cookie(None)):
    if not (uid := WebAuth.check_session_valid(session)):
        return {"err_code": -1, "msg": "会话错误，请重新登录"}
    joined_clan = clanbattle.get_joined_clan(uid)
    if not item.clan_gid in joined_clan:
        return {"err_code": 403, "msg": "您还没有加入该公会"}
    clan = clanbattle.get_clan_data(item.clan_gid)
    challenge_boss = int(item.target_boss)
    cycle = int(item.target_cycle)
    comment = item.comment if item.comment else None
    result = clan.commit_batle_subscribe(uid, challenge_boss, cycle, comment)
    bot: Bot = list(nonebot.get_bots().values())[0]
    if result == CommitSubscribeResult.success:
        await bot.send_group_msg(group_id=item.clan_gid, message=MessageSegment.at(uid) + f"预约了{cycle}周目{challenge_boss}王")
        return{"err_code": 0}
    elif result == CommitSubscribeResult.already_in_progress:
        return{"err_code": 403, "msg": "您已经正在挑战这个boss了"}
    elif result == CommitSubscribeResult.already_subscribed:
        return{"err_code": 403, "msg": "您已经预约了这个boss了"}
    elif result == CommitSubscribeResult.boss_cycle_already_killed:
        return{"err_code": 403, "msg": "boss已经死亡，请刷新页面重新查看"}
    elif result == CommitSubscribeResult.member_not_in_clan:
        return{"err_code": 403, "msg": "您还未加入公会，请发送“加入公会”加入"}


@app.post("/api/clanbattle/report_unsubscribe")
async def _(item: WebReportSubscribe, session: str = Cookie(None)):
    if not (uid := WebAuth.check_session_valid(session)):
        return {"err_code": -1, "msg": "会话错误，请重新登录"}
    joined_clan = clanbattle.get_joined_clan(uid)
    if not item.clan_gid in joined_clan:
        return {"err_code": 403, "msg": "您还没有加入该公会"}
    clan = clanbattle.get_clan_data(item.clan_gid)
    challenge_boss = int(item.target_boss)
    cycle = int(item.target_cycle)
    result = clan.delete_battle_subscribe(uid, challenge_boss, cycle)
    if result:
        return{"err_code": 0}
    else:
        return{"err_code": 403, "msg": "取消预约失败，请确认您已经预约该boss喵"}


@app.post("/api/clanbattle/report_ontree")
async def _(item: WebReportOnTree, session: str = Cookie(None)):
    if not (uid := WebAuth.check_session_valid(session)):
        return {"err_code": -1, "msg": "会话错误，请重新登录"}
    joined_clan = clanbattle.get_joined_clan(uid)
    if not item.clan_gid in joined_clan:
        return {"err_code": 403, "msg": "您还没有加入该公会"}
    clan = clanbattle.get_clan_data(item.clan_gid)
    boss = int(item.boss)
    comment = item.comment if item.comment else None
    result = clan.commit_battle_on_tree(uid, boss, comment)
    if result == CommitBattlrOnTreeResult.success:
        return{"err_code": 0}
    elif result == CommitBattlrOnTreeResult.already_in_other_boss_progress:
        return{"err_code": 403, "msg": "您正在挑战其他Boss，无法在这里挂树哦"}
    elif result == CommitBattlrOnTreeResult.already_on_tree:
        return{"err_code": 403, "msg": "您已经在树上了，不用再挂了"}
    elif result == CommitBattlrOnTreeResult.member_not_in_clan:
        return{"err_code": 403, "msg": "您还未加入公会，请发送“加入公会”加入"}


@app.post("/api/clanbattle/report_sl")
async def _(item: WebReportSL, session: str = Cookie(None)):
    if not (uid := WebAuth.check_session_valid(session)):
        return {"err_code": -1, "msg": "会话错误，请重新登录"}
    joined_clan = clanbattle.get_joined_clan(uid)
    if not item.clan_gid in joined_clan:
        return {"err_code": 403, "msg": "您还没有加入该公会"}
    if item.is_proxy_report:
        joined_clan = clanbattle.get_joined_clan(item.proxy_report_uid)
        if not item.clan_gid in joined_clan:
            return {"err_code": 403, "msg": "您还没有加入该公会"}
    clan = clanbattle.get_clan_data(item.clan_gid)
    boss = int(item.boss)
    proxy_report_uid = item.proxy_report_uid if item.is_proxy_report else None
    comment = item.comment if item.comment else None
    if item.is_proxy_report:
        result = clan.commit_battle_sl(proxy_report_uid, boss, comment, uid)
    else:
        result = clan.commit_battle_sl(uid, boss, comment, proxy_report_uid)
    if result == CommitSLResult.success:
        return{"err_code": 0}
    elif result == CommitSLResult.illegal_target_boss:
        return{"err_code": 403, "msg": "您还不能在这个boss上sl"}
    elif result == CommitSLResult.already_sl:
        return{"err_code": 403, "msg": "您今天已经使用过SL了"}
    elif result == CommitSLResult.member_not_in_clan:
        return{"err_code": 403, "msg": "您还未加入公会，请发送“加入公会”加入"}


@app.post("/api/clanbattle/query_record")
async def _(item: WebQueryReport, session: str = Cookie(None)):
    if not (uid := WebAuth.check_session_valid(session)):
        return {"err_code": -1, "msg": "会话错误，请重新登录"}
    joined_clan = clanbattle.get_joined_clan(uid)
    if not item.clan_gid in joined_clan:
        return {"err_code": 403, "msg": "您还没有加入该公会"}
    clan = clanbattle.get_clan_data(item.clan_gid)
    uid = item.member if item.member != '' else None
    boss = int(item.boss) if item.boss != '' else None
    cycle = int(item.cycle) if item.cycle != '' else None
    if item.date and item.date != '':
        day_data = item.date.split('T')[0]
        detla = datetime.timedelta(
            hours=9) if clan.clan_info.clan_type == "jp" else datetime.timedelta(hours=8)
        now_time_today = datetime.datetime.strptime(
            day_data, "%Y-%m-%d") + datetime.timedelta(days=1)
        start_time = now_time_today + datetime.timedelta(hours=5) - detla
        end_time = now_time_today + datetime.timedelta(hours=29) - detla
    else:
        start_time = None
        end_time = None
    record_list = []
    records = clan.get_record(uid=uid, boss=boss, cycle=cycle,
                              start_time=start_time, end_time=end_time, time_desc=True)
    if not records:
        return {"err_code": 0, "record": []}
    for record in records:
        record_list.append(model_to_dict(record))
    return {"err_code": 0, "record": record_list}


@app.post("/api/clanbattle/change_current_clanbattle_data_num")
async def _(item: WebSetClanbattleData, session: str = Cookie(None)):
    if not (uid := WebAuth.check_session_valid(session)):
        return {"err_code": -1, "msg": "会话错误，请重新登录"}
    joined_clan = clanbattle.get_joined_clan(uid)
    if not item.clan_gid in joined_clan:
        return {"err_code": 403, "msg": "您还没有加入该公会"}
    clan = clanbattle.get_clan_data(item.clan_gid)
    if not clan.check_admin_permission(str(uid)):
        return {"err_code": -2, "msg": "您不是会战管理员，无权切换会战档案"}
    clan.set_current_clanbattle_data(item.data_num)
    bot: Bot = list(nonebot.get_bots().values())[0]
    gid = clan.clan_info.clan_gid
    await bot.send_group_msg(group_id=gid, message=f"会战管理员已经将会战档案切换为{item.data_num}，请注意")
    return {"err_code": 0, "msg": "设置成功"}


@app.post("/api/clanbattle/battle_status")
async def _(item: WebQueryChallengeStatusForm, session: str = Cookie(None)):
    if not (uid := WebAuth.check_session_valid(session)):
        return {"err_code": -1, "msg": "会话错误，请重新登录"}
    joined_clan = clanbattle.get_joined_clan(uid)
    if not item.clan_gid in joined_clan:
        return {"err_code": 403, "msg": "您还没有加入该公会"}
    clan = clanbattle.get_clan_data(item.clan_gid)
    status_list = []
    members = clan.get_clan_members()
    for member in members:
        if not item.date:
            status = clan.get_today_record_status(member)
        else:
            day_data = item.date.split('T')[0]
            detla = datetime.timedelta(
                hours=9) if clan.clan_info.clan_type == "jp" else datetime.timedelta(hours=8)
            now_time_today = datetime.datetime.strptime(
                day_data, "%Y-%m-%d") + datetime.timedelta(days=1)
            start_time = now_time_today + datetime.timedelta(hours=5) - detla
            end_time = now_time_today + datetime.timedelta(hours=29) - detla
            status = clan.get_record_status(member, start_time, end_time)
        status_list.append(status)
    return {"err_code": 0, "status": status_list}


@app.post("/api/clanbattle/notice_member")
async def _(item: WebNoticeChallengeForm, session: str = Cookie(None)):
    if not (uid := WebAuth.check_session_valid(session)):
        return {"err_code": -1, "msg": "会话错误，请重新登录"}
    joined_clan = clanbattle.get_joined_clan(uid)
    if not item.clan_gid in joined_clan:
        return {"err_code": 403, "msg": "您还没有加入该公会"}
    clan = clanbattle.get_clan_data(item.clan_gid)
    if not clan.check_admin_permission(str(uid)):
        return {"err_code": -2, "msg": "您不是会战管理员，无权提醒其他成员出刀"}
    notice_list = []
    for key in item.notice_member:
        if item.notice_member[key] == True:
            if clan.check_joined_clan(key):
                notice_list.append(key)
    bot: Bot = list(nonebot.get_bots().values())[0]
    notice_message = Message("管理员催你快去出刀啦")
    for member in notice_list:
        notice_message += MessageSegment.at(member)
        if len(notice_message) == 20:
            await bot.send_group_msg(group_id=item.clan_gid, message=notice_message)
            notice_message = Message("管理员催你快去出刀啦")
    if len(notice_message) > 1:
        await bot.send_group_msg(group_id=item.clan_gid, message=notice_message)
    return {"err_code": 0}


@app.post("/api/clanbattle/remove_clan_member")
async def _(item: WebRemoveClanMember, session: str = Cookie(None)):
    if not (uid := WebAuth.check_session_valid(session)):
        return {"err_code": -1, "msg": "会话错误，请重新登录"}
    joined_clan = clanbattle.get_joined_clan(uid)
    if not item.clan_gid in joined_clan:
        return {"err_code": 403, "msg": "您还没有加入该公会"}
    clan = clanbattle.get_clan_data(item.clan_gid)
    if not clan.check_admin_permission(str(uid)):
        return {"err_code": -2, "msg": "您不是会战管理员，无权将其他成员移出公会"}
    remove_uid = item.remove_member
    bot: Bot = list(nonebot.get_bots().values())[0]
    if clan.delete_clan_member(remove_uid):
        await bot.send_group_msg(group_id=item.clan_gid, message=f"会战管理员通过网页将成员{remove_uid}移出公会")
        return {"err_code": 0}
    else:
        return {"err_code": 403, "msg": "移出公会失败，Ta可能还未加入公会？请尝试刷新页面！"}


@app.post("/api/clanbattle/change_boss_status")
async def _(item: WebChangeBossStatus, session: str = Cookie(None)):
    if not (uid := WebAuth.check_session_valid(session)):
        return {"err_code": -1, "msg": "会话错误，请重新登录"}
    joined_clan = clanbattle.get_joined_clan(uid)
    if not item.clan_gid in joined_clan:
        return {"err_code": 403, "msg": "您还没有加入该公会"}
    clan = clanbattle.get_clan_data(item.clan_gid)
    if not clan.check_admin_permission(str(uid)):
        return {"err_code": -2, "msg": "您不是会战管理员，无权调整boss状态"}
    if clan.commit_force_change_boss_status(int(item.boss), int(item.cycle), item.remain_hp):
        bot: Bot = list(nonebot.get_bots().values())[0]
        await bot.send_group_msg(group_id=item.clan_gid, message=f"会战管理员通过网页将{item.boss}王调整至{item.cycle}周目，剩余生命值{item.remain_hp}")
        return {"err_code": 0}
    else:
        return {"err_code": 403, "msg": "调整状态出现错误"}


class clanbattle_qq:
    worker = MatcherGroup(
        type="message", block=True
    )
    create_clan = worker.on_regex(r"^创建([台日])服[公工]会")
    commit_record = worker.on_regex(
        r"^报刀 ?(整)? ?([1-5]{1})??( )?(\d+[EeKkWwBb]{0,2})?([:：](.*?))? ?(\[CQ:at,qq=([1-9][0-9]{4,})\] ?)?$"
    )
    commit_kill_record = worker.on_regex(
        r"^尾刀 ?(整)? ?([1-5]{1})?? ?([:：](.*?))? ?(\[CQ:at,qq=([1-9][0-9]{4,})\] ?)?$")
    progress = worker.on_regex(r"^(状态|查) ?([1-5]{0,5})?$")
    query_recent_record = worker.on_regex(r"^查刀 ?(\[CQ:at,qq=([1-9][0-9]{4,})\] ?)?$")
    queue = worker.on_regex(r"^((申请(出刀)?)|进) ?([1-5]{1})?([:：](.*?))?$")
    unqueue = worker.on_regex(r"^取消申请|解锁$")
    showqueue = worker.on_regex(r"^出刀表 ?([1-5]{1,5})?$")
    #clearqueue = worker.on_regex(r"^[清删][空除]出刀表([1-5]{1,5})?$")
    on_tree = worker.on_regex(
        r"^挂树 ?([1-5]{1})?([:：](.*?))? ?(\[CQ:at,qq=([1-9][0-9]{4,})\] ?)?$"
    )
    un_on_tree = worker.on_regex(r"^取消挂树|下树$")
    query_on_tree = worker.on_regex(r"^查树$")
    subscribe = worker.on_regex(
        r"^预约 ?([1-5]{1})( )?([0-9]{1,3})?([:：](.*?))?$")
    showsubscribe = worker.on_regex(r"^预约表$")
    unsubscribe = worker.on_regex(r"^取消预约 ?([1-5]{1})( )?([0-9]{1,3})?$")
    undo_record_commit = worker.on_regex(
        r"^撤[回销]? ?([1-5]{1})?$"
    )
    sl = worker.on_regex(
        r"^[sS][lL](\?|？)? ?([1-5]{1})?([:：](.*?))?(\[CQ:at,qq=([1-9][0-9]{4,})\] ?)?$")
    sl_query = on_regex(r"^查[sS][lL] ?(\[CQ:at,qq=([1-9][0-9]{4,})\] ?)?$")
    today_record = on_regex(r"^今日出刀 ?(\[CQ:at,qq=([1-9][0-9]{4,})\] ?)?$")
    webview = worker.on_regex(r"^面板$")
    help = worker.on_regex(r"^帮助$")
    join_clan = worker.on_regex(
        r"^加入[公工]会 ?(\[CQ:at,qq=([1-9][0-9]{4,})\] ?)?$")
    leave_clan = worker.on_regex(r"^退出[公工]会$")
    refresh_clan_admin = worker.on_regex(r"^刷新会战管理员列表$")
    rename_clan_uname = worker.on_regex(
        r"^修改昵称 ?(.{1,20})(\[CQ:at,qq=([1-9][0-9]{4,})\] ?)?")
    rename_clan = worker.on_regex(r"^修改[公工]会名称 ?(.{1,20})")
    remove_clan_member = worker.on_regex(r"^移出[公工]会 ?(.{1,20})")
    reset_password = worker.on_regex(r"^设置密码 ?(.{1,20})$")
    add_clanbattle_admin = on_regex(
        r"^添加会战管理员 ?(\[CQ:at,qq=([1-9][0-9]{4,})\] ?)$")
    join_all_member = worker.on_regex(r"^加入全部成员$")
    switch_current_clanbattle_data = worker.on_regex(r"^切换会战档案 ?(.{1,2})$")
    clear_current_clanbattle_data = worker.on_regex(r"^清空当前会战档案$")
    force_change_boss_status = worker.on_regex(
        r"^修改进度 ?([1-5]{1}) ([0-9]{1,3}) (\d+[EeKkWwBb]{0,2})$")
    #killcalc = worker.on_regex(r"^合刀( )?(\d+) (\d+) (\d+)( \d+)?$")


@clanbattle_qq.create_clan.handle()
async def create_clan_qq(bot: Bot, event: GroupMessageEvent, state: T_State = State()):
    gid = str(event.group_id)
    clan_area = state['_matched_groups'][0]
    if clan_area == "日":
        clan_type = "jp"
    elif clan_area == "台":
        clan_type = "tw"
    clan = clanbattle.get_clan_data(gid)
    if clan:
        await clanbattle_qq.create_clan.send("公会已经存在！")
    else:
        group_info = await bot.get_group_info(group_id=event.group_id, no_cache=True)
        if not group_info:
            await clanbattle_qq.create_clan.send("获取群信息失败，请尝试将机器人踢出群聊以后重新邀请，要是还是不行也没办法")
            return
        else:
            group_name = group_info["group_name"]
        group_member_list = await bot.get_group_member_list(group_id=event.group_id)
        admin_list = []
        for member in group_member_list:
            if member["role"] in ["owner", "admin"] and member["user_id"] != int(bot.self_id):
                admin_list.append(str(member["user_id"]))
        clanbattle.create_clan(gid, group_name, clan_type, admin_list)
        await clanbattle_qq.create_clan.send("公会创建成功，请发送“帮助”查看使用说明")
        clan = clanbattle.get_clan_data(gid)
        if len(group_member_list) > 36:
            await clanbattle_qq.create_clan.send("当前群内人数过多，仅自动加入管理员，请手动加入需要加入公会的群员，如需加入全部成员请发送“加入全部成员”")
            for member in group_member_list:
                if member["role"] in ["owner", "admin"] and member["user_id"] != int(bot.self_id):
                    clan.add_clan_member(str(
                        member["user_id"]), member["card"] if member["card"] != "" else member["nickname"])
        else:
            for member in group_member_list:
                if member["user_id"] != int(bot.self_id):
                    clan.add_clan_member(str(
                        member["user_id"]), member["card"] if member["card"] != "" else member["nickname"])
            await clanbattle_qq.create_clan.send("已经将全部群成员加入公会")


@clanbattle_qq.progress.handle()
async def get_clanbatle_status_qq(bot: Bot, event: GroupMessageEvent, state: T_State = State()):
    gid = str(event.group_id)
    clan = clanbattle.get_clan_data(gid)
    if not clan:
        await clanbattle_qq.progress.finish("本群还未创建公会，发送“创建[台日]服公会”来创建公会")
    if not clan.check_joined_clan(str(event.user_id)):
        await clanbattle_qq.progress.finish("您还没有加入公会，请发送“加入公会”来加入公会哦")
    boss_status = clan.get_current_boss_state()
    if state['_matched_groups'][0] == "状态" and not state['_matched_groups'][1]:
        msg = "当前状态：\n"
        for boss in boss_status:
            msg += f"{boss.target_cycle}周目{boss.target_boss}王，生命值{Tools.get_num_str_with_dot(boss.boss_hp)}"
            if not clan.check_boss_challengeable(boss.target_cycle, boss.target_boss):
                msg += "（不可挑战）"
            msg += "\n"
        status = clan.get_today_record_status_total()
        msg += f"今日已出{status[0]}刀，剩余{status[1]}刀补偿刀"
        await clanbattle_qq.progress.finish(msg.strip())
    elif state['_matched_groups'][1]:
        boss_count = int(state['_matched_groups'][1])
        boss = boss_status[boss_count-1]
        msg = f"当前{boss_count}王位于{boss.target_cycle}周目，剩余血量{Tools.get_num_str_with_dot(boss.boss_hp)}"
        if not clan.check_boss_challengeable(boss.target_cycle, boss_count):
            msg += "（不可挑战）"
        msg += "\n"
        subs = clan.get_battle_subscribe(
            boss=boss_count, boss_cycle=boss.target_cycle)
        if subs:
            for sub in subs:
                msg += clan.get_user_name(sub.member_uid)
                if sub.comment and sub.comment != "":
                    msg += f"：{sub.comment}"
            msg += "已经预约该boss"
        in_processes = clan.get_battle_in_progress(boss=boss_count)
        if in_processes:
            if subs:
                msg += "\n"
            in_process_list = []
            for proc in in_processes:
                proc_msg = clan.get_user_name(proc.member_uid)
                if proc.comment and proc.comment != "":
                    proc_msg += f"：{proc.comment}"
                in_process_list.append(proc_msg)
            msg += "、".join(in_process_list) + "正在出刀"
        on_tree = clan.get_battle_on_tree(boss=boss_count)
        if on_tree:
            if in_processes or subs:
                msg += "\n"
            on_tree_list = []
            for tree in on_tree:
                on_tree_msg = clan.get_user_name(tree.member_uid)
                if tree.comment and tree.comment != "":
                    on_tree_msg += f"：{tree.comment}"
                on_tree_list.append(on_tree_msg)
            msg += f"当前{ '、'.join(on_tree_list)}还挂在树上"
        await clanbattle_qq.progress.finish(msg.strip() if isinstance(msg, str) else msg)


@clanbattle_qq.commit_record.handle()
async def commit_record_qq(bot: Bot, event: GroupMessageEvent, state: T_State = State()):
    proxy_report_uid: str = None
    if not state['_matched_groups'][7]:
        uid = str(event.user_id)
    else:
        uid = state['_matched_groups'][7]
        proxy_report_uid = str(event.user_id)
    force_use_full_chance = True if state['_matched_groups'][0] else False
    challenge_boss = int(state['_matched_groups'][1]
                         ) if state['_matched_groups'][1] else None
    challenge_damage = state['_matched_groups'][3]
    comment = state['_matched_groups'][5]
    clan = clanbattle.get_clan_data(str(event.group_id))
    if not challenge_boss:
        if progress := clan.get_battle_in_progress(uid=uid):
            challenge_boss = progress[0].target_boss
        elif on_tree := clan.get_battle_on_tree(uid=uid):
            challenge_boss = on_tree[0].target_boss
        else:
            await clanbattle_qq.commit_record.finish("您还没有正在挑战的boss，请发送“报刀x 伤害”来进行报刀")
    if not clan:
        await clanbattle_qq.commit_record.finish("本群还未创建公会，发送“创建[台日]服公会”来创建公会")
    if not clan.check_joined_clan(str(event.user_id)):
        await clanbattle_qq.commit_record.finish("您还没有加入公会，请发送“加入公会”来加入公会哦")
    result = await clan.commit_record(uid, challenge_boss, challenge_damage, comment, proxy_report_uid, force_use_full_chance)
    if result == CommitRecordResult.success:
        record = clan.get_recent_record(uid)[0]
        today_status = clan.get_today_record_status(uid)
        boss_status = clan.get_current_boss_state()[challenge_boss-1]
        if today_status.last_is_addition:
            record_type = "补偿刀"
        else:
            record_type = "完整刀"
        await clanbattle_qq.commit_record.finish(MessageSegment.at(uid) + f"对{challenge_boss}王造成了{Tools.get_num_str_with_dot(record.damage)}点伤害\n今日已出{today_status.today_challenged}刀完整刀，余{today_status.remain_addition_challeng}刀补偿刀，当前刀为{record_type}\n==============\n当前{challenge_boss}王第{boss_status.target_cycle}周目，生命值{Tools.get_num_str_with_dot(boss_status.boss_hp)}")
    elif result == CommitRecordResult.illegal_damage_inpiut:
        await clanbattle_qq.commit_record.finish("上报的伤害格式不合法")
    elif result == CommitRecordResult.damage_out_of_hp:
        await clanbattle_qq.commit_record.finish("上报的伤害超出了boss血量，如已击杀请使用尾刀指令")
    elif result == CommitRecordResult.check_record_legal_failed:
        await clanbattle_qq.commit_record.finish("上报数据合法性检查错误，请检查是否正确上报")
    elif result == CommitRecordResult.member_not_in_clan:
        await clanbattle_qq.commit_record.finish("您还未加入公会，请发送“加入公会”加入")
    elif result == CommitRecordResult.boss_not_challengeable:
        await clanbattle_qq.commit_record.finish("现在无法挑战这个boss，别在这发癫了！")
    elif result == CommitRecordResult.on_another_tree:
        await clanbattle_qq.commit_record.finish("你还挂在其他树上，先下树再说吧")


@clanbattle_qq.commit_kill_record.handle()
async def commit_kill_record(bot: Bot, event: GroupMessageEvent, state: T_State = State()):
    proxy_report_uid: str = None
    if not state['_matched_groups'][5]:
        uid = str(event.user_id)
    else:
        uid = state['_matched_groups'][5]
        proxy_report_uid = str(event.user_id)
    force_use_full_chance = True if state['_matched_groups'][0] else False
    challenge_boss = int(state['_matched_groups'][1]
                         ) if state['_matched_groups'][1] else None
    comment = state['_matched_groups'][3]
    clan = clanbattle.get_clan_data(str(event.group_id))
    if not clan:
        await clanbattle_qq.commit_kill_record.finish("本群还未创建公会，发送“创建[台日]服公会”来创建公会")
    if not clan.check_joined_clan(str(event.user_id)):
        await clanbattle_qq.commit_kill_record.finish("您还没有加入公会，请发送“加入公会”来加入公会哦")
    if not challenge_boss:
        if progress := clan.get_battle_in_progress(uid=uid):
            challenge_boss = progress[0].target_boss
        elif on_tree := clan.get_battle_on_tree(uid=uid):
            challenge_boss = on_tree[0].target_boss
        else:
            await clanbattle_qq.commit_kill_record.finish("您还没有正在挑战的boss，请发送“尾刀x”来进行报刀")
    boss_status = clan.get_current_boss_state()[challenge_boss-1]
    challenge_damage = str(boss_status.boss_hp)
    result = await clan.commit_record(uid, challenge_boss, challenge_damage, comment, proxy_report_uid, force_use_full_chance)
    if result == CommitRecordResult.success:
        record = clan.get_recent_record(uid)[0]
        today_status = clan.get_today_record_status(uid)
        boss_status = clan.get_current_boss_state()[challenge_boss-1]
        if today_status.last_is_addition:
            record_type = "补偿刀"
        else:
            record_type = "完整刀"
        await clanbattle_qq.commit_kill_record.finish(MessageSegment.at(uid) + f"对{challenge_boss}王造成了{Tools.get_num_str_with_dot(record.damage)}点伤害并击破\n今日已出{today_status.today_challenged}刀完整刀，余{today_status.remain_addition_challeng}刀补偿刀，当前刀为{record_type}\n==============\n当前{challenge_boss}王第{boss_status.target_cycle}周目，生命值{Tools.get_num_str_with_dot(boss_status.boss_hp)}")
    elif result == CommitRecordResult.illegal_damage_inpiut:
        await clanbattle_qq.commit_kill_record.finish("上报的伤害格式不合法")
    elif result == CommitRecordResult.damage_out_of_hp:
        await clanbattle_qq.commit_kill_record.finish("上报的伤害超出了boss血量，如已击杀请使用尾刀指令")
    elif result == CommitRecordResult.check_record_legal_failed:
        await clanbattle_qq.commit_kill_record.finish("上报数据合法性检查错误，请检查是否正确上报")
    elif result == CommitRecordResult.member_not_in_clan:
        await clanbattle_qq.commit_kill_record.finish("您还未加入公会，请发送“加入公会”加入")
    elif result == CommitRecordResult.boss_not_challengeable:
        await clanbattle_qq.commit_kill_record.finish("现在无法挑战这个boss，别在这发癫了！")
    elif result == CommitRecordResult.on_another_tree:
        await clanbattle_qq.commit_kill_record.finish("你还挂在其他树上，先下树再说吧")


@clanbattle_qq.queue.handle()
async def commit_in_progress(bot: Bot, event: GroupMessageEvent, state: T_State = State()):
    print(state['_matched_groups'])
    uid = str(event.user_id)
    challenge_boss = int(state['_matched_groups'][3]
                         ) if state['_matched_groups'][3] else None
    comment = state['_matched_groups'][5]
    clan = clanbattle.get_clan_data(str(event.group_id))
    if not clan:
        await clanbattle_qq.queue.finish("本群还未创建公会，发送“创建[台日]服公会”来创建公会")
    if not clan.check_joined_clan(str(event.user_id)):
        await clanbattle_qq.queue.finish("您还没有加入公会，请发送“加入公会”来加入公会哦")
    if not challenge_boss:
        if progress := clan.get_battle_in_progress(uid=uid):
            clan.update_battle_in_progress_record(uid, comment)
            await clanbattle_qq.queue.finish("修改出刀备注成功！")
    msg = ""
    if processes := clan.get_battle_in_progress(boss=challenge_boss):
        in_process_list = []
        for proc in processes:
            if proc.comment and proc.comment != "":
                in_process_list.append(
                    f"{clan.get_user_info(proc.member_uid).uname}：{proc.comment}")
            else:
                in_process_list.append(
                    clan.get_user_info(proc.member_uid).uname)
        msg = "、".join(in_process_list) + "正在对当前boss出刀，请注意"
    result = clan.commit_battle_in_progress(uid, challenge_boss, comment)
    if result == CommitInProgressResult.success:
        if not msg == "":
            await clanbattle_qq.queue.send(msg)
            await asyncio.sleep(0.2)
        await clanbattle_qq.queue.finish(MessageSegment.at(uid) + f"开始挑战{challenge_boss}王")
    elif result == CommitInProgressResult.already_in_battle:
        await clanbattle_qq.queue.finish("您已经有正在挑战的boss")
    elif result == CommitInProgressResult.illegal_target_boss:
        await clanbattle_qq.queue.finish("您目前无法挑战这个boss")
    elif result == CommitInProgressResult.member_not_in_clan:
        await clanbattle_qq.queue.finish("您还未加入公会，请发送“加入公会”加入")
    elif result == CommitInProgressResult.already_in_tree:
        await clanbattle_qq.queue.finish("你还挂在其他树上，先下树再说吧")
    elif result == CommitInProgressResult.boss_not_challengeable:
        await clanbattle_qq.queue.finish("现在无法挑战这个boss，别在这发癫了！")

@clanbattle_qq.on_tree.handle()
async def commit_on_tree(bot: Bot, event: GroupMessageEvent, state: T_State = State()):
    uid = str(event.user_id)
    challenge_boss = int(state['_matched_groups'][0]
                         ) if state['_matched_groups'][0] else None
    comment = state['_matched_groups'][2]
    if not state['_matched_groups'][4]:
        uid = str(event.user_id)
    else:
        uid = state['_matched_groups'][4]
    clan = clanbattle.get_clan_data(str(event.group_id))
    if not clan:
        await clanbattle_qq.on_tree.finish("本群还未创建公会，发送“创建[台日]服公会”来创建公会")
    if not clan.check_joined_clan(str(event.user_id)):
        await clanbattle_qq.on_tree.finish("您还没有加入公会，请发送“加入公会”来加入公会哦")
    if not challenge_boss:
        if in_proc := clan.get_battle_on_tree(uid):
            clan.update_on_tree_record(uid, comment)
            await clanbattle_qq.on_tree.finish("挂树备注更新成功！")
            return
        if progress := clan.get_battle_in_progress(uid=uid):
            challenge_boss = progress[0].target_boss
        else:
            await clanbattle_qq.commit_record.finish("您还没有正在挑战的boss，请发送“挂树x ”来挂树")
    result = clan.commit_battle_on_tree(uid, challenge_boss, comment)
    if result == CommitBattlrOnTreeResult.success:
        await clanbattle_qq.on_tree.finish("嘿呀，" + MessageSegment.at(uid) + f"在{challenge_boss}王挂树了")
    elif result == CommitBattlrOnTreeResult.already_in_other_boss_progress:
        await clanbattle_qq.on_tree.finish("您已经申请挑战其他boss了")
    elif result == CommitBattlrOnTreeResult.already_on_tree:
        await clanbattle_qq.on_tree.finish("您已经挂在树上了，别搁这挂树了")
    elif result == CommitBattlrOnTreeResult.illegal_target_boss:
        await clanbattle_qq.on_tree.finish("您现在还不能挂在这棵树上")
    elif result == CommitBattlrOnTreeResult.member_not_in_clan:
        await clanbattle_qq.on_tree.finish("您还未加入公会，请发送“加入公会”加入")
    elif result == CommitBattlrOnTreeResult.boss_not_challengeable:
        await clanbattle_qq.on_tree.finish("现在无法挑战这个boss，别在这发癫了！")


@clanbattle_qq.subscribe.handle()
async def commit_subscribe(bot: Bot, event: GroupMessageEvent, state: T_State = State()):
    uid = str(event.user_id)
    challenge_boss = int(state['_matched_groups'][0])
    comment = state['_matched_groups'][4]
    cycle = int(state['_matched_groups'][2]
                ) if state['_matched_groups'][2] else None
    clan = clanbattle.get_clan_data(str(event.group_id))
    if not clan:
        await clanbattle_qq.subscribe.finish("本群还未创建公会，发送“创建[台日]服公会”来创建公会")
    if not clan.check_joined_clan(str(event.user_id)):
        await clanbattle_qq.subscribe.finish("您还没有加入公会，请发送“加入公会”来加入公会哦")
    result = clan.commit_batle_subscribe(uid, challenge_boss, cycle,  comment)
    if result == CommitSubscribeResult.success:
        await clanbattle_qq.subscribe.finish("预约成功")
    elif result == CommitSubscribeResult.boss_cycle_already_killed:
        await clanbattle_qq.subscribe.finish("当前boss已经被击杀")
    elif result == CommitSubscribeResult.already_in_progress:
        await clanbattle_qq.subscribe.finish("您已经在挑战该boss了")
    elif result == CommitSubscribeResult.already_subscribed:
        await clanbattle_qq.subscribe.finish("您已经预约过该boss了")
    elif result == CommitSubscribeResult.member_not_in_clan:
        await clanbattle_qq.subscribe.finish("您还未加入公会，请发送“加入公会”加入")


@clanbattle_qq.join_clan.handle()
async def join_clan(bot: Bot, event: GroupMessageEvent, state: T_State = State()):
    if not state['_matched_groups'][1]:
        uid = str(event.user_id)
    else:
        uid = state['_matched_groups'][1]
    clan = clanbattle.get_clan_data(str(event.group_id))
    if not clan:
        await clanbattle_qq.join_clan.finish("本群还未创建公会，发送“创建[台日]服公会”来创建公会")
    if clan.check_joined_clan(uid):
        await clanbattle_qq.join_clan.finish("您已经加入公会了，无需再加入")
    group_member_list = await bot.get_group_member_list(group_id=event.group_id)
    for member in group_member_list:
        if member["user_id"] != int(bot.self_id) and member["user_id"] == int(uid):
            clan.add_clan_member(str(
                member["user_id"]), member["card"] if member["card"] != "" else member["nickname"])
    await clanbattle_qq.join_clan.finish("加入成功")


@clanbattle_qq.today_record.handle()
async def _(bot: Bot, event: GroupMessageEvent, state: T_State = State()):
    uid = str(event.user_id)
    clan = clanbattle.get_clan_data(str(event.group_id))
    if not clan:
        await clanbattle_qq.undo_record_commit.finish("本群还未创建公会，发送“创建[台日]服公会”来创建公会")
    if not clan.check_joined_clan(str(event.user_id)):
        await clanbattle_qq.undo_record_commit.finish("您还没有加入公会，请发送“加入公会”来加入公会哦")
    records = clan.get_today_record(uid)

    pass


@clanbattle_qq.undo_record_commit.handle()
async def undo_record_commit(bot: Bot, event: GroupMessageEvent, state: T_State = State()):
    uid = str(event.user_id)
    clan = clanbattle.get_clan_data(str(event.group_id))
    if not clan:
        await clanbattle_qq.undo_record_commit.finish("本群还未创建公会，发送“创建[台日]服公会”来创建公会")
    if not clan.check_joined_clan(str(event.user_id)):
        await clanbattle_qq.undo_record_commit.finish("您还没有加入公会，请发送“加入公会”来加入公会哦")
    boss_count = int(state['_matched_groups'][0]) if state['_matched_groups'][0] else None
    if boss_count:
        recent_record = clan.get_recent_record(boss=boss_count)
        if recent_record:
            challenge_uid = recent_record[0].member_uid
            proxy_uid = recent_record[0].proxy_report_uid
            if uid in (challenge_uid, proxy_uid) or clan.check_admin_permission(str(event.user_id)):
                ret = clan.delete_recent_record(challenge_uid)
                if ret:
                    msg = "出刀撤回成功"
                    if boss_count:
                        boss_status = clan.get_current_boss_state()
                        boss = boss_status[boss_count-1]
                        msg += f"\n============\n当前{boss_count}王位于{boss.target_cycle}周目，剩余血量{Tools.get_num_str_with_dot(boss.boss_hp)}\n"
                    await clanbattle_qq.undo_record_commit.finish(msg)
                else:
                    await clanbattle_qq.undo_record_commit.finish("出刀撤回失败，内部错误")
            else:
                await clanbattle_qq.undo_record_commit.finish("出刀撤回失败，只有管理员能够撤回其他人的刀哦")

        else:
            await clanbattle_qq.undo_record_commit.finish("出刀撤回失败，未找到对应的出刀记录")
    else:
        recent_record = clan.get_recent_record(uid=uid)
        if not recent_record:
            await clanbattle_qq.undo_record_commit.finish("未找到最近的出刀记录")
        recent_boss_record = clan.get_recent_record(boss=recent_record[0].target_boss)
        if recent_record[0].record_time != recent_boss_record[0].record_time:
            await clanbattle_qq.undo_record_commit.finish(f"您在最近一次出刀后该boss有其他的出刀记录，无法撤回，若是管理员或代报刀可使用'撤回 {recent_record[0].target_boss}'来撤回其他人的出刀")
        ret = clan.delete_recent_record(recent_record[0].member_uid)
        if ret:
            msg = "出刀撤回成功"
            boss_count :int = recent_record[0].target_boss
            if boss_count:
                boss_status = clan.get_current_boss_state()
                boss = boss_status[boss_count -1]
                msg += f"\n============\n当前{boss_count}王位于{boss.target_cycle}周目，剩余血量{Tools.get_num_str_with_dot(boss.boss_hp)}\n"
            await clanbattle_qq.undo_record_commit.finish(msg)
        else:
            await clanbattle_qq.undo_record_commit.finish("出刀撤回失败，内部错误")

            



@clanbattle_qq.un_on_tree.handle()
async def _(bot: Bot, event: GroupMessageEvent, state: T_State = State()):
    uid = str(event.user_id)
    clan = clanbattle.get_clan_data(str(event.group_id))
    if not clan:
        await clanbattle_qq.un_on_tree.finish("本群还未创建公会，发送“创建[台日]服公会”来创建公会")
    if not clan.check_joined_clan(str(event.user_id)):
        await clanbattle_qq.un_on_tree.finish("您还没有加入公会，请发送“加入公会”来加入公会哦")
    result = clan.delete_battle_on_tree(uid)
    if result:
        await clanbattle_qq.un_on_tree.finish("下树成功")
    else:
        await clanbattle_qq.un_on_tree.finish("还没有挂在树上就别下树了")


@clanbattle_qq.unsubscribe.handle()
async def unsubscribe_boss(bot: Bot, event: GroupMessageEvent, state: T_State = State()):
    uid = str(event.user_id)
    challenge_boss = int(state['_matched_groups'][0])
    cycle = int(state['_matched_groups'][2]
                ) if state['_matched_groups'][2] else None
    clan = clanbattle.get_clan_data(str(event.group_id))
    if not clan:
        await clanbattle_qq.unsubscribe.finish("本群还未创建公会，发送“创建[台日]服公会”来创建公会")
    if not clan.check_joined_clan(str(event.user_id)):
        await clanbattle_qq.unsubscribe.finish("您还没有加入公会，请发送“加入公会”来加入公会哦")
    result = clan.delete_battle_subscribe(uid, challenge_boss, cycle)
    if result:
        await clanbattle_qq.unsubscribe.finish("取消预约成功desu")
    else:
        await clanbattle_qq.unsubscribe.finish("取消预约失败，请确认您已经预约该boss喵")


@clanbattle_qq.query_recent_record.handle()
async def query_recent_record(bot: Bot, event: GroupMessageEvent, state: T_State = State()):
    target_qq = state['_matched_groups'][1]
    clan = clanbattle.get_clan_data(str(event.group_id))
    if not clan:
        await clanbattle_qq.query_recent_record.finish("本群还未创建公会，发送“创建[台日]服公会”来创建公会")
    if not clan.check_joined_clan(str(event.user_id)):
        await clanbattle_qq.query_recent_record.finish("您还没有加入公会，请发送“加入公会”来加入公会哦")
    if not target_qq:
        records = clan.get_recent_record(num=5)
        if not records:
            await clanbattle_qq.query_recent_record.finish("现在还没有出刀记录哦，快去出刀吧")
        else:
            msg = "最近五条出刀记录：\n\n"
            for record in records:
                if record.member_uid == "admin":
                    continue
                msg += f"{clan.get_user_info(record.member_uid).uname}于{(record.record_time +datetime.timedelta(hours=8)).strftime('%m月%d日%H时%M分')}对{record.target_cycle}周目{record.target_boss}王造成了{Tools.get_num_str_with_dot(record.damage)}点伤害\n\n"
            msg += "更多记录请前往网页端查看，查询指定成员请at"
            await clanbattle_qq.query_recent_record.finish(msg)
    else:
        if not clan.check_joined_clan(target_qq):
            await clanbattle_qq.query_recent_record.finish("对方还没有加入公会哦")
        records = clan.get_today_record(uid=target_qq)
        if not records:
            await clanbattle_qq.query_recent_record.finish("Ta还没有出刀记录哦，快催Ta去出刀吧")
        else:
            msg = f"{clan.get_user_name(target_qq)}今日的出刀记录："
            for record in records:
                msg += f"\n{record.target_cycle}周目{record.target_boss}王 {Tools.get_num_str_with_dot(record.damage)} "
                if record.remain_next_chance:
                    msg += "尾刀"
                elif record.is_extra_time:
                    msg += "补偿刀"
                else:
                    msg += "完整刀"
            await clanbattle_qq.query_recent_record.finish(msg)
                
                


        

@clanbattle_qq.sl.handle()
async def commit_sl(bot: Bot, event: GroupMessageEvent, state: T_State = State()):
    proxy_report_uid: str = None
    uid = str(event.user_id)
    is_query_sl = True if state['_matched_groups'][0] else False
    challenge_boss = int(state['_matched_groups'][1]
                         ) if state['_matched_groups'][1] else None
    comment = state['_matched_groups'][3]
    if not state['_matched_groups'][5]:
        uid = str(event.user_id)
    else:
        uid = state['_matched_groups'][5]
        proxy_report_uid = str(event.user_id)
    clan = clanbattle.get_clan_data(str(event.group_id))
    if not clan:
        await clanbattle_qq.sl.finish("本群还未创建公会，发送“创建[台日]服公会”来创建公会")
    if not clan.check_joined_clan(str(event.user_id)):
        await clanbattle_qq.sl.finish("您还没有加入公会，请发送“加入公会”来加入公会哦")
    if is_query_sl:
        sl = clan.get_today_battle_sl(uid=uid)
        if sl:
            await clanbattle_qq.sl.finish("您今天已经sl过了")
        else:
            await clanbattle_qq.sl.finish("您今天还没有使用过sl哦")
        return
    if not challenge_boss:
        if progress := clan.get_battle_in_progress(uid=uid):
            challenge_boss = progress[0].target_boss
        elif on_treee := clan.get_battle_on_tree(uid=uid):
            challenge_boss = on_treee[0].target_boss
    result = clan.commit_battle_sl(
        uid, challenge_boss, comment, proxy_report_uid)
    if result == CommitSLResult.success:
        await clanbattle_qq.sl.finish("sl已经记录")
    elif result == CommitSLResult.already_sl:
        await clanbattle_qq.sl.finish("您今天已经sl过了")
    elif result == CommitSLResult.illegal_target_boss:
        await clanbattle_qq.on_tree.finish("您还不能挑战这个boss，别sl了")
    elif result == CommitSLResult.member_not_in_clan:
        await clanbattle_qq.sl.finish("您还未加入公会，请发送“加入公会”加入")


@clanbattle_qq.unqueue.handle()
async def unqueue_boss(bot: Bot, event: GroupMessageEvent, state: T_State = State()):
    uid = str(event.user_id)
    clan = clanbattle.get_clan_data(str(event.group_id))
    if not clan:
        await clanbattle_qq.unqueue.finish("本群还未创建公会，发送“创建[台日]服公会”来创建公会")
    if not clan.check_joined_clan(str(event.user_id)):
        await clanbattle_qq.unqueue.finish("您还没有加入公会，请发送“加入公会”来加入公会哦")
    result = clan.delete_battle_in_progress(uid)
    if result:
        await clanbattle_qq.unsubscribe.finish("取消申请成功desu")
    else:
        await clanbattle_qq.unsubscribe.finish("取消申请失败，请确认您已经申请出刀该boss")


@clanbattle_qq.showqueue.handle()
async def show_queue(bot: Bot, event: GroupMessageEvent, state: T_State = State()):
    clan = clanbattle.get_clan_data(str(event.group_id))
    if not clan:
        await clanbattle_qq.showqueue.finish("本群还未创建公会，发送“创建[台日]服公会”来创建公会")
    if not clan.check_joined_clan(str(event.user_id)):
        await clanbattle_qq.showqueue.finish("您还没有加入公会，请发送“加入公会”来加入公会哦")
    progresses = clan.get_battle_in_progress()
    if not progresses:
        await clanbattle_qq.showqueue.finish("当前没有人申请出刀，赶快来出刀吧")
    else:
        msg = "当前正在出刀的成员：\n"
        for i in range(1, 6):
            prog = clan.get_battle_in_progress(boss=i)
            if prog:
                msg += f"{i}王：\n"
                for pro in prog:
                    msg += f"{clan.get_user_info(pro.member_uid).uname}"
                    if pro.comment and pro.comment != "":
                        msg += f" : {pro.comment}"
                    msg += "\n"
        await clanbattle_qq.showqueue.finish(msg.strip())


@clanbattle_qq.showsubscribe.handle()
async def show_subscribe(bot: Bot, event: GroupMessageEvent, state: T_State = State()):
    clan = clanbattle.get_clan_data(str(event.group_id))
    if not clan:
        await clanbattle_qq.showsubscribe.finish("本群还未创建公会，发送“创建[台日]服公会”来创建公会")
    if not clan.check_joined_clan(str(event.user_id)):
        await clanbattle_qq.showsubscribe.finish("您还没有加入公会，请发送“加入公会”来加入公会哦")
    subs = clan.get_battle_subscribe()
    boss_status = clan.get_current_boss_state()
    if not subs:
        await clanbattle_qq.showsubscribe.finish("当前没有人预约boss，赶快来出刀吧")
    else:
        msg = "当前预约的成员：\n"
        for i in range(1, 6):
            subs = clan.get_battle_subscribe(
                boss=i, boss_cycle=boss_status[i-1].target_cycle)
            if subs:
                msg += f"{i}王：\n"
                for sub in subs:
                    msg += f"{clan.get_user_info(sub.member_uid).uname}"
                    if sub.comment and sub.comment != "":
                        msg += f" : {sub.comment}"
                    msg += "\n"
        if msg == "当前预约的成员：":
            msg = "没有人预约当前周目的boss哦"
        msg += "\n更多其他周目的预约请前往网页面板查看"
        await clanbattle_qq.showsubscribe.finish(msg.strip())


@clanbattle_qq.sl_query.handle()
async def query_sl(bot: Bot, event: GroupMessageEvent, state: T_State = State()):
    uid = str(event.user_id)
    if not state['_matched_groups'][1]:
        uid = str(event.user_id)
    else:
        uid = state['_matched_groups'][1]
    clan = clanbattle.get_clan_data(str(event.group_id))
    if not clan:
        await clanbattle_qq.sl_query.finish("本群还未创建公会，发送“创建[台日]服公会”来创建公会")
    if not clan.check_joined_clan(str(event.user_id)):
        await clanbattle_qq.sl_query.finish("您还没有加入公会，请发送“加入公会”来加入公会哦")
    sl = clan.get_today_battle_sl(uid=uid)
    if sl:
        await clanbattle_qq.sl_query.finish("您今天已经sl过了")
    else:
        await clanbattle_qq.sl_query.finish("您今天还没有使用过sl哦")


@clanbattle_qq.query_on_tree.handle()
async def query_on_tree(bot: Bot, event: GroupMessageEvent, state: T_State = State()):
    clan = clanbattle.get_clan_data(str(event.group_id))
    if not clan:
        await clanbattle_qq.query_on_tree.finish("本群还未创建公会，发送“创建[台日]服公会”来创建公会")
    if not clan.check_joined_clan(str(event.user_id)):
        await clanbattle_qq.query_on_tree.finish("您还没有加入公会，请发送“加入公会”来加入公会哦")
    on_tree_dict = {}
    for i in range(1, 6):
        on_tree_dict[i] = []
    msg = ""
    first_flag = True
    for i in range(1, 6):
        on_tree_list = clan.get_battle_on_tree(boss=i)
        if on_tree_list and len(on_tree_list) > 0:
            msg += f"\n==={i}王===\n" if i == 1 else f"==={i}王===\n"
            for on_tree_item in on_tree_list:
                commemt = f"：{on_tree_item.comment}" if on_tree_item.comment and on_tree_item.comment != "" else ""
                msg += f"{clan.get_user_name(on_tree_item.member_uid)}{commemt}（{Tools.get_chinese_timedetla(on_tree_item.record_time)}）"
                #msg += f"当前{clan.get_user_name(on_tree_item.member_uid)}{commemt}挂在{on_tree_item.target_boss}王上"
                msg += "\n"
    if msg == "":
        msg = "当前没有人挂在树上哦"
    await clanbattle_qq.query_on_tree.finish(msg.strip())


@clanbattle_qq.reset_password.handle()
async def reset_password(bot: Bot, event: PrivateMessageEvent, state: T_State = State()):
    uid = str(event.user_id)
    if user := ClanBattleData.get_user_info(uid):
        WebAuth.set_password(uid, state['_matched_groups'][0])
        await clanbattle_qq.reset_password.finish(
            f"密码已经重置为：{state['_matched_groups'][0]}，请前往网页端登录")
    else:
        await clanbattle_qq.reset_password.finish("不存在您的用户资料，请先加入一个公会")


@clanbattle_qq.leave_clan.handle()
async def leave_clan(bot: Bot, event: GroupMessageEvent, state: T_State = State()):
    uid = str(event.user_id)
    clan = clanbattle.get_clan_data(str(event.group_id))
    if not clan:
        await clanbattle_qq.leave_clan.finish("本群还未创建公会，发送“创建[台日]服公会”来创建公会")
    if clan.delete_clan_member(uid):
        await clanbattle_qq.leave_clan.finish("退出公会成功！")
    else:
        await clanbattle_qq.leave_clan.finish("退出公会失败，可能还没有加入公会？")


@clanbattle_qq.refresh_clan_admin.handle()
async def refresh_clan_admin(bot: Bot, event: GroupMessageEvent, state: T_State = State()):
    gid = str(event.group_id)
    clan = clanbattle.get_clan_data(gid)
    if not clan:
        await clanbattle_qq.refresh_clan_admin.finish("本群还未创建公会，发送“创建[台日]服公会”来创建公会")
    if not clan.check_joined_clan(str(event.user_id)):
        await clanbattle_qq.refresh_clan_admin.finish("您还没有加入公会，请发送“加入公会”来加入公会哦")
    group_member_list = await bot.get_group_member_list(group_id=event.group_id)
    admin_list = []
    for member in group_member_list:
        if member["role"] in ["owner", "admin"] and member["user_id"] != int(bot.self_id):
            admin_list.append(str(member["user_id"]))
    clan.refresh_clan_admin(admin_list)
    await clanbattle_qq.refresh_clan_admin.finish("刷新管理员列表成功")


@clanbattle_qq.rename_clan.handle()
async def rename_clan(bot: Bot, event: GroupMessageEvent, state: T_State = State()):
    gid = str(event.group_id)
    uid = str(event.user_id)
    clan = clanbattle.get_clan_data(gid)
    if not clan:
        await clanbattle_qq.rename_clan.finish("本群还未创建公会，发送“创建[台日]服公会”来创建公会")
    if not clan.check_joined_clan(str(event.user_id)):
        await clanbattle_qq.rename_clan.finish("您还没有加入公会，请发送“加入公会”来加入公会哦")
    if not clan.check_admin_permission(uid):
        await clanbattle_qq.rename_clan.finish("您不是会战管理员，无权使用本指令")
    else:
        clan.rename_clan(state['_matched_groups'][0])
        await clanbattle_qq.rename_clan.finish("修改公会名称成功")


@clanbattle_qq.remove_clan_member.handle()
async def remove_clan_member(bot: Bot, event: GroupMessageEvent, state: T_State = State()):
    gid = str(event.group_id)
    uid = str(event.user_id)
    clan = clanbattle.get_clan_data(gid)
    if not clan:
        await clanbattle_qq.remove_clan_member.finish("本群还未创建公会，发送“创建[台日]服公会”来创建公会")
    if not clan.check_joined_clan(str(event.user_id)):
        await clanbattle_qq.remove_clan_member.finish("您还没有加入公会，请发送“加入公会”来加入公会哦")
    if not clan.check_admin_permission(uid):
        await clanbattle_qq.remove_clan_member.finish("您不是会战管理员，无权使用本指令")
    remove_uid = state['_matched_groups'][0]
    if clan.delete_clan_member(remove_uid):
        await clanbattle_qq.remove_clan_member.finish("成功将该成员移出公会")
    else:
        await clanbattle_qq.remove_clan_member.finish("移出公会失败，Ta可能还未加入公会？")


@clanbattle_qq.rename_clan_uname.handle()
async def rename_clan_uname(bot: Bot, event: GroupMessageEvent, state: T_State = State()):
    gid = str(event.group_id)
    clan = clanbattle.get_clan_data(gid)
    if not clan:
        await clanbattle_qq.rename_clan_uname.finish("本群还未创建公会，发送“创建[台日]服公会”来创建公会")
    if not clan.check_joined_clan(str(event.user_id)):
        await clanbattle_qq.rename_clan_uname.finish("您还没有加入公会，请发送“加入公会”来加入公会哦")
    if not state['_matched_groups'][2]:
        uid = str(event.user_id)
    else:
        if not clan.check_admin_permission(str(event.user_id)):
            await clanbattle_qq.rename_clan_uname.finish("您不是会战管理员，无权修改他人昵称")
        uid = state['_matched_groups'][2]
    uname = state['_matched_groups'][0]
    if clan.rename_user_uname(uid, uname):
        await clanbattle_qq.remove_clan_member.finish("修改昵称成功")
    else:
        await clanbattle_qq.remove_clan_member.finish("修改昵称失败，可能用户还没加入任何公会？")


@clanbattle_qq.force_change_boss_status.handle()
async def force_change_boss_status(bot: Bot, event: GroupMessageEvent, state: T_State = State()):
    gid = str(event.group_id)
    uid = str(event.user_id)
    clan = clanbattle.get_clan_data(gid)
    challenge_boss = int(state['_matched_groups'][0])
    cycle = int(state['_matched_groups'][1])
    remain_hp = state['_matched_groups'][2]
    if not clan:
        await clanbattle_qq.rename_clan.finish("本群还未创建公会，发送“创建[台日]服公会”来创建公会")
    if not clan.check_joined_clan(str(event.user_id)):
        await clanbattle_qq.rename_clan.finish("您还没有加入公会，请发送“加入公会”来加入公会哦")
    if not clan.check_admin_permission(uid):
        await clanbattle_qq.rename_clan.finish("您不是会战管理员，无权使用本指令")
    else:
        clan.commit_force_change_boss_status(challenge_boss, cycle, remain_hp)
        await clanbattle_qq.rename_clan.finish("强制修改boss状态成功")


@clanbattle_qq.help.handle()
async def send_bot_help(bot: Bot, event: MessageEvent, state: T_State = State()):
    if isinstance(event, GroupMessageEvent) or isinstance(event, PrivateMessageEvent):
        await clanbattle_qq.help.finish(f"Yuki Clanbattle Ver{VERSION}\n会战帮助请见{WEB_URL}help")


@clanbattle_qq.webview.handle()
async def send_webview(bot: Bot, event: MessageEvent, state: T_State = State()):
    if isinstance(event, GroupMessageEvent) or isinstance(event, PrivateMessageEvent):
        await clanbattle_qq.webview.finish(f"请登录{WEB_URL}clan查看详情，首次登录前请私聊bot“设置密码+要设置的密码”来设置密码（由于风控暂时无回复）")


@clanbattle_qq.join_all_member.handle()
async def join_all_member(bot: Bot, event: GroupMessageEvent, state: T_State = State()):
    gid = str(event.group_id)
    clan = clanbattle.get_clan_data(gid)
    if not clan:
        await clanbattle_qq.join_all_member.finish("本群还未创建公会，发送“创建[台日]服公会”来创建公会")
    if not clan.check_joined_clan(str(event.user_id)):
        await clanbattle_qq.join_all_member.finish("您还没有加入公会，请发送“加入公会”来加入公会哦")
    if not clan.check_admin_permission(str(event.user_id)):
        await clanbattle_qq.join_all_member.finish("您不是会战管理员，无权加入全部成员")
    group_member_list = await bot.get_group_member_list(group_id=event.group_id)
    for member in group_member_list:
        if member["user_id"] != int(bot.self_id):
            if not clan.check_joined_clan(str(member["user_id"])):
                clan.add_clan_member(str(
                    member["user_id"]), member["card"] if member["card"] != "" else member["nickname"])
    await clanbattle_qq.join_all_member.finish("加入全部成员成功")


@clanbattle_qq.switch_current_clanbattle_data.handle()
async def switch_current_clanbattle_data(bot: Bot, event: GroupMessageEvent, state: T_State = State()):
    gid = str(event.group_id)
    uid = str(event.user_id)
    set_num = int(state['_matched_groups'][0])
    clan = clanbattle.get_clan_data(gid)
    if not clan:
        await clanbattle_qq.remove_clan_member.finish("本群还未创建公会，发送“创建[台日]服公会”来创建公会")
    if not clan.check_joined_clan(str(event.user_id)):
        await clanbattle_qq.remove_clan_member.finish("您还没有加入公会，请发送“加入公会”来加入公会哦")
    if not clan.check_admin_permission(uid):
        await clanbattle_qq.remove_clan_member.finish("您不是会战管理员，无权使用本指令")
    clan.set_current_clanbattle_data(set_num)
    await clanbattle_qq.switch_current_clanbattle_data.finish(f"切换会战档案成功，当前使用会战档案{set_num}")


@clanbattle_qq.clear_current_clanbattle_data.handle()
async def clear_current_clanbattle_data(bot: Bot, event: GroupMessageEvent, state: T_State = State()):
    gid = str(event.group_id)
    uid = str(event.user_id)
    clan = clanbattle.get_clan_data(gid)
    if not clan:
        await clanbattle_qq.clear_current_clanbattle_data.finish("本群还未创建公会，发送“创建[台日]服公会”来创建公会")
    if not clan.check_joined_clan(str(event.user_id)):
        await clanbattle_qq.clear_current_clanbattle_data.finish("您还没有加入公会，请发送“加入公会”来加入公会哦")
    if not clan.check_admin_permission(uid):
        await clanbattle_qq.clear_current_clanbattle_data.finish("您不是会战管理员，无权使用本指令")
    clan.clear_current_clanbattle_data()
    await clanbattle_qq.clear_current_clanbattle_data.finish(f"清空会战档案成功！")


@clanbattle_qq.add_clanbattle_admin.handle()
async def add_clanbattle_admin(bot: Bot, event: GroupMessageEvent, state: T_State = State()):
    gid = str(event.group_id)
    uid = str(event.user_id)
    new_admin_uid = state['_matched_groups'][1]
    clan = clanbattle.get_clan_data(gid)
    if not clan:
        await clanbattle_qq.add_clanbattle_admin.finish("本群还未创建公会，发送“创建[台日]服公会”来创建公会")
    if not clan.check_joined_clan(str(event.user_id)):
        await clanbattle_qq.add_clanbattle_admin.finish("您还没有加入公会，请发送“加入公会”来加入公会哦")
    if not clan.check_admin_permission(uid):
        await clanbattle_qq.add_clanbattle_admin.finish("您不是会战管理员，无权使用本指令")
    admin_list = clan.get_db_strlist_list(clan.clan_info.clan_admin)
    admin_list.append(new_admin_uid)
    clan.refresh_clan_admin(admin_list)
