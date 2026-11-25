"""Lógica de negocio para operaciones de archivos y metadatos en Linux."""
import grp
import os
import pwd
import shutil
import stat
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

DEFAULT_TRASH_DIR = Path.home() / ".papelera"


@dataclass
class FileEntry:
    """Representa un elemento dentro de un directorio."""

    name: str
    path: Path
    is_dir: bool
    size: int
    permissions: str
    owner: str
    modified_ts: float
    modified_str: str


def format_size(size_bytes: int) -> str:
    """Convierte bytes a formato legible (B, KB, MB, GB, TB)."""
    size = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024.0 or unit == "TB":
            return f"{int(size)} B" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size_bytes} B"


def get_owner_name(uid: int, gid: int) -> str:
    """Obtiene usuario:grupo a partir de UID y GID."""
    try:
        user = pwd.getpwuid(uid).pw_name
    except KeyError:
        user = str(uid)
    try:
        group = grp.getgrgid(gid).gr_name
    except KeyError:
        group = str(gid)
    return f"{user}:{group}"


def _build_entry(name: str, path: Path, is_dir: bool, st: os.stat_result) -> FileEntry:
    return FileEntry(
        name=name,
        path=path,
        is_dir=is_dir,
        size=st.st_size,
        permissions=stat.filemode(st.st_mode)[1:],
        owner=get_owner_name(st.st_uid, st.st_gid),
        modified_ts=st.st_mtime,
        modified_str=datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M"),
    )


def list_directory(
    directory: Path,
    show_hidden: bool = False,
    sort_by: str = "name",
) -> list[FileEntry]:
    """Lista el contenido de un directorio aplicando filtros y ordenamiento."""
    entries: list[FileEntry] = []
    target = directory.resolve()
    if target.parent != target:
        entries.append(_build_entry("..", target.parent, True, target.parent.stat()))

    items: list[FileEntry] = []
    try:
        with os.scandir(target) as scanner:
            for item in scanner:
                if not show_hidden and item.name.startswith("."):
                    continue
                try:
                    st = item.stat(follow_symlinks=False)
                    is_dir = item.is_dir(follow_symlinks=False)
                    items.append(_build_entry(item.name, Path(item.path), is_dir, st))
                except OSError:
                    continue
    except PermissionError as exc:
        raise PermissionError(f"Sin permisos para leer: {target}") from exc

    if sort_by == "size":
        items.sort(key=lambda x: (not x.is_dir, -x.size, x.name.lower()))
    elif sort_by == "date":
        items.sort(key=lambda x: (not x.is_dir, -x.modified_ts, x.name.lower()))
    else:
        items.sort(key=lambda x: (not x.is_dir, x.name.lower()))
    return entries + items
