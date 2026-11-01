"""Conexión a SQLite y creación del esquema."""
from __future__ import annotations

import sqlite3
from pathlib import Path

_AHORA = "strftime('%Y-%m-%d %H:%M:%f', 'now', 'localtime')"

ESQUEMA = f"""
CREATE TABLE IF NOT EXISTS album (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre    TEXT NOT NULL UNIQUE,
    creado_en TEXT NOT NULL DEFAULT ({_AHORA})
);

CREATE TABLE IF NOT EXISTS cancion (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    album_id       INTEGER NOT NULL REFERENCES album(id) ON DELETE CASCADE,
    titulo         TEXT NOT NULL,
    letra          TEXT NOT NULL DEFAULT '',
    semitonos      INTEGER NOT NULL DEFAULT 0,
    creado_en      TEXT NOT NULL DEFAULT ({_AHORA}),
    actualizado_en TEXT NOT NULL DEFAULT ({_AHORA})
);

CREATE INDEX IF NOT EXISTS idx_cancion_album ON cancion(album_id);
"""


def conectar(ruta: str | Path) -> sqlite3.Connection:
    """Abre (o crea) la base de datos y deja el esquema listo para usar."""
    if str(ruta) != ":memory:":
        Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(ruta))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")  # necesario para ON DELETE CASCADE
    con.executescript(ESQUEMA)
    return con
