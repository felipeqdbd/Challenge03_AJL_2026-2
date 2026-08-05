# Trazabilidad de la entrega

| Requisito | Estado | Evidencia |
|---|---:|---|
| Repositorio documentado | Cumplido | `README.md`, `.gitignore`, `requirements.txt`, flujo CI |
| Notebook documentado | Cumplido | `notebooks/01_inteligencia_geo_temporal_redes.ipynb` |
| Informe tecnico PDF | Cumplido | `output/pdf/informe_tecnico.pdf` |
| Mapa NDVI/Humedad | Cumplido | `output/interactive/mapa_agro_ndvi.html`, figura 01 |
| Patron espacial de biomasa | Cumplido | K-means, eta cuadrado y prueba por permutaciones |
| ADF de las diez series de energia | Cumplido | `output/tables/adf_energy.csv`, figura 03 |
| Media y varianza movil de ventana 50 | Cumplido | figura 03 y notebook |
| Drift vs random walk de Ener_5 | Cumplido | ADF, incrementos, drift y Ljung-Box |
| FFT/PSD de Ener_4 | Cumplido | figura 04 |
| Espectrograma clean vs noise | Cumplido | figura 05 y rango de ruido en metricas |
| Butterworth y RMSE de Agro_3 | Cumplido | figura 06 y metricas de reconstruccion/prediccion |
| Grafo dirigido NetworkX | Cumplido | figuras 07 y 08, `centrality_energy.csv` |
| Grado, betweenness y cuello de botella | Cumplido | analisis dirigido y sensibilidad no dirigida |
| Granger Ener_10 -> Ener_9 | Cumplido | tabla y seccion P1 del informe |
| Recomendacion geo-agronoma | Cumplido | seccion P2 del informe, con supuesto explicitado |
| ARIMAX con temperatura y centralidad | Cumplido | figura 09, comparacion AIC y holdout |
| Preguntas de autoevaluacion | Cumplido | seccion dedicada del informe y notebook |
| Hipotesis del nodo 214 | Cumplido | prueba de frecuencia, contraste termico y limitaciones |
| Recuperacion de topologia ruidosa | Cumplido | igualdad exacta de conjuntos de aristas clean/noise |

## Advertencias de interpretacion

1. No existe columna de fecha; el orden de fila se usa como orden temporal.
2. No existe variable explicita de interrupcion o flujo. La presencia de registros hacia cada `Target_Node` se usa solo como proxy de telemetria observada.
3. El nodo 214 no es un puente en el grafo no dirigido y el grafo dirigido no contiene caminos de mas de una arista.
4. El filtrado Butterworth cero-fase es valido para reconstruccion offline, no como prueba automatica de mejora predictiva.

