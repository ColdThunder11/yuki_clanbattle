import asyncio
from peewee import *
from typing import Dict, List
import datetime
import nonebot
from enum import Enum
from functools import wraps

from nonebot.adapters.onebot.v11 import Bot
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from peewee import _BoundModelsContext
from .db import BaseModel, User, ClanInfo, BattleOnTree, BattleRecord, BattleInProgress, BattleSL, BattleSubscribe
from .exception import ClanBattleException, ClanBattleDamageParseException
from typing import Any, List, Union, Optional, Tuple
import json
import uuid
import hashlib
import pydantic

from .config import get_config


class BossInfo(pydantic.BaseModel):
    class BossAreaInfo(pydantic.BaseModel):
        jp: List[List[int]]
        tw: List[List[int]]
        cn: List[List[int]]

    class BossCycleInfo(pydantic.BaseModel):
        jp: List[int]
        tw: List[int]
        cn: List[int]

    boss: BossAreaInfo
    cycle: BossCycleInfo


boss_info: dict = None


class BossStatus:
    target_cycle: int
    stage: int
    target_boss: int
    boss_hp: int
    max_boss_hp: int

    def __init__(self, boss: int, cycle: int, stage: int, hp: int, max_boss_hp: int) -> None:
        self.target_cycle = cycle
        self.target_boss = boss
        self.boss_hp = hp
        self.stage = stage
        self.max_boss_hp = max_boss_hp


class MemberInfo:
    uid: str
    uname: str

    def __init__(self, uid: str, uname: str) -> None:
        self.uid = uid
        self.uname = uname


class TodayBattleStatus:
    uid: str
    today_challenged: int
    addition_challeng: int
    remain_addition_challeng: int
    last_is_addition: bool
    use_sl: bool

    def __init__(self, uid: str, today_challenged: int, addition_challeng: int, remain_addition_challeng: int, last_is_addition: bool, use_sl: bool) -> None:
        self.uid = uid
        self.today_challenged = today_challenged
        self.addition_challeng = addition_challeng
        self.remain_addition_challeng = remain_addition_challeng
        self.last_is_addition = last_is_addition
        self.use_sl = use_sl


class CommitRecordResult(Enum):
    success = 0
    illegal_damage_inpiut = 1
    damage_out_of_hp = 2
    check_record_legal_failed = 3
    member_not_in_clan = 4
    boss_not_challengeable = 5
    on_another_tree = 6


class CommitInProgressResult(Enum):
    success = 0
    illegal_target_boss = 1
    already_in_battle = 2
    already_in_tree = 3
    member_not_in_clan = 4
    boss_not_challengeable = 5


class CommitSubscribeResult(Enum):
    success = 0
    boss_cycle_already_killed = 1
    already_in_progress = 2
    member_not_in_clan = 3
    already_subscribed = 4


class CommitBattlrOnTreeResult(Enum):
    success = 0
    already_in_other_boss_progress = 1
    already_on_tree = 2
    member_not_in_clan = 3
    illegal_target_boss = 4
    boss_not_challengeable = 5


class CommitSLResult(Enum):
    success = 0
    already_sl = 1
    member_not_in_clan = 2
    illegal_target_boss = 3


class NewRecordLegalCheckResult(Enum):
    success = 0
    on_another_tree = 1
    boss_not_challengeable = 2


