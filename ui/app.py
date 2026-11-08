"""Ventana principal y navegación entre pantallas."""
from __future__ import annotations

import tkinter as tk
from typing import Callable

import ttkbootstrap as ttk

from services.library_service import NotFoundError, ORDEN_POR_DEFECTO, ServicioBiblioteca
from ui.album_detail_view import VistaAlbum
from ui.album_list_view import VistaAlbumes
from ui.components import ScrollFrame, Toast
from ui.song_form_view import VistaFormulario
from ui.song_view import VistaCancion
from ui.settings_view import DialogoConfiguracion
from ui.theme import Fuentes, TEMAS_DEFINIDOS, construir_paleta, resolver_ttk_theme


class App:
    def __init__(self, servicio: ServicioBiblioteca) -> None:
        self.servicio = servicio
        self.tema_actual = self.servicio.obtener_tema(por_defecto="oscuro")
        tema_ttk = resolver_ttk_theme(self.tema_actual)
        self.root = ttk.Window(title="Mis canciones", themename=tema_ttk, size=(1180, 760), minsize=(800, 560))
        self.pal = construir_paleta(ttk.Style().colors)
        self.fuentes = Fuentes(self.root)
        self.toast = Toast(self.root, self.pal, self.fuentes)
        ScrollFrame.instalar_rueda(self.root)

        # estado de la sesión (no se persiste)
        self.orden_albumes = ORDEN_POR_DEFECTO
        self.orden_canciones = ORDEN_POR_DEFECTO
        self.busqueda_global = ""
        self._busqueda_album: tuple[int, str] = (0, "")

        self.contenedor = ttk.Frame(self.root)
        self.contenedor.pack(fill="both", expand=True)
        self.vista: tk.Misc | None = None
        self.root.protocol("WM_DELETE_WINDOW", self.salir)
        self._centrar()
        self.mostrar_albumes()

    def _centrar(self) -> None:
        self.root.update_idletasks()
        w, h = self.root.winfo_width(), self.root.winfo_height()
        x = max(0, (self.root.winfo_screenwidth() - w) // 2)
        y = max(0, (self.root.winfo_screenheight() - h) // 3)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    # ------------------------------------------------------- estado compartido
    def busqueda_de_album(self, album_id: int) -> str:
        return self._busqueda_album[1] if self._busqueda_album[0] == album_id else ""

    def guardar_busqueda_de_album(self, album_id: int, texto: str) -> None:
        self._busqueda_album = (album_id, texto)

    # -------------------------------------------------------------- navegación
    def _cambiar_vista(self, fabrica: Callable[[tk.Misc], tk.Misc]) -> None:
        anterior = self.vista
        self.vista = None
        if anterior is not None:
            anterior.destroy()
        self.vista = fabrica(self.contenedor)
        self.vista.pack(fill="both", expand=True)

    def mostrar_albumes(self) -> None:
        self._cambiar_vista(lambda p: VistaAlbumes(p, self))

    def mostrar_album(self, album_id: int) -> None:
        try:
            self._cambiar_vista(lambda p: VistaAlbum(p, self, album_id))
        except NotFoundError as e:
            self.toast.mostrar(str(e), "error")
            self.mostrar_albumes()

    def mostrar_cancion(
        self,
        cancion_id: int,
        volver: Callable[[], None],
        desde_seleccion_rapida: bool = False,
    ) -> None:
        try:
            self._cambiar_vista(
                lambda p: VistaCancion(
                    p, self, cancion_id, volver, desde_seleccion_rapida=desde_seleccion_rapida
                )
            )
        except NotFoundError as e:
            self.toast.mostrar(str(e), "error")
            volver()

    def mostrar_formulario(self, album_id: int, cancion_id: int | None, volver: Callable[[], None]) -> None:
        try:
            album = self.servicio.obtener_album(album_id)
            cancion = self.servicio.obtener_cancion(cancion_id) if cancion_id is not None else None
        except NotFoundError as e:
            self.toast.mostrar(str(e), "error")
            volver()
            return
        self._cambiar_vista(lambda p: VistaFormulario(p, self, album, cancion, volver))

    def abrir_configuracion(self) -> None:
        """Abre el diálogo modal de configuración de la app."""
        DialogoConfiguracion(self.root, self).mostrar()

    def aplicar_tema(self, tema_id: str) -> None:
        """Cambia el tema dinámicamente y refresca la interfaz completa."""
        if tema_id not in TEMAS_DEFINIDOS:
            return
        self.tema_actual = tema_id
        self.servicio.guardar_tema(tema_id)

        temas_ttk = getattr(self.root.style, "theme_names", lambda: [])()
        ttk_nombre = resolver_ttk_theme(tema_id, temas_ttk)

        try:
            self.root.style.theme_use(ttk_nombre)
        except Exception:
            pass

        self.pal = construir_paleta(self.root.style.colors)
        self.toast.actualizar_paleta(self.pal)

        # Refrescar la vista actual para reconstruir los widgets con la nueva paleta
        if isinstance(self.vista, VistaAlbumes):
            self.mostrar_albumes()
        elif isinstance(self.vista, VistaAlbum):
            aid = self.vista.album_id
            self.mostrar_album(aid)
        elif isinstance(self.vista, VistaCancion):
            cid = self.vista.cancion.id
            volver = self.vista.volver
            dsr = getattr(self.vista, "desde_seleccion_rapida", False)
            self.mostrar_cancion(cid, volver, desde_seleccion_rapida=dsr)
        elif self.vista is not None:
            self.mostrar_albumes()

        info = TEMAS_DEFINIDOS[tema_id]
        self.toast.mostrar(f"Tema activado: {info['nombre']}", "ok")

    # ------------------------------------------------------------------ ciclo
    def salir(self) -> None:
        confirmar = getattr(self.vista, "confirmar_salida", None)
        if confirmar is not None and not confirmar():
            return
        self.toast.cancelar()
        self.servicio.cerrar()
        self.root.destroy()

    def ejecutar(self) -> None:
        self.root.mainloop()
