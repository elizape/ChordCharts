"""Columna de selección rápida y selector modal de canciones."""
from __future__ import annotations

import tkinter as tk
from typing import Callable

import ttkbootstrap as ttk

from services.library_service import MAX_SELECCION_RAPIDA, ValidationError
from ui import tkw as W
from ui.components import Monograma, ScrollFrame, confirmar, mezclar, plural, recortar


# ============================================================================
# Diálogo de Selección de Canciones (Álbumes -> Canciones, múltiple o simple)
# ============================================================================
class DialogoSelectorCanciones(W.Toplevel):
    """Selector modal con navegación en dos niveles: Álbumes -> Canciones.

    Soporta:
    - Modo 'multiple': selección múltiple para añadir hasta completar el cupo de 15.
      La selección se conserva al navegar entre diferentes álbumes.
    - Modo 'simple': selección de 1 canción para reemplazar en una posición.
    """

    def __init__(
        self,
        parent,
        pal,
        fuentes,
        servicio,
        modo: str = "multiple",
        cancion_actual_id: int | None = None,
        ancho: int = 680,
        alto: int = 580,
    ) -> None:
        super().__init__(parent)
        self.withdraw()
        self.pal, self.fuentes, self.servicio = pal, fuentes, servicio
        self.modo = modo
        self.cancion_actual_id = cancion_actual_id
        self._ancho, self._alto = ancho, alto
        self.resultado = None

        titulo = "Añadir a selección rápida" if modo == "multiple" else "Cambiar canción"
        self.title(titulo)
        self.configure(bg=pal.bg, highlightthickness=1, highlightbackground=pal.borde)
        self.transient(parent.winfo_toplevel())
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.cancelar)
        self.bind("<Escape>", lambda e: self.cancelar())

        # Estado
        self._ids_en_lista = set(self.servicio.obtener_ids_seleccion_rapida())
        if modo == "simple" and cancion_actual_id is not None:
            self._ids_en_lista.discard(cancion_actual_id)

        self._cupo_disponible = max(0, MAX_SELECCION_RAPIDA - len(self.servicio.obtener_ids_seleccion_rapida()))
        self._seleccionadas: set[int] = set()
        self._album_activo = None

        # Contenedor raíz
        self.cuerpo = ttk.Frame(self, padding=(24, 20, 24, 18))
        self.cuerpo.pack(fill="both", expand=True)
        self.cuerpo.rowconfigure(1, weight=1)
        self.cuerpo.columnconfigure(0, weight=1)

        # 1. Cabecera superior
        self.cabecera = ttk.Frame(self.cuerpo)
        self.cabecera.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        self.lbl_titulo = ttk.Label(self.cabecera, text=titulo, font=fuentes.ui(16, "bold"))
        self.lbl_titulo.pack(anchor="w")
        self.lbl_subtitulo = ttk.Label(self.cabecera, text="", foreground=pal.muted, font=fuentes.ui(10))
        self.lbl_subtitulo.pack(anchor="w", pady=(2, 0))

        # 2. Área de contenido central (intercambiable)
        self.contenedor_vistas = W.Frame(self.cuerpo, bg=pal.bg)
        self.contenedor_vistas.grid(row=1, column=0, sticky="nsew")
        self.contenedor_vistas.rowconfigure(0, weight=1)
        self.contenedor_vistas.columnconfigure(0, weight=1)

        self.vista_actual: tk.Misc | None = None

        # 3. Pie inferior
        self.pie = ttk.Frame(self.cuerpo)
        self.pie.grid(row=2, column=0, sticky="ew", pady=(14, 0))
        self.pie.columnconfigure(0, weight=1)

        self.lbl_resumen = ttk.Label(self.pie, text="", foreground=pal.muted, font=fuentes.ui(10))
        self.lbl_resumen.grid(row=0, column=0, sticky="w")

        botones = ttk.Frame(self.pie)
        botones.grid(row=0, column=1, sticky="e")

        self.btn_cancelar = ttk.Button(botones, text="Cancelar", bootstyle="secondary", command=self.cancelar)
        self.btn_cancelar.pack(side="left", padx=(0, 10))

        if modo == "multiple":
            self.btn_aceptar = ttk.Button(
                botones,
                text="Añadir seleccionadas",
                bootstyle="primary",
                command=self._confirmar_multiple,
                state="disabled",
            )
            self.btn_aceptar.pack(side="left")
        else:
            self.btn_aceptar = None

        # Iniciar en vista de álbumes
        self._mostrar_albumes()

    def cancelar(self) -> None:
        self.cerrar(None)

    def cerrar(self, resultado) -> None:
        self.resultado = resultado
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()

    def mostrar(self):
        self.update_idletasks()
        raiz = self.master.winfo_toplevel()
        w, h = self._ancho, self._alto
        x = raiz.winfo_rootx() + (raiz.winfo_width() - w) // 2
        y = raiz.winfo_rooty() + (raiz.winfo_height() - h) // 3
        self.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")
        self.deiconify()
        self.lift()
        try:
            self.wait_visibility()
        except tk.TclError:
            pass
        try:
            self.grab_set()
        except tk.TclError:
            pass
        self.focus_set()
        self.wait_window(self)
        return self.resultado

    # -------------------------------------------------------- Vista: Álbumes
    def _mostrar_albumes(self) -> None:
        self._album_activo = None
        if self.vista_actual is not None:
            self.vista_actual.destroy()

        sub = (
            "Tocá un álbum para ver y elegir sus canciones (podés seleccionar de varios álbumes)."
            if self.modo == "multiple"
            else "Elegí el álbum que contiene la canción con la que querés reemplazar."
        )
        self.lbl_subtitulo.configure(text=sub)

        frame = W.Frame(self.contenedor_vistas, bg=self.pal.bg)
        frame.grid(row=0, column=0, sticky="nsew")
        self.vista_actual = frame

        scroll = ScrollFrame(frame, self.pal)
        scroll.pack(fill="both", expand=True)

        albumes = self.servicio.listar_albumes(orden="recientes")
        if not albumes:
            vacio = ttk.Frame(scroll.cuerpo)
            vacio.pack(expand=True, pady=40)
            ttk.Label(vacio, text="No hay álbumes creados.", font=self.fuentes.ui(12, "bold")).pack()
            self._actualizar_pie()
            return

        for a in albumes:
            self._crear_fila_album(scroll.cuerpo, a)

        self._actualizar_pie()

    def _crear_fila_album(self, parent, album) -> None:
        pal, f = self.pal, self.fuentes
        fila = W.Frame(
            parent,
            bg=pal.card,
            highlightthickness=1,
            highlightbackground=pal.borde,
            cursor="hand2",
            padx=14,
            pady=10,
        )
        fila.pack(fill="x", pady=4, padx=4)
        fila.columnconfigure(1, weight=1)

        inicial = (album.nombre.strip()[:1] or "♪").upper()
        Monograma(fila, pal, f, inicial, album.nombre, tam=40, fondo=pal.card).grid(
            row=0, column=0, rowspan=2, padx=(0, 12), sticky="w"
        )

        lbl_nombre = W.Label(
            fila,
            text=recortar(album.nombre, 50),
            font=f.ui(12, "bold"),
            bg=pal.card,
            fg=pal.fg,
            anchor="w",
            cursor="hand2",
        )
        lbl_nombre.grid(row=0, column=1, sticky="w")

        subtext = plural(album.total_canciones, "canción", "canciones")
        # Contar cuántas seleccionadas pertenecen a este álbum si estamos en múltiple
        if self.modo == "multiple":
            canciones_album = self.servicio.listar_canciones(album.id)
            c_sel = sum(1 for r in canciones_album if r.cancion.id in self._seleccionadas)
            if c_sel > 0:
                subtext += f"  ·  ✓ {c_sel} seleccionadas"

        lbl_det = W.Label(
            fila,
            text=subtext,
            font=f.ui(10),
            bg=pal.card,
            fg=pal.acorde if (self.modo == "multiple" and "✓" in subtext) else pal.muted,
            anchor="w",
            cursor="hand2",
        )
        lbl_det.grid(row=1, column=1, sticky="w")

        lbl_flecha = W.Label(fila, text="Ver canciones →", font=f.ui(10, "bold"), bg=pal.card, fg=pal.primary, cursor="hand2")
        lbl_flecha.grid(row=0, column=2, rowspan=2, padx=(8, 0), sticky="e")

        def _entrar(_e=None):
            self._mostrar_canciones(album)

        def _hover_on(_e=None):
            fila.configure(bg=pal.card_hover, highlightbackground=pal.primary)
            for w in (lbl_nombre, lbl_det, lbl_flecha):
                try:
                    w.configure(bg=pal.card_hover)
                except tk.TclError:
                    pass

        def _hover_off(_e=None):
            fila.configure(bg=pal.card, highlightbackground=pal.borde)
            for w in (lbl_nombre, lbl_det, lbl_flecha):
                try:
                    w.configure(bg=pal.card)
                except tk.TclError:
                    pass

        for w in (fila, lbl_nombre, lbl_det, lbl_flecha):
            w.bind("<Button-1>", _entrar)
            w.bind("<Enter>", _hover_on, add="+")
            w.bind("<Leave>", _hover_off, add="+")

    # ------------------------------------------------------- Vista: Canciones
    def _mostrar_canciones(self, album) -> None:
        self._album_activo = album
        if self.vista_actual is not None:
            self.vista_actual.destroy()

        self.lbl_subtitulo.configure(
            text=f"Álbum: {album.nombre} — " + (
                "Marcá las canciones que querés añadir y presioná el botón inferior."
                if self.modo == "multiple"
                else "Hacé clic en la canción elegida para seleccionarla."
            )
        )

        frame = W.Frame(self.contenedor_vistas, bg=self.pal.bg)
        frame.grid(row=0, column=0, sticky="nsew")
        self.vista_actual = frame
        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)

        # Barra de navegación interna (retroceso)
        barra_nav = ttk.Frame(frame, padding=(4, 0, 4, 8))
        barra_nav.grid(row=0, column=0, sticky="ew")

        btn_volver = ttk.Button(
            barra_nav,
            text="← Volver a álbumes",
            bootstyle="secondary-outline",
            command=self._mostrar_albumes,
        )
        btn_volver.pack(side="left")

        ttk.Label(
            barra_nav,
            text=f"Álbum: {album.nombre}",
            font=self.fuentes.ui(11, "bold"),
            foreground=self.pal.fg,
        ).pack(side="left", padx=(14, 0))

        if self.modo == "multiple":
            btn_desmarcar = ttk.Button(
                barra_nav,
                text="Desmarcar todas",
                bootstyle="secondary-link",
                command=lambda: self._desmarcar_album(album),
            )
            btn_desmarcar.pack(side="right")

            btn_marcar = ttk.Button(
                barra_nav,
                text="Marcar todas",
                bootstyle="secondary-link",
                command=lambda: self._marcar_todas_album(album),
            )
            btn_marcar.pack(side="right", padx=(0, 6))

        # Lista de canciones
        scroll = ScrollFrame(frame, self.pal)
        scroll.grid(row=1, column=0, sticky="nsew")

        canciones_res = self.servicio.listar_canciones(album.id, orden="az")
        if not canciones_res:
            vacio = ttk.Frame(scroll.cuerpo)
            vacio.pack(expand=True, pady=40)
            ttk.Label(vacio, text="Este álbum no tiene canciones.", font=self.fuentes.ui(11, "bold"), foreground=self.pal.muted).pack()
            self._actualizar_pie()
            return

        for r in canciones_res:
            self._crear_fila_cancion(scroll.cuerpo, r.cancion)

        self._actualizar_pie()

    def _crear_fila_cancion(self, parent, cancion) -> None:
        pal, f = self.pal, self.fuentes
        ya_en_lista = cancion.id in self._ids_en_lista

        fila = W.Frame(
            parent,
            bg=pal.card,
            highlightthickness=1,
            highlightbackground=pal.borde,
            cursor="arrow" if ya_en_lista else "hand2",
            padx=12,
            pady=8,
        )
        fila.pack(fill="x", pady=3, padx=4)
        fila.columnconfigure(1, weight=1)

        if self.modo == "multiple":
            var_check = tk.BooleanVar(value=cancion.id in self._seleccionadas)

            def _al_conmutar():
                if ya_en_lista:
                    return
                if var_check.get():
                    # Intenta marcar
                    restantes = self._cupo_disponible - len(self._seleccionadas)
                    if restantes <= 0:
                        var_check.set(False)
                        self.lbl_resumen.configure(
                            text=f"¡Límite de {MAX_SELECCION_RAPIDA} canciones alcanzado! No podés marcar más.",
                            foreground=pal.danger,
                        )
                        return
                    self._seleccionadas.add(cancion.id)
                else:
                    self._seleccionadas.discard(cancion.id)
                self._actualizar_pie()

            chk = ttk.Checkbutton(
                fila,
                variable=var_check,
                command=_al_conmutar,
                state="disabled" if ya_en_lista else "normal",
            )
            chk.grid(row=0, column=0, rowspan=2, padx=(2, 10), sticky="w")

            lbl_titulo = W.Label(
                fila,
                text=recortar(cancion.titulo, 60),
                font=f.ui(11, "bold"),
                bg=pal.card,
                fg=pal.muted if ya_en_lista else pal.fg,
                anchor="w",
                cursor="arrow" if ya_en_lista else "hand2",
            )
            lbl_titulo.grid(row=0, column=1, sticky="w")

            estado_txt = "Ya se encuentra en la selección rápida" if ya_en_lista else "Tocar para seleccionar"
            lbl_sub = W.Label(
                fila,
                text=estado_txt,
                font=f.ui(9),
                bg=pal.card,
                fg=pal.muted,
                anchor="w",
                cursor="arrow" if ya_en_lista else "hand2",
            )
            lbl_sub.grid(row=1, column=1, sticky="w")

            if not ya_en_lista:
                def _click_fila(_e=None):
                    var_check.set(not var_check.get())
                    _al_conmutar()

                def _hover_in(_e=None):
                    fila.configure(bg=pal.card_hover, highlightbackground=pal.primary)
                    lbl_titulo.configure(bg=pal.card_hover)
                    lbl_sub.configure(bg=pal.card_hover)

                def _hover_out(_e=None):
                    fila.configure(bg=pal.card, highlightbackground=pal.borde)
                    lbl_titulo.configure(bg=pal.card)
                    lbl_sub.configure(bg=pal.card)

                for widget in (fila, lbl_titulo, lbl_sub):
                    widget.bind("<Button-1>", _click_fila)
                    widget.bind("<Enter>", _hover_in, add="+")
                    widget.bind("<Leave>", _hover_out, add="+")

        else:
            # Modo simple (reemplazo de una canción)
            lbl_titulo = W.Label(
                fila,
                text=recortar(cancion.titulo, 60),
                font=f.ui(11, "bold"),
                bg=pal.card,
                fg=pal.muted if ya_en_lista else pal.fg,
                anchor="w",
                cursor="arrow" if ya_en_lista else "hand2",
            )
            lbl_titulo.grid(row=0, column=1, sticky="w")

            estado_txt = "Ya en selección rápida" if ya_en_lista else "Tocar para elegir esta canción"
            lbl_sub = W.Label(
                fila,
                text=estado_txt,
                font=f.ui(9),
                bg=pal.card,
                fg=pal.muted,
                anchor="w",
                cursor="arrow" if ya_en_lista else "hand2",
            )
            lbl_sub.grid(row=1, column=1, sticky="w")

            if not ya_en_lista:
                btn_elegir = ttk.Button(
                    fila,
                    text="Seleccionar",
                    bootstyle="primary-outline",
                    command=lambda: self.cerrar(cancion.id),
                )
                btn_elegir.grid(row=0, column=2, rowspan=2, padx=(8, 0), sticky="e")

                def _seleccionar(_e=None):
                    self.cerrar(cancion.id)

                def _hover_in(_e=None):
                    fila.configure(bg=pal.card_hover, highlightbackground=pal.primary)
                    lbl_titulo.configure(bg=pal.card_hover)
                    lbl_sub.configure(bg=pal.card_hover)

                def _hover_out(_e=None):
                    fila.configure(bg=pal.card, highlightbackground=pal.borde)
                    lbl_titulo.configure(bg=pal.card)
                    lbl_sub.configure(bg=pal.card)

                for widget in (fila, lbl_titulo, lbl_sub):
                    widget.bind("<Button-1>", _seleccionar)
                    widget.bind("<Enter>", _hover_in, add="+")
                    widget.bind("<Leave>", _hover_out, add="+")

    def _marcar_todas_album(self, album) -> None:
        canciones = self.servicio.listar_canciones(album.id)
        for r in canciones:
            cid = r.cancion.id
            if cid in self._ids_en_lista:
                continue
            if len(self._seleccionadas) >= self._cupo_disponible:
                break
            self._seleccionadas.add(cid)
        self._mostrar_canciones(album)

    def _desmarcar_album(self, album) -> None:
        canciones = self.servicio.listar_canciones(album.id)
        for r in canciones:
            self._seleccionadas.discard(r.cancion.id)
        self._mostrar_canciones(album)

    def _actualizar_pie(self) -> None:
        if self.modo == "multiple":
            n_sel = len(self._seleccionadas)
            cupo_restante = self._cupo_disponible - n_sel
            if n_sel == 0:
                txt = f"Podés seleccionar hasta {self._cupo_disponible} canciones (límite máximo de {MAX_SELECCION_RAPIDA})."
                self.lbl_resumen.configure(text=txt, foreground=self.pal.muted)
                if self.btn_aceptar is not None:
                    self.btn_aceptar.configure(text="Añadir canciones", state="disabled")
            else:
                txt = f"✓ {n_sel} seleccionadas  ·  quedan {cupo_restante} lugares disponibles"
                self.lbl_resumen.configure(text=txt, foreground=self.pal.acorde)
                if self.btn_aceptar is not None:
                    self.btn_aceptar.configure(text=f"Añadir ({n_sel})", state="normal")
        else:
            self.lbl_resumen.configure(
                text="Seleccioná la canción que reemplazará a la actual en la lista rápida.",
                foreground=self.pal.muted,
            )

    def _confirmar_multiple(self) -> None:
        if self._seleccionadas:
            self.cerrar(list(self._seleccionadas))


