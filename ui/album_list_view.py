"""Pantalla principal: álbumes del usuario y buscador global de canciones."""
from __future__ import annotations

import ttkbootstrap as ttk

from services.library_service import ValidationError  # noqa: F401  (re-exportado para las vistas)
from ui.components import (
    BarraBusqueda, FilaCancion, TarjetaAlbum, ZonaLista, confirmar, crear_combo_orden, pedir_nombre, plural,
)
from ui.quick_selection import PanelSeleccionRapida

ANCHO_MIN_TARJETA = 300
MAX_COLUMNAS = 4


class VistaAlbumes(ttk.Frame):
    def __init__(self, parent, app) -> None:
        super().__init__(parent)
        self.app = app
        pal, f = app.pal, app.fuentes
        self._tarjetas: list = []
        self._cols = 0

        # Columna derecha: Selección rápida
        self.panel_rapido = PanelSeleccionRapida(self, app, ancho=320)
        self.panel_rapido.pack(side="right", fill="y")

        # Contenedor principal izquierdo: Álbumes y buscador
        izq_frame = ttk.Frame(self)
        izq_frame.pack(side="left", fill="both", expand=True)

        cab = ttk.Frame(izq_frame, padding=(32, 28, 32, 4))
        cab.pack(fill="x")
        izq = ttk.Frame(cab)
        izq.pack(side="left")
        ttk.Label(izq, text="Mis álbumes", font=f.ui(24, "bold")).pack(anchor="w")
        self.resumen = ttk.Label(izq, text="", foreground=pal.muted, font=f.ui(11))
        self.resumen.pack(anchor="w", pady=(2, 0))

        acciones_cab = ttk.Frame(cab)
        acciones_cab.pack(side="right")
        ttk.Button(acciones_cab, text="＋  Nuevo álbum", bootstyle="primary", command=self.nuevo_album).pack(side="left", padx=(0, 8))
        self.btn_config = ttk.Button(
            acciones_cab, text="⚙", bootstyle="secondary-outline", width=3, command=app.abrir_configuracion
        )
        self.btn_config.pack(side="left")

        barra = ttk.Frame(izq_frame, padding=(32, 16, 32, 14))
        barra.pack(fill="x")
        self.busqueda = BarraBusqueda(
            barra, pal, f, "Buscar canciones en todos los álbumes…", self._buscar, inicial=app.busqueda_global
        )
        self.busqueda.pack(side="left", fill="x", expand=True)
        crear_combo_orden(barra, app.orden_albumes, self._cambiar_orden).pack(side="right", padx=(14, 0))

        self.zona = ZonaLista(izq_frame, pal, f)
        self.zona.pack(fill="both", expand=True, padx=24, pady=(0, 16))
        self.zona.scroll.al_cambiar_ancho(self._acomodar)
        self.refrescar()

    # ------------------------------------------------------------------ datos
    def refrescar(self) -> None:
        s = self.app.servicio
        albumes = s.listar_albumes()
        total = sum(a.total_canciones for a in albumes)
        self.resumen.configure(
            text="Todavía no hay álbumes" if not albumes
            else f"{plural(len(albumes), 'álbum', 'álbumes')}  ·  {plural(total, 'canción', 'canciones')}"
        )
        self.zona.vaciar()
        self._tarjetas, self._cols = [], 0
        consulta = self.busqueda.texto
        if consulta:
            self._pintar_resultados(consulta)
        else:
            self._pintar_albumes()
        self.panel_rapido.refrescar()

    def _pintar_albumes(self) -> None:
        s, app = self.app.servicio, self.app
        albumes = s.listar_albumes(app.orden_albumes)
        if not albumes:
            self.zona.mostrar_vacio(
                "Todavía no hay álbumes",
                "Creá tu primer álbum para empezar a guardar canciones con sus acordes.",
                "＋  Crear álbum", self.nuevo_album,
            )
            return
        for a in albumes:
            self._tarjetas.append(TarjetaAlbum(
                self.zona.cuerpo, app.pal, app.fuentes, a,
                al_abrir=lambda a=a: app.mostrar_album(a.id),
                al_renombrar=lambda a=a: self.renombrar_album(a),
                al_eliminar=lambda a=a: self.eliminar_album(a),
            ))
        self._acomodar(self.zona.scroll.canvas.winfo_width())

    def _pintar_resultados(self, consulta: str) -> None:
        app = self.app
        resultados = app.servicio.buscar_canciones(consulta, orden=app.orden_albumes)
        if not resultados:
            self.zona.mostrar_vacio("Sin resultados", f"No hay canciones que coincidan con «{consulta}».")
            return
        ttk.Label(self.zona.cuerpo, text=plural(len(resultados), "canción encontrada", "canciones encontradas"),
                  foreground=app.pal.muted, font=app.fuentes.ui(11)).pack(anchor="w", padx=8, pady=(4, 6))
        for r in resultados:
            c = r.cancion
            FilaCancion(
                self.zona.cuerpo, app.pal, app.fuentes, r, True,
                al_abrir=lambda c=c: app.mostrar_cancion(c.id, app.mostrar_albumes),
                al_editar=lambda c=c: app.mostrar_formulario(c.album_id, c.id, app.mostrar_albumes),
                al_eliminar=lambda r=r: self.eliminar_cancion(r),
            ).pack(fill="x", padx=8, pady=5)

    def _acomodar(self, ancho: int) -> None:
        if not self._tarjetas:
            return
        cols = max(1, min(MAX_COLUMNAS, ancho // ANCHO_MIN_TARJETA))
        if cols == self._cols:
            return
        self._cols = cols
        cuerpo = self.zona.cuerpo
        for k in range(MAX_COLUMNAS + 1):
            cuerpo.columnconfigure(k, weight=1 if k < cols else 0, uniform="alb" if k < cols else "")
        for i, t in enumerate(self._tarjetas):
            t.grid(row=i // cols, column=i % cols, sticky="nsew", padx=8, pady=8)

    # ---------------------------------------------------------------- eventos
    def _buscar(self, texto: str) -> None:
        self.app.busqueda_global = texto
        self.refrescar()

    def _cambiar_orden(self, orden: str) -> None:
        self.app.orden_albumes = orden
        self.refrescar()

    def nuevo_album(self) -> None:
        app = self.app
        if pedir_nombre(self, app.pal, app.fuentes, "Nuevo álbum", "Nombre del álbum", "",
                        guardar=app.servicio.crear_album, texto_ok="Crear álbum"):
            app.toast.mostrar("Álbum creado")
            self.refrescar()

    def renombrar_album(self, album) -> None:
        app = self.app
        if pedir_nombre(self, app.pal, app.fuentes, "Renombrar álbum", "Nuevo nombre", album.nombre,
                        guardar=lambda n: app.servicio.renombrar_album(album.id, n)):
            app.toast.mostrar("Álbum renombrado")
            self.refrescar()

    def eliminar_album(self, album) -> None:
        app = self.app
        n = album.total_canciones
        detalle = ("Está vacío." if n == 0
                   else f"Se eliminará también {'su única canción' if n == 1 else f'sus {n} canciones'}.")
        if confirmar(self, app.pal, app.fuentes, "Eliminar álbum",
                     f"¿Eliminar el álbum «{album.nombre}»? {detalle} Esta acción no se puede deshacer."):
            app.servicio.eliminar_album(album.id)
            app.toast.mostrar("Álbum eliminado", "info")
            self.refrescar()

    def eliminar_cancion(self, resultado) -> None:
        app, c = self.app, resultado.cancion
        if confirmar(self, app.pal, app.fuentes, "Eliminar canción",
                     f"¿Eliminar «{c.titulo}» del álbum «{resultado.album_nombre}»? Esta acción no se puede deshacer."):
            app.servicio.eliminar_cancion(c.id)
            app.toast.mostrar("Canción eliminada", "info")
            self.refrescar()
