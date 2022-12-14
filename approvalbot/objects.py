"""
Objects - Shared classes

Copyright::

    +===================================================+
    |                 © 2022 Someguy123                 |
    |               https://github.com/Someguy123       |
    +===================================================+
    |                                                   |
    |        Approval Bot for Discord                   |
    |        License: GNU AGPL v3                       |
    |                                                   |
    |        https://github.com/Someguy123/approvalbot  |
    |                                                   |
    |        Core Developer(s):                         |
    |                                                   |
    |          (+)  Chris (@someguy123)                 |
    |                                                   |
    +===================================================+
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum
import json
import logging
import math
import time
from typing import List, Tuple, Union, Dict, Any, Optional
# import approvalbot.core as core
from os.path import join
from approvalbot import settings
from privex.helpers.cache import adapter_get
from privex.helpers import empty, empty_if, convert_unixtime_datetime, dec_round, DictDataClass, DictObject, convert_datetime
from privex.helpers.exceptions import NotFound
from privex.db import SqliteAsyncWrapper
from privex.db.types import DICT_CORO
from dataclasses import dataclass, field

log = logging.getLogger(__name__)

class MessageStore:
    data: dict
    # cache_key: str

    def __init__(self, msgid: int):
        self.msgid = self.id = msgid
        self.cache = cache = adapter_get()
        # self.cache_key = f"aprv:message:{msgid}"
        log.debug("MessageStore initialised - getting data for key: %s", self.cache_key)
        self.data = self._load()
        log.debug("MessageStore key '%s' contains: %s", self.cache_key, self.data)

    @property
    def cache_key(self) -> str:
        return f"aprv:message:{self.msgid}"
    
    def _load(self):
        return self.cache.get(self.cache_key, {})
    
    def reload(self):
        self.data = self._load()

    """
    Create a new message object in the cache using passed data

    Usage:

        >>> MessageStore.create(12345, action="delete", reason="spam", post="https://example.com" approval_type="approval")
    
    """
    @classmethod
    def create(cls: "MessageStore", msgid: int, **data):
        log.debug("CLASSMETHOD Creating MessageStore object with message ID '%s' and data: %s", msgid, data)
        cache = adapter_get()
        cache.set(f"aprv:message:{msgid}", dict(data))
        return cls(msgid)
    
    @property
    def message(self):
        return self.data.get('message', None)
    
    @message.setter
    def message(self, value):
        self.data['message'] = value
        self.cache.set(self.cache_key, self.data)
    
    @property
    def reason(self):
        return self.data.get('reason', None)
    
    @reason.setter
    def reason(self, value):
        self.data['reason'] = value
        self.cache.set(self.cache_key, self.data)

    @property
    def action(self):
        return self.data.get('action', None)
    
    @action.setter
    def action(self, value):
        self.data['action'] = value
        self.cache.set(self.cache_key, self.data)
    
    @property
    def post(self):
        return self.data.get('post', None)
    
    @post.setter
    def post(self, value):
        self.data['post'] = value
        self.cache.set(self.cache_key, self.data)
    
    @property
    def sender(self):
        return self.data.get('sender', None)
    
    @sender.setter
    def sender(self, value):
        self.data['sender'] = value
        self.cache.set(self.cache_key, self.data)

    @property
    def approval_type(self):
        return self.data.get('approval_type', None)
    
    @approval_type.setter
    def approval_type(self, value):
        self.data['approval_type'] = value
        self.cache.set(self.cache_key, self.data)

    @property
    def approvals(self):
        return self.data.get('approvals', 0)
    
    @approvals.setter
    def approvals(self, value):
        self.data['approvals'] = value
        self.cache.set(self.cache_key, self.data)
    
    @property
    def approvals_list(self) -> list:
        if empty(self.data.get('approvals_list')):
            self.data['approvals_list'] = []
        return self.data['approvals_list']
    
    @approvals_list.setter
    def approvals_list(self, value: list):
        self.data['approvals_list'] = value
        self.cache.set(self.cache_key, self.data)

    @property
    def disapprovals_list(self) -> list:
        if empty(self.data.get('disapprovals_list')):
            self.data['disapprovals_list'] = []
        return self.data['disapprovals_list']
    
    @disapprovals_list.setter
    def disapprovals_list(self, value: list):
        self.data['disapprovals_list'] = value
        self.cache.set(self.cache_key, self.data)

    @property
    def disapprovals(self):
        return self.data.get('disapprovals', 0)
    
    @disapprovals.setter
    def disapprovals(self, value):
        self.data['disapprovals'] = value
        self.cache.set(self.cache_key, self.data)

    def approve(self, user: str) -> int:
        if user not in self.approvals_list:
            if user in self.disapprovals_list:
                log.info("User %s previously disapproved the poll and now wants to approve it - removing their disapproval vote for: %r", user, self)
                self.disapprovals_list.remove(user)
                self.disapprovals -= 1
            log.info("User %s approved: %s", user, self)
            self.approvals += 1
            self.approvals_list.append(user)
            log.info("Poll for post/user %s now has %s approvals, approved by: %s", self.post, self.approvals, self.approvals_list)
        return self.approvals

    def disapprove(self, user: str) -> int:
        if user not in self.disapprovals_list:
            if user in self.approvals_list:
                log.info("User %s previously approved the poll and now wants to disapprove it - removing their approval vote for: %r", user, self)
                self.approvals_list.remove(user)
                self.approvals -= 1
            self.disapprovals += 1
            self.disapprovals_list.append(user)
            log.info("Poll for post/user %s now has %s disapprovals, disapproved by: %s", self.post, self.disapprovals, self.disapprovals_list)
        return self.disapprovals
    
    def __str__(self) -> str:
        return repr(self)

    def __repr__(self) -> str:
        return f"<MessageStore {self.id=} {self.action=} {self.reason=} {self.post=} {self.data=} />"

def now_plus_seconds(seconds: int) -> datetime:
    """Return the current time plus ``seconds`` seconds as a :class:`.datetime`"""
    return convert_unixtime_datetime(time.time() + int(seconds))

def now_plus_minutes(minutes: Union[int, float, Decimal]) -> datetime:
    """Return the current time plus ``minutes`` minutes as a :class:`.datetime`"""
    return now_plus_seconds(dec_round(minutes, 3) * Decimal(60))

def now_plus_hours(hours: Union[int, float, Decimal]) -> datetime:
    """Return the current time plus ``hours`` hours as a :class:`.datetime`"""
    return now_plus_seconds(dec_round(hours, 3) * Decimal(60 * 60))

def now_plus_days(days: Union[int, float, Decimal]) -> datetime:
    """Return the current time plus ``days`` days as a :class:`.datetime`"""
    return now_plus_seconds(dec_round(days, 3) * Decimal(60 * 60 * 24))


def default_endtime() -> datetime:
    """Return the default approval end time as a :class:`.datetime` object"""
    return now_plus_seconds(settings.DEFAULT_APPROVAL_END)

def datetime_to_unix(d: datetime):
    return int(d.timestamp())

def get_relative_seconds(from_dt: datetime, to_dt: datetime = None):
    to_dt = datetime_to_unix(datetime.utcnow()) if to_dt is None else datetime_to_unix(to_dt)
    from_dt = datetime_to_unix(from_dt)
    return to_dt - from_dt

def get_relative_minutes(from_dt: datetime, to_dt: datetime = None):
    relsecs = get_relative_seconds(from_dt, to_dt)
    return dec_round(relsecs / 60, 1)

def get_relative_hours(from_dt: datetime, to_dt: datetime = None):
    return dec_round(get_relative_seconds(from_dt, to_dt) / 60 / 60, 1)

def get_relative_days(from_dt: datetime, to_dt: datetime = None):
    return dec_round(get_relative_seconds(from_dt, to_dt) / 60 / 60, 1)

def auto_relative(from_dt: datetime, to_dt: datetime = None):
    relsecs = get_relative_seconds(from_dt, to_dt)
    if relsecs >= (60 * 60 * 24): return f"{get_relative_days(from_dt, to_dt)} day(s)"
    if relsecs >= (60 * 60): return f"{get_relative_hours(from_dt, to_dt)} hour(s)"
    if relsecs >= 60: return f"{get_relative_minutes(from_dt, to_dt)!s} minute(s)"
    return f"{relsecs} second(s)"

# "id INTEGER PRIMARY KEY AUTOINCREMENT, "
# "message_id INTEGER UNIQUE, "
# "action TEXT NULL, "
# "url TEXT NULL, "
# "reason TEXT NULL, "
# "username TEXT NULL, "
# "approvals INTEGER DEFAULT 0, "
# "disapprovals INTEGER DEFAULT 0, "
# "approved_by TEXT DEFAULT '[]', "
# "disapproved_by TEXT DEFAULT '[]', "
# "outcome TEXT DEFAULT 'UNKNOWN', "
# "total_all_mods INTEGER DEFAULT 0, "
# "end_time DATETIME DEFAULT (datetime('now', '+1 hours')), "
# "timestamp DATETIME DEFAULT CURRENT_TIMESTAMP"

class ApprovalOutcome(Enum):
    APPROVED = 'APPROVED'
    APPROVED_NO_MAJORITY = 'APPROVED_NO_MAJORITY'
    DISAPPROVED = 'DISAPPROVED'
    DISAPPROVED_NO_MAJORITY = 'DISAPPROVED_NO_MAJORITY'
    TIE = 'TIE'
    CANCELLED = 'CANCELLED'
    UNKNOWN = 'UNKNOWN'
    AUTO = 'AUTO'
    APPROVE = APPROVED
    DISAPPROVE = DISAPPROVED
    YES = APPROVED
    NO = DISAPPROVE
    APPROVE_NOMAJ = APPROVED_NO_MAJORITY
    APPROVED_NOMAJ = APPROVED_NO_MAJORITY
    DISAPPROVE_NOMAJ = DISAPPROVED_NO_MAJORITY
    DISAPPROVED_NOMAJ = DISAPPROVED_NO_MAJORITY


@dataclass
class Approval(DictDataClass):
    message_id: Optional[int]
    id: int = None
    action: str = None
    url: str = None
    reason: str = None
    username: str = None
    approvals: int = 0
    disapprovals: int = 0
    approved_by: list = field(default_factory=list)
    disapproved_by: list = field(default_factory=list)
    outcome: ApprovalOutcome = ApprovalOutcome.AUTO
    total_all_mods: int = 0
    end_time: datetime = field(default_factory=default_endtime)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    raw_data: Union[dict, DictObject] = field(default_factory=DictObject)
    
    _UPDATE_FIELDS: Tuple[str, ...] = (
        'message_id', 'approvals', 'disapprovals', 'approved_by', 'disapproved_by', 'outcome', 'total_all_mods'
    )

    def fix_fields(self):
        if isinstance(self.approved_by, str):
            self.approved_by = json.loads(self.approved_by)
        if isinstance(self.disapproved_by, str):
            self.disapproved_by = json.loads(self.disapproved_by)
        if self.id is not None and not isinstance(self.id, int):
            self.id = int(self.id)
        if self.message_id is not None and not isinstance(self.message_id, int):
            self.message_id = int(self.message_id)
        if isinstance(self.timestamp, str):
            self.timestamp = convert_datetime(self.timestamp)
        if isinstance(self.end_time, str):
            self.end_time = convert_datetime(self.end_time)
        self.approvals, self.disapprovals = int(self.approvals), int(self.disapprovals)
        self.total_all_mods = int(self.total_all_mods)
        return self

    @classmethod
    async def from_db(cls, msg_id: int, fail=True) -> Optional["Approval"]:
        adb = ApprovalsDB()
        o = await adb.find_approval_msgid(msg_id)
        if o is None:
            if fail:
                raise NotFound(f"Could not find an Approval with MSG ID: {msg_id}")
            return None
        return cls.from_dict(o).fix_fields()

    @classmethod
    async def from_db_id(cls, id: int, fail=True) -> Optional["Approval"]:
        adb = ApprovalsDB()
        o = await adb.find_approval(id)
        if o is None:
            if fail:
                raise NotFound(f"Could not find an Approval with DB ID: {id}")
            return None
        return cls.from_dict(o).fix_fields()
    
    async def save(self) -> int:
        """
        Save the Approval dataclass to the SQLite DB, and return the database ID for this approval
        """
        adb = ApprovalsDB()

        o = await adb.find_approval_msgid(self.message_id)
        self.fix_fields()
        if empty(o):
            if not empty(self.id):
                await self.update()
            else:
                create_data = await adb.create(
                    self.message_id, self.action, self.url, self.reason, self.username, self.approvals,
                    self.disapprovals, self.approved_by, self.disapproved_by, total_all_mods=self.total_all_mods,
                    outcome=self.outcome, end_time=self.end_time
                )
                self.id = create_data['row_id']
                # o = await adb.find_approval_msgid(self.message_id)
                # self.id = o['id']
        else:
            await self.update()
        return self.id

    async def update(self, fields: Tuple[str, ...] = _UPDATE_FIELDS):
        if empty(self.id):
            raise ValueError("ERROR: No ID set. You can't call update() unless Approval.id is set.")
        adb = ApprovalsDB()
        data = {k: v for k, v in dict(self).items() if k in fields}
        return await adb.update(self.id, **data)
    
    async def approve(self, user: str):
        if user in self.disapproved_by:
            log.debug("User previously disapproved approval, removing disapprove for user %s", user)
            self.disapprovals -= 1
            self.disapproved_by.remove(user)
        if user not in self.approved_by:
            log.debug("Adding approval for user %s", user)
            self.approvals += 1
            self.approved_by.append(user)
        log.debug("Saving approval object after approved by user %s", user)
        await self.save()
        return self.approvals

    async def disapprove(self, user: str):
        log.debug("Approval.disapprove being ran")
        if user in self.approved_by:
            log.debug("User previously approved approval, removing approve for user %s", user)
            self.approvals -= 1
            self.approved_by.remove(user)
        if user not in self.disapproved_by:
            log.debug("Adding disapproval for user %s", user)
            self.disapprovals += 1
            self.disapproved_by.append(user)
        log.debug("Saving approval object after disapproved by user %s", user)
        await self.save()
        return self.disapprovals


class ApprovalsDB(SqliteAsyncWrapper):
    """
    Approvals Database SQLite Wrapper
    Usage::

        >>> adb = ApprovalsDB()
        >>> # First you need to create the database(s) and indexes incase they don't exist
        >>> await adb.create_schemas()
        >>> # To insert an Approval:
        >>> adb.create(123532352, 'delete', 'https://example.com', 'spam', 'SomeUser#1234', 3, 4, 
                 approved_by=['SomeUser#1234', 'JohnDoe#6969'], disapproved_by=['JaneDoe#4200'],
                 total_all_mods=3, outcome=ApprovalOutcome.APPROVED, end_time=now_plus_hours(1)
                 )
        >>> # To find an approval by it's ID:
        >>> aprv = await adb.find_approval(1)
        >>> # To find an approval by it's Discord Message ID:
        >>> aprv = await adb.find_approval_msgid(12341234)

    """
    DEFAULT_DB_FOLDER: str = settings.APPROVAL_DB.parent
    DEFAULT_DB_NAME: str = settings.APPROVAL_DB.name
    DEFAULT_DB: str = join(DEFAULT_DB_FOLDER, DEFAULT_DB_NAME)

    SCHEMAS: List[Tuple[str, str]] = [
        ('approvals', "CREATE TABLE approvals ("
                  "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                  "message_id INTEGER NULL UNIQUE, "
                  "action TEXT NULL, "
                  "url TEXT NULL, "
                  "reason TEXT NULL, "
                  "username TEXT NULL, "
                  "approvals INTEGER DEFAULT 0, "
                  "disapprovals INTEGER DEFAULT 0, "
                  "approved_by TEXT DEFAULT '[]', "
                  "disapproved_by TEXT DEFAULT '[]', "
                  "outcome TEXT DEFAULT 'UNKNOWN', "
                  "total_all_mods INTEGER DEFAULT 0, "
                  "end_time DATETIME DEFAULT (datetime('now', '+1 hours')), "
                  "timestamp DATETIME DEFAULT CURRENT_TIMESTAMP"
                  "); "
            ),
        # ('items', "CREATE TABLE items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT);"),
    ]

    INDEXES: Dict[str, str] = {
        "idx_message_id": "CREATE UNIQUE INDEX idx_message_id ON approvals (message_id); ",
        "idx_outcome": "CREATE INDEX idx_outcome ON approvals (outcome); ",
        "idx_timestamp": "CREATE INDEX idx_timestamp ON approvals (timestamp); ",
        "idx_username": "CREATE INDEX idx_username ON approvals (username); ",
        "idx_url": "CREATE INDEX idx_url ON approvals (url); ",
        "idx_action": "CREATE INDEX idx_action ON approvals (action); ",
    }

    async def create_indexes(self) -> int:
        existing = await self.fetchall("PRAGMA index_list('approvals')")
        exlist = [d['name'] for d in existing]
        count = 0
        for name, idx in self.INDEXES.items():
            if name in exlist:
                log.debug("Index '%s' already exists - skipping", name)
                continue
            log.debug("Creating SQLite index '%s'", name)    
            await self.action(idx)
            count += 1
        log.debug("Created %s SQLite indexes!", count)
        return count

    async def create_schemas(self, *tables) -> DICT_CORO:
        t = await super().create_schemas(*tables)
        await self.create_indexes()
        return t

    async def get_approvals(self) -> List[Dict[str, Any]]:
        return await self.fetchall("SELECT * FROM approvals;")
    
    async def find_approval(self, id: int) -> Optional[Dict[str, Any]]:
        return await self.fetchone("SELECT * FROM approvals WHERE id = ?;", [id])

    async def find_approval_msgid(self, msg_id: int) -> Optional[Dict[str, Any]]:
        return await self.fetchone("SELECT * FROM approvals WHERE message_id = ?;", [msg_id])

    async def create(
            self, message_id: int, action: str, url: str, reason: str, username: str, 
            approvals: int = 0, disapprovals: int = 0, approved_by: Union[str, list] = '[]',
            disapproved_by: Union[str, list] = '[]', total_all_mods: int = 0,
            outcome: ApprovalOutcome = ApprovalOutcome.AUTO,
            end_time: datetime = None
        ) -> dict:
        """
        
            >>> adb = ApprovalsDB()
            >>> adb.create(123532352, 'delete', 'https://example.com', 'spam', 'SomeUser#1234', 3, 4, 
                    approved_by=['SomeUser#1234', 'JohnDoe#6969'], disapproved_by=['JaneDoe#4200'],
                    total_all_mods=3, outcome=ApprovalOutcome.APPROVED, end_time=now_plus_hours(1)
                 )
            {'row_count': 1, 'row_id': 3, 'result': []}
        
        """
        # b = self.builder('approvals')
        if empty(end_time, zero=True): end_time = default_endtime()
        if isinstance(disapproved_by, list): disapproved_by = str(disapproved_by)
        if isinstance(approved_by, list): approved_by = str(approved_by)
        disapprovals, approvals = int(disapprovals), int(approvals)
        if outcome == ApprovalOutcome.AUTO:
            if approvals > disapprovals:
                outcome = ApprovalOutcome.APPROVE if approvals > math.floor(total_all_mods / 2) else ApprovalOutcome.APPROVE_NOMAJ
            elif approvals < disapprovals:
                outcome = ApprovalOutcome.DISAPPROVE if disapprovals > math.floor(total_all_mods / 2) else ApprovalOutcome.DISAPPROVE_NOMAJ
            elif approvals == disapprovals:
                outcome = ApprovalOutcome.TIE
        
        if isinstance(outcome, ApprovalOutcome):
            outcome = outcome.value

        res, cur = await self.execute(
            "INSERT INTO approvals (message_id, action, url, reason, username, approvals, disapprovals, "
            "approved_by, disapproved_by, outcome, total_all_mods, end_time) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
            [
                message_id, action, url, reason, username, approvals, disapprovals, approved_by, 
                disapproved_by, outcome, total_all_mods, end_time

            ]
        )
        return dict(
            row_count=int(cur.rowcount), row_id=int(cur.lastrowid), result=res
        )
    
    async def update(self, id: int, **kwargs):
        """
        Update an existing approval

        Usage::

            >>> adb = ApprovalsDB()
            >>> await adb.update(5, approvals=5, disapprovals=2, outcome=ApprovalOutcome.APPROVED)
        
        """
        kwargs = dict(kwargs)
        if 'approved_by' in kwargs and isinstance(kwargs['approved_by'], list):
            kwargs['approved_by'] = json.dumps(kwargs['approved_by'])
        if 'disapproved_by' in kwargs and isinstance(kwargs['disapproved_by'], list):
            kwargs['disapproved_by'] = json.dumps(kwargs['disapproved_by'])
        if 'timestamp' in kwargs and isinstance(kwargs['timestamp'], datetime):
            kwargs['timestamp'] = str(kwargs['timestamp'].isoformat())
        if 'outcome' in kwargs and isinstance(kwargs['outcome'], ApprovalOutcome):
            kwargs['outcome'] = kwargs['outcome'].value
        fields = [i for i, x in kwargs.items()]
        values = [kwargs[f] for f in fields]
        query = "UPDATE approvals SET "
        for field in fields:
            query += f"{field} = ?, "
        query = query.rstrip(', ')
        query += ' WHERE id = ?;'
        return await self.action(query, values + [id])
    
# x = ApprovalsDB()

# b = x.builder('approvals')

# b.

