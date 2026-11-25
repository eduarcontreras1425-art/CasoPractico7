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