# ============================================================================
# Fila individual de Selección Rápida con Drag & Drop
# ============================================================================
class FilaSeleccionRapida(W.Frame):
    """Fila en la columna de selección rápida con soporte para arrastrar con mouse (reordenar),

    modificar por otra canción, eliminarla, y hacer clic para abrirla.
    """

    def __init__(
        self,
        parent,
        panel,
        pal,
        fuentes,
        posicion: int,
        resultado,
        al_abrir: Callable[[], None],
        al_cambiar: Callable[[], None],
        al_eliminar: Callable[[], None],
        es_actual: bool = False,
    ) -> None:
        self.panel = panel
        self.pal = pal
        self.fuentes = fuentes
        self.posicion = posicion
        self.resultado = resultado
        self.cancion = resultado.cancion
        self.al_abrir = al_abrir
        self.al_cambiar = al_cambiar
        self.al_eliminar = al_eliminar
        self.es_actual = es_actual

        self._start_y = 0
        self._dragging = False

        fondo_inicial = mezclar(pal.card, pal.primary, 0.20) if es_actual else pal.card
        borde_inicial = pal.primary if es_actual else pal.borde

        super().__init__(
            parent,
            bg=fondo_inicial,
            highlightthickness=1,
            highlightbackground=borde_inicial,
            bd=0,
            padx=10,
            pady=8,
        )

        self.columnconfigure(1, weight=1)

        # Handle de arrastre e índice
        prefijo = "▶ " if es_actual else "⠿ "
        self.lbl_handle = W.Label(
            self,
            text=f"{prefijo}{posicion + 1}.",
            font=fuentes.mono(10, "bold"),
            bg=fondo_inicial,
            fg=pal.acorde if es_actual else pal.muted,
            cursor="fleur",
            padx=2,
        )
        self.lbl_handle.grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 8))

        # Textos: Título y Álbum
        self.lbl_titulo = W.Label(
            self,
            text=recortar(self.cancion.titulo, 24),
            font=fuentes.ui(10, "bold"),
            bg=fondo_inicial,
            fg=pal.fg,
            anchor="w",
            cursor="hand2",
        )
        self.lbl_titulo.grid(row=0, column=1, sticky="w")

        info_album = recortar(self.resultado.album_nombre, 22)
        if self.cancion.semitonos:
            info_album += f"  ({self.cancion.semitonos:+d})"
        self.lbl_album = W.Label(
            self,
            text=info_album,
            font=fuentes.ui(9),
            bg=fondo_inicial,
            fg=pal.muted,
            anchor="w",
            cursor="hand2",
        )
        self.lbl_album.grid(row=1, column=1, sticky="w")

        # Acciones a la derecha: Cambiar (⇄) y Eliminar (✕)
        acciones = W.Frame(self, bg=fondo_inicial)
        acciones.grid(row=0, column=2, rowspan=2, sticky="e", padx=(4, 0))

        self.btn_cambiar = W.Label(
            acciones,
            text="⇄",
            font=fuentes.ui(11, "bold"),
            bg=pal.card,
            fg=pal.muted,
            cursor="hand2",
            padx=4,
            pady=2,
        )
        self.btn_cambiar.pack(side="left", padx=2)
        self.btn_cambiar.bind("<Button-1>", lambda e: self.al_cambiar())
        self.btn_cambiar.bind("<Enter>", lambda e: self.btn_cambiar.configure(fg=pal.primary))
        self.btn_cambiar.bind("<Leave>", lambda e: self.btn_cambiar.configure(fg=pal.muted))

        self.btn_eliminar = W.Label(
            acciones,
            text="✕",
            font=fuentes.ui(10, "bold"),
            bg=pal.card,
            fg=pal.muted,
            cursor="hand2",
            padx=4,
            pady=2,
        )
        self.btn_eliminar.pack(side="left", padx=2)
        self.btn_eliminar.bind("<Button-1>", lambda e: self.al_eliminar())
        self.btn_eliminar.bind("<Enter>", lambda e: self.btn_eliminar.configure(fg=pal.danger))
        self.btn_eliminar.bind("<Leave>", lambda e: self.btn_eliminar.configure(fg=pal.muted))

        # Enlazar eventos de mouse para drag & drop y clic de apertura
        elementos_arrastrables = (self, self.lbl_handle, self.lbl_titulo, self.lbl_album)
        for w in elementos_arrastrables:
            w.bind("<ButtonPress-1>", self._on_press)
            w.bind("<B1-Motion>", self._on_motion)
            w.bind("<ButtonRelease-1>", self._on_release)
            w.bind("<Enter>", self._on_enter, add="+")
            w.bind("<Leave>", self._on_leave, add="+")

    def _on_enter(self, _e=None) -> None:
        if not self.panel.esta_arrastrando:
            self._pintar(self.pal.card_hover)
            self.configure(highlightbackground=self.pal.primary)

    def _on_leave(self, _e=None) -> None:
        if not self.panel.esta_arrastrando:
            color = mezclar(self.pal.card, self.pal.primary, 0.20) if self.es_actual else self.pal.card
            borde = self.pal.primary if self.es_actual else self.pal.borde
            self._pintar(color)
            self.configure(highlightbackground=borde)

    def _pintar(self, color: str) -> None:
        for w in (self, self.lbl_handle, self.lbl_titulo, self.lbl_album):
            try:
                w.configure(bg=color)
            except tk.TclError:
                pass

    def _on_press(self, event) -> None:
        self._start_y = event.y_root
        self._dragging = False

    def _on_motion(self, event) -> None:
        dy = abs(event.y_root - self._start_y)
        if dy > 5 and not self._dragging:
            self._dragging = True
            self.panel.iniciar_arrastre(self.posicion)
        if self._dragging:
            self.panel.mover_arrastre(event.y_root)

    def _on_release(self, event) -> None:
        if self._dragging:
            self._dragging = False
            self.panel.finalizar_arrastre(event.y_root)
        else:
            # Clic simple: abrir canción
            self.al_abrir()


