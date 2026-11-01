"""Reglas de negocio: validaciones, orden, búsqueda y transposición guardada."""
from __future__ import annotations

import sqlite3
import unicodedata
from typing import Callable

from database.repositories import AlbumRepository, CancionRepository
from models.entities import Album, Cancion, ResultadoCancion
from services.chords import clasificar_linea, normalizar_semitonos

ORDENES = (
    ("recientes", "Más recientes"),
    ("antiguos", "Más antiguos"),
    ("az", "A → Z"),
    ("za", "Z → A"),
)
ORDEN_POR_DEFECTO = "recientes"

MAX_NOMBRE_ALBUM = 80
MAX_TITULO = 120
MAX_LETRA = 100_000


class ValidationError(Exception):
    """Dato inválido; el mensaje es apto para mostrarse al usuario."""


class NotFoundError(Exception):
    """El álbum o la canción ya no existe."""


def _clave(texto: str) -> str:
    """Clave de comparación: sin mayúsculas ni tildes (para duplicados, orden y búsqueda)."""
    t = unicodedata.normalize("NFKD", texto.casefold())
    return "".join(ch for ch in t if not unicodedata.combining(ch))


def _ordenar(items: list, orden: str, nombre: Callable, fecha: Callable, ident: Callable) -> list:
    if orden == "az":
        return sorted(items, key=lambda x: (_clave(nombre(x)), ident(x)))
    if orden == "za":
        return sorted(items, key=lambda x: (_clave(nombre(x)), ident(x)), reverse=True)
    if orden == "antiguos":
        return sorted(items, key=lambda x: (fecha(x), ident(x)))
    return sorted(items, key=lambda x: (fecha(x), ident(x)), reverse=True)  # recientes


def _normalizar_letra(letra: str) -> str:
    """Unifica saltos de línea y tabulaciones: la alineación de los acordes depende de ello."""
    letra = letra.replace("\r\n", "\n").replace("\r", "\n")
    lineas = [l.expandtabs(4).rstrip() for l in letra.split("\n")]
    return "\n".join(lineas).strip("\n")


