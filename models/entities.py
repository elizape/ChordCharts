"""Entidades del dominio (sin lógica de base de datos ni de interfaz)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Album:
    id: int
    nombre: str
    creado_en: str
    total_canciones: int = 0


@dataclass(frozen=True)
class Cancion:
    id: int
    album_id: int
    titulo: str
    letra: str       # letra con los acordes escritos encima; siempre en la tonalidad ORIGINAL
    semitonos: int   # última transposición aplicada a la vista (se guarda)
    creado_en: str
    actualizado_en: str


@dataclass(frozen=True)
class ResultadoCancion:
    """Una canción con el nombre de su álbum y, si hubo búsqueda, un fragmento de letra."""

    cancion: Cancion
    album_nombre: str
    fragmento: str = ""
