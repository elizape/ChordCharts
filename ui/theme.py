"""Paleta y tipografías derivadas del tema de ttkbootstrap con soporte para temas oscuros, claros y grises."""
from __future__ import annotations

import tkinter.font as tkfont
from dataclasses import dataclass


def _rgb(color: str) -> tuple[int, int, int]:
    c = color.lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def mezclar(a: str, b: str, t: float) -> str:
    """Mezcla dos colores #rrggbb; t=0 devuelve a, t=1 devuelve b."""
    ra, rb = _rgb(a), _rgb(b)
    return "#%02x%02x%02x" % tuple(round(ra[i] * (1 - t) + rb[i] * t) for i in range(3))


def es_color_claro(hex_color: str) -> bool:
    """Determina si un color es percibido como claro mediante fórmula de luminosidad estándar."""
    try:
        r, g, b = _rgb(hex_color)
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        return lum > 140
    except Exception:
        return False


TEMAS_DEFINIDOS = {
    "oscuro": {
        "id": "oscuro",
        "nombre": "Oscuro profundo",
        "descripcion": "Fondo negro suave y alto contraste. Ideal para escenarios y ambientes con poca luz.",
        "ttk_candidatos": ["catppuccin-dark", "darkly", "cyborg"],
        "icono": "🌙",
        "muestra": ("#0f172a", "#1e293b", "#38bdf8"),
    },
    "claro": {
        "id": "claro",
        "nombre": "Claro luminoso",
        "descripcion": "Fondo blanco puro y lectura nítida. Ideal para uso diurno o ensayos bien iluminados.",
        "ttk_candidatos": ["catppuccin-light", "flatly", "cosmo", "bootstrap-light"],
        "icono": "☀️",
        "muestra": ("#f8fafc", "#ffffff", "#0284c7"),
    },
    "grises": {
        "id": "grises",
        "nombre": "Grises (Slate)",
        "descripcion": "Gris grafito intermedio descansado para la vista, sin brillos excesivos ni oscuridad total.",
        "ttk_candidatos": ["nord-dark", "one-dark", "superhero"],
        "icono": "🌫️",
        "muestra": ("#242933", "#2e3440", "#88c0d0"),
    },
    "acustico": {
        "id": "acustico",
        "nombre": "Cálido (Acústico)",
        "descripcion": "Inspirado en instrumentos acústicos, tonos madera cálidos y pergamino vintage.",
        "ttk_candidatos": ["gruvbox-dark", "sandstone-dark", "solarized-dark", "solar"],
        "icono": "🪵",
        "muestra": ("#282828", "#3c3836", "#fabd2f"),
    },
}


def resolver_ttk_theme(tema_id: str, temas_disponibles: list[str] | None = None) -> str:
    """Encuentra el nombre exacto de tema de ttkbootstrap soportado por el entorno."""
    info = TEMAS_DEFINIDOS.get(tema_id, TEMAS_DEFINIDOS["oscuro"])
    candidatos = info["ttk_candidatos"]
    if temas_disponibles:
        for c in candidatos:
            if c in temas_disponibles:
                return c
    return candidatos[0]


@dataclass
class Paleta:
    bg: str
    fg: str
    muted: str        # texto secundario
    tenue: str        # texto de letra en la vista de lectura
    card: str
    card_hover: str
    borde: str
    input_bg: str
    primary: str
    danger: str
    success: str
    warning: str
    acorde: str       # color de los acordes
    acentos: list[str]  # para los monogramas de los álbumes


def construir_paleta(colors) -> Paleta:
    bg, fg = colors.bg, colors.fg
    es_claro = es_color_claro(bg)

    if es_claro:
        muted = mezclar(fg, bg, 0.42)
        tenue = mezclar(fg, bg, 0.12)
        card = mezclar(bg, "#ffffff", 0.75) if bg != "#ffffff" else "#ffffff"
        card_hover = mezclar(card, fg, 0.05)
        borde = mezclar(bg, fg, 0.16)
        acorde = mezclar(colors.primary, "#000000", 0.35)
        acentos = [colors.primary, colors.info, colors.success, "#d97706", "#db2777", "#0d9488"]
    else:
        muted = mezclar(fg, bg, 0.45)
        tenue = mezclar(fg, bg, 0.08)
        card = mezclar(bg, fg, 0.085)
        card_hover = mezclar(bg, fg, 0.14)
        borde = mezclar(bg, fg, 0.18)
        acorde = mezclar(colors.primary, "#ffffff", 0.30)
        acentos = [colors.primary, colors.info, colors.success, colors.warning, "#f43f5e", "#14b8a6"]

    return Paleta(
        bg=bg,
        fg=fg,
        muted=muted,
        tenue=tenue,
        card=card,
        card_hover=card_hover,
        borde=borde,
        input_bg=colors.inputbg,
        primary=colors.primary,
        danger=colors.danger,
        success=colors.success,
        warning=colors.warning,
        acorde=acorde,
        acentos=acentos,
    )



_UI = ["Inter", "Segoe UI", "SF Pro Text", "Noto Sans", "Ubuntu", "Cantarell", "DejaVu Sans", "Helvetica", "Arial"]
_MONO = [
    "JetBrains Mono", "Fira Code", "Cascadia Mono", "Consolas", "Menlo", "DejaVu Sans Mono",
    "Liberation Mono", "Ubuntu Mono", "Noto Sans Mono", "Courier New", "Courier",
]


class Fuentes:
    """Elige tipografías disponibles en el sistema y las aplica como fuentes por defecto."""

    def __init__(self, root) -> None:
        disponibles = set(tkfont.families(root))
        self.familia_ui = next((f for f in _UI if f in disponibles), tkfont.nametofont("TkDefaultFont").actual("family"))
        self.familia_mono = self._elegir_mono(root, disponibles)

        for nombre in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont", "TkCaptionFont", "TkTooltipFont"):
            try:
                tkfont.nametofont(nombre).configure(family=self.familia_ui, size=11)
            except Exception:
                pass
        try:
            tkfont.nametofont("TkFixedFont").configure(family=self.familia_mono, size=11)
        except Exception:
            pass

    @staticmethod
    def _elegir_mono(root, disponibles) -> str:
        for nombre in _MONO:
            if nombre in disponibles:
                try:
                    if tkfont.Font(root=root, family=nombre, size=12).metrics("fixed"):
                        return nombre
                except Exception:
                    continue
        return tkfont.nametofont("TkFixedFont").actual("family")

    def ui(self, tam: int = 11, peso: str = "normal") -> tuple:
        return (self.familia_ui, tam, peso)

    def mono(self, tam: int = 12, peso: str = "normal") -> tuple:
        return (self.familia_mono, tam, peso)
