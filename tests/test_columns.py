import unittest

from ui.columns import construir_unidades, repartir_en_columnas

TEXTO = "\n".join(
    [
        "[Intro]",
        "Am F",
        "",
        "[Verso]",
        "Am    F",
        "Camino por la orilla",
        "C     G",
        "con los zapatos",
        "",
        "Sin acordes aquí",
    ]
)


def textos(col):
    return [t for _, t in col]


class ColumnasTest(unittest.TestCase):
    def test_unidades(self):
        u = construir_unidades(TEXTO)
        tipos = [[t for t, _ in x] for x in u]
        self.assertEqual(
            tipos,
            [
                ["seccion", "acordes"],              # [Intro] + Am F
                ["vacia"],
                ["seccion", "acordes", "letra"],     # [Verso] + primer par
                ["acordes", "letra"],
                ["vacia"],
                ["letra"],
            ],
        )

    def test_una_columna_si_entra(self):
        cols = repartir_en_columnas(construir_unidades(TEXTO), 50)
        self.assertEqual(len(cols), 1)

    def test_acordes_y_verso_nunca_se_separan(self):
        u = construir_unidades(TEXTO)
        for alto in range(1, 14):
            for col in repartir_en_columnas(u, alto):
                for i, (tipo, _) in enumerate(col):
                    if tipo == "acordes" and i + 1 < len(col):
                        self.assertIn(col[i + 1][0], ("letra", "acordes", "vacia", "seccion"))
                    if tipo == "letra" and i > 0:
                        pass
                # el último elemento de una columna nunca es una línea de acordes con verso en la siguiente
            todas = [l for c in repartir_en_columnas(u, alto) for l in c]
            for i, (tipo, _) in enumerate(todas):
                if tipo == "acordes" and i + 1 < len(todas) and todas[i + 1][0] == "letra":
                    # ambos en la misma columna
                    for c in repartir_en_columnas(u, alto):
                        if todas[i] in c:
                            self.assertIn(todas[i + 1], c)

    def test_crea_columna_al_superar_el_alto(self):
        cols = repartir_en_columnas(construir_unidades(TEXTO), 6)
        self.assertGreater(len(cols), 1)
        for c in cols:
            self.assertLessEqual(len(c), 6)

    def test_sin_blancos_al_inicio_ni_al_final(self):
        for alto in range(2, 12):
            for c in repartir_en_columnas(construir_unidades(TEXTO), alto):
                self.assertNotEqual(c[0][0], "vacia")
                self.assertNotEqual(c[-1][0], "vacia")

    def test_se_conservan_todas_las_lineas_con_contenido(self):
        u = construir_unidades(TEXTO)
        esperado = [t for t in TEXTO.split("\n") if t.strip()]
        for alto in range(1, 14):
            obtenido = [t for c in repartir_en_columnas(u, alto) for _, t in c if t.strip()]
            self.assertEqual(obtenido, esperado, alto)

    def test_unidad_mas_alta_que_la_columna(self):
        cols = repartir_en_columnas(construir_unidades("Am\nHola mundo"), 1)
        self.assertEqual(len(cols), 1)
        self.assertEqual(len(cols[0]), 2)

    def test_texto_vacio(self):
        self.assertEqual(repartir_en_columnas(construir_unidades(""), 10), [])


if __name__ == "__main__":
    unittest.main()
