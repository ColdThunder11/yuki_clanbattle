import os
import json
import pydantic


class ConfigClass(pydantic.BaseModel):
    web_url: str
    disable_private_message: bool
    enable_anti_msg_fail: bool
    db_salt: str
    boss_info: dict


clanbattle_config: "ConfigClass" = None

def get_config() -> ConfigClass:
    if not clanbattle_config:
        load_config()
    return clanbattle_config

def load_config():
    global clanbattle_config
    with open(os.path.join(os.path.dirname(__file__), "config.json"), "r", encoding="utf8") as fp:
        clanbattle_config = ConfigClass.parse_obj(json.load(fp))
        #print("load_config finish")
        #boss_info = json.loads(clanbattle_config.boss_info.json())
        #db_salt = clanbattle_config.db_salt