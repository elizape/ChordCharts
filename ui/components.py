"""Componentes de interfaz reutilizables: scroll, buscador, tarjetas, diálogos y avisos."""
from __future__ import annotations

import tkinter as tk
import zlib
from typing import Callable

import ttkbootstrap as ttk

from ui import tkw as W

from services.library_service import ORDENES, ValidationError
from ui.theme import mezclar


def recortar(texto: str, limite: int) -> str:
    texto = " ".join(texto.split())
    return texto if len(texto) <= limite else texto[: limite - 1].rstrip() + "…"


def formatear_fecha(marca: str) -> str:
    """'2026-10-31 10:42:11.123' -> '31/10/2026'."""
    return f"{marca[8:10]}/{marca[5:7]}/{marca[0:4]}" if len(marca) >= 10 else marca


def plural(n: int, singular: str, plural_: str) -> str:
    return f"{n} {singular if n == 1 else plural_}"


class Debounce:
    """Agrupa llamadas seguidas (por ejemplo, al escribir) en una sola."""

    def __init__(self, widget: tk.Misc, ms: int, funcion: Callable) -> None:
        self.widget, self.ms, self.funcion = widget, ms, funcion
        self._job = None
        widget.bind("<Destroy>", lambda e: self.cancelar() if e.widget is widget else None, add="+")

    def __call__(self, *args) -> None:
        self.cancelar()
        self._job = self.widget.after(self.ms, lambda: self._ejecutar(*args))

    def _ejecutar(self, *args) -> None:
        self._job = None
        self.funcion(*args)

    def cancelar(self) -> None:
        if self._job is not None:
            try:
                self.widget.after_cancel(self._job)
            except tk.TclError:
                pass
            self._job = None


# ============================================================================
# Scroll vertical con barra que solo aparece cuando hace falta
# ============================================================================
class ScrollFrame(W.Frame):
    def __init__(self, parent, pal) -> None:
        super().__init__(parent, bg=pal.bg)
        self.canvas = W.Canvas(self, bg=pal.bg, highlightthickness=0, bd=0, yscrollincrement=18)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self._al_desplazar)
        self.canvas.pack(fill="both", expand=True)
        self.cuerpo = W.Frame(self.canvas, bg=pal.bg)
        self._ventana = self.canvas.create_window((0, 0), window=self.cuerpo, anchor="nw")
        self._observadores: list[Callable[[int], None]] = []
        self._vsb_visible = False
        for w in (self, self.canvas, self.cuerpo):
            w._scroll_owner = self  # type: ignore[attr-defined]
        self.cuerpo.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", self._canvas_cambia)

    def al_cambiar_ancho(self, callback: Callable[[int], None]) -> None:
        self._observadores.append(callback)

    def _canvas_cambia(self, e) -> None:
        self.canvas.itemconfigure(self._ventana, width=e.width)
        for cb in self._observadores:
            cb(e.width)

    def _al_desplazar(self, primero, ultimo) -> None:
        self.vsb.set(primero, ultimo)
        hace_falta = float(primero) > 0.0 or float(ultimo) < 1.0
        if hace_falta and not self._vsb_visible:
            # se superpone al borde derecho: no cambia el ancho del contenido (evita parpadeos)
            self.vsb.place(relx=1.0, rely=0.0, relheight=1.0, anchor="ne")
            self._vsb_visible = True
        elif not hace_falta and self._vsb_visible:
            self.vsb.place_forget()
            self._vsb_visible = False

    def vaciar(self) -> None:
        for hijo in self.cuerpo.winfo_children():
            hijo.destroy()
        self.canvas.yview_moveto(0)

    # -- rueda del mouse: un único manejador global que busca el ScrollFrame bajo el puntero
    @staticmethod
    def instalar_rueda(root: tk.Misc) -> None:
        for secuencia in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            root.bind_all(secuencia, ScrollFrame._rueda, add="+")

    @staticmethod
    def _rueda(evento) -> None:
        try:
            w = evento.widget.winfo_containing(evento.x_root, evento.y_root)
        except (KeyError, tk.TclError, AttributeError):
            return
        while w is not None:
            dueno = getattr(w, "_scroll_owner", None)
            if dueno is not None:
                dueno._desplazar(evento)
                return
            w = getattr(w, "master", None)

    def _desplazar(self, evento) -> None:
        if self.canvas.yview() == (0.0, 1.0):
            return
        if evento.num == 4:
            paso = -1
        elif evento.num == 5:
            paso = 1
        elif evento.delta == 0:
            return
        else:
            paso = -1 if evento.delta > 0 else 1
        self.canvas.yview_scroll(paso * 3, "units")


