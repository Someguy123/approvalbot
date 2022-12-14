from dotenv import load_dotenv
from pathlib import Path
from typing import List, Union, Optional
from privex.helpers import env_bool, env_csv, env_int, DictObject
from privex.helpers import settings as pvx_settings
from privex.loghelper import LogHelper
from os import getenv as env
from os.path import dirname, abspath
import os
import logging

BASE_DIR: Path = Path(dirname(dirname(abspath(__file__)))).resolve()

load_dotenv()

VERSION: str = '1.0.0'
"""Version number for ApprovalBot"""
GH_URL: str = "https://github.com/Someguy123/approvalbot"
"""Github URL for ApprovalBot"""
DEBUG: bool = env_bool('DEBUG', False)
"""Debug mode - this affects various default settings such as the log level, cache adapter, etc."""
TOKEN: Optional[str] = env('DISCORD_TOKEN', None)
"""Discord Bot Token"""
CONFIG_FILE: Path = Path(env('CONFIG_FILE', BASE_DIR / 'config.yml')).resolve()
"""Where to store the config file used to store admin/mod lists + various command-adjustable bot settings"""

LOG_LEVEL = logging.getLevelName(env('LOG_LEVEL', 'DEBUG' if DEBUG else 'WARN').upper())

_lh = LogHelper('approvalbot', level=LOG_LEVEL, handler_level=LOG_LEVEL)
_lh.add_console_handler()
log = logging.getLogger(__name__)

DEFAULT_APPROVAL_END = env_int('DEFAULT_APPROVAL_END', 60 * 60)
"""(Default: 1 hour) How long before you can't vote on an approval request any more - in seconds."""

SERVER_IDS: List[int] = [int(i) for i in env_csv('SERVER_IDS', [])]
"""The Discord server IDs the bot should run in"""

CACHE_ADAPTER: str = env('CACHE_ADAPTER', 'memory' if DEBUG else 'sqlite3')
"""
The default Cache Adapter for the application.

For production, it's recommended to use either ``redis`` or ``memcached``, or
at least ``sqlite3`` if it's not possible to use redis/memcached.

Approval request information is stored in the cache, if you use ``memory`` and restart
the application, it might not be possible to vote on approvals made before the app
was restarted.

Options:

  * ``memory``    - Stores the cache in the application memory - WARNING: Does not persist between restarts
  * ``sqlite3``   - Stores the cache in an SQLite3 database
  * ``redis``     - Stores the cache in a Redis server
  * ``memcached`` - Stores the cache in a Memcached server
"""

DATA_DIR: Path = Path(env('DATA_DIR', BASE_DIR / 'data')).resolve()
"""Where to store data files such as SQLite3 cache (if using sqlite adapter), and Approvals DB"""

APPROVAL_DB: Path = Path(env('APPROVAL_DB', DATA_DIR / 'approvals.sqlite3'))
"""Where to store the Approvals DB? Defaults to: DATA_DIR/approvals.sqlite3 (data/approvals.sqlite3)"""

APPROVAL_DB = APPROVAL_DB.resolve()

pvx_settings.SQLITE_APP_DB_FOLDER = env('SQLITE_APP_DB_FOLDER', str(DATA_DIR))
pvx_settings.SQLITE_APP_DB_NAME = env('SQLITE_APP_DB_NAME', 'cache_approvalbot')

CONFIG_DEFAULTS = DictObject(
    moderators=[], admins=[], show_votes=False,
    admins_can_vote=True, majority_include_admins=True
)
CONFIG = DictObject(**CONFIG_DEFAULTS)

if not CONFIG_FILE.is_absolute():
    CONFIG_FILE = BASE_DIR / CONFIG_FILE

if not APPROVAL_DB.is_absolute():
    if APPROVAL_DB.startswith(DATA_DIR.name) or APPROVAL_DB.startswith('./' + DATA_DIR.name):
        APPROVAL_DB = APPROVAL_DB.name
    APPROVAL_DB =  DATA_DIR / APPROVAL_DB

if not Path(pvx_settings.SQLITE_APP_DB_FOLDER).exists():
    log.debug("Sqlite DB dir doesn't exist, creating SQLITE_APP_DB_FOLDER folder: %s", pvx_settings.SQLITE_APP_DB_FOLDER)
    os.mkdir(pvx_settings.SQLITE_APP_DB_FOLDER)

