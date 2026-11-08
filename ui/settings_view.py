"""Pantalla / Diálogo de Configuración general de la aplicación."""
from __future__ import annotations

import tkinter as tk

import ttkbootstrap as ttk

from ui import tkw as W
from ui.components import ScrollFrame, mezclar, rectangulo_redondeado
from ui.theme import TEMAS_DEFINIDOS


class DialogoConfiguracion(W.Toplevel):
    """Diálogo modal de configuración y personalización (temas, apariencia y futuras opciones)."""

    def __init__(self, parent, app, ancho: int = 600, alto: int = 560) -> None:
        super().__init__(parent)
        self.withdraw()
        self.app = app
        self.pal = app.pal
        self.fuentes = app.fuentes
        self._ancho = ancho
        self._alto = alto

        self.title("Configuración")
        self.configure(bg=self.pal.bg, highlightthickness=1, highlightbackground=self.pal.borde)
        self.transient(parent.winfo_toplevel())
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.cerrar)
        self.bind("<Escape>", lambda e: self.cerrar())

        # Contenedor principal
        self.cuerpo = ttk.Frame(self, padding=(28, 22, 28, 20))
        self.cuerpo.pack(fill="both", expand=True)
        self.cuerpo.rowconfigure(1, weight=1)
        self.cuerpo.columnconfigure(0, weight=1)

        # 1. Cabecera
        cab = ttk.Frame(self.cuerpo)
        cab.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        fila_tit = ttk.Frame(cab)
        fila_tit.pack(fill="x")
        ttk.Label(fila_tit, text="⚙  Configuración", font=self.fuentes.ui(17, "bold")).pack(side="left")

        ttk.Label(
            cab,
            text="Personalizá la apariencia y preferencias de la aplicación.",
            foreground=self.pal.muted,
            font=self.fuentes.ui(10),
        ).pack(anchor="w", pady=(2, 0))

        # 2. Área desplazable con secciones de configuración
        self.scroll = ScrollFrame(self.cuerpo, self.pal)
        self.scroll.grid(row=1, column=0, sticky="nsew")

        self._tarjetas_temas: dict[str, W.Frame] = {}
        self._construir_secciones()

        # 3. Pie
        pie = ttk.Frame(self.cuerpo)
        pie.grid(row=2, column=0, sticky="ew", pady=(16, 0))
        pie.columnconfigure(0, weight=1)

        self.lbl_aviso = ttk.Label(pie, text="Los cambios se aplican al instante y quedan guardados.", foreground=self.pal.muted, font=self.fuentes.ui(9))
        self.lbl_aviso.grid(row=0, column=0, sticky="w")

        ttk.Button(pie, text="Cerrar", bootstyle="primary", command=self.cerrar).grid(row=0, column=1, sticky="e")

    def _construir_secciones(self) -> None:
        c = self.scroll.cuerpo
        pal, f = self.pal, self.fuentes

        # --- SECCIÓN: APARIENCIA / TEMAS ---
        sec_tema = W.Frame(c, bg=pal.bg, pady=4)
        sec_tema.pack(fill="x")

        ttk.Label(sec_tema, text="Apariencia y Tema", font=f.ui(12, "bold")).pack(anchor="w")
        ttk.Label(
            sec_tema,
            text="Elegí el esquema de colores que mejor se adapte a tu entorno de lectura o ensayo:",
            foreground=pal.muted,
            font=f.ui(10),
        ).pack(anchor="w", pady=(2, 10))

        tema_actual = self.app.tema_actual

        for tid, tinfo in TEMAS_DEFINIDOS.items():
            es_activo = tid == tema_actual
            tarjeta = self._crear_tarjeta_tema(sec_tema, tid, tinfo, es_activo)
            tarjeta.pack(fill="x", pady=4, padx=2)
            self._tarjetas_temas[tid] = tarjeta

        # --- SECCIÓN: FUTURAS CONFIGURACIONES (Modular) ---
        ttk.Separator(c).pack(fill="x", pady=18)
        sec_futura = W.Frame(c, bg=pal.bg, pady=4)
        sec_futura.pack(fill="x")

        ttk.Label(sec_futura, text="Lectura y Cifrado", font=f.ui(12, "bold")).pack(anchor="w")
        ttk.Label(
            sec_futura,
            text="Próximamente: tamaño de letra por defecto, preferencia de alteraciones (♯ / ♭) y desplazamiento automático.",
            foreground=pal.muted,
            font=f.ui(10),
            wraplength=480,
            justify="left",
        ).pack(anchor="w", pady=(3, 4))

    def _crear_tarjeta_tema(self, parent, tid: str, tinfo: dict, es_activo: bool) -> W.Frame:
        pal, f = self.pal, self.fuentes
        c_bg, c_card, c_acento = tinfo["muestra"]

        borde_color = pal.primary if es_activo else pal.borde
        fondo_color = mezclar(pal.card, pal.primary, 0.08) if es_activo else pal.card

        card = W.Frame(
            parent,
            bg=fondo_color,
            highlightthickness=2 if es_activo else 1,
            highlightbackground=borde_color,
            cursor="hand2",
            padx=14,
            pady=10,
        )
        card.columnconfigure(1, weight=1)

        # Muestra visual (círculos de colores o paleta preview)
        c_preview = W.Canvas(card, width=44, height=44, bg=c_bg, highlightthickness=1, highlightbackground=pal.borde)
        c_preview.grid(row=0, column=0, rowspan=2, padx=(0, 12), sticky="w")
        # Cuadritos de colores de muestra
        rectangulo_redondeado(c_preview, 2, 2, 42, 42, 8, fill=c_bg, outline="")
        rectangulo_redondeado(c_preview, 10, 10, 34, 34, 6, fill=c_card, outline="")
        c_preview.create_oval(17, 17, 27, 27, fill=c_acento, outline="")

        # Textos: Icono + Nombre
        tit_box = W.Frame(card, bg=fondo_color)
        tit_box.grid(row=0, column=1, sticky="w")

        lbl_icono = W.Label(tit_box, text=tinfo["icono"], font=f.ui(11), bg=fondo_color, fg=pal.fg, cursor="hand2")
        lbl_icono.pack(side="left", padx=(0, 6))

        lbl_nombre = W.Label(tit_box, text=tinfo["nombre"], font=f.ui(11, "bold"), bg=fondo_color, fg=pal.fg, cursor="hand2")
        lbl_nombre.pack(side="left")

        # Descripción
        lbl_desc = W.Label(
            card,
            text=tinfo["descripcion"],
            font=f.ui(9),
            bg=fondo_color,
            fg=pal.muted,
            anchor="w",
            cursor="hand2",
            wraplength=340,
            justify="left",
        )
        lbl_desc.grid(row=1, column=1, sticky="w", pady=(2, 0))

        # Badge de estado (Activo)
        if es_activo:
            lbl_badge = W.Label(
                card,
                text="✓ Activo",
                font=f.ui(9, "bold"),
                bg=mezclar(pal.card, pal.primary, 0.3),
                fg=pal.acorde,
                padx=8,
                pady=3,
                cursor="hand2",
            )
        else:
            lbl_badge = W.Label(
                card,
                text="Seleccionar",
                font=f.ui(9),
                bg=pal.card,
                fg=pal.muted,
                padx=6,
                pady=2,
                cursor="hand2",
            )
        lbl_badge.grid(row=0, column=2, rowspan=2, padx=(8, 0), sticky="e")

        def _seleccionar(_e=None):
            if tid != self.app.tema_actual:
                self.app.aplicar_tema(tid)
                # Reabrir o recrear la configuración con los nuevos colores de paleta
                self.cerrar()
                self.app.abrir_configuracion()

        def _hover_in(_e=None):
            if tid != self.app.tema_actual:
                card.configure(bg=pal.card_hover, highlightbackground=pal.primary)
                for w in (tit_box, lbl_icono, lbl_nombre, lbl_desc):
                    try:
                        w.configure(bg=pal.card_hover)
                    except tk.TclError:
                        pass

        def _hover_out(_e=None):
            if tid != self.app.tema_actual:
                card.configure(bg=pal.card, highlightbackground=pal.borde)
                for w in (tit_box, lbl_icono, lbl_nombre, lbl_desc):
                    try:
                        w.configure(bg=pal.card)
                    except tk.TclError:
                        pass

        for w in (card, tit_box, lbl_icono, lbl_nombre, lbl_desc, lbl_badge, c_preview):
            w.bind("<Button-1>", _seleccionar)
            w.bind("<Enter>", _hover_in, add="+")
            w.bind("<Leave>", _hover_out, add="+")

        return card

    def cerrar(self) -> None:
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
