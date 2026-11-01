# Mis canciones

App de escritorio para guardar canciones con sus acordes, organizadas en álbumes.
Python + **ttkbootstrap** (tema *Cyborg*) + **SQLite**. Corre en local: no hay servidor aparte,
todo se guarda en un único archivo `songs.db` junto a la aplicación.

## Instalación (Zorin OS / Debian / Ubuntu)

```bash
sudo apt install python3-tk          # Tk para Python (si todavía no lo tenés)
cd songapp
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py                       # abre la app (crea songs.db la primera vez)
python main.py --demo                # idem, y si la base está vacía carga álbumes de ejemplo
python main.py --db ~/canciones.db   # usar otra ubicación para la base de datos
```

Si el venv no ve Tk, creá el entorno con `python3 -m venv --system-site-packages .venv`.

## Qué hace

| | |
|---|---|
| **Álbumes** | Crear, renombrar y eliminar. Nombres sin duplicados (ignora mayúsculas y tildes). |
| **Canciones** | Cada álbum guarda de 0 a N canciones. Al abrir un álbum ves sus canciones; en cada una se puede **Editar** y **Eliminar**. |
| **Alertas** | Antes de eliminar un álbum (avisa cuántas canciones se borran con él) o una canción. El foco inicial queda en «Cancelar». |
| **Nueva canción** | Pantalla propia con título y un único campo de letra donde los acordes se escriben **encima del verso**. |
| **Lectura** | Al clickear una canción se abre en **columnas dinámicas**: se llena cada columna a lo alto de la ventana y, si el contenido no entra, se crea otra. Las columnas quedan centradas. Una línea de acordes nunca se separa del verso que tiene debajo. |
| **Transposición** | Botones **− / +** (en semitonos) en la pantalla de lectura. La última transposición **se guarda** por canción; la letra original no se modifica y «Original» vuelve a 0. |
| **Orden** | Más recientes, más antiguos, A→Z, Z→A (álbumes y canciones). |
| **Búsqueda** | En la pantalla principal busca canciones en **todos** los álbumes; dentro de un álbum, solo en **ese** álbum. Busca en título y letra, sin distinguir mayúsculas ni tildes, e ignora las líneas de acordes. |

## Cómo escribir los acordes

```
[Estribillo]
C            G
Vuela, vuela, pequeña luz
Am             D7
que la noche es larga
```

- Una línea es «de acordes» cuando **todas** sus palabras son acordes: `Am`, `F#m7`, `Bb`, `D/F#`, `Cadd9`, `Gsus4`…
  También notación latina (`Lam`, `Re7`, `Sol`, `Do/Mi`) y separadores (`|`, `x2`, `N.C.`).
- Se admite una etiqueta al comienzo: `Intro: Am F C G` o `[Coro] Am F`.
- Al transponer se conserva la columna de cada acorde, así siguen alineados con la sílaba.
  Las alteraciones se escriben con sostenidos o bemoles según lo que ya use la canción.
- Límite conocido: una línea que sea **una sola** palabra latina sin alteración ni sufijo
  (`Sol`, `La`, `Si`, `Mi`) se toma como letra, porque son palabras comunes. Con otro acorde en la
  línea, o con sufijo (`Sol7`), se detecta bien.

## Estructura

```
main.py                  arranque (--db, --demo)
database/                conexión SQLite + esquema, repositorios (único lugar con SQL)
models/entities.py       Album, Cancion
services/
  library_service.py     validaciones, orden, búsqueda, transposición guardada
  chords.py              detección de líneas de acordes y transposición
  demo.py                datos de ejemplo
ui/                      vistas ttkbootstrap (álbumes, detalle, formulario, lectura) y componentes
tests/                   unittest
```

## Pruebas

```bash
python -m unittest discover -s tests -t .
xvfb-run -a python -m unittest tests.test_ui_smoke   # opcional: recorre la interfaz sin pantalla (requiere xvfb)
```

La interfaz fue probada con ttkbootstrap 1.10.1 y 2.2.6 sobre Python 3.12. El tema pedido, *cyborg*, figura como nombre
«legacy» en ttkbootstrap 2.x (funciona, con un aviso interno) y se retiraría en la 3.0; por eso `requirements.txt` fija `<3`.
# ChordCharts
