"""Pantalla de lectura: título y letra con acordes, en columnas dinámicas y centradas."""
from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from typing import Callable

import ttkbootstrap as ttk

from ui import tkw as W

from services.chords import formatear_semitonos, normalizar_semitonos, transponer_texto
from ui.columns import construir_unidades, repartir_en_columnas
from ui.components import Debounce

TAM_MAX, TAM_MIN = 17, 9
MARGEN_V, MARGEN_H, ESPACIO_COLUMNAS = 30, 44, 72


class VistaCancion(ttk.Frame):
    def __init__(self, parent, app, cancion_id: int, volver: Callable[[], None]) -> None:
        super().__init__(parent)
        self.app, self.volver = app, volver
        self.cancion = app.servicio.obtener_cancion(cancion_id)
        self.album = app.servicio.obtener_album(self.cancion.album_id)
        self.semitonos = self.cancion.semitonos
        pal, f = app.pal, app.fuentes
        self._fuentes: dict[tuple[int, bool], tkfont.Font] = {}
        self._texto_cache: tuple[int, list] | None = None

        # ---------------------------------------------------------- cabecera
        cab = ttk.Frame(self, padding=(32, 24, 32, 6))
        cab.pack(fill="x")
        cab.columnconfigure(0, weight=1, uniform="lateral")
        cab.columnconfigure(2, weight=1, uniform="lateral")
        ttk.Button(cab, text="←  Volver", bootstyle="secondary-outline", command=self._volver).grid(row=0, column=0, sticky="w")
        centro = ttk.Frame(cab)
        centro.grid(row=0, column=1)
        ttk.Label(centro, text=self.cancion.titulo, font=f.ui(22, "bold"), anchor="center", justify="center",
                  wraplength=640).pack()
        ttk.Label(centro, text=self.album.nombre, foreground=pal.muted, font=f.ui(11)).pack(pady=(2, 0))
        ttk.Button(cab, text="Editar", bootstyle="primary", command=self.editar).grid(row=0, column=2, sticky="e")

        tono = ttk.Frame(self, padding=(0, 10, 0, 14))
        tono.pack()
        ttk.Label(tono, text="Tono", foreground=pal.muted, font=f.ui(11)).pack(side="left", padx=(0, 10))
        ttk.Button(tono, text="−", width=3, bootstyle="secondary", command=lambda: self._cambiar(-1)).pack(side="left")
        self.lbl_tono = ttk.Label(tono, text="", width=5, anchor="center", font=f.ui(14, "bold"), foreground=pal.acorde)
        self.lbl_tono.pack(side="left", padx=6)
        ttk.Button(tono, text="+", width=3, bootstyle="secondary", command=lambda: self._cambiar(1)).pack(side="left")
        self.btn_original = ttk.Button(tono, text="Original", bootstyle="secondary-outline", command=lambda: self._fijar(0))
        self.btn_original.pack(side="left", padx=(14, 0))

        ttk.Separator(self).pack(fill="x")

        # ---------------------------------------------------------- lectura
        zona = W.Frame(self, bg=pal.bg)
        zona.pack(fill="both", expand=True)
        self.canvas = W.Canvas(zona, bg=pal.bg, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self.hsb = ttk.Scrollbar(zona, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(xscrollcommand=self.hsb.set)
        self._hsb_visible = False
        self._redibujar_diferido = Debounce(self, 30, self.redibujar)
        self.canvas.bind("<Configure>", lambda e: self._redibujar_diferido())

        raiz = self.winfo_toplevel()
        self._tecla = raiz.bind("<Escape>", lambda e: self._volver(), add="+")
        self.bind("<Destroy>", self._al_destruir, add="+")
        self._actualizar_tono()

    def _al_destruir(self, e) -> None:
        if e.widget is self:
            try:
                self.winfo_toplevel().unbind("<Escape>", self._tecla)
            except tk.TclError:
                pass

    # --------------------------------------------------------------- tono
    def _actualizar_tono(self) -> None:
        self.lbl_tono.configure(text=formatear_semitonos(self.semitonos))
        self.btn_original.configure(state="normal" if self.semitonos else "disabled")

    def _cambiar(self, delta: int) -> None:
        self._fijar(self.semitonos + delta)

    def _fijar(self, n: int) -> None:
        self.semitonos = self.app.servicio.guardar_transposicion(self.cancion.id, n)  # se guarda siempre
        self._actualizar_tono()
        self.redibujar()

    # ---------------------------------------------------------- navegación
    def _volver(self) -> None:
        self.volver()

    def editar(self) -> None:
        app, c = self.app, self.cancion
        app.mostrar_formulario(c.album_id, c.id, lambda: app.mostrar_cancion(c.id, self.volver))

    # ------------------------------------------------------------- dibujo
    def _fuente(self, tam: int, negrita: bool) -> tkfont.Font:
        clave = (tam, negrita)
        if clave not in self._fuentes:
            self._fuentes[clave] = tkfont.Font(
                root=self, family=self.app.fuentes.familia_mono, size=tam, weight="bold" if negrita else "normal")
        return self._fuentes[clave]

    def _unidades(self) -> list:
        if self._texto_cache is None or self._texto_cache[0] != self.semitonos:
            texto = transponer_texto(self.cancion.letra, self.semitonos)
            self._texto_cache = (self.semitonos, construir_unidades(texto))
        return self._texto_cache[1]

    def redibujar(self) -> None:
        c = self.canvas
        ancho, alto = c.winfo_width(), c.winfo_height()
        if ancho < 80 or alto < 80:
            return
        c.delete("all")
        pal = self.app.pal
        unidades = self._unidades()
        if not any(t != "vacia" for u in unidades for t, _ in u):
            c.create_text(ancho / 2, alto / 2, text="Esta canción todavía no tiene letra.\nUsá «Editar» para añadirla.",
                          fill=pal.muted, font=self.app.fuentes.ui(13), justify="center")
            self._mostrar_hsb(False, ancho, alto, ancho)
            return

        # Se busca el tamaño de letra más grande con el que las columnas entran a lo ancho.
        for tam in range(TAM_MAX, TAM_MIN - 1, -1):
            normal, negrita = self._fuente(tam, False), self._fuente(tam, True)
            alto_linea = normal.metrics("linespace") + 3
            ancho_car = normal.measure("0")
            columnas = repartir_en_columnas(unidades, (alto - 2 * MARGEN_V) // alto_linea)
            anchos = [max(len(t) for _, t in col) * ancho_car for col in columnas]
            total = sum(anchos) + ESPACIO_COLUMNAS * (len(columnas) - 1)
            if total <= ancho - 2 * MARGEN_H:
                break

        desborda = total > ancho - 2 * MARGEN_H
        x = MARGEN_H if desborda else (ancho - total) / 2  # centradas respecto de la pantalla
        estilos = {
            "acordes": (negrita, pal.acorde),
            "letra": (normal, pal.tenue),
            "seccion": (negrita, pal.warning),
        }
        fondo_max = MARGEN_V
        for i, col in enumerate(columnas):
            y = MARGEN_V
            for tipo, linea in col:
                if tipo != "vacia":
                    fuente, color = estilos[tipo]
                    c.create_text(x, y, text=linea, anchor="nw", font=fuente, fill=color)
                y += alto_linea
            fondo_max = max(fondo_max, y)
            x += anchos[i]
            if i < len(columnas) - 1:
                c.create_line(x + ESPACIO_COLUMNAS / 2, MARGEN_V, x + ESPACIO_COLUMNAS / 2, 0, fill=pal.borde, tags="sep")
                x += ESPACIO_COLUMNAS
        for item in c.find_withtag("sep"):  # los separadores llegan hasta la columna más larga
            x0, y0, x1, _ = c.coords(item)
            c.coords(item, x0, y0, x1, fondo_max)
        ancho_total = total + 2 * MARGEN_H
        c.configure(scrollregion=(0, 0, max(ancho, ancho_total), alto))
        self._mostrar_hsb(desborda, ancho, alto, ancho_total)

    def _mostrar_hsb(self, mostrar: bool, ancho: int, alto: int, ancho_total: int) -> None:
        if mostrar and not self._hsb_visible:
            self.hsb.place(relx=0, rely=1.0, relwidth=1.0, anchor="sw")
            self._hsb_visible = True
        elif not mostrar and self._hsb_visible:
            self.hsb.place_forget()
            self._hsb_visible = False
            self.canvas.xview_moveto(0)
