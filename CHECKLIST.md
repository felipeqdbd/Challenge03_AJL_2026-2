# Trazabilidad de la entrega

Cada fila corrige, cuando aplica, un hallazgo de `AUDITORIA.md` (columna "Hallazgo corregido").

| Requisito | Estado | Evidencia | Hallazgo corregido |
|---|---:|---|---|
| Repositorio documentado | Cumplido | `README.md`, `.gitignore`, `requirements.txt`, `requirements-lock.txt`, `.github/workflows/ci.yml` | H1 |
| Pruebas de estructura ejecutables | Cumplido | `tests/test_structure.py`, comando `python -m unittest discover -s tests -v` | H2 |
| Integracion continua | Cumplido | `.github/workflows/ci.yml` (instala `requirements-lock.txt` y corre `tests/`) | H1 |
| Notebook documentado | Cumplido | `notebooks/01_inteligencia_geo_temporal_redes.ipynb`, verificado por `tests/test_structure.py::TestNotebook` | — |
| Informe tecnico PDF | Cumplido | `output/pdf/informe_tecnico.pdf`, portada con los tres integrantes | H3, H4 |
| Mapa NDVI/Humedad | Cumplido | `output/interactive/mapa_agro_ndvi.html`, figura 01 | — |
| Patron espacial de biomasa | Cumplido | K-means, eta cuadrado y prueba por permutaciones (semilla fija `SEED=42`) | — |
| ADF de las diez series de energia | Cumplido | `output/tables/adf_energy.csv`, figura 03, nota metodologica sobre Ener_4 en notebook e informe | H5 |
| Media y varianza movil de ventana 50 | Cumplido | figura 03 y notebook | — |
| Drift vs random walk de Ener_5 | Cumplido | ADF, incrementos, drift y Ljung-Box | — |
| FFT/PSD de Ener_4 | Cumplido | figura 04 | — |
| Espectrograma clean vs noise | Cumplido | figura 05 y rango de ruido en metricas | — |
| Butterworth y RMSE de Agro_3 | Cumplido | figura 06, `output/tables/butterworth_orden.csv`, justificacion numerica del orden 4 en notebook e informe seccion 3.2 | H6 |
| Grafo dirigido NetworkX | Cumplido | figuras 07 y 08, `centrality_energy.csv` | — |
| Grado, betweenness y cuello de botella | Cumplido | analisis dirigido y sensibilidad no dirigida | — |
| Granger Ener_10 -> Ener_9 | Cumplido | tabla y seccion P1 del informe | — |
| Recomendacion geo-agronoma | Cumplido | seccion P2 del informe, con supuesto explicitado | — |
| ARIMAX con temperatura y centralidad | Cumplido | figura 09, comparacion AIC y holdout | — |
| Preguntas de autoevaluacion | Cumplido | seccion dedicada del informe y notebook | — |
| Hipotesis del nodo 214 | Cumplido | prueba de frecuencia, contraste termico y limitaciones | — |
| Recuperacion de topologia ruidosa | Cumplido | igualdad exacta de conjuntos de aristas clean/noise | — |
| Entorno reproducible y determinista | Cumplido | `requirements.txt` con `pandas<3` y `plotly<6`, `requirements-lock.txt`, prueba de determinismo documentada en `AUDITORIA.md` y en el README | H5, H7 |
| Uso de IA declarado | Cumplido | `DECLARACION_USO_IA.md` | — |
| Auditoria de calidad | Cumplido | `AUDITORIA.md` (hallazgos H1-H7 y plan de correccion) | — |

## Advertencias de interpretacion

1. No existe columna de fecha; el orden de fila se usa como orden temporal.
2. No existe variable explicita de interrupcion o flujo. La presencia de registros hacia cada `Target_Node` se usa solo como proxy de telemetria observada.
3. El nodo 214 no es un puente en el grafo no dirigido y el grafo dirigido no contiene caminos de mas de una arista.
4. El filtrado Butterworth cero-fase es valido para reconstruccion offline, no como prueba automatica de mejora predictiva.
5. `Lecture_03_Challenge.pdf` usa "Challenge 02" en su encabezado interno; el repositorio se normalizo a "Challenge 03" en todos los entregables propios (ver README).
