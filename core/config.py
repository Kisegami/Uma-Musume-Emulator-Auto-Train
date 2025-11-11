# utils/config_loader.pyfrom __future__ import annotations
import json, os, threading

class Config:
    _path = "config.json"
    _lock = threading.RLock()
    _cache: dict | None = None
    _mtime: float | None = None

    @classmethod
    def set_path(cls, path: str) -> None:
        cls._path = path
        cls._cache = None
        cls._mtime = None

    @classmethod
    def load(cls) -> dict:
        """Return cached config; hot-reloads when file mtime changes."""
        with cls._lock:
            try:
                mtime = os.path.getmtime(cls._path)
            except OSError:
                # If file missing, keep last good cache or empty
                return cls._cache or {}

            if cls._cache is None or cls._mtime != mtime:
                with open(cls._path, "r", encoding="utf-8") as f:
                    cls._cache = json.load(f)
                cls._mtime = mtime
            return cls._cache

    @classmethod
    def get(cls, key: str, default=None):
        return cls.load().get(key, default)