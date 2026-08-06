# Declaracion de uso de inteligencia artificial

Este documento describe donde y como se uso asistencia de IA generativa en la construccion de este repositorio, y donde no se uso, para que el evaluador pueda distinguir el trabajo del equipo del trabajo asistido.

## Que es trabajo del equipo

El diseno metodologico completo es decision del equipo: que pruebas aplicar a cada serie (ADF antes de diferenciar, Ljung-Box para autocorrelacion de incrementos, Levene para heterogeneidad de varianza), que arquitectura de grafo construir (dirigido Source a Target, con sensibilidad no dirigida para betweenness), que orden de modelo usar en el ARIMAX y por que, y como operacionalizar supuestos que el enunciado deja abiertos (por ejemplo, el percentil 95 como umbral critico del precio spot, o el uso del viento como proxy de pendiente para la recomendacion geo-agronoma). La interpretacion de cada resultado numerico (por ejemplo, que el patron espacial de NDVI bajo no es concluyente al 5%, o que el filtrado Butterworth mejora la reconstruccion offline pero no la prediccion desplegable) y las conclusiones de negocio dirigidas a la narrativa de TechLogistics S.A. son del equipo, no de la IA. La IA no decidio que conclusiones defender ante la junta directiva ficticia del caso; el equipo tomo esas decisiones y las valido contra los datos.

## En que partes se uso asistencia de IA

- Redaccion de codigo Python en `src/workshop_analysis.py`, `src/report_builder.py` y `scripts/create_notebook.py` a partir de especificaciones ya decididas por el equipo (que metrica calcular, contra que serie comparar, que figura generar). La IA ayudo con sintaxis de librerias (statsmodels, scipy.signal, networkx, plotly, reportlab) y con la estructura repetitiva de generacion de tablas y figuras.
- Redaccion y formato de documentos Markdown de este repositorio (`README.md`, `CHECKLIST.md`, este archivo) y del texto narrativo del notebook y del informe PDF, sobre datos y cifras ya calculadas por el pipeline.
- Auditoria tecnica de control de calidad documentada en `AUDITORIA.md`: un agente de IA reviso el repositorio de forma independiente (reproducibilidad en entorno limpio, cobertura de tareas y preguntas del enunciado, rigor de ADF/Butterworth/RMSE/espectrogramas, riesgos de version de dependencias) y reporto hallazgos que el equipo luego decidio como corregir.
- Correccion de los hallazgos de esa auditoria (fijar semillas, ajustar techos de version, agregar pruebas de determinismo, justificar el orden del filtro Butterworth con una tabla comparativa, normalizar la numeracion "Challenge 03", crear `tests/` y el flujo de CI).

## En que partes NO se uso IA

- La seleccion de las preguntas de negocio a responder y su enfoque (P1, P2, P3) no fue generada por IA: responde a la lectura del equipo del enunciado `Lecture_03_Challenge.pdf`.
- Los datos fuente (`agro_clean.csv`, `agro_noise.csv`, `ener_clean.csv`, `ener_noise.csv`) son los provistos por el curso, sin alteracion.
- [COMPLETAR: el equipo debe indicar aqui si hubo division de trabajo entre integrantes en la revision de resultados, por ejemplo quien reviso cada seccion del informe antes de la entrega].

## Verificacion humana

- Los resultados numericos del pipeline se revisaron contra los archivos fuente antes de aceptarlos como definitivos (por ejemplo, se verifico que el RMSE de reconstruccion de `Agro_3` se calcula contra la serie `Agro_3` clean y no contra otra serie, y que las columnas "noise" provienen integramente de `agro_noise.csv`/`ener_noise.csv` sin generacion sintetica adicional).
- La auditoria tecnica documentada en `AUDITORIA.md` funciono como control de calidad adicional: identifico brechas entre lo declarado en `CHECKLIST.md` y lo verificable en el repositorio (evidencia inexistente, inconsistencias de nombre, un parametro sin justificar, y una fuente de no determinismo entre entornos), y cada hallazgo (H1 a H7) fue corregido y verificado de nuevo antes de esta entrega.
- [COMPLETAR: el equipo debe indicar aqui si algun integrante repitio manualmente algun calculo clave (por ejemplo el ADF de una serie o el AIC del ARIMAX) por fuera del pipeline como verificacion independiente].

## Alcance de esta declaracion

Esta declaracion cubre el estado del repositorio en la rama `fix/challenge3-cumplimiento-entrega` al momento de esta entrega. No cubre cambios posteriores que el equipo realice despues de este merge.
