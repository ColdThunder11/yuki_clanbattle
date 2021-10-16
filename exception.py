class ClanBattleExceptin(Exception):
    def __init__(self,err_msg):
        self.msg = err_msg
    def __str__(self):
        return self.msg
