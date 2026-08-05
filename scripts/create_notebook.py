"""Genera y ejecuta el notebook narrativo de la entrega."""

from __future__ import annotations

import json
import os
from pathlib import Path

import nbformat as nbf
from nbclient import NotebookClient
from jupyter_client.kernelspec import KernelSpecManager


def _md(text: str):
    return nbf.v4.new_markdown_cell(text.strip())


def _code(text: str):
    return nbf.v4.new_code_cell(text.strip())


def build_notebook(root: Path, metrics: dict | None = None, execute: bool = True) -> Path:
    if metrics is None:
        with (root / "output" / "metrics.json").open(encoding="utf-8") as stream:
            metrics = json.load(stream)

    geo = metrics["geo"]
    stationarity = metrics["stationarity"]
    signals = metrics["signals"]
    graph = metrics["graphs"]
    models = metrics["models"]
    validation = metrics["validation"]

    cells = [
        _md(
            """
# Challenge 02: Inteligencia Geo-Temporal y de Redes

**Optimización de activos críticos - TechLogistics S.A.**  
Maestría en Ciencia de los Datos, Universidad EAFIT, periodo 2026-1.

Este notebook sigue CRISP-DM y cubre cada tarea del reto: mapa geoespacial, ADF y ventanas móviles, FFT y espectrogramas, Butterworth, grafos, Granger, ARIMAX y las preguntas de validación. Las afirmaciones observadas se separan de los supuestos narrativos del caso.
"""
        ),
        _md(
            """
## 0. Reproducibilidad y configuración

La siguiente celda detecta la raíz del proyecto, importa el módulo analítico y ejecuta el flujo completo con semilla fija. Regenera todas las tablas, figuras, el mapa HTML y `metrics.json`; los CSV de entrada no se modifican.
"""
        ),
        _code(
            """
from pathlib import Path
import sys
import json
import pandas as pd
from IPython.display import display, Image, HTML

CURRENT = Path.cwd().resolve()
ROOT = CURRENT.parent if CURRENT.name == "notebooks" else CURRENT
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# En Windows el entorno local puede compartir el Python del sistema. Se incorpora
# su site-packages para que el notebook ejecutado use exactamente las dependencias
# instaladas por el proyecto, sin dejar rutas absolutas en el archivo final.
for candidate in [ROOT / ".venv" / "Lib" / "site-packages", *ROOT.glob(".venv/lib/python*/site-packages")]:
    if candidate.exists() and str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from src import workshop_analysis as wa

metrics = wa.run_analysis(ROOT)
print(f"Proyecto: {ROOT}")
print("Pipeline ejecutado correctamente.")
"""
        ),
        _md(
            """
## 1. Data Understanding

Se valida tamaño, nulos, duplicados y número de nodos. Las cuatro tablas tienen 2.000 registros, 14 columnas y esquema numérico homogéneo. La ausencia de fecha obliga a interpretar el índice de fila como orden temporal y las frecuencias como ciclos por registro.
"""
        ),
        _code(
            """
audit = pd.read_csv(ROOT / "output" / "tables" / "data_audit.csv")
display(audit)

assert (audit[["filas", "columnas", "nulos", "duplicados"]] == [2000, 14, 0, 0]).all().all()
display(pd.DataFrame(metrics["audit"]["topology"]).T)
"""
        ),
        _md(
            f"""
## 2. Fase 1 - Exploración geo-temporal

El mapa usa `scatter_mapbox`: color para NDVI (`Agro_5`) y tamaño para humedad (`Agro_1`). Para evitar una conclusión puramente visual se agrupan las coordenadas en seis regiones K-means y se contrasta el porcentaje de varianza explicada mediante 499 permutaciones.

Resultado: $\\eta^2={geo['eta_squared']:.4f}$ y $p={geo['permutation_p']:.3f}$. No se identifica un cluster con biomasa consistentemente baja al 5%; el patrón observado es débil y exploratorio.
"""
        ),
        _code(
            """
clusters = pd.read_csv(ROOT / "output" / "tables" / "geo_clusters.csv")
display(clusters.style.format({"ndvi_mean": "{:.3f}", "low_ndvi_share": "{:.1%}", "wind_variance": "{:.3f}"}))
display(Image(filename=str(ROOT / "output" / "figures" / "01_mapa_agro.png"), width=950))
display(HTML('<a href="../output/interactive/mapa_agro_ndvi.html" target="_blank">Abrir mapa interactivo</a>'))
"""
        ),
        _md(
            f"""
### Recomendación geo-agronómica

El puntaje de prioridad combina NDVI bajo y varianza alta de `Agro_10`, usando **el supuesto del enunciado** de que el viento aproxima una zona de pendiente. Se prioriza el cluster {geo['priority_cluster']} para un piloto de riego por goteo sectorizado, almacenamiento local, control de presión y zanjas de infiltración. La inversión a escala queda condicionada a topografía y prueba A/B porque Levene no detecta heterogeneidad espacial de varianza ($p={geo['wind_variance_levene_p']:.3f}$).
"""
        ),
        _code(
            """
display(Image(filename=str(ROOT / "output" / "figures" / "02_prioridad_geo_agronoma.png"), width=850))
pd.Series(metrics["geo"]["gps_latitude_rmse"], name="RMSE_latitud").to_frame()
"""
        ),
        _md(
            f"""
## 3. ADF, diferenciación y ventana de 50

ADF se aplica a las diez series clean. Las series no estacionarias son: **{', '.join(stationarity['nonstationary_series'])}**. Para ellas se generan media y varianza móvil de 50 registros. `Ener_5` no rechaza raíz unitaria en nivel y sí en primera diferencia; el incremento medio positivo y la falta de autocorrelación significativa en los incrementos son compatibles con random walk con drift.
"""
        ),
        _code(
            """
adf = pd.read_csv(ROOT / "output" / "tables" / "adf_energy.csv")
display(adf.style.format({"p_level": "{:.4g}", "p_first_difference": "{:.4g}"}))
display(Image(filename=str(ROOT / "output" / "figures" / "03_estacionariedad_ener5.png"), width=900))
"""
        ),
        _md(
            f"""
## 4. Fase 2 - FFT y espectrogramas de `Ener_4`

Se estima la densidad espectral mediante Welch, una FFT segmentada que reduce la varianza, y se construyen espectrogramas con la misma escala de color. El SNR empírico es {signals['ener4']['empirical_snr_db']:.2f} dB. El 90% de la potencia excedente está entre {signals['ener4']['excess_power_90_band'][0]:.4f} y {signals['ener4']['excess_power_90_band'][1]:.4f} ciclos por registro: es ruido de banda ancha, coherente con AWGN.
"""
        ),
        _code(
            """
display(Image(filename=str(ROOT / "output" / "figures" / "04_fft_ener4.png"), width=900))
display(Image(filename=str(ROOT / "output" / "figures" / "05_espectrogramas_ener4.png"), width=950))
"""
        ),
        _md(
            f"""
## 5. Butterworth y reconstrucción de `Agro_3`

Se calibra un paso bajo Butterworth de orden 4 en el primer 60% de la pareja clean/noise. El corte seleccionado es {signals['agro3_filter']['selected_cutoff_cycles_per_record']:.4f} ciclos por registro. El RMSE offline baja de {signals['agro3_filter']['raw_rmse']:.3f} a {signals['agro3_filter']['filtered_rmse']:.3f}.

Para responder si mejora la predicción se ejecuta un AR(24) de un paso con información exclusivamente pasada. El RMSE cambia de {signals['agro3_filter']['prediction_raw_rmse']:.3f} a {signals['agro3_filter']['prediction_filtered_rmse']:.3f}; por tanto, la reconstrucción mejora, pero la capacidad predictiva desplegable no. Usar `filtfilt` sobre todo el holdout habría introducido fuga temporal.
"""
        ),
        _code(
            """
display(pd.Series(metrics["signals"]["agro3_filter"], name="valor").to_frame())
display(Image(filename=str(ROOT / "output" / "figures" / "06_filtro_agro3.png"), width=930))
"""
        ),
        _md(
            f"""
## 6. Fase 3 - Grafo dirigido y centralidad

Se crea un `DiGraph` con {graph['nodes']} nodos y {graph['unique_edges']} aristas únicas; la frecuencia de cada arista queda como peso de tráfico. Los identificadores Source y Target son disjuntos y todas las aristas van Source -> Target, de modo que no hay caminos dirigidos de longitud mayor que uno: **todos los betweenness dirigidos son cero**.

Como sensibilidad se ignora la dirección sin inventar nuevas aristas. El nodo {graph['traffic_bottleneck']} lidera tráfico y betweenness no dirigido. No se observan bridges.
"""
        ),
        _code(
            """
centrality = pd.read_csv(ROOT / "output" / "tables" / "centrality_energy.csv")
display(centrality.sort_values(["traffic_weight", "undirected_betweenness_sensitivity"], ascending=False).head(12))
display(Image(filename=str(ROOT / "output" / "figures" / "07_centralidad_red.png"), width=930))
display(Image(filename=str(ROOT / "output" / "figures" / "08_red_energia.png"), width=900))
"""
        ),
        _md(
            f"""
## 7. Nodo 214 y causalidad de Granger

El umbral crítico se operacionaliza como P95 de `Ener_2`. La frecuencia de Target 214 no cae cuando se supera el umbral (Fisher $p={graph['node_214']['fisher_p']:.3f}$) y su temperatura media no es anómala (Welch $p={graph['node_214']['temperature_test_p']:.3f}$). Los CSV no incluyen flujo ni estado de interrupción; la narrativa del fallo no puede confirmarse.

El VAR elige rezago {models['granger']['selected_lag']}. `Ener_10 -> Ener_9` produce $p={models['granger']['power_factor_to_voltage']['p_value']:.3f}$ y la dirección inversa $p={models['granger']['voltage_to_power_factor']['p_value']:.3f}$. No hay evidencia de Granger.
"""
        ),
        _code(
            """
display(pd.read_csv(ROOT / "output" / "tables" / "granger_results.csv"))
display(pd.Series(metrics["graphs"]["node_214"], name="valor").to_frame())
display(Image(filename=str(ROOT / "output" / "figures" / "09_nodo214.png"), width=850))
"""
        ),
        _md(
            f"""
## 8. ARIMAX de la Demanda

`Ener_1` es I(1), así que se usa $d=1$. Tras seleccionar $p,q\\in\\{{0,1,2\\}}$ con temperatura, se compara el mismo orden {tuple(models['arimax']['order'])} con y sin centralidad estandarizada del nodo Source.

El AIC cambia de {models['arimax']['aic_temperature']:.2f} a {models['arimax']['aic_temperature_centrality']:.2f} ($\\Delta={models['arimax']['delta_aic_extended_minus_base']:+.2f}$). **La centralidad no mejora el AIC**, aunque su coeficiente individual resulte distinto de cero; el criterio de información favorece la especificación parsimoniosa.
"""
        ),
        _code(
            """
display(pd.read_csv(ROOT / "output" / "tables" / "arimax_comparison.csv"))
display(Image(filename=str(ROOT / "output" / "figures" / "10_arimax.png"), width=900))
"""
        ),
        _md(
            f"""
## 9. Autoevaluación

1. **Estacionariedad:** `Ener_5` y `Ener_6` correlacionan {validation['spurious_correlation']['level_correlation']:.3f} en nivel, pero {validation['spurious_correlation']['first_difference_correlation']:.3f} tras diferenciar. Pearson en niveles estaba dominado por tendencia.
2. **SNR:** `Agro_7` tiene {validation['snr_5db_arma']['empirical_snr_db']:.3f} dB y el desplazamiento L2 de coeficientes AR/MA es {validation['snr_5db_arma']['coefficient_l2_shift']:.3f}; el ruido altera materialmente la dinámica estimada.
3. **Bridge:** su falla separaría componentes y sería sistémica. No hay bridges observados en la sensibilidad no dirigida.
4. **Geo-inteligencia:** pendiente, exposición y microclima pueden cambiar la varianza; este dataset no detecta diferencias significativas entre clusters.
"""
        ),
        _code(
            """
display(pd.read_csv(ROOT / "output" / "tables" / "arma_5db_coefficients.csv"))
display(Image(filename=str(ROOT / "output" / "figures" / "11_snr_arma.png"), width=780))
"""
        ),
        _md(
            """
## 10. Conclusiones

- Diferenciar las seis series I(1) evita relaciones espurias y hace coherente el ARIMAX.
- El ruido de `Ener_4` es de banda ancha; `Agro_3` se reconstruye bien offline, pero el filtro no mejora automáticamente una predicción en tiempo real.
- El grafo exigido no permite propagación dirigida de múltiples saltos; el nodo 119 es la prioridad por tráfico, no el 214.
- La centralidad no reduce el AIC de la Demanda y no hay Granger entre factor de potencia y voltaje.
- La inversión hídrica debe comenzar como piloto medible, porque el patrón espacial y la relación viento-pendiente no son concluyentes en los datos.

El informe ejecutivo en `output/pdf/informe_tecnico.pdf` contiene la discusión completa, limitaciones, plan de acción y trazabilidad contra el checklist.
"""
        ),
    ]

    notebook = nbf.v4.new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3"},
            "title": "Challenge 02 - Inteligencia Geo-Temporal y de Redes",
        },
    )
    destination = root / "notebooks" / "01_inteligencia_geo_temporal_redes.ipynb"
    if execute:
        ipython_dir = root / "tmp" / "ipython"
        ipython_dir.mkdir(parents=True, exist_ok=True)
        os.environ["IPYTHONDIR"] = str(ipython_dir)
        manager = KernelSpecManager()
        available = manager.find_kernel_specs()
        selected_kernel = None
        for name in ("python3", "codex-python313", *available.keys()):
            if name not in available:
                continue
            specification = manager.get_kernel_spec(name)
            executable = Path(specification.argv[0])
            if executable.exists():
                selected_kernel = name
                break
        if selected_kernel is None:
            raise RuntimeError("No se encontro un kernel Jupyter con ejecutable valido")
        client = NotebookClient(
            notebook,
            timeout=600,
            kernel_name=selected_kernel,
            resources={"metadata": {"path": str(root)}},
            allow_errors=False,
        )
        client.execute()
    nbf.write(notebook, destination)
    return destination


if __name__ == "__main__":
    build_notebook(Path(__file__).resolve().parents[1])
