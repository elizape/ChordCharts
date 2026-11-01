"""Detalle de un álbum: sus canciones, con buscador propio (solo dentro del álbum)."""
from __future__ import annotations

import ttkbootstrap as ttk

from ui.components import BarraBusqueda, FilaCancion, ZonaLista, confirmar, crear_combo_orden, pedir_nombre, plural


class VistaAlbum(ttk.Frame):
    def __init__(self, parent, app, album_id: int) -> None:
        super().__init__(parent)
        self.app = app
        self.album_id = album_id
        pal, f = app.pal, app.fuentes
        album = app.servicio.obtener_album(album_id)

        cab = ttk.Frame(self, padding=(32, 24, 32, 4))
        cab.pack(fill="x")
        ttk.Button(cab, text="←  Álbumes", bootstyle="secondary-outline", command=app.mostrar_albumes).pack(side="left")
        centro = ttk.Frame(cab)
        centro.pack(side="left", padx=(20, 0))
        self.titulo = ttk.Label(centro, text=album.nombre, font=f.ui(22, "bold"))
        self.titulo.pack(anchor="w")
        self.resumen = ttk.Label(centro, text="", foreground=pal.muted, font=f.ui(11))
        self.resumen.pack(anchor="w", pady=(2, 0))
        ttk.Button(cab, text="＋  Nueva canción", bootstyle="primary", command=self.nueva_cancion).pack(side="right")
        ttk.Button(cab, text="Renombrar", bootstyle="secondary-outline", command=self.renombrar).pack(side="right", padx=(0, 10))

        barra = ttk.Frame(self, padding=(32, 16, 32, 14))
        barra.pack(fill="x")
        self.busqueda = BarraBusqueda(
            barra, pal, f, "Buscar en este álbum…", self._buscar, inicial=app.busqueda_de_album(album_id)
        )
        self.busqueda.pack(side="left", fill="x", expand=True)
        crear_combo_orden(barra, app.orden_canciones, self._cambiar_orden).pack(side="right", padx=(14, 0))

        self.zona = ZonaLista(self, pal, f)
        self.zona.pack(fill="both", expand=True, padx=24, pady=(0, 16))
        self.refrescar()

    # ------------------------------------------------------------------ datos
    def refrescar(self) -> None:
        app = self.app
        album = app.servicio.obtener_album(self.album_id)
        self.titulo.configure(text=album.nombre)
        n = album.total_canciones
        self.resumen.configure(text="Sin canciones" if n == 0 else plural(n, "canción", "canciones"))
        self.zona.vaciar()
        consulta = self.busqueda.texto
        resultados = app.servicio.listar_canciones(self.album_id, consulta, app.orden_canciones)
        if not resultados:
            if consulta:
                self.zona.mostrar_vacio("Sin resultados", f"Ninguna canción de este álbum coincide con «{consulta}».")
            else:
                self.zona.mostrar_vacio(
                    "Este álbum está vacío", "Añadí la primera canción con su letra y sus acordes.",
                    "＋  Nueva canción", self.nueva_cancion,
                )
            return
        for r in resultados:
            c = r.cancion
            FilaCancion(
                self.zona.cuerpo, app.pal, app.fuentes, r, False,
                al_abrir=lambda c=c: app.mostrar_cancion(c.id, lambda: app.mostrar_album(self.album_id)),
                al_editar=lambda c=c: app.mostrar_formulario(self.album_id, c.id, lambda: app.mostrar_album(self.album_id)),
                al_eliminar=lambda r=r: self.eliminar_cancion(r),
            ).pack(fill="x", padx=8, pady=5)

    # ---------------------------------------------------------------- eventos
    def _buscar(self, texto: str) -> None:
        self.app.guardar_busqueda_de_album(self.album_id, texto)
        self.refrescar()

    def _cambiar_orden(self, orden: str) -> None:
        self.app.orden_canciones = orden
        self.refrescar()

    def nueva_cancion(self) -> None:
        app = self.app
        app.mostrar_formulario(self.album_id, None, lambda: app.mostrar_album(self.album_id))

    def renombrar(self) -> None:
        app = self.app
        album = app.servicio.obtener_album(self.album_id)
        if pedir_nombre(self, app.pal, app.fuentes, "Renombrar álbum", "Nuevo nombre", album.nombre,
                        guardar=lambda n: app.servicio.renombrar_album(self.album_id, n)):
            app.toast.mostrar("Álbum renombrado")
            self.refrescar()

    def eliminar_cancion(self, resultado) -> None:
        app, c = self.app, resultado.cancion
        if confirmar(self, app.pal, app.fuentes, "Eliminar canción",
                     f"¿Eliminar la canción «{c.titulo}»? Esta acción no se puede deshacer."):
            app.servicio.eliminar_cancion(c.id)
            app.toast.mostrar("Canción eliminada", "info")
            self.refrescar()
