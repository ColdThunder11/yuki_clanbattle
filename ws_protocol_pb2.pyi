from typing import Any

class WsRequestMessage:

    request_uuid: str
    request_type: int
    session: str
    route: str
    data: str

    def __str__(self) -> str:
        ...

    def IsInitialized() -> bool:
        ...

    def CopyFrom(self, other_msg: WsRequestMessage):
        ...

    def Clear(self):
        ...

    def SerializeToString(self) -> bytes:
        ...

    def ParseFromString(self, data: bytes) -> WsRequestMessage:
        ...

class WsResponseMessage:

    response_uuid: str
    data: str

    def __str__(self) -> str:
        ...

    def IsInitialized() -> bool:
        ...

    def CopyFrom(self, other_msg: WsResponseMessage):
        ...

    def Clear(self):
        ...

    def SerializeToString(self) -> bytes:
        ...

    def ParseFromString(self, data: bytes) -> WsResponseMessage:
        ...

class WsUpdateRequireNotice:

    request_uuid: str

    def __str__(self) -> str:
        ...

    def IsInitialized() -> bool:
        ...

    def CopyFrom(self, other_msg: WsUpdateRequireNotice):
        ...

    def Clear(self):
        ...

    def SerializeToString(self) -> bytes:
        ...

    def ParseFromString(self, data: bytes) -> WsUpdateRequireNotice:
        ...

class WsHeartBreakMessage:

    heart_break_id: int

    def __str__(self) -> str:
        ...

    def IsInitialized() -> bool:
        ...

    def CopyFrom(self, other_msg: WsHeartBreakMessage):
        ...

    def Clear(self):
        ...

    def SerializeToString(self) -> bytes:
        ...

    def ParseFromString(self, data: bytes) -> WsHeartBreakMessage:
        ...

