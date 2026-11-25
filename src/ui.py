"""Interfaz de usuario en terminal con curses estilo Midnight Commander."""
import curses
from pathlib import Path
from typing import Any

from src.config_manager import add_bookmark, load_config, remove_bookmark, save_config
from src.file_ops import (
    FileEntry,
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


class PanelState:
    """Mantiene el estado independiente de cada panel (izquierdo/derecho)."""

    def __init__(self, start_path: Path) -> None:
        self.current_dir: Path = start_path.resolve()
        self.entries: list[FileEntry] = []
        self.selected_idx: int = 0
        self.scroll_offset: int = 0

    def refresh(self, show_hidden: bool, sort_by: str) -> str | None:
        """Recarga la lista de archivos del directorio actual."""
        try:
            self.entries = list_directory(
                self.current_dir, show_hidden=show_hidden, sort_by=sort_by
            )
            if self.selected_idx >= len(self.entries):
                self.selected_idx = max(0, len(self.entries) - 1)
            return None
        except PermissionError as exc:
            return str(exc)

    @property
    def selected_entry(self) -> FileEntry | None:
        if not self.entries:
            return None
        return self.entries[self.selected_idx]


class CommanderApp:
    """Aplicación principal de dos paneles sobre curses."""

    def __init__(self, stdscr: "curses.window") -> None:
        self.stdscr = stdscr
        self.config: dict[str, Any] = load_config()
        self.show_hidden: bool = bool(self.config.get("show_hidden", False))
        self.sort_by: str = str(self.config.get("sort_by", "name"))
        self.panels = [PanelState(Path.cwd()), PanelState(Path.home())]
        self.active_idx = 0
        self.status_msg = "Listo. Usa flechas para navegar, Tab cambia panel, q salir."
        self._init_colors()
        curses.curs_set(0)
        self.stdscr.keypad(True)
        for panel in self.panels:
            panel.refresh(self.show_hidden, self.sort_by)

    def _init_colors(self) -> None:
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_CYAN)
        curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(4, curses.COLOR_YELLOW, -1)
        curses.init_pair(5, curses.COLOR_RED, -1)

    @property
    def active_panel(self) -> PanelState:
        return self.panels[self.active_idx]

    @property
    def inactive_panel(self) -> PanelState:
        return self.panels[1 - self.active_idx]

    def _save_preferences(self) -> None:
        self.config["show_hidden"] = self.show_hidden
        self.config["sort_by"] = self.sort_by
        save_config(self.config)

    def _draw_panel(
        self, panel: PanelState, is_active: bool, y: int, x: int, h: int, w: int
    ) -> None:
        if h < 4 or w < 15:
            return
        win = curses.newwin(h, w, y, x)
        if is_active:
            win.attron(curses.color_pair(4))
        win.box()
        if is_active:
            win.attroff(curses.color_pair(4))
        title = f" {panel.current_dir} "
        win.addstr(0, 2, title[: max(1, w - 4)], curses.A_BOLD if is_active else curses.A_NORMAL)
        col_header = (
            f"{'Nombre':<22} {'Tamaño':>9} {'Permisos':<9} "
            f"{'Propietario':<12} {'Fecha':<16}"
        )
        win.addstr(1, 1, col_header[: max(1, w - 2)], curses.A_UNDERLINE)

        list_height = max(1, h - 3)
        if panel.selected_idx < panel.scroll_offset:
            panel.scroll_offset = panel.selected_idx
        elif panel.selected_idx >= panel.scroll_offset + list_height:
            panel.scroll_offset = panel.selected_idx - list_height + 1

        for row in range(list_height):
            entry_idx = panel.scroll_offset + row
            if entry_idx >= len(panel.entries):
                break
            entry = panel.entries[entry_idx]
            is_real_dir = entry.is_dir and entry.name != ".."
            disp_name = f"/{entry.name}" if is_real_dir else entry.name
            size_txt = "<DIR>" if entry.is_dir else format_size(entry.size)
            line = (
                f"{disp_name[:21]:<22} {size_txt:>9} "
                f"{entry.permissions:<9} {entry.owner[:11]:<12} {entry.modified_str:<16}"
            )
            if is_active and entry_idx == panel.selected_idx:
                attr = curses.color_pair(2) | curses.A_BOLD
            elif entry.is_dir:
                attr = curses.color_pair(1) | curses.A_BOLD
            else:
                attr = curses.A_NORMAL
            win.addstr(row + 2, 1, line[: max(1, w - 2)], attr)
        win.noutrefresh()

    def render(self) -> None:
        self.stdscr.erase()
        height, width = self.stdscr.getmaxyx()
        if height < 10 or width < 40:
            self.stdscr.addstr(0, 0, "Terminal muy pequeña. Amplía la ventana.")
            self.stdscr.refresh()
            return
        top_bar = (
            f" EXPLORADOR SSH | Orden: {self.sort_by.upper()} | "
            f"Ocultos: {'SÍ' if self.show_hidden else 'NO'} "
        )
        self.stdscr.addstr(0, 0, top_bar.ljust(width)[:width], curses.color_pair(3) | curses.A_BOLD)
        panel_h = height - 3
        left_w = width // 2
        right_w = width - left_w
        self.stdscr.noutrefresh()
        self._draw_panel(self.panels[0], self.active_idx == 0, 1, 0, panel_h, left_w)
        self._draw_panel(self.panels[1], self.active_idx == 1, 1, left_w, panel_h, right_w)
        keys_bar = (
            " [Tab]Cambiar de panel [Enter]Abrir [v]Visor de texto [c]Copiar [m]Mover [n]Crear carpeta "
            "[r]Renombrar [d]Papelera [/]Buscar por nombre [o]Ordenar por nombre tamaño y fecha [h]Ocultos "
            "[p]Cambiar permisos [t]Tamaño total de una carpeta [b]Marcadores de ruta favorita [q]Salir "
        )
        self.stdscr.addstr(
            height - 2, 0, keys_bar.ljust(width)[: max(1, width - 1)], curses.color_pair(3)
        )
        self.stdscr.addstr(height - 1, 0, f" {self.status_msg}"[: max(1, width - 1)])
        curses.doupdate()
