#import redis
import sys

from os import path
from peewee import *
import sqlite3


redis_db = 2

#redis_instance = redis.StrictRedis(host='localhost', port=6379, db=redis_db)

if not "pytest" in sys.modules:
    db_path = path.join(path.dirname(__file__),
                        "clanbattle.db").replace(":\\", ":\\\\")
else:
    db_path = path.join(path.dirname(__file__),
                        "clanbattle_test.db").replace(":\\", ":\\\\")

#Check and update table
if(path.exists(db_path)):
    db_conn = sqlite3.connect(db_path)
    c = db_conn.cursor()
    cur = c.execute("PRAGMA table_info('clan_info')")
    v_0_2_3_detected = False
    for row in cur:
        if(row[1] == "clan_query_info"):
            v_0_2_3_detected = True
    cur.close()
    if(not v_0_2_3_detected):
        print("YukiClanbattle: Old database detected, update table struct...")
        c = db_conn.cursor()
        c.execute("ALTER TABLE clan_info ADD COLUMN clan_query_info text")
        c.close()
        print("YukiClanbattle: Update table struct success")
    db_conn.commit()
    db_conn.close()




sqlite_db = SqliteDatabase(db_path)


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
    clan_api_key = CharField(unique=True, null=True)
    clan_admin = TextField()  # list,split by |
    clan_members = TextField(null=True)  # list,split by |
    create_time = DateTimeField()
    current_using_data_num = IntegerField(default=1)
    #current_cycle = IntegerField()
    #current_boss = IntegerField()
    #current_boss_hp = IntegerField()
    clan_web_msg_push = BooleanField(default=True)
    clan_query_info = TextField()

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