# ============================================================================
# Columna / Panel de Selección Rápida en la Pantalla Principal
# ============================================================================
class PanelSeleccionRapida(W.Frame):
    """Columna de selección rápida que gestiona hasta 15 canciones."""

    def __init__(
        self,
        parent,
        app,
        ancho: int = 320,
        cancion_actual_id: int | None = None,
        al_abrir_cancion: Callable[[object], None] | None = None,
        al_colapsar: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(
            parent,
            bg=mezclar(app.pal.bg, app.pal.card, 0.4),
            highlightthickness=1,
            highlightbackground=app.pal.borde,
            width=ancho,
        )
        self.app = app
        self.pal = app.pal
        self.fuentes = app.fuentes
        self.ancho = ancho
        self.cancion_actual_id = cancion_actual_id
        self.al_abrir_cancion = al_abrir_cancion
        self.al_colapsar = al_colapsar
        self.pack_propagate(False)

        self._filas: list[FilaSeleccionRapida] = []
        self._drag_origen: int | None = None
        self._drag_destino: int | None = None
        self.esta_arrastrando = False

        # 1. Cabecera del panel
        cab = W.Frame(self, bg=self.cget("bg"), padx=16, pady=16)
        cab.pack(fill="x")
        cab.columnconfigure(0, weight=1)

        fila_tit = W.Frame(cab, bg=self.cget("bg"))
        fila_tit.pack(fill="x")
        W.Label(
            fila_tit,
            text="Selección rápida",
            font=self.fuentes.ui(13, "bold"),
            bg=self.cget("bg"),
            fg=self.pal.fg,
        ).pack(side="left")

        if self.al_colapsar:
            btn_cerrar = W.Label(
                fila_tit,
                text="▶ Ocultar",
                font=self.fuentes.ui(9, "bold"),
                bg=self.cget("bg"),
                fg=self.pal.primary,
                cursor="hand2",
                padx=4,
            )
            btn_cerrar.pack(side="right", padx=(6, 0))
            btn_cerrar.bind("<Button-1>", lambda e: self.al_colapsar())

        self.lbl_contador = W.Label(
            fila_tit,
            text="0/15",
            font=self.fuentes.ui(10, "bold"),
            bg=mezclar(self.pal.card, self.pal.primary, 0.25),
            fg=self.pal.acorde,
            padx=7,
            pady=2,
        )
        self.lbl_contador.pack(side="right")

        fila_botones = ttk.Frame(cab)
        fila_botones.pack(fill="x", pady=(10, 0))

        self.btn_anadir = ttk.Button(
            fila_botones,
            text="＋  Añadir",
            bootstyle="primary",
            command=self.anadir_canciones,
        )
        self.btn_anadir.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.btn_vaciar = ttk.Button(
            fila_botones,
            text="Vaciar",
            bootstyle="secondary-outline",
            command=self.vaciar_lista,
        )
        self.btn_vaciar.pack(side="right")

        ttk.Separator(self).pack(fill="x", padx=14)

        # 2. Área de lista desplazable
        self.scroll = ScrollFrame(self, self.pal)
        self.scroll.pack(fill="both", expand=True, padx=8, pady=8)

        # Línea indicadora de inserción para drag & drop
        self.indicador = W.Frame(self.scroll.cuerpo, bg=self.pal.primary, height=3)

        self.refrescar()

    # ------------------------------------------------------------------ datos
    def refrescar(self) -> None:
        self.scroll.vaciar()
        self._filas.clear()
        self.indicador = W.Frame(self.scroll.cuerpo, bg=self.pal.primary, height=3)

        items = self.app.servicio.listar_seleccion_rapida()
        total = len(items)

        self.lbl_contador.configure(text=f"{total}/{MAX_SELECCION_RAPIDA}")

        if total >= MAX_SELECCION_RAPIDA:
            self.btn_anadir.configure(state="disabled")
        else:
            self.btn_anadir.configure(state="normal")

        if total == 0:
            self.btn_vaciar.configure(state="disabled")
            self._mostrar_vacio()
            return

        self.btn_vaciar.configure(state="normal")
        for idx, r in enumerate(items):
            es_act = (self.cancion_actual_id is not None and r.cancion.id == self.cancion_actual_id)
            if self.al_abrir_cancion:
                cb_abrir = (lambda c=r.cancion: self.al_abrir_cancion(c))
            else:
                cb_abrir = (lambda c=r.cancion: self.app.mostrar_cancion(c.id, self.app.mostrar_albumes, desde_seleccion_rapida=True))

            fila = FilaSeleccionRapida(
                self.scroll.cuerpo,
                panel=self,
                pal=self.pal,
                fuentes=self.fuentes,
                posicion=idx,
                resultado=r,
                al_abrir=cb_abrir,
                al_cambiar=lambda i=idx, c=r.cancion: self.cambiar_cancion(i, c),
                al_eliminar=lambda i=idx, c=r.cancion: self.eliminar_cancion(i, c),
                es_actual=es_act,
            )
            fila.pack(fill="x", pady=2)
            self._filas.append(fila)

    def _mostrar_vacio(self) -> None:
        vacio = W.Frame(self.scroll.cuerpo, bg=self.pal.bg, padx=12, pady=40)
        vacio.pack(fill="both", expand=True)

        W.Label(vacio, text="♪", font=self.fuentes.ui(28, "bold"), bg=self.pal.bg, fg=self.pal.acorde).pack()
        W.Label(vacio, text="Sin canciones", font=self.fuentes.ui(12, "bold"), bg=self.pal.bg, fg=self.pal.fg).pack(pady=(6, 2))
        W.Label(
            vacio,
            text=f"Añadí hasta {MAX_SELECCION_RAPIDA} canciones\npara tenerlas siempre a mano.",
            font=self.fuentes.ui(10),
            bg=self.pal.bg,
            fg=self.pal.muted,
            justify="center",
        ).pack(pady=(0, 14))

        ttk.Button(vacio, text="＋ Añadir canciones", bootstyle="primary-outline", command=self.anadir_canciones).pack()

    # --------------------------------------------------------------- acciones
    def anadir_canciones(self) -> None:
        actuales = len(self._filas)
        if actuales >= MAX_SELECCION_RAPIDA:
            self.app.toast.mostrar(f"Ya alcanzaste el límite de {MAX_SELECCION_RAPIDA} canciones.", "info")
            return

        dlg = DialogoSelectorCanciones(
            self,
            pal=self.pal,
            fuentes=self.fuentes,
            servicio=self.app.servicio,
            modo="multiple",
        )
        seleccionadas = dlg.mostrar()
        if seleccionadas:
            try:
                self.app.servicio.agregar_a_seleccion_rapida(seleccionadas)
                n = len(seleccionadas)
                self.app.toast.mostrar(f"{plural(n, 'canción añadida', 'canciones añadidas')} a selección rápida")
                self.refrescar()
            except ValidationError as e:
                self.app.toast.mostrar(str(e), "error")

    def cambiar_cancion(self, posicion: int, cancion) -> None:
        dlg = DialogoSelectorCanciones(
            self,
            pal=self.pal,
            fuentes=self.fuentes,
            servicio=self.app.servicio,
            modo="simple",
            cancion_actual_id=cancion.id,
        )
        nueva_id = dlg.mostrar()
        if nueva_id is not None:
            try:
                self.app.servicio.reemplazar_en_seleccion_rapida(posicion, nueva_id)
                self.app.toast.mostrar("Canción cambiada")
                self.refrescar()
            except ValidationError as e:
                self.app.toast.mostrar(str(e), "error")

    def eliminar_cancion(self, posicion: int, cancion) -> None:
        try:
            self.app.servicio.eliminar_de_seleccion_rapida(posicion)
            self.app.toast.mostrar("Canción quitada de la lista rápida")
            self.refrescar()
        except ValidationError as e:
            self.app.toast.mostrar(str(e), "error")

    def vaciar_lista(self) -> None:
        if not self._filas:
            return
        if confirmar(
            self,
            self.pal,
            self.fuentes,
            titulo="Vaciar lista rápida",
            mensaje="¿Deseás vaciar todas las canciones de la selección rápida?",
            texto_ok="Vaciar lista",
            peligro=True,
        ):
            self.app.servicio.vaciar_seleccion_rapida()
            self.app.toast.mostrar("Selección rápida vaciada", "info")
            self.refrescar()

    # ----------------------------------------------------------- drag & drop
    def iniciar_arrastre(self, origen: int) -> None:
        self.esta_arrastrando = True
        self._drag_origen = origen
        self._drag_destino = origen
        if 0 <= origen < len(self._filas):
            fila = self._filas[origen]
            fila.configure(highlightbackground=self.pal.primary)

    def mover_arrastre(self, y_root: int) -> None:
        if not self._filas or self._drag_origen is None:
            return
        # Calcular el índice destino según la posición vertical
        destino = len(self._filas) - 1
        for idx, fila in enumerate(self._filas):
            try:
                f_y = fila.winfo_rooty()
                f_h = fila.winfo_height()
                if y_root < f_y + f_h // 2:
                    destino = idx
                    break
            except tk.TclError:
                pass

        self._drag_destino = destino
        # Actualizar posición del indicador visual
        try:
            if destino < len(self._filas):
                target_fila = self._filas[destino]
                if destino <= self._drag_origen:
                    self.indicador.pack(in_=self.scroll.cuerpo, before=target_fila, fill="x", pady=1)
                else:
                    self.indicador.pack(in_=self.scroll.cuerpo, after=target_fila, fill="x", pady=1)
            else:
                self.indicador.pack(in_=self.scroll.cuerpo, fill="x", pady=1)
        except tk.TclError:
            pass

    def finalizar_arrastre(self, _y_root: int) -> None:
        self.indicador.pack_forget()
        self.esta_arrastrando = False
        origen = self._drag_origen
        destino = self._drag_destino
        self._drag_origen = None
        self._drag_destino = None

        if origen is not None and destino is not None and origen != destino:
            try:
                self.app.servicio.mover_en_seleccion_rapida(origen, destino)
                self.refrescar()
            except ValidationError as e:
                self.app.toast.mostrar(str(e), "error")
        else:
            self.refrescar()
