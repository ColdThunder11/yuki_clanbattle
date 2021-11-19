#import redis
import datetime

from os import path
from enum import unique
from peewee import *


redis_db = 2

#redis_instance = redis.StrictRedis(host='localhost', port=6379, db=redis_db)

db_path = path.join(path.dirname(__file__),
                    "clanbattle.db").replace(":\\", ":\\\\")

sqlite_db = SqliteDatabase(db_path)
#db = SqliteDatabase(r"d:\\Code\nb2_pcr_clanbattle_bot\plugins\clanbattle\clanbattle.db")


class BaseModel(Model):
    class Meta:
        database = sqlite_db


class User(BaseModel):
    qq_uid = CharField(unique=True)
    tg_uid = CharField(unique=True, null=True)
    uname = CharField(null=True)
    password = CharField(null=True)
    clan_joined = TextField(null=True)  # list,split by |
    web_session = CharField(null=True)
    is_super_admin = BooleanField(default=False)
    class Meta:
        table_name = "user"


class ClanInfo(BaseModel):
    clan_gid = CharField(unique=True, index=True)
    clan_name = CharField()
    clan_type = CharField()  # cn为国，tw为台，jp为日
    clan_api_key = CharField(unique=True,null=True)
    clan_admin = TextField()  # list,split by |
    clan_members = TextField(null=True) # list,split by |
    create_time = DateTimeField()
    current_using_data_num = IntegerField(default=1)
    #current_cycle = IntegerField()
    #current_boss = IntegerField()
    #current_boss_hp = IntegerField()
    clan_web_msg_push = BooleanField(default=True)
    class Meta:
        table_name = "clan_info"


class BattleRecord(BaseModel):
    clan_gid = CharField()
    member_uid = CharField()
    record_time = DateTimeField()
    using_data_num = IntegerField()
    target_cycle = IntegerField()
    target_boss = IntegerField()
    boss_hp = IntegerField()
    damage = IntegerField()
    comment = TextField(null=True)
    is_extra_time = BooleanField()
    remain_next_chance = BooleanField()
    proxy_report_uid = CharField(null=True)
    class Meta:
        table_name = "battle_record"

class BattleSubscribe(BaseModel):
    clan_gid = CharField()
    member_uid = CharField()
    record_time = DateTimeField()
    using_data_num = IntegerField()
    target_cycle = IntegerField()
    target_boss = IntegerField()
    comment = TextField(null=True)
    class Meta:
        table_name = "battle_subscribe"


class BattleOnTree(BaseModel):
    clan_gid = CharField()
    member_uid = CharField()
    record_time = DateTimeField()
    using_data_num = IntegerField()
    target_cycle = IntegerField()
    target_boss = IntegerField()
    comment = TextField(null=True)
    class Meta:
        table_name = "battle_on_tree"


class BattleInProgress(BaseModel):
    clan_gid = CharField()
    member_uid = CharField()
    record_time = DateTimeField()
    using_data_num = IntegerField()
    target_cycle = IntegerField()
    target_boss = IntegerField()
    comment = TextField(null=True)
    class Meta:
        table_name = "battle_in_progress"

class BattleSL(BaseModel):
    clan_gid = CharField()
    member_uid = CharField()
    record_time = DateTimeField()
    using_data_num = IntegerField()
    target_cycle = IntegerField(null=True)
    target_boss = IntegerField(null=True)
    comment = TextField(null=True)
    proxy_report_uid = CharField(null=True)
    class Meta:
        table_name = "battle_sl"


sqlite_db.connect()
sqlite_db.create_tables([User, ClanInfo, BattleRecord,
                 BattleSubscribe, BattleOnTree, BattleInProgress, BattleSL])
