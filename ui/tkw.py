"""Widgets `tk.*` que conservan los colores que se les asignan.

ttkbootstrap 1.x re-aplica el color del tema a todo widget `tk.*` al construirlo (y pisa
los `bg`/`fg` pasados). Aceptan ``autostyle=False`` para evitarlo; ttkbootstrap 2.x no lo
necesita ni lo acepta. Esto detecta cuál es el caso y se comporta igual en las dos versiones.
"""
from __future__ import annotations

import tkinter as tk

_soporta: bool | None = None


def _autostyle_soportado() -> bool:
    global _soporta
    if _soporta is None:
        raiz = getattr(tk, "_default_root", None)
        if raiz is None:
            return False  # todavía no se puede probar; se reintenta en el próximo widget
        try:
            tk.Frame(raiz, autostyle=False).destroy()
            _soporta = True
        except (tk.TclError, TypeError):
            _soporta = False
    return _soporta


def _sin_tema(base: type) -> type:
    class Widget(base):  # type: ignore[misc, valid-type]
        def __init__(self, *args, **kwargs) -> None:
            if _autostyle_soportado():
                kwargs["autostyle"] = False
            super().__init__(*args, **kwargs)

    Widget.__name__ = Widget.__qualname__ = base.__name__
    return Widget


Frame = _sin_tema(tk.Frame)
Label = _sin_tema(tk.Label)
Canvas = _sin_tema(tk.Canvas)
Text = _sin_tema(tk.Text)
Toplevel = _sin_tema(tk.Toplevel)