class ClanBattleData:

    cache = {}

    def __init__(self, gid: str) -> None:
        clan: ClanInfo = ClanInfo.get(ClanInfo.clan_gid == gid)
        if not clan:
            raise ClanBattleException("公会不存在")
        self.clan_info = clan

    def cache_return(get_func):

        @wraps(get_func)
        def decorated(*args, **kwargs):
            return get_func(*args, **kwargs)
            cache_key = str(args) + str(kwargs) + str(get_func)
            cache_obj: dict = args[0].cache
            cache_res = cache_obj.get(cache_key, "@*^")
            if cache_res != "@*^":
                #print("cache hit")
                return cache_res
            else:
                result = get_func(*args, **kwargs)
                cache_obj[cache_key] = result
                #print("cache not hit")
                return result

        return decorated

    def clear_cache(get_func):

        @wraps(get_func)
        def decorated(*args, **kwargs):
            ret = get_func(*args, **kwargs)
            args[0].cache = {}
            return ret

        return decorated

    @staticmethod
    def get_db_strlist_list(text_field: TextField) -> List[str]:
        return str(text_field).split("|") if text_field else []

    @staticmethod
    def get_db_strlist_str(sql_list: List[str]) -> str:
        return "|".join(sql_list) if sql_list else None

    @staticmethod
    def parse_damage(damage_str: str) -> int:
        try:
            if damage_str.endswith(("E", "e")):
                damage_num = int(float(damage_str[:-1]) * 100000000)
            elif damage_str.endswith(("kw", "kW", "Kw", "KW")):
                damage_num = int(float(damage_str[:-2]) * 10000000)
            elif damage_str.endswith(("bw", "bW", "Bw", "BW")):
                damage_num = int(float(damage_str[:-2]) * 1000000)
            elif damage_str.endswith(("w", "W")):
                damage_num = int(float(damage_str[:-1]) * 10000)
            elif damage_str.endswith(("k", "K")):
                damage_num = int(float(damage_str[:-1]) * 1000)
            else:
                damage_num = int(damage_str)
            return damage_num
        except:
            raise ClanBattleDamageParseException()

    @staticmethod
    def create_clan(gid: str, clan_name: str, clan_type: str, clan_admin: List[str]):
        ClanInfo.create(clan_gid=gid, clan_name=clan_name, create_time=datetime.datetime.utcnow(),
                        clan_type=clan_type, clan_admin=ClanBattleData.get_db_strlist_str(clan_admin))

    @staticmethod
    def delete_clan(gid: str):
        qry = ClanInfo.delete().where(ClanInfo.clan_gid == gid)
        qry.execute()

    @staticmethod
    def get_user_info(uid: str) -> User:
        user_list = User.select().where(User.qq_uid == uid)
        return user_list[0] if user_list else None

    @staticmethod
    def get_user_name(uid: str) -> User:
        user_list = User.select().where(User.qq_uid == uid)
        return user_list[0].uname if user_list else None

    @staticmethod
    def rename_user_uname(uid: str, uname: str) -> bool:
        user = ClanBattleData.get_user_info(uid)
        if not user:
            return False
        user.uname = uname
        user.save()
        return True

    def get_today_datetime(self) -> Tuple[datetime.datetime, datetime.datetime]:
        start_time = None
        end_time = None
        detla = datetime.timedelta(
            hours=9) if self.clan_info.clan_type == "jp" else datetime.timedelta(hours=8)
        now_time = datetime.datetime.utcnow() + detla
        now_time_today = datetime.datetime.strptime(
            str(now_time.date()), "%Y-%m-%d")
        if now_time.hour < 5:
            start_time = now_time_today - datetime.timedelta(hours=19) - detla
            end_time = now_time_today + datetime.timedelta(hours=5) - detla
        else:
            start_time = now_time_today + datetime.timedelta(hours=5) - detla
            end_time = now_time_today + datetime.timedelta(hours=29) - detla
        return (start_time, end_time)

    @cache_return
    def get_clan_members(self) -> List[str]:
        return self.get_db_strlist_list(self.clan_info.clan_members)

    @cache_return
    def get_clan_members_with_info(self) -> List[MemberInfo]:
        member_list = self.get_db_strlist_list(self.clan_info.clan_members)
        ret_list = []
        for member in member_list:
            user: User = self.get_user_info(member)
            member_info = MemberInfo(member, str(user.uname))
            ret_list.append(member_info)
        return ret_list

    @cache_return
    def get_current_clanbattle_data(self) -> int:
        return self.clan_info.current_using_data_num

    @clear_cache
    def set_clan_members(self, members: List[str]):
        self.clan_info.clan_members = self.get_db_strlist_str(members)
        self.clan_info.save()

    @clear_cache
    def set_clan_name(self, clan_name: str):
        self.clan_info.clan_name = clan_name
        self.clan_info.save()

    @clear_cache
    def set_using_data_num(self, num: int):
        self.clan_info.current_using_data_num = num
        self.clan_info.save()

    @clear_cache
    def set_current_clanbattle_data(self, data_num: int):
        self.clan_info.current_using_data_num = data_num
        self.clan_info.save()

    @clear_cache
    def clear_current_clanbattle_data(self):
        clan_record = self.get_record()
        if clan_record:
            for record in clan_record:
                record.delete_instance()
        clan_in_progress = self.get_battle_in_progress()
        if clan_in_progress:
            for in_progress in clan_in_progress:
                in_progress.delete_instance()
        clan_sl = BattleSL.select().where((BattleSL.clan_gid == self.clan_info.clan_gid)
                                          & (BattleSL.using_data_num == self.clan_info.current_using_data_num))
        if clan_sl:
            for sl in clan_sl:
                sl.delete_instance()
        clan_battle_subscribe = self.get_battle_subscribe()
        if clan_battle_subscribe:
            for battle_subscribe in clan_battle_subscribe:
                battle_subscribe.delete_instance()
        battle_on_tree = self.get_battle_on_tree()
        if battle_on_tree:
            for on_tree in battle_on_tree:
                on_tree.delete_instance()

    @clear_cache
    def rename_clan(self, name: str):
        self.clan_info.clan_name = name
        self.clan_info.save()

    @clear_cache
    def add_clan_member(self, uid: str, name: str) -> bool:
        if not self.get_user_info(uid):
            User.create(qq_uid=uid, uname=name,
                        clan_joined=self.clan_info.clan_gid)
            member_list = self.get_clan_members()
            member_list.append(uid)
            self.set_clan_members(member_list)
            return True
        else:
            members = self.get_clan_members()
            if uid in members:
                return False
            user = self.get_user_info(uid)
            joined_clan = self.get_db_strlist_list(user.clan_joined)
            joined_clan.append(self.clan_info.clan_gid)
            user.clan_joined = self.get_db_strlist_str(joined_clan)
            user.save()
            members.append(uid)
            self.set_clan_members(members)
            return True

    @clear_cache
    def delete_clan_member(self, uid: str) -> bool:
        if not (user := self.get_user_info(uid)):
            return False
        joined_clan = self.get_db_strlist_list(user.clan_joined)
        if not self.clan_info.clan_gid in joined_clan:
            return False
        joined_clan.remove(self.clan_info.clan_gid)
        user.clan_joined = self.get_db_strlist_str(joined_clan)
        user.save()
        members = self.get_clan_members()
        members.remove(uid)
        self.set_clan_members(members)
        return True

    @clear_cache
    def refresh_clan_admin(self, admins: List[str]):
        clan = self.clan_info
        clan.clan_admin = self.get_db_strlist_str(admins)
        clan.save()

    @cache_return
    def check_joined_clan(self, uid: str) -> bool:
        user = self.get_user_info(uid)
        if not user:
            return False
        db_list = self.get_db_strlist_list(user.clan_joined)
        if not user or not self.clan_info.clan_gid in db_list:
            return False
        return True

    @cache_return
    def get_record(self, uid: str = None, boss: int = None, cycle: int = None, start_time: datetime.datetime = None, end_time: datetime.datetime = None, num: int = None, time_desc: bool = False) -> List[BattleRecord]:
        res = BattleRecord.select().where((BattleRecord.clan_gid == self.clan_info.clan_gid)
                                          & (BattleRecord.using_data_num == self.clan_info.current_using_data_num))
        if uid:
            res = res.where((BattleRecord.member_uid == uid))
        if boss:
            res = res.where((BattleRecord.target_boss == boss))
        if cycle:
            res = res.where((BattleRecord.target_cycle == cycle))
        if start_time:
            res = res.where((BattleRecord.record_time > start_time))
        if end_time:
            res = res.where((BattleRecord.record_time < end_time))
        if time_desc:
            res = res.order_by(BattleRecord.record_time.desc())
        if num:
            res = res.limit(num)
        return res if res else None

    def get_today_record(self, uid: str = None, boss: int = None, cycle: int = None, num: int = None) -> List[BattleRecord]:
        start_time = None
        end_time = None
        today_time = self.get_today_datetime()
        start_time = today_time[0]
        end_time = today_time[1]
        return self.get_record(uid, boss, cycle, start_time, end_time, num)

    @cache_return
    def get_recent_record(self, uid: str = None, boss: int = None, num: int = 1) -> List[BattleRecord]:
        return self.get_record(uid=uid, boss=boss, num=num, time_desc=True)

    @cache_return
    def get_battle_in_progress(self, uid: str = None, boss: int = None) -> List[BattleInProgress]:
        progresses = BattleInProgress.select().where((BattleInProgress.clan_gid == self.clan_info.clan_gid) & (
            BattleInProgress.using_data_num == self.clan_info.current_using_data_num))
        if uid:
            progresses = progresses.where((BattleInProgress.member_uid == uid))
        if boss:
            progresses = progresses.where(
                (BattleInProgress.target_boss == boss))
        ret_list = []
        for progress in progresses:
            ret_list.append(progress)
        return ret_list

    @cache_return
    def get_battle_subscribe(self, uid: str = None, boss: int = None, boss_cycle: int = None) -> List[BattleSubscribe]:
        subscribes = BattleSubscribe.select().where((BattleSubscribe.clan_gid == self.clan_info.clan_gid) & (
            BattleSubscribe.using_data_num == self.clan_info.current_using_data_num))
        if uid:
            subscribes = subscribes.where((BattleSubscribe.member_uid == uid))
        if boss:
            subscribes = subscribes.where(
                (BattleSubscribe.target_boss == boss))
        if boss_cycle:
            subscribes = subscribes.where(
                (BattleSubscribe.target_cycle == boss_cycle))
        ret_list = []
        for subscribe in subscribes:
            ret_list.append(subscribe)
        return ret_list

    @cache_return
    def get_battle_on_tree(self, uid: str = None, boss: int = None) -> List[BattleOnTree]:
        progresses = BattleOnTree.select().where((BattleOnTree.clan_gid == self.clan_info.clan_gid) & (
            BattleOnTree.using_data_num == self.clan_info.current_using_data_num))
        if uid:
            progresses = progresses.where((BattleOnTree.member_uid == uid))
        if boss:
            progresses = progresses.where((BattleOnTree.target_boss == boss))
        ret_list = []
        for progress in progresses:
            ret_list.append(progress)
        return ret_list

    @cache_return
    def get_battle_sl(self, uid: str = None, boss: int = None, boss_cycle: int = None, start_time: datetime.datetime = None, end_time: datetime.datetime = None) -> List[BattleSL]:
        sls = BattleSL.select().where((BattleSL.clan_gid == self.clan_info.clan_gid) & (
            BattleSL.using_data_num == self.clan_info.current_using_data_num) & (BattleSL.record_time > start_time) & (BattleSL.record_time < end_time))
        if uid:
            sls = sls.where((BattleSL.member_uid == uid))
        if boss:
            sls = sls.where((BattleSL.target_boss == boss))
        if boss_cycle:
            sls = sls.where((BattleSL.target_cycle == boss_cycle))
        ret_list = []
        for sl in sls:
            ret_list.append(sl)
        return ret_list

    def get_today_battle_sl(self, uid: str = None, boss: int = None, boss_cycle: int = None) -> List[BattleSL]:
        today_time = self.get_today_datetime()
        return self.get_battle_sl(uid, boss, boss_cycle, today_time[0], today_time[1])

    @clear_cache
    def create_new_battle_subscribe(self, uid: str, target_cycle: int, target_boss: int, comment: str):
        BattleSubscribe.create(clan_gid=self.clan_info.clan_gid, member_uid=uid, record_time=datetime.datetime.utcnow(),
                               target_cycle=target_cycle, target_boss=target_boss,
                               using_data_num=self.clan_info.current_using_data_num, comment=comment)

    @clear_cache
    def create_new_battle_in_progress(self, uid: str, target_cycle: int, target_boss: int, comment: str):
        BattleInProgress.create(clan_gid=self.clan_info.clan_gid, member_uid=uid, record_time=datetime.datetime.utcnow(),
                                target_cycle=target_cycle, target_boss=target_boss,
                                using_data_num=self.clan_info.current_using_data_num, comment=comment)

    @clear_cache
    def create_new_battle_on_tree(self, uid: str, target_cycle: int, target_boss: int, comment: str):
        BattleOnTree.create(clan_gid=self.clan_info.clan_gid, member_uid=uid, record_time=datetime.datetime.utcnow(),
                            target_cycle=target_cycle, target_boss=target_boss,
                            using_data_num=self.clan_info.current_using_data_num, comment=comment)

    @clear_cache
    def create_new_battle_sl(self, uid: str, target_cycle: int, target_boss: int, comment: str, proxy_report_uid: str):
        BattleSL.create(clan_gid=self.clan_info.clan_gid, member_uid=uid, record_time=datetime.datetime.utcnow(),
                        using_data_num=self.clan_info.current_using_data_num, comment=comment,
                        target_cycle=target_cycle, target_boss=target_boss,
                        proxy_report_uid=proxy_report_uid)

    @clear_cache
    def create_new_record(self, uid: str, target_cycle: int, target_boss: int, damage: int, boss_hp: int, comment: str, is_extra_time: bool, remain_next_chance: bool, proxy_report_uid: str):
        BattleRecord.create(clan_gid=self.clan_info.clan_gid, member_uid=uid, record_time=datetime.datetime.utcnow(),
                            target_cycle=target_cycle, target_boss=target_boss, using_data_num=self.clan_info.current_using_data_num, damage=damage, boss_hp=boss_hp, comment=comment,
                            is_extra_time=is_extra_time, remain_next_chance=remain_next_chance, proxy_report_uid=proxy_report_uid)

    @clear_cache
    def delete_recent_record(self, uid: str, boss_count=None) -> bool:
        record = self.get_recent_record(uid=uid, boss=boss_count)
        if not record:
            return False
        else:
            record[0].delete_instance()
            return True

    @clear_cache
    def delete_battle_in_progress(self, uid: str) -> bool:
        progress = self.get_battle_in_progress(uid)
        if not progress:
            return False
        for proc in progress:
            proc.delete_instance()
        return True

    @clear_cache
    def delete_battle_subscribe(self, uid: str, boss: int, cycle: int = None) -> bool:
        subs = self.get_battle_subscribe(uid, boss, cycle)
        if not subs:
            return False
        for sub in subs:
            sub.delete_instance()
        return True

    @clear_cache
    def delete_battle_on_tree(self, uid: str) -> bool:
        on_tree = self.get_battle_on_tree(uid)
        if not on_tree:
            return False
        for proc in on_tree:
            proc.delete_instance()
        return True

    @clear_cache
    def update_battle_in_progress_record(self, uid: str, comment: str) -> bool:
        progress = self.get_battle_in_progress(uid)
        if not progress:
            return False
        for proc in progress:
            proc.comment = comment
            proc.save()
        return True

    @clear_cache
    def update_on_tree_record(self, uid: str, comment: str) -> bool:
        on_treee_list = self.get_battle_on_tree(uid)
        if not on_treee_list:
            return False
        for on_tree_item in on_treee_list:
            on_tree_item.comment = comment
            on_tree_item.save()
        return True

    def get_record_status(self, uid: str, start_time: datetime.datetime = None, end_time: datetime.datetime = None) -> TodayBattleStatus:
        records = self.get_record(uid=uid, start_time=start_time, end_time=end_time) if (
            start_time and end_time) else self.get_today_record(uid)
        total_challenge = 0
        addition_challeng = 0
        remain_addition_challeng = 0
        is_exta_time = False
        if start_time and end_time:
            is_sl = True if self.get_battle_sl(
                uid=uid, start_time=start_time, end_time=end_time) else False
        else:
            is_sl = True if self.get_today_battle_sl(uid=uid) else False
        if not records or len(records) == 0:
            return TodayBattleStatus(uid, 0, 0, 0, False, is_sl)
        for record in records:
            if record.remain_next_chance:
                remain_addition_challeng += 1
            if not record.is_extra_time:
                total_challenge += 1
            else:
                addition_challeng += 1
                remain_addition_challeng -= 1
        if records[len(records)-1].is_extra_time:
            is_exta_time = True
        return TodayBattleStatus(uid, total_challenge, addition_challeng, remain_addition_challeng, is_exta_time, is_sl)

    def get_today_record_status(self, uid: str) -> TodayBattleStatus:
        return self.get_record_status(uid)

    def get_today_member_status(self) -> List[TodayBattleStatus]:
        ret_status = []
        members = self.get_clan_members()
        for member in members:
            status = self.get_today_record_status(member)
            ret_status.append(status)
        return ret_status

    # 完整刀 补偿刀
    def get_today_record_status_total(self) -> Tuple[int, int]:
        today_record = self.get_today_record()
        total_challenge = 0
        next_chance_challenge = 0
        if not today_record or len(today_record) == 0:
            return (0, 0)
        for record in today_record:
            if record.member_uid == "admin":
                continue
            if not record.is_extra_time:
                total_challenge += 1
            if record.remain_next_chance:
                next_chance_challenge += 1
            if record.is_extra_time:
                next_chance_challenge -= 1
        return (total_challenge, next_chance_challenge)

    @cache_return
    def check_admin_permission(self, uid: str) -> bool:
        admins = self.get_db_strlist_list(self.clan_info.clan_admin)
        if uid in admins:
            return True
        return False

    @cache_return
    def get_cycle_stage(self, cycle: int) -> int:
        max_cycle = len(boss_info["cycle"][self.clan_info.clan_type])
        for i in range(len(boss_info["cycle"][self.clan_info.clan_type])):
            if max_cycle - 1 == i and cycle >= boss_info["cycle"][self.clan_info.clan_type][i]:
                return i+1
            elif max_cycle != i and cycle >= boss_info["cycle"][self.clan_info.clan_type][i] and cycle < boss_info["cycle"][self.clan_info.clan_type][i+1]:
                return i+1
        raise ClanBattleException("cycle error")

    @cache_return
    def get_current_boss_state(self) -> List[BossStatus]:
        ret_list = []
        for i in range(1, 6):
            result: BattleRecord = BattleRecord.select().where((BattleRecord.target_boss == i)
                                                               & (BattleRecord.using_data_num == self.clan_info.current_using_data_num)
                                                               & (BattleRecord.clan_gid == self.clan_info.clan_gid)
                                                               ).order_by(BattleRecord.record_time.desc()).limit(1)
            if not result:
                ret_list.append(BossStatus(
                    i, 1, 1, boss_info["boss"][self.clan_info.clan_type][0][i-1], boss_info["boss"][self.clan_info.clan_type][0][i-1]))
            else:
                result = result[0]
                if result.boss_hp == result.damage:
                    boss_cycle = result.target_cycle+1
                    boss_stage = self.get_cycle_stage(boss_cycle)
                    ret_list.append(BossStatus(result.target_boss, boss_cycle, boss_stage,
                                    boss_info["boss"][self.clan_info.clan_type][boss_stage-1][result.target_boss-1], boss_info["boss"][self.clan_info.clan_type][boss_stage-1][result.target_boss-1]))
                else:
                    boss_cycle = result.target_cycle
                    boss_stage = self.get_cycle_stage(boss_cycle)
                    ret_list.append(BossStatus(
                        result.target_boss, boss_cycle, boss_stage, result.boss_hp-result.damage, boss_info["boss"][self.clan_info.clan_type][boss_stage-1][result.target_boss-1]))
        return ret_list

    async def boss_kill_process(self, uid: str, boss: int, proxy_report_uid: str):
        bot: Bot = list(nonebot.get_bots().values())[0]
        gid = self.clan_info.clan_gid
        current_boss_status = self.get_current_boss_state()
        on_tree_list = self.get_battle_on_tree(boss=boss)
        battle_subscribe_list = self.get_battle_subscribe(boss=boss)
        battle_in_progress_list = self.get_battle_in_progress(boss=boss)
        current_max_challenge_cycle = self.get_max_challenge_boss_cycle(
            current_boss_status)
        current_boss_status[boss-1].target_cycle -= 1
        previous_max_challenge_cycle = self.get_max_challenge_boss_cycle(
            current_boss_status)
        current_boss_status[boss-1].target_cycle += 1
        no_report_uid_set = {uid, proxy_report_uid}
        on_tree_mention_set = set()
        battle_subscribe_mention_qq_set = set()
        battle_in_progress_mention_qq_set = set()
        battle_subscribe_able_challenge_set = set()
        # 处理挂树
        for on_tree in on_tree_list:
            on_tree_mention_set.add(on_tree.member_uid)
            on_tree.delete_instance()
        # 处理当前boss正在出刀和预约
        for battle_subscribe in battle_subscribe_list:
            if battle_subscribe.target_cycle != current_boss_status[boss-1].target_cycle - 1:
                continue
            battle_subscribe_mention_qq_set.add(
                str(battle_subscribe.member_uid))
            battle_subscribe.delete_instance()
        for battle_in_progress in battle_in_progress_list:
            battle_in_progress_mention_qq_set.add(
                battle_in_progress.member_uid)
            battle_in_progress.delete_instance()
        # 处理可以出刀提醒
        for boss_state in current_boss_status:
            if boss_state.target_boss == boss or (current_max_challenge_cycle >= previous_max_challenge_cycle and boss_state.target_cycle == current_max_challenge_cycle):
                if sub_records := self.get_battle_subscribe(boss=boss_state.target_boss, boss_cycle=boss_state.target_cycle):
                    for sub_record in sub_records:
                        battle_subscribe_able_challenge_set.add(
                            str(sub_record.member_uid))
        on_tree_mention_set -= no_report_uid_set
        battle_subscribe_able_challenge_set -= no_report_uid_set
        battle_in_progress_mention_qq_set -= no_report_uid_set
        battle_subscribe_able_challenge_set -= no_report_uid_set
        # 预约当前和正在挑战提醒
        memtion_boss_killed_msg = Message()
        if battle_subscribe_mention_qq_set or battle_in_progress_mention_qq_set:
            memtion_boss_killed_msg += MessageSegment.text(
                f"{boss}王已被击败，无需继续挑战\n")
            if battle_subscribe_mention_qq_set:
                memtion_boss_killed_msg += Message(
                    map(MessageSegment.at, battle_subscribe_mention_qq_set))
            if battle_in_progress_mention_qq_set:
                memtion_boss_killed_msg += Message(
                    map(MessageSegment.at, battle_subscribe_mention_qq_set))
        if len(memtion_boss_killed_msg) > 0:
            try:
                await bot.send_group_msg(group_id=gid, message=memtion_boss_killed_msg)
                await asyncio.sleep(0.5)
            except:
                pass
        # 下树提醒
        on_tree_mention_msg = Message()
        if on_tree_mention_set:
            on_tree_mention_msg += MessageSegment.text("下树啦\n") + \
                Message(map(MessageSegment.at, on_tree_mention_set))
        if len(on_tree_mention_msg) > 0:
            try:
                await bot.send_group_msg(group_id=gid, message=on_tree_mention_msg)
                await asyncio.sleep(0.5)
            except:
                pass
        # 预约可挑战提醒
        battle_subscribe_able_challenge_msg = Message()
        if battle_subscribe_able_challenge_set:
            battle_subscribe_able_challenge_msg += MessageSegment.text("现在可以出刀了\n") + Message(
                map(MessageSegment.at, battle_subscribe_able_challenge_set))
        if len(battle_subscribe_able_challenge_msg) > 0:
            try:
                await bot.send_group_msg(group_id=gid, message=battle_subscribe_able_challenge_msg)
                await asyncio.sleep(0.5)
            except:
                pass

    def get_max_challenge_boss_cycle(self, boss_data: List[BossStatus]) -> int:
        current_max_cycle = boss_data[0].target_cycle
        current_min_cycle = boss_data[0].target_cycle
        for boss in boss_data:
            if current_max_cycle < boss.target_cycle:
                current_max_cycle = boss.target_cycle
            if current_min_cycle > boss.target_cycle:
                current_min_cycle = boss.target_cycle
        current_stage = self.get_cycle_stage(current_min_cycle)
        next_stage = current_stage + 1
        if current_max_cycle - current_min_cycle == 2:
            return current_max_cycle - 1
        elif current_max_cycle - current_min_cycle == 1:
            if next_stage == len(boss_info["cycle"][self.clan_info.clan_type]) + 1:
                return current_max_cycle
            if current_max_cycle == boss_info["cycle"][self.clan_info.clan_type][next_stage - 1]:
                return current_min_cycle
            else:
                return current_max_cycle
        else:
            return current_max_cycle

    def check_boss_challengeable(self, target_cycle: int, target_boss: int):
        boss_state = self.get_current_boss_state()
        challenge_boss_state = boss_state[target_boss - 1]
        if target_cycle <= self.get_max_challenge_boss_cycle(boss_state) and challenge_boss_state.target_cycle == target_cycle:
            return True
        return False

    def check_new_record_legal(self, uid: str, target_cycle: int, target_boss: int, damage: int) -> NewRecordLegalCheckResult:
        boss_state = self.get_current_boss_state()
        challenge_boss_state = boss_state[target_boss - 1]
        if target_cycle <= self.get_max_challenge_boss_cycle(boss_state) and challenge_boss_state.target_cycle == target_cycle and challenge_boss_state.boss_hp >= damage:
            if on_tree := self.get_battle_on_tree(uid):
                if on_tree[0].target_boss == target_boss:
                    return NewRecordLegalCheckResult.success
                else:
                    return NewRecordLegalCheckResult.on_another_tree
            return NewRecordLegalCheckResult.success
        return NewRecordLegalCheckResult.boss_not_challengeable

    async def commit_record(self, uid: str, target_boss: int, damage: str, comment: str, proxy_report_uid: str = None, force_use_full_chance: bool = False) -> CommitRecordResult:
        damage_num = 0
        try:
            damage_num = self.parse_damage(damage)
        except ClanBattleDamageParseException:
            return CommitRecordResult.illegal_damage_inpiut
        boss_status = self.get_current_boss_state()
        boss = boss_status[target_boss-1]
        record_status = self.get_today_record_status(uid)
        if damage_num > boss.boss_hp:
            return CommitRecordResult.damage_out_of_hp
        if (check_result := self.check_new_record_legal(uid, boss.target_cycle, boss.target_boss, damage_num)) == NewRecordLegalCheckResult.boss_not_challengeable:
            return CommitRecordResult.boss_not_challengeable
        if check_result == NewRecordLegalCheckResult.on_another_tree:
            return CommitRecordResult.on_another_tree
        if not self.check_joined_clan(uid):
            return CommitRecordResult.member_not_in_clan
        if on_tree := self.get_battle_on_tree(uid=uid):
            on_tree[0].delete_instance()
        if on_sub := self.get_battle_subscribe(uid=uid, boss=target_boss, boss_cycle=boss.target_cycle):
            on_sub[0].delete_instance()
        if in_progress := self.get_battle_in_progress(uid, target_boss):
            in_progress[0].delete_instance()
        # process proxy reporter
        if proxy_report_uid:
            if on_tree := self.get_battle_on_tree(uid=proxy_report_uid):
                on_tree[0].delete_instance()
            if on_sub := self.get_battle_subscribe(uid=proxy_report_uid, boss=target_boss, boss_cycle=boss.target_cycle):
                on_sub[0].delete_instance()
            if in_progress := self.get_battle_in_progress(proxy_report_uid, target_boss):
                in_progress[0].delete_instance()
        if record_status.remain_addition_challeng > 0 and not force_use_full_chance:
            self.create_new_record(uid, boss.target_cycle,
                                   target_boss, damage_num, boss.boss_hp, comment, True, False, proxy_report_uid)
        elif damage_num == boss.boss_hp:
            self.create_new_record(uid, boss.target_cycle,
                                   target_boss, damage_num, boss.boss_hp, comment, False, True, proxy_report_uid)
        else:
            self.create_new_record(uid, boss.target_cycle,
                                   target_boss, damage_num, boss.boss_hp, comment, False, False, proxy_report_uid)
        if damage_num == boss.boss_hp:
            await self.boss_kill_process(uid, target_boss, proxy_report_uid)
        return CommitRecordResult.success

    def commit_battle_in_progress(self, uid: str, target_boss: int, comment: str) -> CommitInProgressResult:
        boss_status = self.get_current_boss_state()
        boss = boss_status[target_boss-1]
        if (check_result := self.check_new_record_legal(uid, boss.target_cycle, boss.target_boss, 1)) == NewRecordLegalCheckResult.boss_not_challengeable:
            return CommitInProgressResult.boss_not_challengeable
        if check_result == NewRecordLegalCheckResult.on_another_tree:
            return CommitInProgressResult.already_in_tree
        if not self.check_joined_clan(uid):
            return CommitInProgressResult.member_not_in_clan
        if on_tree := self.get_battle_on_tree(uid):
            return CommitInProgressResult.already_in_tree
        if in_proc := self.get_battle_in_progress(uid):
            return CommitInProgressResult.already_in_battle
        if sub := self.get_battle_subscribe(uid, target_boss, boss.target_cycle):
            sub[0].delete_instance()
        self.create_new_battle_in_progress(
            uid, boss.target_cycle, target_boss, comment)
        return CommitInProgressResult.success

    def commit_batle_subscribe(self, uid: str, target_boss: int, target_cycle: int = None, comment: str = None) -> CommitSubscribeResult:
        boss_status = self.get_current_boss_state()
        boss = boss_status[target_boss-1]
        if not target_cycle:
            if self.get_max_challenge_boss_cycle(boss_status) < boss_status[target_boss-1].target_cycle:
                cycle = boss.target_cycle
            else:
                cycle = boss.target_cycle + 1
        else:
            cycle = target_cycle
        if not self.check_joined_clan(uid):
            return CommitSubscribeResult.member_not_in_clan
        if self.get_battle_in_progress(uid, target_boss):
            return CommitSubscribeResult.already_in_progress
        if self.get_battle_subscribe(uid, target_boss, cycle):
            return CommitSubscribeResult.already_subscribed
        if cycle < boss.target_cycle:
            return CommitSubscribeResult.boss_cycle_already_killed
        self.create_new_battle_subscribe(
            uid, cycle, target_boss, comment)
        return CommitSubscribeResult.success

    def commit_battle_on_tree(self, uid: str, target_boss: int, comment: str) -> CommitBattlrOnTreeResult:
        boss_status = self.get_current_boss_state()
        boss = boss_status[target_boss-1]
        if not self.check_joined_clan(uid):
            return CommitBattlrOnTreeResult.member_not_in_clan
        if (check_result := self.check_new_record_legal(uid, boss.target_cycle, boss.target_boss, 1)) == NewRecordLegalCheckResult.boss_not_challengeable:
            return CommitBattlrOnTreeResult.boss_not_challengeable
        if (check_result := self.check_new_record_legal(uid, boss.target_cycle, boss.target_boss, 1)) == NewRecordLegalCheckResult.boss_not_challengeable:
            return CommitBattlrOnTreeResult.already_on_tree
        if self.get_battle_on_tree(uid):
            return CommitBattlrOnTreeResult.already_on_tree
        if sub := self.get_battle_subscribe(uid, target_boss, boss.target_cycle):
            sub[0].delete_instance()
        if in_progress := self.get_battle_in_progress(uid, target_boss):
            in_progress[0].delete_instance()
        self.create_new_battle_on_tree(
            uid, boss.target_cycle, target_boss, comment)
        return CommitBattlrOnTreeResult.success

    def commit_battle_sl(self, uid: str,  target_boss: int = None, comment: str = None, proxy_report_uid: str = None) -> CommitSLResult:
        if not self.check_joined_clan(uid):
            return CommitSLResult.member_not_in_clan
        if self.get_today_battle_sl(uid):
            return CommitSLResult.already_sl
        if target_boss:
            boss_status = self.get_current_boss_state()
            boss = boss_status[target_boss-1]
            if not self.check_new_record_legal(uid, boss.target_cycle, boss.target_boss, 1):
                return CommitSLResult.illegal_target_boss
            if on_tree := self.get_battle_on_tree(uid=uid):
                on_tree[0].delete_instance()
            self.create_new_battle_sl(
                uid, boss.target_cycle, target_boss, comment, proxy_report_uid)
        else:
            self.create_new_battle_sl(
                uid, None, None, comment, proxy_report_uid)
        return CommitSLResult.success

    def commit_force_change_boss_status(self, target_boss: int, target_cycle: int, target_hp: str) -> bool:
        try:
            boss_hp = self.parse_damage(target_hp)
            self.create_new_record("admin", target_cycle, target_boss,
                                    0, boss_hp, "本条记录为会战管理员强制修改进度所创建", False, False, None)
        except ClanBattleDamageParseException:
            return False
        return True


