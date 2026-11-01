"""Detección y transposición de acordes escritos sobre la letra.

Los acordes se escriben en el mismo texto de la canción, en una línea propia
encima del verso (como en cualquier cifrado):

    Am        F
    Camino por la orilla

Una línea se considera "de acordes" cuando TODAS sus palabras son acordes
(notación inglesa: Am, F#m7, D/F#, Bb... o latina: Lam, Re7, Sol, Do/Mi...) o
separadores habituales (| / - x2 N.C.). Opcionalmente puede empezar con una
etiqueta, por ejemplo ``Intro: Am F C G`` o ``[Coro] Am F``.

Al transponer se conservan las columnas de cada acorde, para que sigan
alineados con la sílaba donde cambian.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# --------------------------------------------------------------------------
# Gramática
# --------------------------------------------------------------------------
_RAIZ_EN = r"[A-G][#b]?"
_RAIZ_LAT = r"(?:Do|Re|Mi|Fa|Sol|La|Si)[#b]?"
_SUFIJO = r"(?:maj|min|dim|aug|sus|add|alt|m|M|\+|-|°|º|ø|[#b]|\d|\(|\))*"

_ACORDE_EN = re.compile(rf"^(?P<raiz>{_RAIZ_EN})(?P<sufijo>{_SUFIJO})(?:/(?P<bajo>{_RAIZ_EN}))?$")
_ACORDE_LAT = re.compile(rf"^(?P<raiz>{_RAIZ_LAT})(?P<sufijo>{_SUFIJO})(?:/(?P<bajo>{_RAIZ_LAT}))?$")

# Separadores que pueden convivir con acordes: | || / - . N.C. x2 (x2) 2x
_SEPARADOR = re.compile(r"^(?:[|/\\.\-–—:;,~*]+|N\.?C\.?|\(?[xX]\d+\)?|\d+[xX])$")

_PALABRA_ETIQUETA = r"[^\W\d_][^\W_]*"
_ETIQUETA = (
    rf"(?:\[[^\]\n]{{1,30}}\]|{_PALABRA_ETIQUETA}(?: [^\W_]+){{0,2}}\s*:)"
)
_RE_ETIQUETA_INICIAL = re.compile(rf"^\s*{_ETIQUETA}\s*")
_RE_SECCION = re.compile(rf"^\s*{_ETIQUETA}\s*$")


@dataclass(frozen=True)
class _Token:
    inicio: int       # columna donde empieza dentro de la línea
    prefijo: str      # paréntesis de apertura pegados al acorde
    nucleo: str       # el acorde (o separador) propiamente dicho
    sufijo: str       # paréntesis de cierre pegados al acorde
    es_acorde: bool


@dataclass(frozen=True)
class _LineaAcordes:
    etiqueta: str                 # texto inicial que no se toca ("Intro: ")
    tokens: tuple[_Token, ...]


def _coincidencia(nucleo: str):
    """Devuelve (match, es_latino) o (None, False)."""
    m = _ACORDE_EN.match(nucleo)
    if m:
        return m, False
    m = _ACORDE_LAT.match(nucleo)
    if m:
        return m, True
    return None, False


def _envoltura(crudo: str) -> tuple[str, str, str]:
    m = re.match(r"^(\(*)(.*?)(\)*)$", crudo)
    return m.group(1), m.group(2), m.group(3)


def _analizar(linea: str) -> _LineaAcordes | None:
    if not linea.strip():
        return None
    m_etiqueta = _RE_ETIQUETA_INICIAL.match(linea)
    inicio = m_etiqueta.end() if m_etiqueta else 0
    resto = linea[inicio:]

    tokens: list[_Token] = []
    for t in re.finditer(r"\S+", resto):
        crudo = t.group()
        pre, nucleo, suf = _envoltura(crudo)
        m, _ = _coincidencia(nucleo) if nucleo else (None, False)
        if m:
            tokens.append(_Token(inicio + t.start(), pre, nucleo, suf, True))
        elif _SEPARADOR.match(crudo):
            tokens.append(_Token(inicio + t.start(), "", crudo, "", False))
        else:
            return None  # hay una palabra que no es un acorde: es letra

    acordes = [t for t in tokens if t.es_acorde]
    if not acordes:
        return None

    # "Si", "La", "Sol", "Mi"... sueltos son palabras muy comunes en una letra.
    # Una línea con un único acorde latino "pelado" no se toma como línea de acordes.
    if len(tokens) == 1:
        m, latino = _coincidencia(acordes[0].nucleo)
        decorado = bool(m["sufijo"] or m["bajo"] or m["raiz"][-1] in "#b")
        if latino and not decorado:
            return None

    return _LineaAcordes(linea[:inicio], tuple(tokens))


# --------------------------------------------------------------------------
# Clasificación de líneas (la usan la vista de lectura y el editor)
# --------------------------------------------------------------------------
def es_linea_de_acordes(linea: str) -> bool:
    return _analizar(linea) is not None


def clasificar_linea(linea: str) -> str:
    """'vacia' | 'acordes' | 'seccion' (ej. «[Coro]», «Estribillo:») | 'letra'."""
    if not linea.strip():
        return "vacia"
    if _analizar(linea) is not None:
        return "acordes"
    if _RE_SECCION.match(linea):
        return "seccion"
    return "letra"


# --------------------------------------------------------------------------
# Transposición
# --------------------------------------------------------------------------
_BASE_EN = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_BASE_LAT = {"Do": 0, "Re": 2, "Mi": 4, "Fa": 5, "Sol": 7, "La": 9, "Si": 11}

# Cómo se escribe cada una de las 12 notas según la preferencia de la canción.
_NOMBRES = {
    (False, "sost"): ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"],
    (False, "bem"): ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"],
    (False, "mixto"): ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"],
    (True, "sost"): ["Do", "Do#", "Re", "Re#", "Mi", "Fa", "Fa#", "Sol", "Sol#", "La", "La#", "Si"],
    (True, "bem"): ["Do", "Reb", "Re", "Mib", "Mi", "Fa", "Solb", "Sol", "Lab", "La", "Sib", "Si"],
    (True, "mixto"): ["Do", "Do#", "Re", "Mib", "Mi", "Fa", "Fa#", "Sol", "Lab", "La", "Sib", "Si"],
}


def _indice_nota(raiz: str, latino: bool) -> int:
    alteracion = raiz[-1] if raiz[-1] in "#b" else ""
    nombre = raiz[:-1] if alteracion else raiz
    base = (_BASE_LAT if latino else _BASE_EN)[nombre]
    return (base + (1 if alteracion == "#" else -1 if alteracion == "b" else 0)) % 12


def _transponer_acorde(nucleo: str, n: int, pref: str) -> str:
    m, latino = _coincidencia(nucleo)
    if not m:
        return nucleo
    nombres = _NOMBRES[(latino, pref)]
    resultado = nombres[(_indice_nota(m["raiz"], latino) + n) % 12] + m["sufijo"]
    if m["bajo"]:
        resultado += "/" + nombres[(_indice_nota(m["bajo"], latino) + n) % 12]
    return resultado


def _preferencia(lineas: list[_LineaAcordes]) -> str:
    """Decide si la canción escribe sus alteraciones con sostenidos o bemoles."""
    sost = bem = 0
    for linea in lineas:
        for t in linea.tokens:
            if not t.es_acorde:
                continue
            m, _ = _coincidencia(t.nucleo)
            for raiz in (m["raiz"], m["bajo"]):
                if raiz and raiz[-1] == "#":
                    sost += 1
                elif raiz and raiz[-1] == "b":
                    bem += 1
    if sost > bem:
        return "sost"
    if bem > sost:
        return "bem"
    return "sost" if sost else "mixto"


def _reconstruir(linea: _LineaAcordes, n: int, pref: str) -> str:
    """Reescribe la línea conservando la columna de inicio de cada acorde."""
    salida = linea.etiqueta
    for t in linea.tokens:
        texto = t.nucleo if not t.es_acorde else _transponer_acorde(t.nucleo, n, pref)
        texto = t.prefijo + texto + t.sufijo
        if len(salida) < t.inicio:
            salida += " " * (t.inicio - len(salida))
        elif salida and not salida.endswith(" "):
            salida += " "  # el acorde se alargó: separarlo del anterior
        salida += texto
    return salida


def normalizar_semitonos(n: int) -> int:
    """Lleva cualquier cantidad de semitonos al rango -5..+6 (12 = volver al original)."""
    return ((int(n) + 5) % 12) - 5


def formatear_semitonos(n: int) -> str:
    return "0" if n == 0 else f"{n:+d}"


def transponer_texto(texto: str, semitonos: int) -> str:
    """Transpone todos los acordes de ``texto``; la letra no se modifica."""
    n = int(semitonos) % 12
    if n == 0 or not texto:
        return texto
    lineas = texto.split("\n")
    analizadas = [_analizar(l) for l in lineas]
    pref = _preferencia([a for a in analizadas if a])
    return "\n".join(
        _reconstruir(a, n, pref) if a else original for original, a in zip(lineas, analizadas)
    )
