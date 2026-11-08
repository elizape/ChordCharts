"""Pruebas de la interfaz de Selección Rápida y Diálogo Selector."""
import tkinter as tk
import unittest

try:
    import ttkbootstrap  # noqa: F401
    HAY_UI = True
except Exception:  # pragma: no cover
    HAY_UI = False

from database.connection import conectar
from services.demo import cargar_demo
from services.library_service import MAX_SELECCION_RAPIDA, ServicioBiblioteca


@unittest.skipUnless(HAY_UI, "ttkbootstrap/tkinter no disponibles")
class QuickSelectionUITest(unittest.TestCase):
    def setUp(self):
        from ui.app import App
        from ui.quick_selection import DialogoSelectorCanciones, PanelSeleccionRapida

        self.App = App
        self.DialogoSelectorCanciones = DialogoSelectorCanciones
        self.PanelSeleccionRapida = PanelSeleccionRapida

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
        self.app.root.update_idletasks()
        self.app.root.update()

    def test_panel_seleccion_rapida_renderiza_y_actualiza(self):
        self._pump()
        vista = self.app.vista
        panel = vista.panel_rapido
        self.assertIsNotNone(panel)
        self.assertEqual(panel.lbl_contador.cget("text"), "0/15")

        # Añadir 2 canciones
        canciones = [r.cancion for r in self.svc.buscar_canciones("")]
        c1, c2 = canciones[0], canciones[1]
        self.svc.agregar_a_seleccion_rapida([c1.id, c2.id])
        panel.refrescar()
        self._pump()

        self.assertEqual(panel.lbl_contador.cget("text"), "2/15")
        self.assertEqual(len(panel._filas), 2)
        self.assertEqual(panel._filas[0].cancion.id, c1.id)
        self.assertEqual(panel._filas[1].cancion.id, c2.id)

        # Reordenar arrastrando
        self.svc.mover_en_seleccion_rapida(0, 1)
        panel.refrescar()
        self._pump()
        self.assertEqual(panel._filas[0].cancion.id, c2.id)
        self.assertEqual(panel._filas[1].cancion.id, c1.id)

        # Eliminar una
        panel.eliminar_cancion(0, c2)
        self._pump()
        self.assertEqual(panel.lbl_contador.cget("text"), "1/15")
        self.assertEqual(len(panel._filas), 1)

    def test_dialogo_selector_navegacion_y_seleccion_multiple(self):
        self._pump()
        albumes_con_canciones = [a for a in self.svc.listar_albumes() if a.total_canciones > 0]
        a1 = albumes_con_canciones[0]
        a2 = albumes_con_canciones[1]

        c_a1 = self.svc.listar_canciones(a1.id)
        c_a2 = self.svc.listar_canciones(a2.id)

        dlg = self.DialogoSelectorCanciones(
            self.app.root,
            pal=self.app.pal,
            fuentes=self.app.fuentes,
            servicio=self.svc,
            modo="multiple",
        )
        self.app.root.update_idletasks()

        # Vista inicial: Álbumes
        self.assertIsNone(dlg._album_activo)

        # Navegar al Álbum 1
        dlg._mostrar_canciones(a1)
        self.assertEqual(dlg._album_activo.id, a1.id)

        # Seleccionar la primera canción del Álbum 1
        id_tema1 = c_a1[0].cancion.id
        dlg._seleccionadas.add(id_tema1)
        dlg._actualizar_pie()
        self.assertIn(id_tema1, dlg._seleccionadas)

        # Retroceder a la vista de Álbumes con el botón de retroceso
        dlg._mostrar_albumes()
        self.assertIsNone(dlg._album_activo)
        # La selección se debe conservar
        self.assertIn(id_tema1, dlg._seleccionadas)

        # Navegar al Álbum 2
        dlg._mostrar_canciones(a2)
        self.assertEqual(dlg._album_activo.id, a2.id)

        # Seleccionar la primera canción del Álbum 2
        id_tema2 = c_a2[0].cancion.id
        dlg._seleccionadas.add(id_tema2)
        dlg._actualizar_pie()

        # Ambas canciones deben estar seleccionadas
        self.assertEqual(dlg._seleccionadas, {id_tema1, id_tema2})
        self.assertEqual(dlg.btn_aceptar.cget("text"), "Añadir (2)")

        dlg.destroy()

    def test_vista_cancion_columna_rapida_solo_cuando_accede_desde_ella(self):
        self._pump()
        cancion = self.svc.buscar_canciones("")[0].cancion

        # 1. Acceso normal desde Álbum -> NO debe tener panel_rapido
        self.app.mostrar_cancion(cancion.id, self.app.mostrar_albumes, desde_seleccion_rapida=False)
        self._pump()
        vista = self.app.vista
        self.assertFalse(vista.desde_seleccion_rapida)
        self.assertIsNone(vista.panel_rapido)
        self.assertFalse(hasattr(vista, "btn_toggle_panel"))

        # 2. Acceso desde Selección Rápida -> SÍ debe tener panel_rapido y botón de toggle
        self.app.mostrar_cancion(cancion.id, self.app.mostrar_albumes, desde_seleccion_rapida=True)
        self._pump()
        vista = self.app.vista
        self.assertTrue(vista.desde_seleccion_rapida)
        self.assertIsNotNone(vista.panel_rapido)
        self.assertTrue(vista._panel_desplegado)

        # Probar colapsar
        vista._toggle_panel()
        self._pump()
        self.assertFalse(vista._panel_desplegado)

        # Probar desplegar
        vista._toggle_panel()
        self._pump()
        self.assertTrue(vista._panel_desplegado)

    def test_vista_cancion_boton_agregar_y_quitar_seleccion_rapida(self):
        self._pump()
        cancion = self.svc.buscar_canciones("")[0].cancion
        self.svc.vaciar_seleccion_rapida()

        self.app.mostrar_cancion(cancion.id, self.app.mostrar_albumes, desde_seleccion_rapida=False)
        self._pump()
        vista = self.app.vista

        # Inicialmente no está en la lista rápida
        self.assertEqual(vista.btn_fav.cget("text"), "＋ A lista")

        # Agregar mediante el botón
        vista._toggle_lista()
        self._pump()
        self.assertEqual(vista.btn_fav.cget("text"), "✓ En lista")
        self.assertIn(cancion.id, self.svc.obtener_ids_seleccion_rapida())

        # Quitar mediante el botón
        vista._toggle_lista()
        self._pump()
        self.assertEqual(vista.btn_fav.cget("text"), "＋ A lista")
        self.assertNotIn(cancion.id, self.svc.obtener_ids_seleccion_rapida())


if __name__ == "__main__":
    unittest.main()