class ClanBattle:

    clan_data_dict: Dict[str, ClanBattleData] = {}

    def __init__(self) -> None:
        pass

    def get_joined_clan(self, uid: str) -> List[str]:
        user: User = User.select().where(User.qq_uid == uid).get()
        return ClanBattleData.get_db_strlist_list(user.clan_joined)

    def get_clan_data(self, gid: str) -> ClanBattleData:
        if not gid in list(self.clan_data_dict.keys()):
            try:
                clan_data = ClanBattleData(gid)
                self.clan_data_dict[gid] = clan_data
                return clan_data
            except:
                return None
        else:
            return self.clan_data_dict[gid]

    def create_clan(self, gid: str, clan_name: str, clan_type: str, clan_admin: List[str]):
        ClanBattleData.create_clan(gid, clan_name, clan_type, clan_admin)
        self.get_clan_data(gid)

    def delete_clan(self, gid: str):
        clan = self.get_clan_data(gid)
        clan.clear_current_clanbattle_data()
        members = clan.get_clan_members()
        for member in members:
            clan.delete_clan_member(member)
        ClanBattleData.delete_clan(gid)
        del self.clan_data_dict[gid]


class WebAuth:

    @staticmethod
    def check_password(uid: str, password: str) -> bool:
        user: User = User.get(User.qq_uid == uid)
        if user.password:
            if user.password == hashlib.md5((password+get_config().db_salt).encode("utf-8")).hexdigest():
                return True
        return False

    @staticmethod
    def set_password(uid: str, password: str):
        password = hashlib.md5(
            (password+"sa823bs7ty1d1293asiu7ysaas").encode("utf-8")).hexdigest()
        password_md5 = hashlib.md5(
            (password+get_config().db_salt).encode("utf-8")).hexdigest()
        user: User = User.select().where(User.qq_uid == uid).get()
        user.password = password_md5
        user.save()

    @staticmethod
    def check_session_valid(session: str) -> str:
        if not session:
            return None
        user = User.select().where(User.web_session == session)
        return user[0].qq_uid if user else None

    @staticmethod
    def create_session(uid: str) -> str:
        session = str(uuid.uuid4()).replace("-", "")
        while User.select().where(User.web_session == session):
            session = str(uuid.uuid4()).replace("-", "")
        user: User = User.select().where(User.qq_uid == uid).get()
        user.web_session = session
        user.save()
        return session

    @staticmethod
    # Tuple(code, sessison)
    def login(uid: str, password: str) -> Tuple[int, str]:
        user = User.select().where(User.qq_uid == uid)
        if not user:
            return (404, "")
        if not WebAuth.check_password(uid, password):
            return (403, "")
        return (0, WebAuth.create_session(uid))


