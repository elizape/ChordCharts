"""Pruebas del sistema de configuración, temas y persistencia."""
import tkinter as tk
import unittest

try:
    import ttkbootstrap  # noqa: F401
    HAY_UI = True
except Exception:  # pragma: no cover
    HAY_UI = False

from database.connection import conectar
from services.library_service import ServicioBiblioteca
from ui.theme import TEMAS_DEFINIDOS, es_color_claro, resolver_ttk_theme


class SettingsServiceTest(unittest.TestCase):
    def setUp(self):
        self.svc = ServicioBiblioteca(conectar(":memory:"))

    def tearDown(self):
        self.svc.cerrar()

    def test_obtener_y_guardar_tema(self):
        self.assertEqual(self.svc.obtener_tema(), "oscuro")
        self.svc.guardar_tema("claro")
        self.assertEqual(self.svc.obtener_tema(), "claro")
        self.svc.guardar_tema("grises")
        self.assertEqual(self.svc.obtener_tema(), "grises")

    def test_resolver_temas_definidos(self):
        for tid in ("oscuro", "claro", "grises", "acustico"):
            self.assertIn(tid, TEMAS_DEFINIDOS)
            ttk_nom = resolver_ttk_theme(tid)
            self.assertTrue(isinstance(ttk_nom, str) and len(ttk_nom) > 0)

    def test_deteccion_color_claro(self):
        self.assertTrue(es_color_claro("#ffffff"))
        self.assertTrue(es_color_claro("#f8fafc"))
        self.assertFalse(es_color_claro("#000000"))
        self.assertFalse(es_color_claro("#121212"))


@unittest.skipUnless(HAY_UI, "ttkbootstrap/tkinter no disponibles")
class SettingsUITest(unittest.TestCase):
    def setUp(self):
        from ui.app import App
        from ui.settings_view import DialogoConfiguracion

        self.App = App
        self.DialogoConfiguracion = DialogoConfiguracion

        self.svc = ServicioBiblioteca(conectar(":memory:"))
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
        self.app.root.update_idletasks()
        self.app.root.update()

    def test_cambio_dinamico_de_temas(self):
        self._pump()
        # Cambiar a tema claro
        self.app.aplicar_tema("claro")
        self._pump()
        self.assertEqual(self.app.tema_actual, "claro")
        self.assertEqual(self.svc.obtener_tema(), "claro")
        self.assertTrue(es_color_claro(self.app.pal.bg))

        # Cambiar a tema grises
        self.app.aplicar_tema("grises")
        self._pump()
        self.assertEqual(self.app.tema_actual, "grises")
        self.assertEqual(self.svc.obtener_tema(), "grises")

        # Cambiar a tema oscuro
        self.app.aplicar_tema("oscuro")
        self._pump()
        self.assertEqual(self.app.tema_actual, "oscuro")
        self.assertFalse(es_color_claro(self.app.pal.bg))

    def test_dialogo_configuracion_renderiza(self):
        self._pump()
        dlg = self.DialogoConfiguracion(self.app.root, self.app)
        self.app.root.update_idletasks()
        self.assertEqual(len(dlg._tarjetas_temas), len(TEMAS_DEFINIDOS))
        dlg.cerrar()


if __name__ == "__main__":
    unittest.main()