# ============================================================================
# Buscador con texto de ayuda y botón para limpiar
# ============================================================================
class BarraBusqueda(ttk.Frame):
    def __init__(self, parent, pal, fuentes, ayuda: str, al_cambiar: Callable[[str], None], inicial: str = "") -> None:
        super().__init__(parent)
        self.pal, self.ayuda = pal, ayuda
        self._var = tk.StringVar()
        self._mostrando_ayuda = False
        self._programatico = False
        self._aviso = Debounce(self, 180, al_cambiar)

        self.entry = ttk.Entry(self, textvariable=self._var, font=fuentes.ui(12))
        self.entry.grid(row=0, column=0, sticky="ew", ipady=5)
        self.limpiar = ttk.Button(self, text="✕", width=3, bootstyle="secondary-link", command=self.vaciar)
        self.columnconfigure(0, weight=1)

        self.entry.bind("<FocusIn>", self._foco_dentro)
        self.entry.bind("<FocusOut>", self._foco_fuera)
        self.entry.bind("<Escape>", lambda e: self.vaciar())
        self._var.trace_add("write", self._escribio)

        if inicial:
            self._poner(inicial)
        else:
            self._mostrar_ayuda()

    @property
    def texto(self) -> str:
        return "" if self._mostrando_ayuda else self._var.get().strip()

    def _poner(self, valor: str) -> None:
        self._programatico = True
        self._var.set(valor)
        self._programatico = False
        self._mostrando_ayuda = False
        self.entry.configure(foreground=self.pal.fg)
        self._actualizar_boton()

    def _mostrar_ayuda(self) -> None:
        self._programatico = True
        self._var.set(self.ayuda)
        self._programatico = False
        self._mostrando_ayuda = True
        self.entry.configure(foreground=self.pal.muted)
        self._actualizar_boton()

    def _foco_dentro(self, _e) -> None:
        if self._mostrando_ayuda:
            self._poner("")

    def _foco_fuera(self, _e) -> None:
        if not self._var.get().strip():
            self._mostrar_ayuda()

    def _escribio(self, *_args) -> None:
        if self._programatico or self._mostrando_ayuda:
            return
        self._actualizar_boton()
        self._aviso(self.texto)

    def _actualizar_boton(self) -> None:
        if self.texto:
            self.limpiar.grid(row=0, column=1, padx=(6, 0))
        else:
            self.limpiar.grid_remove()

    def vaciar(self) -> None:
        self._poner("")
        self._aviso.cancelar()
        self.entry.focus_set()
        self._aviso("")


def crear_combo_orden(parent, orden_actual: str, al_cambiar: Callable[[str], None]) -> ttk.Combobox:
    claves = [k for k, _ in ORDENES]
    combo = ttk.Combobox(parent, values=[e for _, e in ORDENES], state="readonly", width=15)
    combo.current(claves.index(orden_actual) if orden_actual in claves else 0)

    def _seleccion(_e) -> None:
        combo.selection_clear()
        al_cambiar(claves[combo.current()])

    combo.bind("<<ComboboxSelected>>", _seleccion)
    return combo


# ============================================================================
# Dibujo
# ============================================================================
def rectangulo_redondeado(canvas: tk.Canvas, x1, y1, x2, y2, r, **kw) -> int:
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return canvas.create_polygon(pts, smooth=True, **kw)


