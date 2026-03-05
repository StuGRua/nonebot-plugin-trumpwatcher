"""Compatibility shim for loaders using the PyPI package name."""

from importlib import import_module

_impl = import_module("nonebot_plugin_trumpwatcher")
__plugin_meta__ = getattr(_impl, "__plugin_meta__", None)
