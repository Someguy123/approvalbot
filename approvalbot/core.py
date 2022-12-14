"""
Core - Shared variables and functions

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
import copy
from pathlib import Path
from dotenv import load_dotenv
from os import getenv as env
from privex.helpers import env_bool, env_csv, empty, empty_if, DictObject
from privex.loghelper import LogHelper
from privex.helpers.cache import adapter_set, async_adapter_set
from typing import Union, List, Optional
from approvalbot import settings
import logging
import sys
import yaml
import os

__all__ = [
    'print_err', 'IndentDumper', 'load_config', 'save_config', 
    'add_missing_config_defaults',
]


log = logging.getLogger(__name__)

def print_err(*msg, **kwargs):
    print(*msg, file=sys.stderr, **kwargs)

if not settings.DATA_DIR.exists():
    log.debug("Data dir doesn't exist, creating DATA_DIR folder: %s", settings.DATA_DIR)
    os.mkdir(settings.DATA_DIR)


try:
    log.debug("Setting cache adapter to: %s", settings.CACHE_ADAPTER)
    adapter_set(settings.CACHE_ADAPTER)
    log.debug("Setting async cache adapter to: %s", settings.CACHE_ADAPTER)
    async_adapter_set(settings.CACHE_ADAPTER)
except KeyError as e:
    if 'not found in category' in str(e):
        print_err(f" [ERROR] Invalid settings.CACHE_ADAPTER setting '{settings.CACHE_ADAPTER}', valid cache adapter options: memory, sqlite3, redis, memcached")
    else:
        print_err(f" [ERROR] A KeyError was raised while loading cache adapter '{settings.CACHE_ADAPTER}' - reason: {e!s}")
    sys.exit(4)
except (AttributeError, IndexError, ImportError) as e:
    print_err(f" [ERROR] !!! Failed to set cache adapter to '{settings.CACHE_ADAPTER}', exception message: {type(e)} - {e!s}")
    print_err(f" [ERROR] Packages required for that cache adapter may be missing, please run 'pipenv install', or 'pip3 install -U \"privex-helpers[cache]\"'")
    sys.exit(3)


class IndentDumper(yaml.Dumper):
    def increase_indent(self, flow=False, indentless=False):
        return super(IndentDumper, self).increase_indent(flow, False)

def add_missing_config_defaults(cfg: Optional[Union[dict, DictObject]] = None, auto_save=True) -> DictObject:
    if cfg is None:
        cfg = settings.CONFIG
    
    was_missing = False
    for k, v in settings.CONFIG_DEFAULTS.items():
        if k not in cfg:
            log.debug("Adding missing key '%s' to CONFIG from CONFIG_DEFAULTS: '%s = %s'", k, k, v)
            cfg[k] = copy.deepcopy(v)
            was_missing = True
    
    if auto_save and was_missing:
        log.debug("Config was missing some keys which have now been added and set to their defaults, auto-saving updated config...")
        save_config(cfg)
    return DictObject(cfg)

def load_config(cfg_file: Union[str, Path] = settings.CONFIG_FILE, update_global=True, add_missing=True) -> Union[DictObject, dict]:
    log.info("Loading config from file: %s", cfg_file)
    with open(str(cfg_file), 'r') as fh:
        cfg = empty_if(yaml.safe_load(fh), {}, itr=True)
    
    if update_global:
        log.debug("Updating global config object")
        settings.CONFIG.clear()
        settings.CONFIG.update(cfg)
    # If add_missing is True, run add_missing_config_defaults to add any missing
    # config keys and set them to their default value from CONFIG_DEFAULTS
    if add_missing:
        cfg = add_missing_config_defaults(cfg)
    log.debug("Config data: %s", cfg)
    return cfg

def save_config(data: Union[DictObject, dict] = None, cfg_file: Union[str, Path] = settings.CONFIG_FILE) -> Union[DictObject, dict]:
    if data in [None, '']:
        data = settings.CONFIG
    else:
        settings.CONFIG.update(data)
    
    log.debug("Config data: %s", data)
    log.info("Saving config to file: %s", cfg_file)
    
    with open(str(cfg_file), 'w') as fh:
        yaml.dump(dict(data), fh, indent=4, Dumper=IndentDumper)
        fh.flush()
    
    return data

if not settings.CONFIG_FILE.exists():
    save_config()

load_config()


if empty(settings.TOKEN) or settings.TOKEN == 'MyBotToken':
    print_err("ERROR! You must set TOKEN in your .env file to a valid Discord Bot token")
    print_err("You can create and manage a Discord bot on the Discord developer portal here: https://discord.com/developers/applications")
    sys.exit(2)

