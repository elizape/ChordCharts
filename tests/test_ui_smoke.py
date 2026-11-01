"""Prueba de humo de la interfaz: recorre todas las pantallas y comprueba que no fallen.

Se omite sola si no hay Tk o no hay pantalla (por ejemplo en un servidor sin entorno gráfico).
En Linux sin pantalla:  xvfb-run -a python -m unittest tests.test_ui_smoke
"""
import time
import tkinter as tk
import unittest

try:
    import ttkbootstrap  # noqa: F401
    HAY_UI = True
except Exception:  # pragma: no cover
    HAY_UI = False

from database.connection import conectar
from services.demo import cargar_demo
from services.library_service import ServicioBiblioteca


@unittest.skipUnless(HAY_UI, "ttkbootstrap/tkinter no disponibles")
class UISmokeTest(unittest.TestCase):
    def setUp(self):
        from ui.app import App

        self.svc = ServicioBiblioteca(conectar(":memory:"))
        cargar_demo(self.svc)
        try:
            self.app = App(self.svc)
        except tk.TclError as e:
            self.skipTest(f"sin pantalla disponible: {e}")

    def tearDown(self):
        try:
            self.app.root.destroy()
        except Exception:
            pass

    def _pump(self):
        # la vista de lectura agrupa los redibujados con un retardo corto: hay que dejar pasar el tiempo
        for _ in range(6):
            self.app.root.update_idletasks()
            self.app.root.update()
            time.sleep(0.03)

    def test_recorrido_de_pantallas(self):
        app = self.app
        self._pump()
        album = self.svc.listar_albumes()[0]
        cancion = self.svc.buscar_canciones("")[0].cancion
        for abrir in (
            lambda: app.mostrar_album(album.id),
            lambda: app.mostrar_cancion(cancion.id, app.mostrar_albumes),
            lambda: app.mostrar_formulario(album.id, cancion.id, app.mostrar_albumes),
            lambda: app.mostrar_formulario(album.id, None, app.mostrar_albumes),
            app.mostrar_albumes,
        ):
            abrir()
            self._pump()

    def test_lectura_dibuja_columnas_y_guarda_tono(self):
        app = self.app
        cancion = next(r.cancion for r in self.svc.buscar_canciones("") if r.cancion.titulo == "Luciérnagas")
        app.root.geometry("1180x760")
        app.mostrar_cancion(cancion.id, app.mostrar_albumes)
        self._pump()
        vista = app.vista
        self.assertGreater(len(vista.canvas.find_all()), 20)  # se dibujó la letra
        vista._cambiar(2)
        self._pump()
        self.assertEqual(self.svc.obtener_cancion(cancion.id).semitonos, 2)


if __name__ == "__main__":
    unittest.main()
