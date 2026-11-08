"""Repositorios: único lugar de la aplicación donde hay SQL."""
from __future__ import annotations

import sqlite3

from models.entities import Album, Cancion

_AHORA = "strftime('%Y-%m-%d %H:%M:%f', 'now', 'localtime')"


def _a_album(fila: sqlite3.Row) -> Album:
    total = fila["total"] if "total" in fila.keys() else 0
    return Album(id=fila["id"], nombre=fila["nombre"], creado_en=fila["creado_en"], total_canciones=total)


def _a_cancion(fila: sqlite3.Row) -> Cancion:
    return Cancion(
        id=fila["id"],
        album_id=fila["album_id"],
        titulo=fila["titulo"],
        letra=fila["letra"],
        semitonos=fila["semitonos"],
        creado_en=fila["creado_en"],
        actualizado_en=fila["actualizado_en"],
    )


class AlbumRepository:
    def __init__(self, con: sqlite3.Connection) -> None:
        self.con = con

    def listar(self) -> list[Album]:
        filas = self.con.execute(
            """
            SELECT a.id, a.nombre, a.creado_en, COUNT(c.id) AS total
            FROM album a LEFT JOIN cancion c ON c.album_id = a.id
            GROUP BY a.id
            ORDER BY a.creado_en, a.id
            """
        ).fetchall()
        return [_a_album(f) for f in filas]

    def obtener(self, album_id: int) -> Album | None:
        fila = self.con.execute(
            """
            SELECT a.id, a.nombre, a.creado_en, COUNT(c.id) AS total
            FROM album a LEFT JOIN cancion c ON c.album_id = a.id
            WHERE a.id = ?
            GROUP BY a.id
            """,
            (album_id,),
        ).fetchone()
        return _a_album(fila) if fila else None

    def crear(self, nombre: str) -> int:
        with self.con:
            cur = self.con.execute("INSERT INTO album (nombre) VALUES (?)", (nombre,))
        return int(cur.lastrowid)

    def renombrar(self, album_id: int, nombre: str) -> None:
        with self.con:
            self.con.execute("UPDATE album SET nombre = ? WHERE id = ?", (nombre, album_id))

    def eliminar(self, album_id: int) -> None:
        with self.con:  # las canciones se borran solas por ON DELETE CASCADE
            self.con.execute("DELETE FROM album WHERE id = ?", (album_id,))


class CancionRepository:
    def __init__(self, con: sqlite3.Connection) -> None:
        self.con = con

    def listar_con_album(self, album_id: int | None = None) -> list[tuple[Cancion, str]]:
        sql = (
            "SELECT c.*, a.nombre AS album_nombre FROM cancion c "
            "JOIN album a ON a.id = c.album_id"
        )
        params: tuple = ()
        if album_id is not None:
            sql += " WHERE c.album_id = ?"
            params = (album_id,)
        sql += " ORDER BY c.creado_en, c.id"
        return [(_a_cancion(f), f["album_nombre"]) for f in self.con.execute(sql, params).fetchall()]

    def obtener(self, cancion_id: int) -> Cancion | None:
        fila = self.con.execute("SELECT * FROM cancion WHERE id = ?", (cancion_id,)).fetchone()
        return _a_cancion(fila) if fila else None

    def crear(self, album_id: int, titulo: str, letra: str) -> int:
        with self.con:
            cur = self.con.execute(
                "INSERT INTO cancion (album_id, titulo, letra) VALUES (?, ?, ?)",
                (album_id, titulo, letra),
            )
        return int(cur.lastrowid)

    def actualizar(self, cancion_id: int, titulo: str, letra: str) -> None:
        with self.con:
            self.con.execute(
                f"UPDATE cancion SET titulo = ?, letra = ?, actualizado_en = {_AHORA} WHERE id = ?",
                (titulo, letra, cancion_id),
            )

    def actualizar_semitonos(self, cancion_id: int, semitonos: int) -> None:
        with self.con:
            self.con.execute("UPDATE cancion SET semitonos = ? WHERE id = ?", (semitonos, cancion_id))

    def eliminar(self, cancion_id: int) -> None:
        with self.con:
            self.con.execute("DELETE FROM cancion WHERE id = ?", (cancion_id,))


class SeleccionRapidaRepository:
    def __init__(self, con: sqlite3.Connection) -> None:
        self.con = con

    def listar_con_cancion(self) -> list[tuple[Cancion, str]]:
        sql = (
            "SELECT c.*, a.nombre AS album_nombre, s.posicion "
            "FROM seleccion_rapida s "
            "JOIN cancion c ON c.id = s.cancion_id "
            "JOIN album a ON a.id = c.album_id "
            "ORDER BY s.posicion ASC"
        )
        return [(_a_cancion(f), f["album_nombre"]) for f in self.con.execute(sql).fetchall()]

    def listar_ids(self) -> list[int]:
        filas = self.con.execute("SELECT cancion_id FROM seleccion_rapida ORDER BY posicion ASC").fetchall()
        return [int(f["cancion_id"]) for f in filas]

    def guardar_todas(self, cancion_ids: list[int]) -> None:
        with self.con:
            self.con.execute("DELETE FROM seleccion_rapida")
            self.con.executemany(
                "INSERT INTO seleccion_rapida (posicion, cancion_id) VALUES (?, ?)",
                [(idx, cid) for idx, cid in enumerate(cancion_ids)],
            )

    def vaciar(self) -> None:
        with self.con:
            self.con.execute("DELETE FROM seleccion_rapida")


class ConfiguracionRepository:
    def __init__(self, con: sqlite3.Connection) -> None:
        self.con = con

    def obtener(self, clave: str, por_defecto: str = "") -> str:
        fila = self.con.execute("SELECT valor FROM configuracion WHERE clave = ?", (clave,)).fetchone()
        return fila["valor"] if fila else por_defecto

    def guardar(self, clave: str, valor: str) -> None:
        with self.con:
            self.con.execute(
                "INSERT INTO configuracion (clave, valor) VALUES (?, ?) "
                "ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor",
                (clave, valor),
            )


