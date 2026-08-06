"""Pruebas minimas de estructura de la entrega (H2: tests/ real y ejecutable)."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SOURCE_CSVS = [
    "agro_clean.csv",
    "agro_noise.csv",
    "ener_clean.csv",
    "ener_noise.csv",
]

OUTPUT_ARTIFACTS = [
    "output/pdf/informe_tecnico.pdf",
    "output/interactive/mapa_agro_ndvi.html",
    "output/metrics.json",
    "output/figures/01_mapa_agro.png",
    "output/figures/02_prioridad_geo_agronoma.png",
    "output/figures/03_estacionariedad_ener5.png",
    "output/figures/04_fft_ener4.png",
    "output/figures/05_espectrogramas_ener4.png",
    "output/figures/06_filtro_agro3.png",
    "output/figures/07_centralidad_red.png",
    "output/figures/08_red_energia.png",
    "output/figures/09_nodo214.png",
    "output/figures/10_arimax.png",
    "output/figures/11_snr_arma.png",
]

EXPECTED_METRICS_KEYS = {
    "metadata",
    "audit",
    "geo",
    "stationarity",
    "signals",
    "graphs",
    "models",
    "validation",
}

NOTEBOOK_PATH = ROOT / "notebooks" / "01_inteligencia_geo_temporal_redes.ipynb"


class TestFuentesDeDatos(unittest.TestCase):
    def test_csv_fuente_existen(self) -> None:
        for name in SOURCE_CSVS:
            with self.subTest(csv=name):
                self.assertTrue((ROOT / name).is_file(), f"falta {name} en la raiz del repositorio")


class TestArtefactosDeSalida(unittest.TestCase):
    def test_artefactos_declarados_existen(self) -> None:
        for relative_path in OUTPUT_ARTIFACTS:
            with self.subTest(artifact=relative_path):
                self.assertTrue(
                    (ROOT / relative_path).is_file(),
                    f"falta el artefacto declarado en README: {relative_path}",
                )


class TestMetricsJson(unittest.TestCase):
    def test_metrics_parsea_y_tiene_claves_esperadas(self) -> None:
        metrics_path = ROOT / "output" / "metrics.json"
        self.assertTrue(metrics_path.is_file(), "output/metrics.json no existe")
        with metrics_path.open(encoding="utf-8") as stream:
            metrics = json.load(stream)
        self.assertEqual(EXPECTED_METRICS_KEYS, set(metrics.keys()))


class TestNotebook(unittest.TestCase):
    def test_markdown_precede_cada_celda_de_codigo(self) -> None:
        self.assertTrue(NOTEBOOK_PATH.is_file(), "el notebook no existe")
        with NOTEBOOK_PATH.open(encoding="utf-8") as stream:
            notebook = json.load(stream)
        cells = notebook["cells"]
        for index, cell in enumerate(cells):
            if cell["cell_type"] != "code":
                continue
            self.assertGreater(index, 0, f"la celda de codigo {index} no tiene celda previa")
            previous = cells[index - 1]
            self.assertEqual(
                previous["cell_type"],
                "markdown",
                f"la celda de codigo {index} no esta precedida por una celda markdown",
            )
            markdown_text = "".join(previous["source"]).strip()
            self.assertGreater(
                len(markdown_text),
                20,
                f"la celda markdown previa a la celda de codigo {index} no tiene contenido explicativo sustantivo",
            )

    def test_notebook_tiene_outputs_ejecutados(self) -> None:
        with NOTEBOOK_PATH.open(encoding="utf-8") as stream:
            notebook = json.load(stream)
        code_cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
        self.assertGreater(len(code_cells), 0, "el notebook no tiene celdas de codigo")
        for index, cell in enumerate(code_cells):
            with self.subTest(code_cell=index):
                self.assertIsNotNone(cell.get("execution_count"), f"celda de codigo {index} sin ejecutar")
                self.assertTrue(cell.get("outputs"), f"celda de codigo {index} sin outputs")


if __name__ == "__main__":
    unittest.main()
