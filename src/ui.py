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

    def _prompt_input(self, prompt: str) -> str | None:
        height, width = self.stdscr.getmaxyx()
        win = curses.newwin(3, max(20, width - 4), max(1, height // 2 - 1), 2)
        win.box()
        win.addstr(0, 2, f" {prompt} "[: width - 8], curses.A_BOLD)
        win.refresh()
        curses.echo()
        curses.curs_set(1)
        try:
            raw = win.getstr(1, 2, max(10, width - 10))
            return raw.decode("utf-8", errors="replace").strip()
        except curses.error:
            return None
        finally:
            curses.noecho()
            curses.curs_set(0)

    def _prompt_confirm(self, question: str) -> bool:
        height, width = self.stdscr.getmaxyx()
        win = curses.newwin(3, max(20, width - 4), max(1, height // 2 - 1), 2)
        win.box()
        msg = f"{question} [s/N]: "
        win.addstr(1, 2, msg[: width - 8], curses.color_pair(5) | curses.A_BOLD)
        win.refresh()
        key = win.getch()
        return key in (ord("s"), ord("S"), ord("y"), ord("Y"))

    def _handle_search(self) -> None:
        query = self._prompt_input("Buscar archivo/carpeta (nombre):")
        if not query:
            return
        results = search_files(
            self.active_panel.current_dir, query, show_hidden=self.show_hidden
        )
        if not results:
            self.status_msg = f"Sin coincidencias para '{query}'."
            return
        selected_idx = 0
        while True:
            self.stdscr.erase()
            height, width = self.stdscr.getmaxyx()
            max_rows = max(1, height - 3)
            header = f" RESULTADOS PARA '{query}' ({len(results)} encontrados) "
            self.stdscr.addstr(0, 0, header.ljust(width)[:width], curses.color_pair(3))
            start = max(0, selected_idx - max_rows + 1)
            for i in range(max_rows):
                idx = start + i
                if idx >= len(results):
                    break
                rel = str(results[idx])
                attr = curses.color_pair(2) if idx == selected_idx else curses.A_NORMAL
                self.stdscr.addstr(i + 1, 1, rel[: max(1, width - 2)], attr)
            footer = " [Enter] Ir a ubicación | [q/Esc] Cancelar "
            self.stdscr.addstr(
                height - 1, 0, footer.ljust(width)[: max(1, width - 1)], curses.color_pair(3)
            )
            self.stdscr.refresh()
            key = self.stdscr.getch()
            if key == curses.KEY_DOWN and selected_idx < len(results) - 1:
                selected_idx += 1
            elif key == curses.KEY_UP and selected_idx > 0:
                selected_idx -= 1
            elif key in (10, 13):
                chosen = results[selected_idx]
                target_dir = chosen if chosen.is_dir() else chosen.parent
                self.active_panel.current_dir = target_dir
                self.active_panel.selected_idx = 0
                self.active_panel.refresh(self.show_hidden, self.sort_by)
                for idx, entry in enumerate(self.active_panel.entries):
                    if entry.path == chosen:
                        self.active_panel.selected_idx = idx
                        break
                self.status_msg = f"Ubicado en: {chosen}"
                break
            elif key in (ord("q"), ord("Q"), 27):
                break

    def _handle_bookmarks(self) -> None:
        while True:
            bookmarks: list[str] = self.config.get("bookmarks", [])
            self.stdscr.erase()
            height, width = self.stdscr.getmaxyx()
            header = " MARCADORES FAVORITOS (Guardados en JSON) "
            self.stdscr.addstr(0, 0, header.ljust(width)[:width], curses.color_pair(3))
            for idx, bpath in enumerate(bookmarks[: max(1, height - 3)]):
                self.stdscr.addstr(idx + 1, 2, f"[{idx + 1}] {bpath}"[: max(1, width - 4)])
            footer = " [1-9] Ir | [a] Agregar ruta actual | [x] Borrar #1 | [q] Cerrar "
            self.stdscr.addstr(
                height - 1, 0, footer.ljust(width)[: max(1, width - 1)], curses.color_pair(3)
            )
            self.stdscr.refresh()
            key = self.stdscr.getch()
            if key in (ord("q"), ord("Q"), 27):
                break
            if key in (ord("a"), ord("A")):
                updated = add_bookmark(str(self.active_panel.current_dir))
                self.config["bookmarks"] = updated
                self.status_msg = f"Marcador guardado: {self.active_panel.current_dir}"
            elif key in (ord("x"), ord("X")) and bookmarks:
                updated = remove_bookmark(bookmarks[0])
                self.config["bookmarks"] = updated
            elif ord("1") <= key <= ord("9"):
                choice = key - ord("1")
                if choice < len(bookmarks):
                    dest = Path(bookmarks[choice])
                    if dest.is_dir():
                        self.active_panel.current_dir = dest
                        self.active_panel.selected_idx = 0
                        self.active_panel.refresh(self.show_hidden, self.sort_by)
                        self.status_msg = f"Saltado a marcador: {dest}"
                    else:
                        self.status_msg = f"La ruta guardada ya no existe: {dest}"
                    break
