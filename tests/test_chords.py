import unittest

from services.chords import (
    clasificar_linea,
    es_linea_de_acordes,
    formatear_semitonos,
    normalizar_semitonos,
    transponer_texto,
)


class DeteccionTest(unittest.TestCase):
    def test_lineas_de_acordes(self):
        for linea in [
            "Am F C G",
            "   Am        F",
            "F#m7  Bb  D/F#  Cadd9  Esus4  G7b9",
            "Am | F | C | G",
            "Am F C G  x2",
            "(Am) F (C)",
            "Intro: Am F C G",
            "[Coro] Am F",
            "Lam  Re7  Sol  Do/Mi",
            "Dom Fa#m",
            "Do Re",
            "C7(b9)  N.C.  G",
        ]:
            self.assertTrue(es_linea_de_acordes(linea), linea)

    def test_lineas_de_letra(self):
        for linea in [
            "Camino por la orilla de la tarde",
            "A mi me gusta el mar",
            "Dame la mano y bailamos",
            "Si",
            "Sol",
            "La",
            "Mi vida",
            "Estribillo",
            "Y dijo que no volvería",
            "",
            "   ",
        ]:
            self.assertFalse(es_linea_de_acordes(linea), repr(linea))

    def test_clasificacion(self):
        self.assertEqual(clasificar_linea(""), "vacia")
        self.assertEqual(clasificar_linea("Am F"), "acordes")
        self.assertEqual(clasificar_linea("[Estribillo]"), "seccion")
        self.assertEqual(clasificar_linea("Verso 1:"), "seccion")
        self.assertEqual(clasificar_linea("Intro: Am F"), "acordes")
        self.assertEqual(clasificar_linea("Hola mundo"), "letra")


class TransposicionTest(unittest.TestCase):
    def test_basica(self):
        self.assertEqual(transponer_texto("Am F C G", 2), "Bm G D A")

    def test_cero_y_octava(self):
        self.assertEqual(transponer_texto("Am F C G", 0), "Am F C G")
        self.assertEqual(transponer_texto("Am F C G", 12), "Am F C G")

    def test_negativa(self):
        self.assertEqual(transponer_texto("C", -1), "B")
        self.assertEqual(transponer_texto("Am", -2), "Gm")

    def test_bemoles_y_sostenidos(self):
        # el acorde se acorta pero el siguiente conserva su columna
        self.assertEqual(transponer_texto("Bb F Gm", 2), "C  G Am")
        self.assertEqual(transponer_texto("F#m D/F# E", 2), "G#m E/G# F#")
        # sin alteraciones en el original, se prefiere la grafía habitual de guitarra
        self.assertEqual(transponer_texto("Am F", 1), "Bbm F#")

    def test_sufijos_y_bajos(self):
        self.assertEqual(transponer_texto("Cmaj7 Dm7b5 G/B Asus4", 5), "Fmaj7 Gm7b5 C/E Dsus4")

    def test_notacion_latina(self):
        self.assertEqual(transponer_texto("Lam Re7 Sol Do/Mi", 2), "Sim Mi7 La  Re/Fa#")
        self.assertEqual(transponer_texto("Do Fa", 1), "Do# Fa#")

    def test_letra_intacta(self):
        texto = "Am        F\nCamino por la orilla\n\nA mi me gusta"
        resultado = transponer_texto(texto, 3).split("\n")
        self.assertEqual(resultado[1], "Camino por la orilla")
        self.assertEqual(resultado[3], "A mi me gusta")

    def test_conserva_columnas(self):
        resultado = transponer_texto("Am        F        C", 2)
        self.assertEqual(resultado, "Bm        G        D")
        # si el acorde se alarga, nunca se pisa con el siguiente
        resultado = transponer_texto("Am F", 1)  # Bbm F#
        self.assertEqual(resultado, "Bbm F#")
        # la canción ya usa sostenidos (F#m), así que se mantienen: A -> A#
        resultado = transponer_texto("A F#m", 1)
        self.assertEqual(resultado, "A# Gm")

    def test_etiqueta_y_separadores(self):
        self.assertEqual(transponer_texto("Intro: Am F | C", 2), "Intro: Bm G | D")
        self.assertEqual(transponer_texto("Am F x2", 2), "Bm G x2")
        self.assertEqual(transponer_texto("(Am) F", 2), "(Bm) G")

    def test_ida_y_vuelta_con_naturales(self):
        original = "Am F C G\nDm E7 C/G Fmaj7\nSi bemol no\nEm B7"
        for n in range(-11, 12):
            ida = transponer_texto(original, n)
            vuelta = transponer_texto(ida, -n)
            # los acordes vuelven a ser los mismos (el espaciado puede haberse ensanchado;
            # la app nunca encadena transposiciones: siempre parte de la letra original)
            self.assertEqual(
                [l.split() for l in vuelta.split("\n")], [l.split() for l in original.split("\n")], n
            )

    def test_texto_vacio(self):
        self.assertEqual(transponer_texto("", 3), "")


class SemitonosTest(unittest.TestCase):
    def test_normalizar(self):
        self.assertEqual(normalizar_semitonos(0), 0)
        self.assertEqual(normalizar_semitonos(12), 0)
        self.assertEqual(normalizar_semitonos(7), -5)
        self.assertEqual(normalizar_semitonos(6), 6)
        self.assertEqual(normalizar_semitonos(-6), 6)
        self.assertEqual(normalizar_semitonos(-5), -5)

    def test_formatear(self):
        self.assertEqual(formatear_semitonos(0), "0")
        self.assertEqual(formatear_semitonos(3), "+3")
        self.assertEqual(formatear_semitonos(-2), "-2")


if __name__ == "__main__":
    unittest.main()
