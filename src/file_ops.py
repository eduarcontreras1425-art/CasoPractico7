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


def create_directory(parent_dir: Path, folder_name: str) -> Path:
    """Crea una nueva carpeta dentro del directorio indicado."""
    if not folder_name or "/" in folder_name or folder_name in (".", ".."):
        raise ValueError("Nombre de carpeta inválido.")
    new_dir = parent_dir / folder_name
    new_dir.mkdir(parents=False, exist_ok=False)
    return new_dir


def rename_item(source: Path, new_name: str) -> Path:
    """Renombra un archivo o carpeta en su mismo directorio."""
    if not new_name or "/" in new_name or new_name in (".", ".."):
        raise ValueError("Nuevo nombre inválido.")
    destination = source.parent / new_name
    if destination.exists():
        raise FileExistsError(f"Ya existe '{new_name}' en el destino.")
    return source.rename(destination)


def copy_item(source: Path, dest_dir: Path) -> Path:
    """Copia un archivo o directorio completo al directorio destino."""
    destination = dest_dir / source.name
    if destination.exists():
        raise FileExistsError(f"El destino ya contiene '{source.name}'.")
    if source.is_dir():
        shutil.copytree(source, destination, symlinks=True)
    else:
        shutil.copy2(source, destination)
    return destination


def move_item(source: Path, dest_dir: Path) -> Path:
    """Mueve un archivo o directorio hacia el directorio destino."""
    destination = dest_dir / source.name
    if destination.exists():
        raise FileExistsError(f"El destino ya contiene '{source.name}'.")
    shutil.move(str(source), str(destination))
    return destination


def create_directory(parent_dir: Path, folder_name: str) -> Path:
    """Crea una nueva carpeta dentro del directorio indicado."""
    if not folder_name or "/" in folder_name or folder_name in (".", ".."):
        raise ValueError("Nombre de carpeta inválido.")
    new_dir = parent_dir / folder_name
    new_dir.mkdir(parents=False, exist_ok=False)
    return new_dir


def rename_item(source: Path, new_name: str) -> Path:
    """Renombra un archivo o carpeta en su mismo directorio."""
    if not new_name or "/" in new_name or new_name in (".", ".."):
        raise ValueError("Nuevo nombre inválido.")
    destination = source.parent / new_name
    if destination.exists():
        raise FileExistsError(f"Ya existe '{new_name}' en el destino.")
    return source.rename(destination)


def copy_item(source: Path, dest_dir: Path) -> Path:
    """Copia un archivo o directorio completo al directorio destino."""
    destination = dest_dir / source.name
    if destination.exists():
        raise FileExistsError(f"El destino ya contiene '{source.name}'.")
    if source.is_dir():
        shutil.copytree(source, destination, symlinks=True)
    else:
        shutil.copy2(source, destination)
    return destination


def move_item(source: Path, dest_dir: Path) -> Path:
    """Mueve un archivo o directorio hacia el directorio destino."""
    destination = dest_dir / source.name
    if destination.exists():
        raise FileExistsError(f"El destino ya contiene '{source.name}'.")
    shutil.move(str(source), str(destination))
    return destination


def move_to_trash(source: Path, trash_dir: Path = DEFAULT_TRASH_DIR) -> Path:
    """Envía un archivo o carpeta a ~/.papelera en lugar de borrarlo definitivamente."""
    trash_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    trash_target = trash_dir / f"{source.name}_{timestamp}"
    shutil.move(str(source), str(trash_target))
    return trash_target


def search_files(root_dir: Path, query: str, show_hidden: bool = False) -> list[Path]:
    """Busca archivos o carpetas por subcadena en root_dir y subcarpetas."""
    matches: list[Path] = []
    q_lower = query.strip().lower()
    if not q_lower:
        return matches
    for current_root, dirs, files in os.walk(root_dir):
        if not show_hidden:
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            files = [f for f in files if not f.startswith(".")]
        for name in dirs + files:
            if q_lower in name.lower():
                matches.append(Path(current_root) / name)
    return sorted(matches)
