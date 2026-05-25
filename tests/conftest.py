from __future__ import annotations

import sys
from unittest.mock import MagicMock

# ── Seed mocks into sys.modules BEFORE any real nonebot imports ──
# This is the only reliable way to prevent get_driver() calls at import time.

_nb = MagicMock()
_nb.get_driver.return_value = MagicMock(config=MagicMock())
_nb.get_bots.return_value = {}
_nb.on_command.return_value = MagicMock()
_nb.require = lambda *a, **kw: None
_nb.plugin = MagicMock()
_nb.plugin.PluginMetadata = MagicMock()
_nb.plugin.get_plugin_config = lambda cls: cls()
_nb.permission = MagicMock()
_nb.permission.SUPERUSER = MagicMock()

_adapters = MagicMock()

_ob_v11 = MagicMock()
_ob_v11.permission = MagicMock()
_ob_v11.permission.GROUP_ADMIN = MagicMock()
_ob_v11.permission.GROUP_OWNER = MagicMock()

from sqlalchemy.orm import DeclarativeBase

class _FakeModel(DeclarativeBase):
    __abstract__ = True

_nb_orm = MagicMock()
_nb_orm.Model = _FakeModel

_nb_aps = MagicMock()
_nb_aps.scheduler = MagicMock()

# Build the module tree before anything imports it
sys.modules["nonebot"] = _nb
sys.modules["nonebot.plugin"] = _nb.plugin
sys.modules["nonebot.plugin.load"] = MagicMock()
sys.modules["nonebot.adapters"] = _adapters
sys.modules["nonebot.adapters.onebot"] = MagicMock()
sys.modules["nonebot.adapters.onebot.v11"] = _ob_v11
sys.modules["nonebot.adapters.onebot.v11.permission"] = _ob_v11.permission
sys.modules["nonebot.permission"] = _nb.permission
sys.modules["nonebot_plugin_orm"] = _nb_orm
sys.modules["nonebot_plugin_apscheduler"] = _nb_aps
