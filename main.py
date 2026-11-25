"""Punto de entrada principal del Explorador de Archivos para Servidores."""
import curses
import sys

from src.ui import start_ui


def main() -> int:
    """Inicia la interfaz curses de manera segura."""
    try:
        curses.wrapper(start_ui)
    except KeyboardInterrupt:
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"Error inesperado en la interfaz: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
