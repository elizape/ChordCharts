"""Mis canciones: álbumes, letras con acordes y transposición.

Uso:
    python main.py                 # usa songs.db junto a este archivo
    python main.py --db ruta.db    # otra base de datos
    python main.py --demo          # si la base está vacía, carga álbumes y canciones de ejemplo
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

from database.connection import conectar  # noqa: E402
from services.demo import cargar_demo  # noqa: E402
from services.library_service import ServicioBiblioteca  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Gestor de canciones con acordes (ttkbootstrap + SQLite)")
    parser.add_argument("--db", default=os.environ.get("SONGAPP_DB", str(RAIZ / "songs.db")),
                        help="ruta de la base de datos SQLite (por defecto songs.db junto a main.py)")
    parser.add_argument("--demo", action="store_true", help="cargar datos de ejemplo si la base está vacía")
    args = parser.parse_args()

    servicio = ServicioBiblioteca(conectar(args.db))
    if args.demo:
        cargar_demo(servicio)

    from ui.app import App  # se importa acá para que --help funcione sin tener Tk instalado

    App(servicio).ejecutar()


if __name__ == "__main__":
    main()
