"""Pruebas unitarias para la lógica de operaciones y configuración."""
import stat

import pytest

from src.config_manager import add_bookmark, load_config, remove_bookmark
from src.file_ops import (
    calculate_directory_size,
    change_permissions,
    copy_item,
    create_directory,
    format_size,
    list_directory,
    move_item,
    move_to_trash,
    rename_item,
    search_files,
)


def test_list_directory_filters_hidden(tmp_path):
    (tmp_path / "visible.txt").write_text("hola")
    (tmp_path / ".oculto.txt").write_text("secreto")
    names_no_hidden = [e.name for e in list_directory(tmp_path, show_hidden=False)]
    assert "visible.txt" in names_no_hidden
    assert ".oculto.txt" not in names_no_hidden
    names_with_hidden = [e.name for e in list_directory(tmp_path, show_hidden=True)]
    assert ".oculto.txt" in names_with_hidden


def test_list_directory_sort_by_size(tmp_path):
    (tmp_path / "pequeno.txt").write_text("a")
    (tmp_path / "grande.txt").write_text("a" * 500)
    entries = [e for e in list_directory(tmp_path, sort_by="size") if e.name != ".."]
    assert entries[0].name == "grande.txt"
    assert entries[1].name == "pequeno.txt"


def test_create_directory(tmp_path):
    created = create_directory(tmp_path, "nueva_carpeta")
    assert created.exists()
    assert created.is_dir()


def test_create_directory_invalid_name(tmp_path):
    with pytest.raises(ValueError):
        create_directory(tmp_path, "../hack")


def test_rename_item(tmp_path):
    original = tmp_path / "viejo.log"
    original.write_text("log data")
    renamed = rename_item(original, "nuevo.log")
    assert not original.exists()
    assert renamed.exists()
    assert renamed.read_text() == "log data"


def test_copy_item_file_and_dir(tmp_path):
    src_dir = tmp_path / "origen"
    dst_dir = tmp_path / "destino"
    src_dir.mkdir()
    dst_dir.mkdir()
    archivo = src_dir / "config.conf"
    archivo.write_text("port=8080")
    copied = copy_item(archivo, dst_dir)
    assert archivo.exists()
    assert copied.exists()
    assert copied.read_text() == "port=8080"


def test_move_item(tmp_path):
    src_dir = tmp_path / "origen"
    dst_dir = tmp_path / "destino"
    src_dir.mkdir()
    dst_dir.mkdir()
    archivo = src_dir / "mover.txt"
    archivo.write_text("contenido")
    moved = move_item(archivo, dst_dir)
    assert not archivo.exists()
    assert moved.exists()


def test_move_to_trash(tmp_path):
    trash = tmp_path / "papelera_test"
    archivo = tmp_path / "importante.db"
    archivo.write_text("datos críticos")
    trashed = move_to_trash(archivo, trash_dir=trash)
    assert not archivo.exists()
    assert trashed.exists()
    assert trashed.parent == trash
    assert trashed.read_text() == "datos críticos"


def test_search_files_recursive(tmp_path):
    sub = tmp_path / "sub1" / "sub2"
    sub.mkdir(parents=True)
    target = sub / "reporte_servidor.txt"
    target.write_text("ok")
    (tmp_path / "otro.txt").write_text("no")
    results = search_files(tmp_path, "servidor")
    assert len(results) == 1
    assert results[0] == target


def test_change_permissions(tmp_path):
    script = tmp_path / "deploy.sh"
    script.write_text("#!/bin/bash")
    change_permissions(script, "755")
    assert stat.S_IMODE(script.stat().st_mode) == 0o755


def test_calculate_directory_size(tmp_path):
    sub = tmp_path / "logs"
    sub.mkdir()
    (tmp_path / "a.bin").write_bytes(b"x" * 100)
    (sub / "b.bin").write_bytes(b"y" * 250)
    assert calculate_directory_size(tmp_path) == 350
    assert format_size(2048) == "2.0 KB"


def test_bookmarks_persistence(tmp_path):
    cfg_file = tmp_path / "config.json"
    folder = tmp_path / "proyecto"
    folder.mkdir()
    bookmarks = add_bookmark(str(folder), config_path=cfg_file)
    assert str(folder.resolve()) in bookmarks
    loaded = load_config(config_path=cfg_file)
    assert str(folder.resolve()) in loaded["bookmarks"]
    bookmarks_after = remove_bookmark(str(folder), config_path=cfg_file)
    assert str(folder.resolve()) not in bookmarks_after