class ServicioBiblioteca:
    def __init__(self, con: sqlite3.Connection) -> None:
        self.con = con
        self.albumes = AlbumRepository(con)
        self.canciones = CancionRepository(con)

    def cerrar(self) -> None:
        self.con.close()

    # ------------------------------------------------------------------ álbumes
    def _validar_nombre_album(self, nombre: str, excluir_id: int | None = None) -> str:
        nombre = " ".join(nombre.split())
        if not nombre:
            raise ValidationError("El nombre del álbum no puede estar vacío.")
        if len(nombre) > MAX_NOMBRE_ALBUM:
            raise ValidationError(f"El nombre es demasiado largo (máximo {MAX_NOMBRE_ALBUM} caracteres).")
        clave = _clave(nombre)
        for a in self.albumes.listar():
            if a.id != excluir_id and _clave(a.nombre) == clave:
                raise ValidationError(f"Ya existe un álbum llamado «{a.nombre}».")
        return nombre

    def listar_albumes(self, orden: str = ORDEN_POR_DEFECTO) -> list[Album]:
        return _ordenar(self.albumes.listar(), orden, lambda a: a.nombre, lambda a: a.creado_en, lambda a: a.id)

    def obtener_album(self, album_id: int) -> Album:
        album = self.albumes.obtener(album_id)
        if album is None:
            raise NotFoundError("El álbum ya no existe.")
        return album

    def crear_album(self, nombre: str) -> Album:
        nombre = self._validar_nombre_album(nombre)
        try:
            nuevo_id = self.albumes.crear(nombre)
        except sqlite3.IntegrityError:
            raise ValidationError(f"Ya existe un álbum llamado «{nombre}».") from None
        return self.obtener_album(nuevo_id)

    def renombrar_album(self, album_id: int, nombre: str) -> Album:
        self.obtener_album(album_id)
        nombre = self._validar_nombre_album(nombre, excluir_id=album_id)
        try:
            self.albumes.renombrar(album_id, nombre)
        except sqlite3.IntegrityError:
            raise ValidationError(f"Ya existe un álbum llamado «{nombre}».") from None
        return self.obtener_album(album_id)

    def eliminar_album(self, album_id: int) -> int:
        """Borra el álbum y todas sus canciones. Devuelve cuántas canciones se borraron."""
        album = self.obtener_album(album_id)
        self.albumes.eliminar(album_id)
        return album.total_canciones

    # ---------------------------------------------------------------- canciones
    @staticmethod
    def _validar_titulo(titulo: str) -> str:
        titulo = " ".join(titulo.split())
        if not titulo:
            raise ValidationError("El título de la canción no puede estar vacío.")
        if len(titulo) > MAX_TITULO:
            raise ValidationError(f"El título es demasiado largo (máximo {MAX_TITULO} caracteres).")
        return titulo

    @staticmethod
    def _validar_letra(letra: str) -> str:
        letra = _normalizar_letra(letra)
        if len(letra) > MAX_LETRA:
            raise ValidationError("La letra es demasiado larga.")
        return letra

    def obtener_cancion(self, cancion_id: int) -> Cancion:
        cancion = self.canciones.obtener(cancion_id)
        if cancion is None:
            raise NotFoundError("La canción ya no existe.")
        return cancion

    def crear_cancion(self, album_id: int, titulo: str, letra: str) -> Cancion:
        self.obtener_album(album_id)
        titulo = self._validar_titulo(titulo)
        letra = self._validar_letra(letra)
        return self.obtener_cancion(self.canciones.crear(album_id, titulo, letra))

    def actualizar_cancion(self, cancion_id: int, titulo: str, letra: str) -> Cancion:
        self.obtener_cancion(cancion_id)
        titulo = self._validar_titulo(titulo)
        letra = self._validar_letra(letra)
        self.canciones.actualizar(cancion_id, titulo, letra)
        return self.obtener_cancion(cancion_id)

    def eliminar_cancion(self, cancion_id: int) -> None:
        self.obtener_cancion(cancion_id)
        self.canciones.eliminar(cancion_id)

    def guardar_transposicion(self, cancion_id: int, semitonos: int) -> int:
        """Guarda la última transposición de la canción (la letra original no cambia)."""
        self.obtener_cancion(cancion_id)
        semitonos = normalizar_semitonos(semitonos)
        self.canciones.actualizar_semitonos(cancion_id, semitonos)
        return semitonos

    # ------------------------------------------------- listado y búsqueda
    def buscar_canciones(
        self,
        consulta: str = "",
        album_id: int | None = None,
        orden: str = ORDEN_POR_DEFECTO,
    ) -> list[ResultadoCancion]:
        """Canciones cuyo título o letra (sin contar las líneas de acordes) contienen
        todas las palabras de ``consulta``. Con ``album_id`` busca solo en ese álbum."""
        terminos = _clave(consulta).split()
        resultados: list[ResultadoCancion] = []
        for c, album_nombre in self.canciones.listar_con_album(album_id):
            fragmento = ""
            if terminos:
                titulo_k = _clave(c.titulo)
                lineas = [
                    l for l in c.letra.split("\n") if clasificar_linea(l) in ("letra", "seccion")
                ]
                claves = [_clave(l) for l in lineas]
                pajar = titulo_k + "\n" + "\n".join(claves)
                if not all(t in pajar for t in terminos):
                    continue
                if not all(t in titulo_k for t in terminos):
                    for original, k in zip(lineas, claves):
                        if any(t in k for t in terminos):
                            fragmento = " ".join(original.split())
                            if len(fragmento) > 90:
                                fragmento = fragmento[:89].rstrip() + "…"
                            break
            resultados.append(ResultadoCancion(c, album_nombre, fragmento))
        return _ordenar(
            resultados, orden, lambda r: r.cancion.titulo, lambda r: r.cancion.creado_en, lambda r: r.cancion.id
        )

    def listar_canciones(self, album_id: int, consulta: str = "", orden: str = ORDEN_POR_DEFECTO):
        self.obtener_album(album_id)
        return self.buscar_canciones(consulta, album_id=album_id, orden=orden)
