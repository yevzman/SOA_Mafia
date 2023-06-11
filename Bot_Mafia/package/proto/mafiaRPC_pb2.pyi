from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DAY_VOTE: Status
DESCRIPTOR: _descriptor.FileDescriptor
END_GAME: Status
FAIL: Status
MORNING_NOTIFICATION: Status
NIGHT_VOTE: Status
ROLE_DISTRIBUTION: Status
START_GAME: Status
SUCCESS: Status
YOU_KILLED: Status

class Player(_message.Message):
    __slots__ = ["address", "id", "name"]
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    address: str
    id: int
    name: str
    def __init__(self, id: _Optional[int] = ..., name: _Optional[str] = ..., address: _Optional[str] = ...) -> None: ...

class PlayerId(_message.Message):
    __slots__ = ["id"]
    ID_FIELD_NUMBER: _ClassVar[int]
    id: int
    def __init__(self, id: _Optional[int] = ...) -> None: ...

class Request(_message.Message):
    __slots__ = ["message"]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    message: str
    def __init__(self, message: _Optional[str] = ...) -> None: ...

class Response(_message.Message):
    __slots__ = ["data", "status"]
    DATA_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    data: str
    status: Status
    def __init__(self, status: _Optional[_Union[Status, str]] = ..., data: _Optional[str] = ...) -> None: ...

class VoteRequest(_message.Message):
    __slots__ = ["player_id", "session_id"]
    PLAYER_ID_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    player_id: int
    session_id: int
    def __init__(self, session_id: _Optional[int] = ..., player_id: _Optional[int] = ...) -> None: ...

class VoteResponse(_message.Message):
    __slots__ = ["status"]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    status: Status
    def __init__(self, status: _Optional[_Union[Status, str]] = ...) -> None: ...

class Status(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []
