import unittest

from database.connection import conectar
from services.library_service import NotFoundError, ServicioBiblioteca, ValidationError


class ServicioTest(unittest.TestCase):
    def setUp(self):
        self.svc = ServicioBiblioteca(conectar(":memory:"))

    def tearDown(self):
        self.svc.cerrar()

    # ---------------------------------------------------------------- álbumes
    def test_crear_listar_renombrar_eliminar_album(self):
        a = self.svc.crear_album("  Rock   nacional ")
        self.assertEqual(a.nombre, "Rock nacional")
        self.assertEqual([x.nombre for x in self.svc.listar_albumes()], ["Rock nacional"])
        a = self.svc.renombrar_album(a.id, "Folklore")
        self.assertEqual(a.nombre, "Folklore")
        self.svc.eliminar_album(a.id)
        self.assertEqual(self.svc.listar_albumes(), [])

    def test_album_nombre_vacio(self):
        for nombre in ("", "   "):
            with self.assertRaises(ValidationError):
                self.svc.crear_album(nombre)

    def test_album_duplicado_ignora_mayusculas_y_tildes(self):
        self.svc.crear_album("Música")
        for repetido in ("Música", "música", "MUSICA", "  musica "):
            with self.assertRaises(ValidationError):
                self.svc.crear_album(repetido)

    def test_renombrar_a_si_mismo_y_a_otro_existente(self):
        a = self.svc.crear_album("Uno")
        b = self.svc.crear_album("Dos")
        self.assertEqual(self.svc.renombrar_album(a.id, "UNO").nombre, "UNO")  # cambia mayúsculas
        with self.assertRaises(ValidationError):
            self.svc.renombrar_album(b.id, "uno")

    def test_album_inexistente(self):
        with self.assertRaises(NotFoundError):
            self.svc.obtener_album(999)
        with self.assertRaises(NotFoundError):
            self.svc.eliminar_album(999)

    # -------------------------------------------------------------- canciones
    def test_album_con_cero_o_muchas_canciones(self):
        a = self.svc.crear_album("A")
        self.assertEqual(self.svc.obtener_album(a.id).total_canciones, 0)
        for i in range(5):
            self.svc.crear_cancion(a.id, f"Tema {i}", "")
        self.assertEqual(self.svc.obtener_album(a.id).total_canciones, 5)

    def test_crear_y_editar_cancion(self):
        a = self.svc.crear_album("A")
        c = self.svc.crear_cancion(a.id, "  Mi   canción ", "Am  F\r\nHola\t mundo   \r\n\r\n")
        self.assertEqual(c.titulo, "Mi canción")
        self.assertEqual(c.letra, "Am  F\nHola     mundo")  # CRLF -> LF, tabs -> espacios, sin cola
        c2 = self.svc.actualizar_cancion(c.id, "Otro", "G C")
        self.assertEqual((c2.titulo, c2.letra), ("Otro", "G C"))
        self.assertGreaterEqual(c2.actualizado_en, c.actualizado_en)

    def test_titulo_vacio(self):
        a = self.svc.crear_album("A")
        with self.assertRaises(ValidationError):
            self.svc.crear_cancion(a.id, "   ", "letra")
        c = self.svc.crear_cancion(a.id, "ok", "")
        with self.assertRaises(ValidationError):
            self.svc.actualizar_cancion(c.id, "", "x")

    def test_titulos_repetidos_se_permiten(self):
        a = self.svc.crear_album("A")
        self.svc.crear_cancion(a.id, "Igual", "")
        self.svc.crear_cancion(a.id, "Igual", "")
        self.assertEqual(self.svc.obtener_album(a.id).total_canciones, 2)

    def test_borrar_album_borra_sus_canciones(self):
        a = self.svc.crear_album("A")
        b = self.svc.crear_album("B")
        c1 = self.svc.crear_cancion(a.id, "uno", "")
        self.svc.crear_cancion(a.id, "dos", "")
        c3 = self.svc.crear_cancion(b.id, "tres", "")
        self.assertEqual(self.svc.eliminar_album(a.id), 2)
        with self.assertRaises(NotFoundError):
            self.svc.obtener_cancion(c1.id)
        self.assertEqual(self.svc.obtener_cancion(c3.id).titulo, "tres")

    def test_eliminar_cancion(self):
        a = self.svc.crear_album("A")
        c = self.svc.crear_cancion(a.id, "uno", "")
        self.svc.eliminar_cancion(c.id)
        self.assertEqual(self.svc.listar_canciones(a.id), [])

    def test_crear_cancion_en_album_inexistente(self):
        with self.assertRaises(NotFoundError):
            self.svc.crear_cancion(42, "x", "")

    # ----------------------------------------------------------- transposición
    def test_transposicion_se_guarda_y_la_letra_original_no_cambia(self):
        a = self.svc.crear_album("A")
        c = self.svc.crear_cancion(a.id, "T", "Am F\nHola")
        self.assertEqual(c.semitonos, 0)
        self.assertEqual(self.svc.guardar_transposicion(c.id, 3), 3)
        c = self.svc.obtener_cancion(c.id)
        self.assertEqual((c.semitonos, c.letra), (3, "Am F\nHola"))
        self.assertEqual(self.svc.guardar_transposicion(c.id, 12), 0)
        self.assertEqual(self.svc.guardar_transposicion(c.id, 8), -4)

    def test_editar_no_pierde_la_transposicion(self):
        a = self.svc.crear_album("A")
        c = self.svc.crear_cancion(a.id, "T", "Am")
        self.svc.guardar_transposicion(c.id, 2)
        c = self.svc.actualizar_cancion(c.id, "T2", "Am F")
        self.assertEqual(c.semitonos, 2)

    # ------------------------------------------------------------------ orden
    def test_orden_por_fecha_y_alfabetico(self):
        for nombre in ("Zeta", "álbum", "Beta"):
            self.svc.crear_album(nombre)
        nombres = lambda orden: [a.nombre for a in self.svc.listar_albumes(orden)]
        self.assertEqual(nombres("antiguos"), ["Zeta", "álbum", "Beta"])
        self.assertEqual(nombres("recientes"), ["Beta", "álbum", "Zeta"])
        self.assertEqual(nombres("az"), ["álbum", "Beta", "Zeta"])  # «á» se ordena como «a»
        self.assertEqual(nombres("za"), ["Zeta", "Beta", "álbum"])

    def test_orden_de_canciones(self):
        a = self.svc.crear_album("A")
        for t in ("Cielo", "Árbol", "Brisa"):
            self.svc.crear_cancion(a.id, t, "")
        titulos = lambda orden: [r.cancion.titulo for r in self.svc.listar_canciones(a.id, orden=orden)]
        self.assertEqual(titulos("antiguos"), ["Cielo", "Árbol", "Brisa"])
        self.assertEqual(titulos("recientes"), ["Brisa", "Árbol", "Cielo"])
        self.assertEqual(titulos("az"), ["Árbol", "Brisa", "Cielo"])
        self.assertEqual(titulos("za"), ["Cielo", "Brisa", "Árbol"])

    # --------------------------------------------------------------- búsqueda
    def _escenario_busqueda(self):
        rock = self.svc.crear_album("Rock")
        folk = self.svc.crear_album("Folklore")
        self.svc.crear_cancion(rock.id, "Camino al mar", "Am F\nCaminando junto al río")
        self.svc.crear_cancion(rock.id, "Noche", "Am F\nLa luna se esconde")
        self.svc.crear_cancion(folk.id, "Zamba del río", "G D\nVa el agua cantando")
        return rock, folk

    def test_busqueda_global_en_todos_los_albumes(self):
        self._escenario_busqueda()
        r = self.svc.buscar_canciones("rio")  # sin tilde: encuentra «río»
        self.assertEqual(sorted(x.cancion.titulo for x in r), ["Camino al mar", "Zamba del río"])
        self.assertEqual({x.album_nombre for x in r}, {"Rock", "Folklore"})

    def test_busqueda_dentro_de_un_album(self):
        rock, folk = self._escenario_busqueda()
        r = self.svc.listar_canciones(rock.id, "rio")
        self.assertEqual([x.cancion.titulo for x in r], ["Camino al mar"])
        r = self.svc.listar_canciones(folk.id, "luna")
        self.assertEqual(r, [])

    def test_busqueda_por_titulo_y_varias_palabras(self):
        self._escenario_busqueda()
        self.assertEqual([x.cancion.titulo for x in self.svc.buscar_canciones("NOCHE")], ["Noche"])
        self.assertEqual([x.cancion.titulo for x in self.svc.buscar_canciones("luna esconde")], ["Noche"])
        self.assertEqual(self.svc.buscar_canciones("luna rio"), [])

    def test_busqueda_ignora_las_lineas_de_acordes(self):
        self._escenario_busqueda()
        self.assertEqual(self.svc.buscar_canciones("F"), [])  # «F» solo aparece en líneas de acordes

    def test_fragmento(self):
        self._escenario_busqueda()
        (r,) = self.svc.buscar_canciones("agua")
        self.assertEqual(r.fragmento, "Va el agua cantando")
        (r,) = self.svc.buscar_canciones("zamba")  # coincide el título: no hace falta fragmento
        self.assertEqual(r.fragmento, "")

    def test_consulta_vacia_devuelve_todo(self):
        self._escenario_busqueda()
        self.assertEqual(len(self.svc.buscar_canciones("")), 3)

    # -------------------------------------------------------- selección rápida
    def test_seleccion_rapida_flujo_completo(self):
        a = self.svc.crear_album("Álbum A")
        c1 = self.svc.crear_cancion(a.id, "Canción 1", "Letra 1")
        c2 = self.svc.crear_cancion(a.id, "Canción 2", "Letra 2")
        c3 = self.svc.crear_cancion(a.id, "Canción 3", "Letra 3")

        # Inicialmente vacía
        self.assertEqual(self.svc.listar_seleccion_rapida(), [])

        # Agregar canciones (múltiples)
        res = self.svc.agregar_a_seleccion_rapida([c1.id, c2.id])
        self.assertEqual([r.cancion.id for r in res], [c1.id, c2.id])
        self.assertEqual(res[0].album_nombre, "Álbum A")

        # Reordenar (mover de 1 a 0)
        res = self.svc.mover_en_seleccion_rapida(1, 0)
        self.assertEqual([r.cancion.id for r in res], [c2.id, c1.id])

        # Reemplazar canción en pos 1 por c3
        res = self.svc.reemplazar_en_seleccion_rapida(1, c3.id)
        self.assertEqual([r.cancion.id for r in res], [c2.id, c3.id])

        # Eliminar una
        res = self.svc.eliminar_de_seleccion_rapida(0)
        self.assertEqual([r.cancion.id for r in res], [c3.id])

        # Vaciar lista
        self.svc.vaciar_seleccion_rapida()
        self.assertEqual(self.svc.listar_seleccion_rapida(), [])

    def test_seleccion_rapida_limite_15_canciones(self):
        a = self.svc.crear_album("Álbum Límite")
        canciones = [self.svc.crear_cancion(a.id, f"Tema {i}", f"Letra {i}") for i in range(16)]

        # Añadir 15 canciones permitidas
        self.svc.agregar_a_seleccion_rapida([c.id for c in canciones[:15]])
        self.assertEqual(len(self.svc.listar_seleccion_rapida()), 15)

        # Intentar añadir una más debe fallar
        with self.assertRaises(ValidationError):
            self.svc.agregar_a_seleccion_rapida([canciones[15].id])

    def test_seleccion_rapida_cascada_al_eliminar_cancion(self):
        a = self.svc.crear_album("Álbum Cascada")
        c1 = self.svc.crear_cancion(a.id, "Tema A", "")
        c2 = self.svc.crear_cancion(a.id, "Tema B", "")
        self.svc.agregar_a_seleccion_rapida([c1.id, c2.id])
        self.assertEqual(len(self.svc.listar_seleccion_rapida()), 2)

        # Al eliminar c1 de la base de datos, se elimina de selección rápida
        self.svc.eliminar_cancion(c1.id)
        restantes = self.svc.listar_seleccion_rapida()
        self.assertEqual(len(restantes), 1)
        self.assertEqual(restantes[0].cancion.id, c2.id)



if __name__ == "__main__":
    unittest.main()