class Monograma(W.Canvas):
    """Cuadrado redondeado con una letra: la 'portada' de cada álbum."""

    def __init__(self, parent, pal, fuentes, texto: str, clave: str, tam: int = 56, fondo: str | None = None) -> None:
        fondo = fondo or pal.card
        super().__init__(parent, width=tam, height=tam, bg=fondo, highlightthickness=0, bd=0)
        acento = pal.acentos[zlib.crc32(clave.encode("utf-8")) % len(pal.acentos)]
        rectangulo_redondeado(self, 1, 1, tam - 1, tam - 1, tam // 4, fill=mezclar(fondo, acento, 0.24), outline="")
        self.create_text(
            tam / 2, tam / 2 + 1, text=texto, fill=mezclar(acento, "#ffffff", 0.38),
            font=fuentes.ui(max(12, tam // 2 - 2), "bold"),
        )


class Enlace(W.Label):
    """Texto clicable de acción (Editar, Eliminar...) que cambia de color al pasar el mouse."""

    def __init__(self, parent, texto: str, comando: Callable, color: str, color_hover: str, bg: str, fuente) -> None:
        super().__init__(parent, text=texto, fg=color, bg=bg, cursor="hand2", font=fuente, padx=4, pady=2)
        self.bind("<Button-1>", lambda e: comando())
        self.bind("<Enter>", lambda e: self.configure(fg=color_hover), add="+")
        self.bind("<Leave>", lambda e: self.configure(fg=color), add="+")


def _pintar(widget: tk.Misc, color: str) -> None:
    if isinstance(widget, (tk.Frame, tk.Label, tk.Canvas)):
        try:
            widget.configure(bg=color)
        except tk.TclError:
            pass
    for hijo in widget.winfo_children():
        _pintar(hijo, color)


class Tarjeta(W.Frame):
    """Contenedor clicable con efecto hover (borde de color y fondo más claro)."""

    def __init__(self, parent, pal) -> None:
        super().__init__(parent, bg=pal.card, highlightthickness=1, highlightbackground=pal.borde,
                         highlightcolor=pal.borde, bd=0)
        self.pal = pal
        self._encima = False

    def activar(self, al_abrir: Callable[[], None]) -> None:
        """Llamar cuando ya están creados todos los hijos."""
        self._enlazar(self, al_abrir)

    def _enlazar(self, w: tk.Misc, al_abrir) -> None:
        if not isinstance(w, Enlace):
            w.bind("<Button-1>", lambda e: al_abrir(), add="+")
            try:
                w.configure(cursor="hand2")
            except tk.TclError:
                pass
        w.bind("<Enter>", self._entra, add="+")
        w.bind("<Leave>", self._sale, add="+")
        for hijo in w.winfo_children():
            self._enlazar(hijo, al_abrir)

    def _entra(self, _e=None) -> None:
        if self._encima:
            return
        self._encima = True
        _pintar(self, self.pal.card_hover)
        self.configure(highlightbackground=self.pal.primary)

    def _sale(self, _e=None) -> None:
        self.after(25, self._verificar_salida)

    def _verificar_salida(self) -> None:
        try:
            x, y = self.winfo_pointerxy()
            w = self.winfo_containing(x, y)
        except (KeyError, tk.TclError):
            w = None
        while w is not None:
            if w is self:
                return
            w = getattr(w, "master", None)
        if self._encima:
            self._encima = False
            _pintar(self, self.pal.card)
            self.configure(highlightbackground=self.pal.borde)


class TarjetaAlbum(Tarjeta):
    def __init__(self, parent, pal, fuentes, album, al_abrir, al_renombrar, al_eliminar) -> None:
        super().__init__(parent, pal)
        self.columnconfigure(1, weight=1)
        inicial = (album.nombre.strip()[:1] or "♪").upper()
        Monograma(self, pal, fuentes, inicial, album.nombre, 60).grid(
            row=0, column=0, rowspan=2, padx=(18, 14), pady=(18, 8), sticky="n")
        W.Label(self, text=recortar(album.nombre, 60), font=fuentes.ui(14, "bold"), bg=pal.card, fg=pal.fg,
                 anchor="w", justify="left", wraplength=170).grid(row=0, column=1, sticky="sw", padx=(0, 16), pady=(18, 0))
        n = album.total_canciones
        texto = "Sin canciones" if n == 0 else plural(n, "canción", "canciones")
        W.Label(self, text=texto, font=fuentes.ui(11), bg=pal.card, fg=pal.muted, anchor="w").grid(
            row=1, column=1, sticky="nw", padx=(0, 16), pady=(2, 8))
        acciones = W.Frame(self, bg=pal.card)
        acciones.grid(row=2, column=0, columnspan=2, sticky="e", padx=(10, 12), pady=(0, 12))
        f = fuentes.ui(10)
        Enlace(acciones, "Renombrar", al_renombrar, pal.muted, pal.fg, pal.card, f).pack(side="left", padx=2)
        Enlace(acciones, "Eliminar", al_eliminar, pal.muted, pal.danger, pal.card, f).pack(side="left", padx=2)
        self.activar(al_abrir)


class FilaCancion(Tarjeta):
    def __init__(self, parent, pal, fuentes, resultado, mostrar_album, al_abrir, al_editar, al_eliminar) -> None:
        super().__init__(parent, pal)
        c = resultado.cancion
        self.columnconfigure(1, weight=1)
        Monograma(self, pal, fuentes, "♪", c.titulo, 46).grid(row=0, column=0, padx=(16, 14), pady=14)

        textos = W.Frame(self, bg=pal.card)
        textos.grid(row=0, column=1, sticky="ew", pady=10)
        W.Label(textos, text=recortar(c.titulo, 70), font=fuentes.ui(13, "bold"), bg=pal.card, fg=pal.fg,
                 anchor="w").pack(fill="x")
        partes = []
        if mostrar_album:
            partes.append(resultado.album_nombre)
        partes.append(f"“{resultado.fragmento}”" if resultado.fragmento else f"Creada el {formatear_fecha(c.creado_en)}")
        W.Label(textos, text="  ·  ".join(partes), font=fuentes.ui(10), bg=pal.card, fg=pal.muted,
                 anchor="w").pack(fill="x", pady=(2, 0))

        col = 2
        if c.semitonos:
            W.Label(self, text=f"Tono {c.semitonos:+d}", font=fuentes.ui(10, "bold"), bg=mezclar(pal.card, pal.primary, 0.2),
                     fg=pal.acorde, padx=9, pady=3).grid(row=0, column=col, padx=(8, 4))
            col += 1
        acciones = W.Frame(self, bg=pal.card)
        acciones.grid(row=0, column=col, padx=(8, 14))
        f = fuentes.ui(10)
        Enlace(acciones, "Editar", al_editar, pal.muted, pal.fg, pal.card, f).pack(side="left", padx=2)
        Enlace(acciones, "Eliminar", al_eliminar, pal.muted, pal.danger, pal.card, f).pack(side="left", padx=2)
        self.activar(al_abrir)


class EstadoVacio(ttk.Frame):
    def __init__(self, parent, pal, fuentes, titulo: str, detalle: str = "", boton: str = "", comando=None) -> None:
        super().__init__(parent)
        interior = ttk.Frame(self)
        interior.place(relx=0.5, rely=0.42, anchor="center")
        c = W.Canvas(interior, width=84, height=84, bg=pal.bg, highlightthickness=0)
        rectangulo_redondeado(c, 2, 2, 82, 82, 22, fill=mezclar(pal.bg, pal.primary, 0.16), outline="")
        c.create_text(42, 43, text="♪", fill=pal.acorde, font=fuentes.ui(34, "bold"))
        c.pack(pady=(0, 18))
        ttk.Label(interior, text=titulo, font=fuentes.ui(17, "bold")).pack()
        if detalle:
            ttk.Label(interior, text=detalle, foreground=pal.muted, font=fuentes.ui(11), justify="center").pack(pady=(6, 0))
        if boton and comando:
            ttk.Button(interior, text=boton, bootstyle="primary", command=comando).pack(pady=(20, 0))


# ============================================================================
# Diálogos modales con el aspecto de la app
# ============================================================================
class _Modal(W.Toplevel):
    def __init__(self, parent, pal, titulo: str, ancho: int = 460) -> None:
        super().__init__(parent)
        self.withdraw()
        self.pal, self._ancho = pal, ancho
        self.title(titulo)
        self.configure(bg=pal.bg, highlightthickness=1, highlightbackground=pal.borde)
        self.transient(parent.winfo_toplevel())
        self.resizable(False, False)
        self.resultado = None
        self.protocol("WM_DELETE_WINDOW", self.cancelar)
        self.bind("<Escape>", lambda e: self.cancelar())
        self.cuerpo = ttk.Frame(self, padding=(26, 24, 26, 22))
        self.cuerpo.pack(fill="both", expand=True)

    def cancelar(self) -> None:
        self.cerrar(None)

    def cerrar(self, resultado) -> None:
        self.resultado = resultado
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()

    def mostrar(self, foco: tk.Misc | None = None):
        self.update_idletasks()
        raiz = self.master.winfo_toplevel()
        w, h = max(self._ancho, self.winfo_reqwidth()), self.winfo_reqheight()
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
        (foco or self).focus_set()
        self.wait_window(self)
        return self.resultado


class _DialogoConfirmar(_Modal):
    def __init__(self, parent, pal, fuentes, titulo, mensaje, texto_ok, peligro) -> None:
        super().__init__(parent, pal, titulo)
        color = pal.danger if peligro else pal.primary
        icono = W.Canvas(self.cuerpo, width=46, height=46, bg=pal.bg, highlightthickness=0)
        icono.create_oval(1, 1, 45, 45, fill=mezclar(pal.bg, color, 0.22), outline="")
        icono.create_text(23, 24, text="!" if peligro else "?", fill=mezclar(color, "#ffffff", 0.3), font=fuentes.ui(20, "bold"))
        icono.grid(row=0, column=0, rowspan=2, sticky="n", padx=(0, 18))
        ttk.Label(self.cuerpo, text=titulo, font=fuentes.ui(15, "bold")).grid(row=0, column=1, sticky="w")
        ttk.Label(self.cuerpo, text=mensaje, wraplength=330, justify="left", foreground=pal.muted,
                  font=fuentes.ui(11)).grid(row=1, column=1, sticky="w", pady=(8, 0))
        botones = ttk.Frame(self.cuerpo)
        botones.grid(row=2, column=0, columnspan=2, sticky="e", pady=(24, 0))
        self.b_cancelar = ttk.Button(botones, text="Cancelar", bootstyle="secondary", command=self.cancelar)
        self.b_cancelar.pack(side="left", padx=(0, 10))
        ttk.Button(botones, text=texto_ok, bootstyle="danger" if peligro else "primary",
                   command=lambda: self.cerrar(True)).pack(side="left")
        self.bind("<Return>", self._enter)

    def _enter(self, _e) -> None:
        w = self.focus_get()
        if isinstance(w, ttk.Button):
            w.invoke()


class _DialogoNombre(_Modal):
    def __init__(self, parent, pal, fuentes, titulo, etiqueta, inicial, guardar, texto_ok) -> None:
        super().__init__(parent, pal, titulo)
        self._guardar = guardar
        ttk.Label(self.cuerpo, text=titulo, font=fuentes.ui(15, "bold")).pack(anchor="w")
        ttk.Label(self.cuerpo, text=etiqueta, foreground=pal.muted, font=fuentes.ui(11)).pack(anchor="w", pady=(14, 6))
        self._var = tk.StringVar(value=inicial)
        self.entry = ttk.Entry(self.cuerpo, textvariable=self._var, font=fuentes.ui(12), width=38)
        self.entry.pack(fill="x", ipady=5)
        self._error = ttk.Label(self.cuerpo, text="", foreground=pal.danger, font=fuentes.ui(10), wraplength=380)
        self._error.pack(anchor="w", pady=(8, 0))
        botones = ttk.Frame(self.cuerpo)
        botones.pack(anchor="e", pady=(18, 0))
        ttk.Button(botones, text="Cancelar", bootstyle="secondary", command=self.cancelar).pack(side="left", padx=(0, 10))
        ttk.Button(botones, text=texto_ok, bootstyle="primary", command=self._enviar).pack(side="left")
        self.entry.bind("<Return>", lambda e: self._enviar())
        self._var.trace_add("write", lambda *a: self._error.configure(text=""))

    def _enviar(self) -> None:
        try:
            self._guardar(self._var.get())
        except ValidationError as error:
            self._error.configure(text=str(error))
            self.entry.focus_set()
            return
        self.cerrar(True)

    def mostrar(self, foco=None):
        self.after(60, lambda: (self.entry.focus_set(), self.entry.selection_range(0, "end"), self.entry.icursor("end")))
        return super().mostrar(self.entry)


def confirmar(parent, pal, fuentes, titulo: str, mensaje: str, texto_ok: str = "Eliminar", peligro: bool = True) -> bool:
    """Alerta de confirmación. El foco inicial está en «Cancelar» para evitar borrados accidentales."""
    dlg = _DialogoConfirmar(parent, pal, fuentes, titulo, mensaje, texto_ok, peligro)
    return bool(dlg.mostrar(dlg.b_cancelar))


def pedir_nombre(parent, pal, fuentes, titulo: str, etiqueta: str, inicial: str,
                 guardar: Callable[[str], object], texto_ok: str = "Guardar") -> bool:
    """Diálogo con un campo de texto. ``guardar`` puede lanzar ValidationError: el mensaje se
    muestra en el mismo diálogo, que sigue abierto. Devuelve True si se guardó."""
    return bool(_DialogoNombre(parent, pal, fuentes, titulo, etiqueta, inicial, guardar, texto_ok).mostrar())


# ============================================================================
# Aviso breve en la parte inferior
# ============================================================================
class Toast:
    def __init__(self, raiz: tk.Misc, pal, fuentes) -> None:
        self.raiz, self.pal, self.fuentes = raiz, pal, fuentes
        self._label: tk.Label | None = None
        self._job = None

    def mostrar(self, texto: str, tipo: str = "ok", ms: int = 2400) -> None:
        color = {"ok": self.pal.success, "info": self.pal.primary, "error": self.pal.danger}.get(tipo, self.pal.success)
        if self._label is None:
            self._label = W.Label(self.raiz, font=self.fuentes.ui(11, "bold"), padx=20, pady=11, bd=0)
        self._label.configure(text=texto, bg=mezclar(self.pal.bg, color, 0.3), fg="#ffffff",
                              highlightthickness=1, highlightbackground=color)
        self._label.place(relx=0.5, rely=1.0, y=-26, anchor="s")
        self._label.lift()
        if self._job is not None:
            self.raiz.after_cancel(self._job)
        self._job = self.raiz.after(ms, self.ocultar)

    def ocultar(self) -> None:
        self._job = None
        if self._label is not None:
            self._label.place_forget()


class ZonaLista(W.Frame):
    """Área desplazable con la posibilidad de mostrar un estado vacío encima."""

    def __init__(self, parent, pal, fuentes) -> None:
        super().__init__(parent, bg=pal.bg)
        self.pal, self.fuentes = pal, fuentes
        self.scroll = ScrollFrame(self, pal)
        self.scroll.pack(fill="both", expand=True)
        self._vacio: EstadoVacio | None = None

    @property
    def cuerpo(self) -> tk.Frame:
        return self.scroll.cuerpo

    def vaciar(self) -> None:
        self.ocultar_vacio()
        self.scroll.vaciar()

    def mostrar_vacio(self, titulo: str, detalle: str = "", boton: str = "", comando=None) -> None:
        self.ocultar_vacio()
        self._vacio = EstadoVacio(self, self.pal, self.fuentes, titulo, detalle, boton, comando)
        self._vacio.place(relx=0, rely=0, relwidth=1, relheight=1)

    def ocultar_vacio(self) -> None:
        if self._vacio is not None:
            self._vacio.destroy()
            self._vacio = None