class Tools:

    @staticmethod
    def get_chinese_timedetla(target_time: datetime.datetime) -> str:
        now_time = datetime.datetime.utcnow()
        time_detla = now_time - target_time
        detla_seconds = time_detla.total_seconds()
        current_seconds = detla_seconds
        ret_text = ""
        if current_seconds > 3600 * 24:
            ret_text += f"{int(current_seconds // (3600 * 24))}天"
            current_seconds %= (3600 * 24)
        if current_seconds > 3600:
            ret_text += f"{int(current_seconds // 3600)}小时"
            current_seconds %= 3600
        if current_seconds > 60:
            ret_text += f"{int(current_seconds // 60)}分钟"
            current_seconds %= 60
        else:
            ret_text += "0分钟"
        #ret_text += f"{int(detla_seconds)}秒"
        return ret_text

    @staticmethod
    def get_num_str_with_dot(num: int) -> str:
        num_list = list(str(num))
        index = len(str(num))
        while (index > 3):
            index -= 3
            num_list.insert(index, ",")
        return "".join(num_list)

    @staticmethod
    def update_boss_info():
        global boss_info
        boss_info = get_config().boss_info

class MessageFormatter:

    @staticmethod
    def get_boss_status_msg(clan:ClanBattleData, boss_count:int) -> str:
        boss_status = clan.get_current_boss_state()
        boss = boss_status[boss_count-1]
        msg = f"当前{boss_count}王位于{boss.target_cycle}周目，剩余血量{Tools.get_num_str_with_dot(boss.boss_hp)}"
        if not clan.check_boss_challengeable(boss.target_cycle, boss_count):
            msg += "（不可挑战）"
        subs = clan.get_battle_subscribe(
            boss=boss_count, boss_cycle=boss.target_cycle)
        if subs:
            has_add_msg = True
            msg += "\n📅 "
            for sub in subs:
                msg += " "
                msg += clan.get_user_name(sub.member_uid)
                if sub.comment and sub.comment != "":
                    msg += f"：{sub.comment}"
        in_processes = clan.get_battle_in_progress(boss=boss_count)
        if in_processes:
            has_add_msg = True
            msg += "\n🔪 "
            for proc in in_processes:
                msg += " "
                proc_msg = clan.get_user_name(proc.member_uid)
                if proc.comment and proc.comment != "":
                    proc_msg += f"：{proc.comment}"
                msg += proc_msg
        on_tree = clan.get_battle_on_tree(boss=boss_count)
        if on_tree:
            has_add_msg = True
            msg += "\n🎄 "
            for tree in on_tree:
                msg += " "
                on_tree_msg = clan.get_user_name(tree.member_uid)
                if tree.comment and tree.comment != "":
                    on_tree_msg += f"：{tree.comment}"
                msg += on_tree_msg
        return msg

    @staticmethod
    def get_all_boss_status_msg(clan:ClanBattleData) -> str:
        boss_status = clan.get_current_boss_state()
        msg = ""
        boss_count = 0
        for boss in boss_status:
            boss_count += 1
            msg += f"{boss.target_cycle}周目{boss.target_boss}王，生命值{Tools.get_num_str_with_dot(boss.boss_hp)}" if not get_config(
            ).enable_anti_msg_fail else f"{boss.target_cycle}周目{boss.target_boss}王 HP{Tools.get_num_str_with_dot(boss.boss_hp)}"
            if not clan.check_boss_challengeable(boss.target_cycle, boss.target_boss):
                msg += "（不可挑战）"
            has_add_msg = False
            subs = clan.get_battle_subscribe(
                boss=boss_count, boss_cycle=boss.target_cycle)
            if subs:
                has_add_msg = True
                msg += "\n📅 "
                for sub in subs:
                    msg += " "
                    msg += clan.get_user_name(sub.member_uid)
                    if sub.comment and sub.comment != "":
                        msg += f"：{sub.comment}"
            in_processes = clan.get_battle_in_progress(boss=boss_count)
            if in_processes:
                has_add_msg = True
                msg += "\n🔪 "
                for proc in in_processes:
                    msg += " "
                    proc_msg = clan.get_user_name(proc.member_uid)
                    if proc.comment and proc.comment != "":
                        proc_msg += f"：{proc.comment}"
                    msg += proc_msg
            on_tree = clan.get_battle_on_tree(boss=boss_count)
            if on_tree:
                has_add_msg = True
                msg += "\n🎄 "
                for tree in on_tree:
                    msg += " "
                    on_tree_msg = clan.get_user_name(tree.member_uid)
                    if tree.comment and tree.comment != "":
                        on_tree_msg += f"：{tree.comment}"
                    msg += on_tree_msg
            msg += "\n"
            if(has_add_msg):
                msg += "----------------------\n"
        return msg
