"""Paleta y tipografías derivadas del tema de ttkbootstrap (Cyborg)."""
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
    return Paleta(
        bg=bg,
        fg=fg,
        muted=mezclar(fg, bg, 0.48),
        tenue=mezclar(fg, bg, 0.08),
        card=mezclar(bg, fg, 0.075),
        card_hover=mezclar(bg, fg, 0.125),
        borde=mezclar(bg, fg, 0.16),
        input_bg=colors.inputbg,
        primary=colors.primary,
        danger=colors.danger,
        success=colors.success,
        warning=colors.warning,
        acorde=mezclar(colors.primary, "#ffffff", 0.22),
        acentos=[colors.primary, colors.info, colors.success, colors.warning, "#e5446d", "#14b8a6"],
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
