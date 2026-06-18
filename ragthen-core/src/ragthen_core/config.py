import json
from pathlib import Path

_APP_DIR = Path.home() / ".ragthen"
CONFIG_FILE = _APP_DIR / "config.json"
LIBRARIES_DIR = _APP_DIR / "libraries"

DEFAULT_CONFIG = {
    "backend_mode": "local",
    "remote_url": "http://localhost:8000",
    "libraries_path": str(LIBRARIES_DIR),
    "vault_path": "",
    "chunk_size": 1200,
    "chunk_overlap": 250,
    "llm_model": "gpt-4o",
}

_config_cache = None


def _create_default_config():
    _APP_DIR.mkdir(parents=True, exist_ok=True)
    LIBRARIES_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")
    return dict(DEFAULT_CONFIG)


def load_config() -> dict:
    global _config_cache
    if _config_cache is not None:
        return _config_cache
    if CONFIG_FILE.exists():
        try:
            _config_cache = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            return _config_cache
        except Exception:
            pass
    _config_cache = _create_default_config()
    return _config_cache


def get_libraries_dir() -> Path:
    cfg = load_config()
    raw = cfg.get("libraries_path", str(LIBRARIES_DIR))
    return Path(raw).expanduser().resolve()


CONFIG_DIR = _APP_DIR
