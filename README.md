# Resultados UNAM — Datos de admisión a licenciatura (2021–2026)

*[English version below](#english)*

Dataset abierto con los resultados del examen de ingreso a licenciatura de la UNAM, extraídos de las páginas públicas de resultados de la **Dirección General de Administración Escolar (DGAE)**, para las 4 áreas de conocimiento, años 2021 a 2026.

> ⚠️ **Aviso importante**: este es un proyecto independiente, **sin afiliación con la UNAM ni con la DGAE**. Los datos se obtuvieron mediante *web scraping* de páginas públicas de resultados y se ofrecen "tal cual", sin garantía de exactitud. Ver [Aviso legal](#aviso-legal--disclaimer) para más detalle.

## Contenido del repositorio

```
├── data/processed/    # CSV final, limpio y listo para analizar
├── notebooks/         # Análisis exploratorio en Jupyter
├── src/               # Script de extracción (scraper)
├── requirements.txt   # Dependencias de Python
├── LICENSE            # Licencia del código (MIT)
└── LICENSE-DATA.md    # Licencia de los datos (CC BY 4.0)
```

## El dataset

Archivo: `data/processed/aciertos_unam_2021_2026.csv` — **1,027,716 filas**, una por cada folio (aspirante) registrado.

| Columna | Tipo | Descripción |
|---|---|---|
| `folio` | entero | Folio del aspirante (identificador anónimo, no es información personal) |
| `aciertos` | entero (puede ser nulo) | Número de respuestas correctas en el examen. Nulo si el aspirante no presentó |
| `acreditado` | `S` / `N` / `C` / nulo | `S` = seleccionado, `N` = no seleccionado, `C` = cancelado. Nulo cuando no aplica (ver notas) |
| `año` | entero | Año del proceso de admisión (2021–2026) |
| `area` | entero (1–4) | Área de conocimiento según clasificación de la DGAE |
| `carrera` | texto | Carrera solicitada |
| `plantel` | texto | Plantel/facultad solicitada |

**Notas metodológicas:**
- Los folios sin `aciertos` corresponden a aspirantes registrados que no presentaron examen o fueron dados de baja — no se eliminaron para conservar el universo completo de aspirantes registrados.
- Una misma carrera puede aparecer en varios planteles (p. ej. Ingeniería Civil en Facultad de Ingeniería, FES Acatlán y FES Aragón); si buscas comparar por escuela, filtra por `plantel`.
- El corte de aciertos para ser `acreditado = S` se calcula por la propia DGAE sobre el conjunto agregado de planteles de cada carrera, no está en el dataset como columna explícita.

## Cómo usar los datos

```python
import pandas as pd
df = pd.read_csv("data/processed/aciertos_unam_2021_2026.csv")
```

O directamente desde GitHub sin clonar:
```python
url = "https://raw.githubusercontent.com/agn3si/ResultadosUNAM---data/main/data/processed/aciertos_unam_2021_2026.csv"
df = pd.read_csv(url)
```

Para correr el notebook de análisis:
```bash
pip install -r requirements.txt
jupyter notebook notebooks/aciertos_por_carrera.ipynb
```

## Cómo se obtuvieron los datos

El script `src/fetch_and_parse.py` recorre las páginas públicas de resultados de la DGAE (`dgae.unam.mx`) para las 4 áreas y los 6 años disponibles, con una pausa de 1.5 segundos entre solicitudes para no sobrecargar el servidor. El HTML crudo se guarda localmente (no se distribuye en este repositorio) y se procesa a la tabla final en `data/processed/`.

## Cómo citar este dataset

Ver [`CITATION.cff`](CITATION.cff). Formato sugerido:

> Karen Arlet Castrillo Cruz. (2026). *Resultados UNAM — Datos de admisión a licenciatura (2021–2026)* [Conjunto de datos]. GitHub. https://github.com/agn3si/ResultadosUNAM---data

## Licencias

- **Código** (`src/`, notebooks): [MIT License](LICENSE) — úsalo, modifícalo y redistribúyelo libremente, dando crédito.
- **Datos** (`data/processed/`): [CC BY 4.0](LICENSE-DATA.md) — puedes usar, redistribuir y crear trabajos derivados con los datos, siempre dando crédito a este proyecto.

## Aviso legal / Disclaimer

Este proyecto es de autoría independiente y **no está afiliado, patrocinado ni avalado por la UNAM ni por la DGAE**. Los datos provienen de páginas públicamente accesibles de resultados de admisión; no incluyen nombres ni datos personales identificables — solo folios (identificadores administrativos), número de aciertos y estatus de acreditación. El dataset se ofrece "tal cual" (*as-is*), sin garantía de exactitud, integridad o vigencia; pueden existir errores derivados del proceso de extracción automatizada. Para información oficial, consulta siempre las fuentes de la DGAE (dgae.unam.mx).

## Contribuciones

Si encuentras un error en los datos o quieres proponer una mejora al notebook, abre un *issue* o un *pull request*.

---

<a id="english"></a>
## English

Open dataset with UNAM undergraduate admission exam results, scraped from the public results pages of UNAM's **Dirección General de Administración Escolar (DGAE)**, covering all 4 knowledge areas, years 2021–2026.

> ⚠️ **Important notice**: this is an independent project, **not affiliated with UNAM or the DGAE**. Data was obtained via web scraping of public results pages and is provided "as-is", with no guarantee of accuracy. See [Legal notice](#aviso-legal--disclaimer) above for details.

**Dataset**: `data/processed/aciertos_unam_2021_2026.csv` — 1,027,716 rows, one per registered applicant folio. Columns: `folio` (anonymous applicant ID), `aciertos` (correct answers, null if the applicant didn't sit the exam), `acreditado` (`S`=admitted, `N`=not admitted, `C`=cancelled), `año` (year), `area` (knowledge area 1–4), `carrera` (program), `plantel` (campus/school).

**Quick start:**
```python
import pandas as pd
df = pd.read_csv("data/processed/aciertos_unam_2021_2026.csv")
```

**Licensing**: code under [MIT](LICENSE), data under [CC BY 4.0](LICENSE-DATA.md) — attribution required. See [`CITATION.cff`](CITATION.cff) for the suggested citation format.

**Disclaimer**: no personal data is included (only anonymous applicant folios, scores, and admission status). Data is provided as-is, without warranty of accuracy or completeness. For official information, always refer to DGAE's own sources (dgae.unam.mx).
