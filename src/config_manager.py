"""Gestión de configuración persistente y marcadores favoritos en JSON."""
import json
from pathlib import Path
from typing import Any

DEFAULT_CONFIG_PATH = Path.home() / ".explorador_ssh_config.json"


def load_config(config_path: Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    """Carga la configuración desde disco o devuelve valores por defecto."""
    default_data: dict[str, Any] = {
        "show_hidden": False,
        "sort_by": "name",
        "bookmarks": [str(Path.home()), "/var/log", "/etc"],
    }
    if not config_path.exists():
        save_config(default_data, config_path)
        return default_data
    try:
        with config_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        for key, val in default_data.items():
            data.setdefault(key, val)
        return data
    except (json.JSONDecodeError, OSError):
        return default_data


def save_config(data: dict[str, Any], config_path: Path = DEFAULT_CONFIG_PATH) -> None:
    """Guarda la configuración actual en formato JSON."""
    with config_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


def add_bookmark(path_str: str, config_path: Path = DEFAULT_CONFIG_PATH) -> list[str]:
    """Agrega una ruta a los marcadores favoritos si no existe."""
    config = load_config(config_path)
    resolved = str(Path(path_str).resolve())
    if resolved not in config["bookmarks"]:
        config["bookmarks"].append(resolved)
        save_config(config, config_path)
    return config["bookmarks"]


def remove_bookmark(path_str: str, config_path: Path = DEFAULT_CONFIG_PATH) -> list[str]:
    """Elimina una ruta de los marcadores favoritos."""
    config = load_config(config_path)
    resolved = str(Path(path_str).resolve())
    if resolved in config["bookmarks"]:
        config["bookmarks"].remove(resolved)
        save_config(config, config_path)
    return config["bookmarks"]
