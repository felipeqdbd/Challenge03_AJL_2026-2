"""Punto de entrada unico para regenerar la entrega completa."""

from __future__ import annotations

from pathlib import Path

from scripts.create_notebook import build_notebook
from src.report_builder import build_report
from src.workshop_analysis import run_analysis


def main() -> None:
    root = Path(__file__).resolve().parent
    print("[1/3] Ejecutando analisis y generando evidencia...")
    metrics = run_analysis(root)
    print("[2/3] Generando y ejecutando notebook...")
    notebook = build_notebook(root, metrics=metrics, execute=True)
    print("[3/3] Construyendo informe tecnico PDF...")
    report = build_report(root, metrics=metrics)
    print(f"Notebook: {notebook}")
    print(f"Informe:  {report}")
    print("Entrega regenerada correctamente.")


if __name__ == "__main__":
    main()

