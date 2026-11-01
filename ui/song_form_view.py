"""Formulario de canción (añadir / editar): título y letra con los acordes escritos encima."""
from __future__ import annotations

import tkinter as tk
from typing import Callable

import ttkbootstrap as ttk

from ui import tkw as W

from services.chords import clasificar_linea, formatear_semitonos
from services.library_service import ValidationError
from ui.components import Debounce, confirmar


class VistaFormulario(ttk.Frame):
    def __init__(self, parent, app, album, cancion, volver: Callable[[], None]) -> None:
        super().__init__(parent)
        self.app, self.album, self.cancion, self.volver = app, album, cancion, volver
        pal, f = app.pal, app.fuentes
        self._titulo_inicial = cancion.titulo if cancion else ""
        self._letra_inicial = cancion.letra if cancion else ""

        # ------------------------------------------------------- cabecera
        cab = ttk.Frame(self, padding=(32, 24, 32, 6))
        cab.pack(fill="x")
        ttk.Button(cab, text="←  Cancelar", bootstyle="secondary-outline", command=self.cancelar).pack(side="left")
        bloque = ttk.Frame(cab)
        bloque.pack(side="left", padx=(20, 0))
        ttk.Label(bloque, text="Editar canción" if cancion else "Nueva canción", font=f.ui(22, "bold")).pack(anchor="w")
        ttk.Label(bloque, text=f"Álbum: {album.nombre}", foreground=pal.muted, font=f.ui(11)).pack(anchor="w", pady=(2, 0))

        # ----------------------------------------------------------- cuerpo
        cuerpo = ttk.Frame(self, padding=(32, 14, 32, 22))
        cuerpo.pack(fill="both", expand=True)
        cuerpo.rowconfigure(5, weight=1)
        cuerpo.columnconfigure(0, weight=1)

        ttk.Label(cuerpo, text="Título", font=f.ui(11, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.var_titulo = tk.StringVar(value=self._titulo_inicial)
        self.entry = ttk.Entry(cuerpo, textvariable=self.var_titulo, font=f.ui(14))
        self.entry.grid(row=1, column=0, sticky="ew", ipady=6)
        self.error = ttk.Label(cuerpo, text="", foreground=pal.danger, font=f.ui(10))
        self.error.grid(row=2, column=0, sticky="w", pady=(4, 0))

        ttk.Label(cuerpo, text="Letra y acordes", font=f.ui(11, "bold")).grid(row=3, column=0, sticky="w", pady=(10, 2))
        ayuda = ("Escribí los acordes en una línea encima del verso, alineados con la sílaba donde cambian "
                 "(por ejemplo «Am    F» y debajo la letra). Se resaltan solos.")
        if cancion and cancion.semitonos:
            ayuda += (f"  Estás editando la letra en su tono original; la lectura está transpuesta "
                      f"{formatear_semitonos(cancion.semitonos)}.")
        ttk.Label(cuerpo, text=ayuda, foreground=pal.muted, font=f.ui(10), wraplength=900, justify="left").grid(
            row=4, column=0, sticky="w", pady=(0, 8))

        marco = W.Frame(cuerpo, bg=pal.borde, padx=1, pady=1)
        marco.grid(row=5, column=0, sticky="nsew")
        marco.rowconfigure(0, weight=1)
        marco.columnconfigure(0, weight=1)
        self.texto = W.Text(
            marco, wrap="none", undo=True, maxundo=200, font=f.mono(12), bg=pal.input_bg, fg=pal.fg,
            insertbackground=pal.fg, selectbackground=pal.primary, selectforeground="#ffffff",
            relief="flat", bd=0, padx=16, pady=12, spacing1=1, spacing3=1, highlightthickness=0,
        )
        self.texto.grid(row=0, column=0, sticky="nsew")
        vsb = ttk.Scrollbar(marco, orient="vertical", command=self.texto.yview)
        hsb = ttk.Scrollbar(marco, orient="horizontal", command=self.texto.xview)
        self.texto.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        self.texto.tag_configure("acorde", foreground=pal.acorde, font=f.mono(12, "bold"))
        self.texto.tag_configure("seccion", foreground=pal.warning, font=f.mono(12, "bold"))
        self.texto.insert("1.0", self._letra_inicial)
        self.texto.edit_reset()
        self.texto.edit_modified(False)

        self._resaltar_diferido = Debounce(self, 90, self._resaltar)
        self.texto.bind("<<Modified>>", self._modificado)
        self.texto.bind("<Tab>", lambda e: (self.texto.insert("insert", "    "), "break")[1])
        self._resaltar()

        botones = ttk.Frame(cuerpo)
        botones.grid(row=6, column=0, sticky="e", pady=(16, 0))
        ttk.Button(botones, text="Cancelar", bootstyle="secondary", command=self.cancelar).pack(side="left", padx=(0, 10))
        ttk.Button(botones, text="Guardar", bootstyle="primary", command=self.guardar).pack(side="left")

        self.var_titulo.trace_add("write", lambda *a: self.error.configure(text=""))
        self.entry.bind("<Return>", lambda e: (self.texto.focus_set(), "break")[1])
        for w in (self.entry, self.texto):
            w.bind("<Control-s>", lambda e: (self.guardar(), "break")[1])
        self.after(80, lambda: (self.entry if not cancion else self.texto).focus_set())

    # ------------------------------------------------------------ resaltado
    def _modificado(self, _e=None) -> None:
        if self.texto.edit_modified():
            self.texto.edit_modified(False)
            self._resaltar_diferido()

    def _resaltar(self) -> None:
        t = self.texto
        for tag in ("acorde", "seccion"):
            t.tag_remove(tag, "1.0", "end")
        total = int(t.index("end-1c").split(".")[0])
        for i in range(1, total + 1):
            tipo = clasificar_linea(t.get(f"{i}.0", f"{i}.end"))
            if tipo == "acordes":
                t.tag_add("acorde", f"{i}.0", f"{i}.end")
            elif tipo == "seccion":
                t.tag_add("seccion", f"{i}.0", f"{i}.end")

    # --------------------------------------------------------------- acciones
    def _contenido(self) -> tuple[str, str]:
        return self.var_titulo.get(), self.texto.get("1.0", "end-1c")

    def hay_cambios(self) -> bool:
        titulo, letra = self._contenido()
        return titulo.strip() != self._titulo_inicial.strip() or letra.rstrip() != self._letra_inicial.rstrip()

    def confirmar_salida(self) -> bool:
        if not self.hay_cambios():
            return True
        return confirmar(self, self.app.pal, self.app.fuentes, "Descartar cambios",
                         "Hay cambios sin guardar. Si salís ahora se van a perder.", "Descartar")

    def cancelar(self) -> None:
        if self.confirmar_salida():
            self.volver()

    def guardar(self) -> None:
        titulo, letra = self._contenido()
        s = self.app.servicio
        try:
            if self.cancion:
                s.actualizar_cancion(self.cancion.id, titulo, letra)
            else:
                s.crear_cancion(self.album.id, titulo, letra)
        except ValidationError as error:
            self.error.configure(text=str(error))
            self.entry.focus_set()
            return
        self.app.toast.mostrar("Cambios guardados" if self.cancion else "Canción añadida")
        self.volver()
