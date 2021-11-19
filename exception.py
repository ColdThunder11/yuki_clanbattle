class ClanBattleException(Exception):
    def __init__(self,err_msg):
        self.msg = err_msg
    def __str__(self):
        return self.msg

class ClanBattleDamageParseException(Exception):
    def __init__(self):
        pass

    def __str__(self):
        return "伤害解析错误，请确保输入伤害格式正确"

class WebsocketAuthException(Exception):
    def __init__(self):
        pass

    def __str__(self):
        return "Websocket鉴权错误"

class WebsocketResloveException(Exception):
    def __init__(self):
        pass

    def __str__(self):
        return "Websocket数据解析错误"