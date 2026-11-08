"""Pantalla de lectura: título y letra con acordes, en columnas dinámicas y centradas."""
from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from typing import Callable

import ttkbootstrap as ttk

from services.chords import formatear_semitonos, normalizar_semitonos, transponer_texto
from services.library_service import ValidationError
from ui import tkw as W
from ui.columns import construir_unidades, repartir_en_columnas
from ui.components import Debounce
from ui.quick_selection import PanelSeleccionRapida

TAM_MAX, TAM_MIN = 17, 9
MARGEN_V, MARGEN_H, ESPACIO_COLUMNAS = 30, 44, 72


class VistaCancion(ttk.Frame):
    def __init__(
        self,
        parent,
        app,
        cancion_id: int,
        volver: Callable[[], None],
        desde_seleccion_rapida: bool = False,
    ) -> None:
        super().__init__(parent)
        self.app, self.volver = app, volver
        self.desde_seleccion_rapida = desde_seleccion_rapida
        self.cancion = app.servicio.obtener_cancion(cancion_id)
        self.album = app.servicio.obtener_album(self.cancion.album_id)
        self.semitonos = self.cancion.semitonos
        pal, f = app.pal, app.fuentes
        self._fuentes: dict[tuple[int, bool], tkfont.Font] = {}
        self._texto_cache: tuple[int, list] | None = None

        # ---------------------------------------------------------- cabecera
        cab = ttk.Frame(self, padding=(24, 16, 24, 10))
        cab.pack(fill="x")
        cab.columnconfigure(0, weight=0)
        cab.columnconfigure(1, weight=1)
        cab.columnconfigure(2, weight=0)

        ttk.Button(cab, text="←  Volver", bootstyle="secondary-outline", command=self._volver).grid(row=0, column=0, sticky="w")

        centro = ttk.Frame(cab)
        centro.grid(row=0, column=1, padx=16)
        ttk.Label(
            centro,
            text=self.cancion.titulo,
            font=f.ui(20, "bold"),
            anchor="center",
            justify="center",
            wraplength=480,
        ).pack()
        ttk.Label(centro, text=self.album.nombre, foreground=pal.muted, font=f.ui(10)).pack(pady=(1, 0))

        # Acciones a la derecha
        acciones_der = ttk.Frame(cab)
        acciones_der.grid(row=0, column=2, sticky="e")

        # 1. Botonera para trasponer los acordes (a la izquierda del botón Editar)
        bloque_tono = ttk.Frame(acciones_der)
        bloque_tono.pack(side="left", padx=(0, 12))

        ttk.Label(bloque_tono, text="Tono", foreground=pal.muted, font=f.ui(10)).pack(side="left", padx=(0, 5))
        ttk.Button(bloque_tono, text="−", width=2, bootstyle="secondary", command=lambda: self._cambiar(-1)).pack(side="left")
        self.lbl_tono = ttk.Label(bloque_tono, text="", width=4, anchor="center", font=f.ui(12, "bold"), foreground=pal.acorde)
        self.lbl_tono.pack(side="left", padx=2)
        ttk.Button(bloque_tono, text="+", width=2, bootstyle="secondary", command=lambda: self._cambiar(1)).pack(side="left")
        self.btn_original = ttk.Button(bloque_tono, text="Orig.", bootstyle="secondary-outline", command=lambda: self._fijar(0))
        self.btn_original.pack(side="left", padx=(5, 0))

        # 2. Botón para añadir o quitar de selección rápida
        self.btn_fav = ttk.Button(acciones_der, text="＋ A lista", bootstyle="secondary-outline", command=self._toggle_lista)
        self.btn_fav.pack(side="left", padx=(0, 8))
        self._actualizar_boton_lista()

        # 3. Botón Editar
        ttk.Button(acciones_der, text="Editar", bootstyle="primary", command=self.editar).pack(side="left", padx=(0, 8))

        # 4. Botón Configuración (⚙)
        ttk.Button(acciones_der, text="⚙", bootstyle="secondary-outline", width=3, command=app.abrir_configuracion).pack(side="left")

        # 5. Toggle de columna de selección rápida (solo si se accedió desde ella)
        if self.desde_seleccion_rapida:
            self.btn_toggle_panel = ttk.Button(
                acciones_der,
                text="▶ Ocultar lista",
                bootstyle="info-outline",
                command=self._toggle_panel,
            )
            self.btn_toggle_panel.pack(side="left", padx=(8, 0))

        ttk.Separator(self).pack(fill="x")

        # ---------------------------------------------------------- cuerpo principal
        cuerpo = W.Frame(self, bg=pal.bg)
        cuerpo.pack(fill="both", expand=True)

        # Zona de lectura (canvas con scroll horizontal)
        self.zona_lectura = W.Frame(cuerpo, bg=pal.bg)
        self.zona_lectura.pack(side="left", fill="both", expand=True)

        self.canvas = W.Canvas(self.zona_lectura, bg=pal.bg, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self.hsb = ttk.Scrollbar(self.zona_lectura, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(xscrollcommand=self.hsb.set)
        self._hsb_visible = False
        self._redibujar_diferido = Debounce(self, 30, self.redibujar)
        self.canvas.bind("<Configure>", lambda e: self._redibujar_diferido())

        # Columna de Selección Rápida a la derecha (solo cuando se accede desde ella)
        if self.desde_seleccion_rapida:
            self._panel_desplegado = True
            self.panel_rapido = PanelSeleccionRapida(
                cuerpo,
                app=self.app,
                ancho=310,
                cancion_actual_id=self.cancion.id,
                al_abrir_cancion=self._abrir_desde_panel,
                al_colapsar=self._toggle_panel,
            )
            self.panel_rapido.pack(side="right", fill="y")
        else:
            self._panel_desplegado = False
            self.panel_rapido = None

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

    # -------------------------------------------------- selección rápida
    def _actualizar_boton_lista(self) -> None:
        en_lista = self.cancion.id in self.app.servicio.obtener_ids_seleccion_rapida()
        if en_lista:
            self.btn_fav.configure(text="✓ En lista", bootstyle="success-outline")
        else:
            self.btn_fav.configure(text="＋ A lista", bootstyle="secondary-outline")

    def _toggle_lista(self) -> None:
        actuales = self.app.servicio.obtener_ids_seleccion_rapida()
        if self.cancion.id in actuales:
            idx = actuales.index(self.cancion.id)
            self.app.servicio.eliminar_de_seleccion_rapida(idx)
            self.app.toast.mostrar("Canción quitada de la selección rápida")
        else:
            try:
                self.app.servicio.agregar_a_seleccion_rapida([self.cancion.id])
                self.app.toast.mostrar("Canción añadida a selección rápida", "ok")
            except ValidationError as e:
                self.app.toast.mostrar(str(e), "error")
                return

        self._actualizar_boton_lista()
        if self.panel_rapido is not None:
            self.panel_rapido.refrescar()

    def _toggle_panel(self) -> None:
        if not self.desde_seleccion_rapida or self.panel_rapido is None:
            return
        if self._panel_desplegado:
            self.panel_rapido.pack_forget()
            self._panel_desplegado = False
            if hasattr(self, "btn_toggle_panel"):
                self.btn_toggle_panel.configure(text="◀ Lista rápida", bootstyle="secondary-outline")
        else:
            self.panel_rapido.pack(side="right", fill="y")
            self._panel_desplegado = True
            if hasattr(self, "btn_toggle_panel"):
                self.btn_toggle_panel.configure(text="▶ Ocultar lista", bootstyle="info-outline")

        self.update_idletasks()
        self.redibujar()

    def _abrir_desde_panel(self, cancion) -> None:
        if cancion.id != self.cancion.id:
            self.app.mostrar_cancion(cancion.id, self.volver, desde_seleccion_rapida=True)

    # ---------------------------------------------------------- navegación
    def _volver(self) -> None:
        self.volver()

    def editar(self) -> None:
        app, c = self.app, self.cancion
        app.mostrar_formulario(
            c.album_id,
            c.id,
            lambda: app.mostrar_cancion(c.id, self.volver, desde_seleccion_rapida=self.desde_seleccion_rapida),
        )

    # ------------------------------------------------------------- dibujo
    def _fuente(self, tam: int, negrita: bool) -> tkfont.Font:
        clave = (tam, negrita)
        if clave not in self._fuentes:
            self._fuentes[clave] = tkfont.Font(
                root=self, family=self.app.fuentes.familia_mono, size=tam, weight="bold" if negrita else "normal"
            )
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
            c.create_text(
                ancho / 2,
                alto / 2,
                text="Esta canción todavía no tiene letra.\nUsá «Editar» para añadirla.",
                fill=pal.muted,
                font=self.app.fuentes.ui(13),
                justify="center",
            )
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
