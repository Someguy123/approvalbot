#!/usr/bin/env python3
"""
Module Runner - code ran when the module is called with ``python3 -m approvalbot``

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
from approvalbot.bot import bot

if __name__ == '__main__':
    bot.start()
