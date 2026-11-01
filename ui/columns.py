"""Reparto de la letra en columnas (lógica pura, sin Tk, para poder testearla).

Una letra se divide en «unidades» que nunca se separan entre columnas:
  - una línea de acordes junto con el verso que tiene debajo,
  - un título de sección («[Coro]») junto con lo que viene después,
  - una línea suelta (verso sin acordes, línea en blanco).
Las columnas se llenan hacia abajo hasta ``max_lineas``; si la siguiente unidad
no entra, se abre una columna nueva.
"""
from __future__ import annotations

from services.chords import clasificar_linea

Linea = tuple[str, str]  # (tipo, texto) con tipo: 'acordes' | 'letra' | 'seccion' | 'vacia'
Unidad = list[Linea]


def construir_unidades(texto: str) -> list[Unidad]:
    lineas = [(clasificar_linea(l), l) for l in texto.split("\n")]
    unidades: list[Unidad] = []
    i = 0
    while i < len(lineas):
        tipo, _ = lineas[i]
        if tipo == "acordes" and i + 1 < len(lineas) and lineas[i + 1][0] == "letra":
            unidades.append([lineas[i], lineas[i + 1]])
            i += 2
        else:
            unidades.append([lineas[i]])
            i += 1

    # un título de sección se queda pegado a lo que le sigue
    fusionadas: list[Unidad] = []
    pendiente: Unidad | None = None
    for u in unidades:
        if pendiente is not None:
            if u[0][0] == "vacia":
                fusionadas.append(pendiente)
                pendiente = None
            else:
                u = pendiente + u
                pendiente = None
        if len(u) == 1 and u[0][0] == "seccion":
            pendiente = u
        else:
            fusionadas.append(u)
    if pendiente is not None:
        fusionadas.append(pendiente)
    return fusionadas


def repartir_en_columnas(unidades: list[Unidad], max_lineas: int) -> list[list[Linea]]:
    """Reparte las unidades en columnas de como mucho ``max_lineas`` líneas
    (una unidad más alta que eso ocupa igualmente una columna propia)."""
    max_lineas = max(1, max_lineas)
    columnas: list[list[Linea]] = [[]]
    for u in unidades:
        actual = columnas[-1]
        es_blanco = all(t == "vacia" for t, _ in u)
        if es_blanco and not actual:
            continue  # sin líneas en blanco al comienzo de una columna
        if actual and len(actual) + len(u) > max_lineas:
            if es_blanco:
                continue  # el espacio en blanco no merece abrir una columna
            columnas.append([])
            actual = columnas[-1]
        actual.extend(u)
    for col in columnas:
        while col and col[-1][0] == "vacia":
            col.pop()
    return [c for c in columnas if c]
