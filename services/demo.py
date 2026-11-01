"""Datos de ejemplo (opcionales): `python main.py --demo`. Letras originales de demostración."""
from __future__ import annotations

from services.library_service import ServicioBiblioteca


def _v(*segmentos: tuple[str, str]) -> str:
    """Arma un verso con los acordes alineados sobre la sílaba donde cambian."""
    acordes = letra = ""
    for acorde, texto in segmentos:
        ancho = max(len(texto), len(acorde) + 1)
        acordes += acorde.ljust(ancho)
        letra += texto.ljust(ancho)
    return acordes.rstrip() + "\n" + letra.rstrip()


def _bloque(*partes: str) -> str:
    return "\n".join(partes)


LUCIERNAGAS = "\n\n".join(
    [
        "[Intro]\nG   D   Em   C",
        "[Verso 1]\n"
        + _bloque(
            _v(("G", "Cuando cae la tarde "), ("D", "sobre el campo")),
            _v(("Em", "se prenden las luces "), ("C", "de la noche")),
            _v(("G", "Las luciérnagas "), ("D", "dibujan mapas")),
            _v(("Em", "de caminos que "), ("C", "nadie recorre")),
        ),
        "[Estribillo]\n"
        + _bloque(
            _v(("C", "Vuela, vuela, "), ("G", "pequeña luz")),
            _v(("Am", "que la noche es "), ("D7", "larga y tengo sed de cielo")),
            _v(("C", "Vuela, vuela, "), ("G", "pequeña luz")),
            _v(("Am", "y enséñame el "), ("D7", "camino de "), ("G", "regreso")),
        ),
        "[Verso 2]\n"
        + _bloque(
            _v(("G", "En la mesa quedan "), ("D", "los mates fríos")),
            _v(("Em", "y un guitarrero "), ("C", "afina su silencio")),
            _v(("G", "Las historias "), ("D", "viejas se despiertan")),
            _v(("Em", "con el humo que "), ("C", "se va hacia el cielo")),
        ),
        "[Estribillo]\n"
        + _bloque(
            _v(("C", "Vuela, vuela, "), ("G", "pequeña luz")),
            _v(("Am", "que la noche es "), ("D7", "larga y tengo sed de cielo")),
            _v(("C", "Vuela, vuela, "), ("G", "pequeña luz")),
            _v(("Am", "y enséñame el "), ("D7", "camino de "), ("G", "regreso")),
        ),
        "[Puente]\n"
        + _bloque(
            _v(("Em", "Y si el viento "), ("D", "cambia de rumbo")),
            _v(("C", "yo me quedo acá, "), ("G", "bajo este techo")),
            _v(("Am", "de estrellas, sin "), ("D7", "apuro, sin reloj")),
        ),
        "[Verso 3]\n"
        + _bloque(
            _v(("G", "Cuando el alba "), ("D", "pinte de naranja")),
            _v(("Em", "las ramas del sauce "), ("C", "junto al río")),
            _v(("G", "Guardaré en el "), ("D", "bolsillo una chispa")),
            _v(("Em", "para cuando "), ("C", "vuelva a hacerse "), ("G", "tarde")),
        ),
    ]
)

MAREA_BAJA = "\n\n".join(
    [
        "[Intro]\nAm   F   C   G",
        "[Verso]\n"
        + _bloque(
            _v(("Am", "Camino por la orilla "), ("F", "de la tarde")),
            _v(("C", "con los zapatos "), ("G", "llenos de arena")),
            _v(("Am", "y el mar se va "), ("F", "quedando sin su nombre")),
            _v(("C", "mientras la luz "), ("G", "se apaga en la ladera")),
        ),
        "[Estribillo]\n"
        + _bloque(
            _v(("F", "Marea baja, "), ("C", "marea baja")),
            _v(("G", "llévate lo que "), ("Am", "ya no me hace falta")),
            _v(("F", "Marea baja, "), ("C", "marea baja")),
            _v(("G", "y déjame la "), ("Am", "calma en la garganta")),
        ),
    ]
)

FARO = "\n\n".join(
    [
        "Intro: Dm  Bb  F  C/E",
        "[Verso]\n"
        + _bloque(
            _v(("Dm", "Un faro viejo "), ("Bb", "vigila el puerto")),
            _v(("F", "y cuenta barcos "), ("C/E", "que no regresan")),
            _v(("Dm", "yo le prometo "), ("Gm", "que vuelvo pronto")),
            _v(("A7", "pero la sal me "), ("Dm", "borra las señas")),
        ),
        "[Coro]\n"
        + _bloque(
            _v(("Bb", "Ilumina, "), ("F", "ilumina")),
            _v(("C", "aunque no haya "), ("Dm", "nadie mirando")),
        ),
    ]
)

SOMBRA_DE_SAUCE = "\n\n".join(
    [
        "[Intro]  Lam   Fa   Do   Sol",
        "[Estrofa]\n"
        + _bloque(
            _v(("Lam", "Bajo la sombra "), ("Fa", "del sauce viejo")),
            _v(("Do", "se duerme el día "), ("Sol", "sin hacer ruido")),
            _v(("Lam", "el río cuenta "), ("Fa", "sus mismas historias")),
            _v(("Sol7", "y yo las escucho "), ("Do", "como si fueran nuevas")),
        ),
    ]
)

ENSAYO = "\n\n".join(
    [
        "[Base]\nE   A   B   E",
        _v(("E", "Canción de prueba "), ("A", "para el ensayo")),
    ]
)


def cargar_demo(servicio: ServicioBiblioteca) -> bool:
    """Carga álbumes y canciones de ejemplo si la base está vacía. Devuelve True si cargó."""
    if servicio.listar_albumes():
        return False
    fogon = servicio.crear_album("Fogón de verano")
    costa = servicio.crear_album("Costa")
    servicio.crear_album("Ideas sueltas")  # álbum vacío, para ver el estado vacío
    ensayos = servicio.crear_album("Ensayos")

    servicio.crear_cancion(fogon.id, "Luciérnagas", LUCIERNAGAS)
    servicio.crear_cancion(fogon.id, "Sombra de sauce", SOMBRA_DE_SAUCE)
    servicio.crear_cancion(costa.id, "Marea baja", MAREA_BAJA)
    servicio.crear_cancion(costa.id, "Faro", FARO)
    servicio.crear_cancion(ensayos.id, "Prueba de sonido", ENSAYO)
    return True
