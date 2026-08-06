# Challenge 03 - Inteligencia Geo-Temporal y de Redes

Solucion reproducible del taller de la Maestria en Ciencia de los Datos de EAFIT. El proyecto integra analisis geoespacial, estacionariedad, procesamiento de senales, grafos, causalidad de Granger y ARIMAX sobre los activos de TechLogistics S.A.

Nota de numeracion: el PDF fuente del docente (`Lecture_03_Challenge.pdf`) usa "Challenge 02" en su encabezado interno; este repositorio se normalizo a "Challenge 03" en todos sus propios entregables (README, CHECKLIST, notebook e informe).

## Integrantes

| Nombre | Cedula |
|---|---|
| Juan Jose Restrepo | 1193082063 |
| Luis Felipe Quesada | 1005755239 |
| Andres Velez Rendon | 1001371042 |

## Entregables

- `notebooks/01_inteligencia_geo_temporal_redes.ipynb`: notebook ejecutado y documentado. Cada celda de codigo esta precedida por una explicacion Markdown.
- `output/pdf/informe_tecnico.pdf`: informe ejecutivo con las preguntas de negocio y de autoevaluacion.
- `output/figures/`: evidencia grafica en formato PNG.
- `output/interactive/mapa_agro_ndvi.html`: mapa geoespacial interactivo sin necesidad de token Mapbox.
- `output/tables/`: resultados tabulares en CSV.
- `output/metrics.json`: metricas completas para auditoria.
- `src/workshop_analysis.py`: implementacion reutilizable del analisis.
- `src/report_builder.py`: constructor del informe PDF.
- `CHECKLIST.md`: trazabilidad entre cada requisito y su evidencia.
- [`AUDITORIA.md`](AUDITORIA.md): auditoria tecnica de la entrega (hallazgos H1-H7 y plan de correccion).
- [`DECLARACION_USO_IA.md`](DECLARACION_USO_IA.md): declaracion de uso de inteligencia artificial en este repositorio.
- `tests/`: pruebas minimas de estructura de la entrega.
- `.github/workflows/ci.yml`: integracion continua (instala `requirements-lock.txt` y corre `tests/`).

Los cuatro CSV y los tres PDF de referencia se conservan sin modificaciones en la raiz del proyecto.

## Hallazgos principales

- No se detecta un cluster espacial estadisticamente concluyente de NDVI bajo: los seis clusters explican cerca de 0.4% de su variacion y la prueba por permutaciones no rechaza aleatoriedad espacial al 5%.
- `Ener_1`, `Ener_2`, `Ener_3`, `Ener_5`, `Ener_6` y `Ener_7` son I(1) segun ADF y se diferencian antes del ARIMAX. `Ener_5` es compatible con random walk con drift positivo.
- El ruido de `Ener_4` es de banda ancha; el 90% de la potencia espectral excedente queda aproximadamente entre 0.004 y 0.465 ciclos por registro.
- El Butterworth de orden 4 reduce el RMSE de reconstruccion de `Agro_3` de 3.34 a 0.85, pero no mejora el experimento predictivo sin fuga temporal. Se separan deliberadamente reconstruccion offline y prediccion desplegable.
- El grafo dirigido exigido es bipartito y solo contiene aristas Source -> Target; por ello todos los betweenness dirigidos son cero. El nodo 119 es el cuello de botella por trafico y por betweenness en la sensibilidad no dirigida.
- No hay evidencia de Granger entre `Ener_10` y `Ener_9` al rezago seleccionado, ni mejora del AIC al agregar centralidad al ARIMAX.
- La hipotesis narrativa de interrupcion/temperatura anomala del nodo 214 no queda respaldada por estos CSV; el informe la trata como riesgo de negocio, no como hecho observado.

## Reproduccion

Desde la raiz del proyecto, en Linux o macOS:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python run_pipeline.py
```

En Windows, active el entorno con `.\.venv\Scripts\Activate.ps1` en vez de `source .venv/bin/activate`.

El comando regenera tablas, figuras, mapa interactivo, metricas, informe y notebook. Para validar la estructura basica:

```bash
python -m unittest discover -s tests -v
```

### Entorno de referencia (determinismo)

`requirements.txt` fija techos de version compatibles entre si (en particular `pandas<3` y `plotly<6`, ver `AUDITORIA.md` hallazgo H5/H7). Para reproducir exactamente el entorno usado para generar los artefactos de este repositorio, use `requirements-lock.txt` en vez de `requirements.txt`:

```bash
python -m pip install -r requirements-lock.txt
```

`requirements-lock.txt` es la salida de `pip freeze` sobre un venv limpio con Python 3.13.11. Se verifico que dos ejecuciones independientes de `python run_pipeline.py` en venvs limpios separados, con ese entorno congelado, producen un `output/metrics.json` identico campo a campo (0 diferencias en 267 campos hoja comparados de forma recursiva). El detalle de esa prueba de determinismo esta en `AUDITORIA.md`.

## Decisiones metodologicas

- El eje temporal no tiene sello de tiempo ni frecuencia de muestreo. Por eso las frecuencias se reportan en ciclos por registro y no en Hz.
- El umbral critico del precio spot no esta definido en el enunciado; se operacionaliza como el percentil 95 y queda documentado.
- El mapa usa `scatter_mapbox` con estilo abierto. La salida HTML conserva zoom, tooltips y filtrado visual.
- La centralidad se calcula sobre aristas unicas; el numero de observaciones por arista se conserva como peso de trafico.
- La version `noise` mantiene exactamente `Source_Node` y `Target_Node`. La recuperacion topologica es exacta sin inferir adyacencias desde GPS.

## Estructura sugerida de commits

Para conservar un historial claro al publicar en GitHub:

1. `chore: agrega datos y documentos fuente`
2. `feat: implementa analisis geo-temporal y de senales`
3. `feat: agrega grafos, Granger y ARIMAX`
4. `docs: incorpora notebook ejecutado e informe tecnico`
5. `ci: agrega validacion reproducible`

## Autoria y uso academico

Entrega grupal (ver seccion Integrantes). Antes de enviar por la plataforma oficial de la universidad, revise que el enlace del repositorio en la plataforma apunte a esta rama o a `main` tras el merge, y revise `DECLARACION_USO_IA.md` si la politica del curso exige declarar el uso de asistencia de IA.

