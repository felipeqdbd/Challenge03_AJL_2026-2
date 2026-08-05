# Challenge 03 - Inteligencia Geo-Temporal y de Redes

Solucion reproducible del taller de la Maestria en Ciencia de los Datos de EAFIT. El proyecto integra analisis geoespacial, estacionariedad, procesamiento de senales, grafos, causalidad de Granger y ARIMAX sobre los activos de TechLogistics S.A.

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

Desde la raiz del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python run_pipeline.py
```

En Linux o macOS, active el entorno con `source .venv/bin/activate`.

El comando regenera tablas, figuras, mapa interactivo, metricas, informe y notebook. Para validar la estructura basica:

```powershell
python -m unittest discover -s tests -v
```

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

Entrega individual. Revise el contenido, agregue su nombre y enlace del repositorio antes de enviarlo por la plataforma oficial de la universidad.

