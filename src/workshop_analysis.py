"""Pipeline analitico reproducible para el Challenge 02.

Las funciones de este modulo trabajan unicamente con los cuatro CSV originales y
generan tablas, figuras, un mapa interactivo y un archivo JSON auditable.
"""

from __future__ import annotations

import json
import math
import warnings
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
import plotly.express as px
import seaborn as sns
from scipy import signal, stats
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.api import VAR
from statsmodels.tsa.ar_model import AutoReg
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.stattools import adfuller, grangercausalitytests


SEED = 42
WINDOW = 50
ENERGY_COLUMNS = [f"Ener_{i}" for i in range(1, 11)]
AGRO_COLUMNS = [f"Agro_{i}" for i in range(1, 11)]
NAVY = "#003B70"
BLUE = "#1479B8"
ORANGE = "#D05A00"
TEAL = "#188977"
RED = "#C0392B"
GRAY = "#667085"


def _configure_plots() -> None:
    sns.set_theme(style="whitegrid", context="notebook")
    plt.rcParams.update(
        {
            "figure.dpi": 130,
            "savefig.dpi": 190,
            "font.family": "DejaVu Sans",
            "axes.titleweight": "bold",
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "legend.frameon": False,
        }
    )


def output_paths(root: Path) -> dict[str, Path]:
    paths = {
        "output": root / "output",
        "figures": root / "output" / "figures",
        "tables": root / "output" / "tables",
        "interactive": root / "output" / "interactive",
        "pdf": root / "output" / "pdf",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def load_datasets(root: Path) -> dict[str, pd.DataFrame]:
    """Carga los cuatro activos y valida el esquema minimo esperado."""

    files = {
        "agro_clean": "agro_clean.csv",
        "agro_noise": "agro_noise.csv",
        "ener_clean": "ener_clean.csv",
        "ener_noise": "ener_noise.csv",
    }
    data = {name: pd.read_csv(root / filename) for name, filename in files.items()}

    required_common = {"Latitude", "Longitude", "Source_Node", "Target_Node"}
    for name, frame in data.items():
        expected = set(AGRO_COLUMNS if name.startswith("agro") else ENERGY_COLUMNS)
        missing = (expected | required_common) - set(frame.columns)
        if missing:
            raise ValueError(f"{name} no contiene las columnas requeridas: {sorted(missing)}")
        if frame.empty:
            raise ValueError(f"{name} no contiene registros")
    return data


def audit_datasets(data: dict[str, pd.DataFrame], paths: dict[str, Path]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for name, frame in data.items():
        rows.append(
            {
                "dataset": name,
                "filas": len(frame),
                "columnas": frame.shape[1],
                "nulos": int(frame.isna().sum().sum()),
                "duplicados": int(frame.duplicated().sum()),
                "source_nodes": int(frame["Source_Node"].nunique()),
                "target_nodes": int(frame["Target_Node"].nunique()),
            }
        )
    audit = pd.DataFrame(rows)
    audit.to_csv(paths["tables"] / "data_audit.csv", index=False)

    topology = {}
    for domain in ("agro", "ener"):
        clean = data[f"{domain}_clean"]
        noise = data[f"{domain}_noise"]
        clean_edges = set(map(tuple, clean[["Source_Node", "Target_Node"]].drop_duplicates().to_numpy()))
        noise_edges = set(map(tuple, noise[["Source_Node", "Target_Node"]].drop_duplicates().to_numpy()))
        topology[domain] = {
            "same_shape": clean.shape == noise.shape,
            "same_edges": clean_edges == noise_edges,
            "unique_edges": len(clean_edges),
            "same_source_target_rows": bool(
                clean[["Source_Node", "Target_Node"]].equals(noise[["Source_Node", "Target_Node"]])
            ),
        }
    return {"datasets": rows, "topology": topology}


def empirical_snr_table(data: dict[str, pd.DataFrame], paths: dict[str, Path]) -> pd.DataFrame:
    rows = []
    for domain, prefix in (("agro", "Agro"), ("ener", "Ener")):
        clean = data[f"{domain}_clean"]
        noise = data[f"{domain}_noise"]
        for index in range(1, 11):
            column = f"{prefix}_{index}"
            error = noise[column] - clean[column]
            snr_db = 10 * np.log10(np.var(clean[column], ddof=0) / np.var(error, ddof=0))
            rows.append(
                {
                    "series": column,
                    "snr_db": float(snr_db),
                    "error_mean": float(error.mean()),
                    "error_std": float(error.std(ddof=0)),
                }
            )
    table = pd.DataFrame(rows)
    table.to_csv(paths["tables"] / "empirical_snr.csv", index=False)
    return table


def analyze_geospatial(
    data: dict[str, pd.DataFrame], paths: dict[str, Path]
) -> dict[str, Any]:
    agro = data["agro_clean"].copy()
    noisy = data["agro_noise"]

    scaler = StandardScaler()
    coordinates = scaler.fit_transform(agro[["Latitude", "Longitude"]])
    labels = KMeans(n_clusters=6, random_state=SEED, n_init=30).fit_predict(coordinates)
    agro["cluster"] = labels
    low_threshold = float(agro["Agro_5"].quantile(0.25))

    cluster = (
        agro.groupby("cluster")
        .agg(
            n=("Agro_5", "size"),
            latitude=("Latitude", "mean"),
            longitude=("Longitude", "mean"),
            ndvi_mean=("Agro_5", "mean"),
            humidity_mean=("Agro_1", "mean"),
            low_ndvi_share=("Agro_5", lambda series: (series <= low_threshold).mean()),
            wind_variance=("Agro_10", "var"),
        )
        .reset_index()
    )
    cluster["risk_score"] = (
        -(cluster["ndvi_mean"] - cluster["ndvi_mean"].mean()) / cluster["ndvi_mean"].std(ddof=0)
        + (cluster["wind_variance"] - cluster["wind_variance"].mean())
        / cluster["wind_variance"].std(ddof=0)
    )
    cluster.to_csv(paths["tables"] / "geo_clusters.csv", index=False)

    overall_mean = agro["Agro_5"].mean()
    total_ss = float(((agro["Agro_5"] - overall_mean) ** 2).sum())
    between_ss = float(
        sum(
            len(group) * (group["Agro_5"].mean() - overall_mean) ** 2
            for _, group in agro.groupby("cluster")
        )
    )
    eta_squared = between_ss / total_ss
    rng = np.random.default_rng(SEED)
    permutation_eta = []
    for _ in range(499):
        shuffled = rng.permutation(agro["Agro_5"].to_numpy())
        shuffled_mean = shuffled.mean()
        perm_between = sum(
            np.sum(labels == label) * (shuffled[labels == label].mean() - shuffled_mean) ** 2
            for label in np.unique(labels)
        )
        permutation_eta.append(float(perm_between / np.sum((shuffled - shuffled_mean) ** 2)))
    permutation_p = (1 + sum(value >= eta_squared for value in permutation_eta)) / (
        len(permutation_eta) + 1
    )

    # La version noise solo altera Latitude; se cuantifica si un suavizado ingenuo ayuda.
    gps_rmse = {
        "raw": float(np.sqrt(np.mean((noisy["Latitude"] - agro["Latitude"]) ** 2)))
    }
    for window in (3, 5, 9, 21, 51):
        smoothed = noisy["Latitude"].rolling(window, center=True, min_periods=1).median()
        gps_rmse[str(window)] = float(np.sqrt(np.mean((smoothed - agro["Latitude"]) ** 2)))

    levene = stats.levene(
        *[agro.loc[agro["cluster"] == label, "Agro_10"] for label in sorted(agro["cluster"].unique())],
        center="median",
    )

    # Mapa interactivo solicitado por el enunciado (Tarea 1: scatter_mapbox). requirements.txt
    # fija plotly<6 para que esta API siga vigente sin advertencia de obsolescencia.
    map_figure = px.scatter_mapbox(
            agro,
            lat="Latitude",
            lon="Longitude",
            color="Agro_5",
            size="Agro_1",
            hover_data={
                "Source_Node": True,
                "Target_Node": True,
                "Agro_5": ":.3f",
                "Agro_1": ":.2f",
                "Agro_7": ":.2f",
                "Latitude": ":.5f",
                "Longitude": ":.5f",
            },
            color_continuous_scale="RdYlGn",
            zoom=10,
            height=720,
            title="Sensores agro: NDVI (color) y humedad (tamano)",
        )
    map_figure.update_layout(
        mapbox_style="open-street-map",
        margin={"r": 0, "t": 55, "l": 0, "b": 0},
        coloraxis_colorbar_title="NDVI",
    )
    map_figure.write_html(
        paths["interactive"] / "mapa_agro_ndvi.html",
        include_plotlyjs=True,
        full_html=True,
    )

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2), constrained_layout=True)
    sizes = 18 + 75 * (agro["Agro_1"] - agro["Agro_1"].min()) / agro["Agro_1"].max()
    scatter = axes[0].scatter(
        agro["Longitude"],
        agro["Latitude"],
        c=agro["Agro_5"],
        s=sizes,
        cmap="RdYlGn",
        alpha=0.7,
        linewidths=0,
    )
    axes[0].set_title("NDVI y humedad por ubicacion")
    axes[0].set_xlabel("Longitud")
    axes[0].set_ylabel("Latitud")
    fig.colorbar(scatter, ax=axes[0], label="NDVI (Agro_5)")

    bars = cluster.sort_values("cluster")
    colors = [ORANGE if value == bars["ndvi_mean"].min() else NAVY for value in bars["ndvi_mean"]]
    axes[1].bar(bars["cluster"].astype(str), bars["ndvi_mean"], color=colors)
    axes[1].axhline(agro["Agro_5"].mean(), color=GRAY, linestyle="--", label="Media global")
    axes[1].set_title("NDVI medio en seis regiones K-means")
    axes[1].set_xlabel("Cluster espacial")
    axes[1].set_ylabel("NDVI medio")
    axes[1].legend()
    axes[1].set_ylim(1.0, 1.25)
    fig.suptitle("Exploracion geoespacial del Oriente antioqueno", color=NAVY, fontsize=15, fontweight="bold")
    fig.savefig(paths["figures"] / "01_mapa_agro.png", bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9.5, 4.8), constrained_layout=True)
    ordered = cluster.sort_values("risk_score", ascending=True)
    ax.barh(
        ordered["cluster"].astype(str),
        ordered["risk_score"],
        color=[ORANGE if value == ordered["risk_score"].max() else BLUE for value in ordered["risk_score"]],
    )
    ax.axvline(0, color=GRAY, linewidth=1)
    ax.set_title("Prioridad relativa: NDVI bajo y varianza del viento alta")
    ax.set_xlabel("Puntaje estandarizado (supuesto de pendiente del enunciado)")
    ax.set_ylabel("Cluster")
    fig.savefig(paths["figures"] / "02_prioridad_geo_agronoma.png", bbox_inches="tight")
    plt.close(fig)

    priority_row = cluster.loc[cluster["risk_score"].idxmax()]
    return {
        "cluster_count": 6,
        "low_ndvi_threshold": low_threshold,
        "eta_squared": float(eta_squared),
        "permutation_p": float(permutation_p),
        "lowest_ndvi_cluster": int(cluster.loc[cluster["ndvi_mean"].idxmin(), "cluster"]),
        "priority_cluster": int(priority_row["cluster"]),
        "priority_cluster_latitude": float(priority_row["latitude"]),
        "priority_cluster_longitude": float(priority_row["longitude"]),
        "priority_cluster_ndvi": float(priority_row["ndvi_mean"]),
        "priority_cluster_wind_variance": float(priority_row["wind_variance"]),
        "wind_variance_levene_p": float(levene.pvalue),
        "gps_latitude_rmse": gps_rmse,
        "cluster_table": cluster.to_dict(orient="records"),
    }


def analyze_stationarity(
    data: dict[str, pd.DataFrame], paths: dict[str, Path]
) -> dict[str, Any]:
    energy = data["ener_clean"]
    rows = []
    rolling = pd.DataFrame(index=energy.index)

    for column in ENERGY_COLUMNS:
        level = adfuller(energy[column].to_numpy(), autolag="AIC")
        difference = adfuller(energy[column].diff().dropna().to_numpy(), autolag="AIC")
        integration = 1 if level[1] >= 0.05 else 0
        rows.append(
            {
                "series": column,
                "adf_level": float(level[0]),
                "p_level": float(level[1]),
                "adf_first_difference": float(difference[0]),
                "p_first_difference": float(difference[1]),
                "integration_order": integration,
            }
        )
        if integration == 1:
            rolling[f"{column}_mean_50"] = energy[column].rolling(WINDOW).mean()
            rolling[f"{column}_variance_50"] = energy[column].rolling(WINDOW).var()

    table = pd.DataFrame(rows)
    table.to_csv(paths["tables"] / "adf_energy.csv", index=False)
    rolling.to_csv(paths["tables"] / "rolling_window50_energy.csv", index_label="registro")

    gas = energy["Ener_5"]
    increments = gas.diff().dropna()
    drift_test = stats.ttest_1samp(increments, popmean=0.0)
    ljung = acorr_ljungbox(increments, lags=[10], return_df=True).iloc[0]

    fig, axes = plt.subplots(3, 1, figsize=(12, 9), constrained_layout=True)
    axes[0].plot(gas.index, gas, color=BLUE, linewidth=1.2, label="Ener_5")
    axes[0].plot(gas.rolling(WINDOW).mean(), color=ORANGE, linewidth=2, label="Media movil 50")
    axes[0].set_title("Costo del gas: nivel y media movil")
    axes[0].set_ylabel("Costo")
    axes[0].legend(ncol=2)

    axes[1].plot(gas.rolling(WINDOW).var(), color=TEAL, linewidth=1.6)
    axes[1].set_title("Varianza movil de 50 registros")
    axes[1].set_ylabel("Varianza")

    axes[2].plot(increments.index, increments, color=GRAY, linewidth=0.8)
    axes[2].axhline(increments.mean(), color=RED, linestyle="--", label=f"Drift medio = {increments.mean():.4f}")
    axes[2].set_title("Primera diferencia: incrementos sin autocorrelacion significativa")
    axes[2].set_xlabel("Registro")
    axes[2].set_ylabel("Delta Ener_5")
    axes[2].legend()
    fig.suptitle("Diagnostico de Ener_5: random walk con drift", color=NAVY, fontsize=15, fontweight="bold")
    fig.savefig(paths["figures"] / "03_estacionariedad_ener5.png", bbox_inches="tight")
    plt.close(fig)

    nonstationary = table.loc[table["integration_order"] == 1, "series"].tolist()
    return {
        "window": WINDOW,
        "nonstationary_series": nonstationary,
        "stationary_series": table.loc[table["integration_order"] == 0, "series"].tolist(),
        "adf_table": table.to_dict(orient="records"),
        "ener5": {
            "adf_level_p": float(table.loc[table["series"] == "Ener_5", "p_level"].iloc[0]),
            "adf_difference_p": float(
                table.loc[table["series"] == "Ener_5", "p_first_difference"].iloc[0]
            ),
            "mean_increment": float(increments.mean()),
            "increment_ttest_p": float(drift_test.pvalue),
            "ljung_box_lag10_p": float(ljung["lb_pvalue"]),
            "interpretation": "random_walk_with_positive_drift",
        },
    }


def _one_step_autoreg_predictions(series: np.ndarray, split: int, lags: int) -> np.ndarray:
    model = AutoReg(series[:split], lags=lags, trend="c", old_names=False).fit()
    predictions = []
    for index in range(split, len(series)):
        lag_values = np.array([series[index - lag] for lag in range(1, lags + 1)])
        predictions.append(float(model.params[0] + np.dot(model.params[1:], lag_values)))
    return np.asarray(predictions)


def analyze_signals(
    data: dict[str, pd.DataFrame], paths: dict[str, Path], snr_table: pd.DataFrame
) -> dict[str, Any]:
    energy = data["ener_clean"]
    energy_noise = data["ener_noise"]
    agro = data["agro_clean"]
    agro_noise = data["agro_noise"]

    clean_wind = energy["Ener_4"].to_numpy()
    noisy_wind = energy_noise["Ener_4"].to_numpy()
    frequencies, clean_psd = signal.welch(clean_wind, fs=1.0, nperseg=256, noverlap=128)
    _, noisy_psd = signal.welch(noisy_wind, fs=1.0, nperseg=256, noverlap=128)
    excess_psd = np.maximum(noisy_psd - clean_psd, 0)
    total_excess = float(np.trapezoid(excess_psd, frequencies))
    cumulative = np.cumsum((excess_psd[:-1] + excess_psd[1:]) / 2 * np.diff(frequencies))
    low_index = int(np.searchsorted(cumulative, 0.05 * total_excess))
    high_index = int(np.searchsorted(cumulative, 0.95 * total_excess))
    low_frequency = float(frequencies[1:][min(low_index, len(frequencies) - 2)])
    high_frequency = float(frequencies[1:][min(high_index, len(frequencies) - 2)])
    high_mask = frequencies >= 0.1
    high_power_ratio = float(
        np.trapezoid(noisy_psd[high_mask], frequencies[high_mask])
        / np.trapezoid(clean_psd[high_mask], frequencies[high_mask])
    )
    high_power_gain_db = float(10 * np.log10(high_power_ratio))

    psd_table = pd.DataFrame(
        {
            "frequency_cycles_per_record": frequencies,
            "psd_clean": clean_psd,
            "psd_noise": noisy_psd,
            "psd_excess": excess_psd,
        }
    )
    psd_table.to_csv(paths["tables"] / "ener4_power_spectrum.csv", index=False)

    fig, ax = plt.subplots(figsize=(10.5, 5.2), constrained_layout=True)
    floor = np.finfo(float).tiny
    ax.semilogy(frequencies, np.maximum(clean_psd, floor), label="Clean", color=NAVY, linewidth=2)
    ax.semilogy(frequencies, np.maximum(noisy_psd, floor), label="Noise", color=ORANGE, alpha=0.85)
    ax.axvspan(low_frequency, high_frequency, color=ORANGE, alpha=0.12, label="90% potencia excedente")
    ax.set_title("Densidad espectral de potencia - Ener_4")
    ax.set_xlabel("Frecuencia (ciclos por registro)")
    ax.set_ylabel("PSD (escala logaritmica)")
    ax.legend(ncol=3)
    fig.savefig(paths["figures"] / "04_fft_ener4.png", bbox_inches="tight")
    plt.close(fig)

    f_clean, t_clean, s_clean = signal.spectrogram(
        clean_wind, fs=1.0, nperseg=128, noverlap=96, scaling="density"
    )
    f_noise, t_noise, s_noise = signal.spectrogram(
        noisy_wind, fs=1.0, nperseg=128, noverlap=96, scaling="density"
    )
    combined = np.concatenate([10 * np.log10(s_clean + 1e-12), 10 * np.log10(s_noise + 1e-12)])
    vmin, vmax = np.quantile(combined, [0.02, 0.98])
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.1), sharey=True, constrained_layout=True)
    clean_mesh = axes[0].pcolormesh(
        t_clean,
        f_clean,
        10 * np.log10(s_clean + 1e-12),
        shading="auto",
        cmap="viridis",
        vmin=vmin,
        vmax=vmax,
    )
    axes[0].set_title("Ener_4 clean")
    axes[0].set_ylabel("Frecuencia (ciclos/registro)")
    noise_mesh = axes[1].pcolormesh(
        t_noise,
        f_noise,
        10 * np.log10(s_noise + 1e-12),
        shading="auto",
        cmap="viridis",
        vmin=vmin,
        vmax=vmax,
    )
    axes[1].set_title("Ener_4 noise")
    for ax in axes:
        ax.set_xlabel("Registro")
        ax.axhline(low_frequency, color="white", linestyle="--", linewidth=1)
        ax.axhline(high_frequency, color="white", linestyle="--", linewidth=1)
    fig.colorbar(noise_mesh, ax=axes, label="Potencia (dB)", shrink=0.9)
    fig.suptitle("Espectrogramas comparables con una escala comun", color=NAVY, fontsize=15, fontweight="bold")
    fig.savefig(paths["figures"] / "05_espectrogramas_ener4.png", bbox_inches="tight")
    plt.close(fig)

    clean_humidity = agro["Agro_3"].to_numpy()
    noisy_humidity = agro_noise["Agro_3"].to_numpy()
    calibration_end = int(0.60 * len(clean_humidity))
    cutoff_grid = np.linspace(0.0025, 0.10, 40)
    candidates: list[tuple[float, float]] = []
    for cutoff in cutoff_grid:
        sos = signal.butter(4, cutoff, btype="low", fs=1.0, output="sos")
        calibration_filtered = signal.sosfiltfilt(sos, noisy_humidity[:calibration_end])
        calibration_rmse = float(
            np.sqrt(np.mean((calibration_filtered - clean_humidity[:calibration_end]) ** 2))
        )
        candidates.append((calibration_rmse, float(cutoff)))
    _, selected_cutoff = min(candidates)

    # Comparacion de orden del Butterworth (H6): a igual frecuencia de corte, se mide
    # RMSE de reconstruccion, atenuacion en 2x el corte (empinamiento del rolloff) y el
    # sobreimpulso (ringing) de la respuesta al escalon, ya que filtfilt cancela el
    # desfase pero no el sobreimpulso propio de un orden alto.
    order_rows = []
    step_input = np.concatenate([np.zeros(60), np.ones(140)])
    for order in (2, 4, 6):
        order_sos = signal.butter(order, selected_cutoff, btype="low", fs=1.0, output="sos")
        order_filtered = signal.sosfiltfilt(order_sos, noisy_humidity)
        order_rmse = float(np.sqrt(np.mean((order_filtered - clean_humidity) ** 2)))
        _, magnitude = signal.sosfreqz(order_sos, worN=[selected_cutoff * 2], fs=1.0)
        attenuation_2x_cutoff_db = float(20 * np.log10(np.abs(magnitude[0]) + 1e-12))
        step_response = signal.sosfilt(order_sos, step_input)
        overshoot_pct = float(100 * max(0.0, step_response.max() - 1.0))
        order_rows.append(
            {
                "order": order,
                "cutoff_cycles_per_record": selected_cutoff,
                "reconstruction_rmse": order_rmse,
                "attenuation_at_2x_cutoff_db": attenuation_2x_cutoff_db,
                "step_overshoot_pct": overshoot_pct,
            }
        )
    butterworth_order_table = pd.DataFrame(order_rows)
    butterworth_order_table.to_csv(paths["tables"] / "butterworth_orden.csv", index=False)

    sos = signal.butter(4, selected_cutoff, btype="low", fs=1.0, output="sos")
    filtered_humidity = signal.sosfiltfilt(sos, noisy_humidity)
    raw_rmse = float(np.sqrt(np.mean((noisy_humidity - clean_humidity) ** 2)))
    filtered_rmse = float(np.sqrt(np.mean((filtered_humidity - clean_humidity) ** 2)))

    # Evaluacion temporal sin mirar el futuro: al estimar cada punto filtrado se usa solo su historia.
    split = int(0.80 * len(clean_humidity))
    lags = 24
    raw_predictions = _one_step_autoreg_predictions(noisy_humidity, split, lags)
    filtered_train = signal.sosfiltfilt(sos, noisy_humidity[:split])
    filtered_model = AutoReg(filtered_train, lags=lags, trend="c", old_names=False).fit()
    filtered_predictions = []
    for index in range(split, len(noisy_humidity)):
        past_only_filtered = signal.sosfiltfilt(sos, noisy_humidity[:index])
        lag_values = np.array(
            [past_only_filtered[-lag] for lag in range(1, lags + 1)]
        )
        filtered_predictions.append(
            float(filtered_model.params[0] + np.dot(filtered_model.params[1:], lag_values))
        )
    filtered_predictions = np.asarray(filtered_predictions)
    holdout_truth = clean_humidity[split:]
    prediction_raw_rmse = float(np.sqrt(np.mean((raw_predictions - holdout_truth) ** 2)))
    prediction_filtered_rmse = float(
        np.sqrt(np.mean((filtered_predictions - holdout_truth) ** 2))
    )

    pd.DataFrame(
        {
            "registro": np.arange(len(clean_humidity)),
            "agro3_clean": clean_humidity,
            "agro3_noise": noisy_humidity,
            "agro3_filtered": filtered_humidity,
        }
    ).to_csv(paths["tables"] / "agro3_filtered.csv", index=False)

    view = slice(0, 420)
    fig, axes = plt.subplots(2, 1, figsize=(12, 7.5), constrained_layout=True)
    axes[0].plot(clean_humidity[view], color=NAVY, linewidth=2, label="Clean")
    axes[0].plot(noisy_humidity[view], color=GRAY, linewidth=0.8, alpha=0.65, label="Noise")
    axes[0].plot(filtered_humidity[view], color=ORANGE, linewidth=1.8, label="Butterworth")
    axes[0].set_title("Reconstruccion offline de Agro_3")
    axes[0].set_ylabel("Humedad relativa")
    axes[0].legend(ncol=3)
    axes[1].bar(
        ["Entrada ruidosa", "Filtrada offline"],
        [raw_rmse, filtered_rmse],
        color=[GRAY, TEAL],
        label="Reconstruccion",
    )
    axes[1].scatter(
        [0, 1],
        [prediction_raw_rmse, prediction_filtered_rmse],
        color=[RED, ORANGE],
        s=90,
        zorder=5,
        label="Prediccion un paso",
    )
    axes[1].set_title("RMSE: reconstruccion no equivale a mejora predictiva")
    axes[1].set_ylabel("RMSE contra Agro_3 clean")
    axes[1].legend()
    fig.savefig(paths["figures"] / "06_filtro_agro3.png", bbox_inches="tight")
    plt.close(fig)

    ener4_snr = float(snr_table.loc[snr_table["series"] == "Ener_4", "snr_db"].iloc[0])
    return {
        "ener4": {
            "empirical_snr_db": ener4_snr,
            "excess_power_90_band": [low_frequency, high_frequency],
            "nyquist": 0.5,
            "high_frequency_power_gain_db": high_power_gain_db,
            "interpretation": "broadband_awgn",
        },
        "agro3_filter": {
            "order": 4,
            "order_justification": "order_comparison_table",
            "order_comparison": order_rows,
            "selected_cutoff_cycles_per_record": selected_cutoff,
            "calibration_fraction": 0.60,
            "raw_rmse": raw_rmse,
            "filtered_rmse": filtered_rmse,
            "reconstruction_improvement_pct": float(100 * (raw_rmse - filtered_rmse) / raw_rmse),
            "prediction_lags": lags,
            "prediction_raw_rmse": prediction_raw_rmse,
            "prediction_filtered_rmse": prediction_filtered_rmse,
            "prediction_improved": bool(prediction_filtered_rmse < prediction_raw_rmse),
        },
    }


def _build_weighted_digraph(frame: pd.DataFrame) -> nx.DiGraph:
    edges = frame.groupby(["Source_Node", "Target_Node"]).size().rename("weight").reset_index()
    graph = nx.DiGraph()
    for row in edges.itertuples(index=False):
        graph.add_edge(int(row.Source_Node), int(row.Target_Node), weight=int(row.weight))
    return graph


def analyze_graphs(data: dict[str, pd.DataFrame], paths: dict[str, Path]) -> dict[str, Any]:
    energy = data["ener_clean"]
    graph = _build_weighted_digraph(energy)
    degree = nx.degree_centrality(graph)
    betweenness = nx.betweenness_centrality(graph, normalized=True)
    traffic = dict(graph.degree(weight="weight"))
    undirected = graph.to_undirected()
    undirected_betweenness = nx.betweenness_centrality(undirected, normalized=True)
    bridges = list(nx.bridges(undirected))

    nodes = sorted(graph.nodes())
    centrality = pd.DataFrame(
        {
            "node": nodes,
            "role": ["Source" if node in set(energy["Source_Node"]) else "Target" for node in nodes],
            "degree_centrality": [degree[node] for node in nodes],
            "directed_betweenness": [betweenness[node] for node in nodes],
            "undirected_betweenness_sensitivity": [undirected_betweenness[node] for node in nodes],
            "traffic_weight": [traffic[node] for node in nodes],
        }
    )
    centrality.to_csv(paths["tables"] / "centrality_energy.csv", index=False)

    traffic_bottleneck = int(max(traffic, key=traffic.get))
    sensitivity_bottleneck = int(max(undirected_betweenness, key=undirected_betweenness.get))

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), constrained_layout=True)
    top_traffic = centrality.nlargest(10, "traffic_weight").sort_values("traffic_weight")
    axes[0].barh(top_traffic["node"].astype(str), top_traffic["traffic_weight"], color=BLUE)
    axes[0].barh(
        str(traffic_bottleneck),
        traffic[traffic_bottleneck],
        color=ORANGE,
    )
    axes[0].set_title("Top 10 por trafico observado")
    axes[0].set_xlabel("Numero de registros incidentes")
    axes[0].set_ylabel("Nodo")

    top_between = centrality.nlargest(10, "undirected_betweenness_sensitivity").sort_values(
        "undirected_betweenness_sensitivity"
    )
    axes[1].barh(
        top_between["node"].astype(str),
        top_between["undirected_betweenness_sensitivity"],
        color=TEAL,
    )
    axes[1].barh(
        str(sensitivity_bottleneck),
        undirected_betweenness[sensitivity_bottleneck],
        color=ORANGE,
    )
    axes[1].set_title("Sensibilidad: betweenness no dirigido")
    axes[1].set_xlabel("Betweenness normalizado")
    axes[1].set_ylabel("Nodo")
    fig.suptitle("Centralidad y cuello de botella de la red energetica", color=NAVY, fontsize=15, fontweight="bold")
    fig.savefig(paths["figures"] / "07_centralidad_red.png", bbox_inches="tight")
    plt.close(fig)

    sources = sorted(set(energy["Source_Node"]))
    targets = sorted(set(energy["Target_Node"]))
    positions = {
        **{node: (0, index) for index, node in enumerate(sources)},
        **{
            node: (1, index * (max(len(sources) - 1, 1) / max(len(targets) - 1, 1)))
            for index, node in enumerate(targets)
        },
    }
    fig, ax = plt.subplots(figsize=(12.5, 8), constrained_layout=True)
    nx.draw_networkx_edges(graph, positions, ax=ax, alpha=0.055, width=0.6, arrows=False, edge_color=GRAY)
    source_sizes = [90 + 7 * traffic[node] for node in sources]
    target_sizes = [55 + 7 * traffic[node] for node in targets]
    nx.draw_networkx_nodes(graph, positions, nodelist=sources, node_color=BLUE, node_size=source_sizes, ax=ax)
    nx.draw_networkx_nodes(graph, positions, nodelist=targets, node_color=TEAL, node_size=target_sizes, ax=ax)
    nx.draw_networkx_nodes(
        graph,
        positions,
        nodelist=[traffic_bottleneck],
        node_color=ORANGE,
        node_size=140 + 8 * traffic[traffic_bottleneck],
        edgecolors="white",
        linewidths=2,
        ax=ax,
    )
    labels_to_show = {node: str(node) for node in set([traffic_bottleneck, 214] + sources)}
    nx.draw_networkx_labels(graph, positions, labels=labels_to_show, font_size=7, font_color="black", ax=ax)
    ax.text(0, len(sources) + 1, "Source nodes", ha="center", color=BLUE, fontweight="bold")
    ax.text(1, len(sources) + 1, "Target nodes", ha="center", color=TEAL, fontweight="bold")
    ax.set_title("Red bipartita dirigida (tamano = trafico; naranja = nodo 119)", color=NAVY)
    ax.axis("off")
    fig.savefig(paths["figures"] / "08_red_energia.png", bbox_inches="tight")
    plt.close(fig)

    threshold = float(energy["Ener_2"].quantile(0.95))
    high_price = energy["Ener_2"] > threshold
    target_214 = energy["Target_Node"] == 214
    contingency = pd.crosstab(high_price, target_214).reindex(
        index=[False, True], columns=[False, True], fill_value=0
    )
    odds_ratio, fisher_p = stats.fisher_exact(contingency)
    temp_test = stats.ttest_ind(
        energy.loc[target_214, "Ener_3"],
        energy.loc[~target_214, "Ener_3"],
        equal_var=False,
    )
    normal_rate = float(contingency.loc[False, True] / contingency.loc[False].sum())
    high_rate = float(contingency.loc[True, True] / contingency.loc[True].sum())

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.6), constrained_layout=True)
    axes[0].bar(["Precio <= P95", "Precio > P95"], [normal_rate, high_rate], color=[BLUE, ORANGE])
    axes[0].set_title("Frecuencia relativa de Target 214")
    axes[0].set_ylabel("Proporcion de registros")
    axes[0].tick_params(axis="x", rotation=10)
    temp_means = [
        energy.loc[~target_214, "Ener_3"].mean(),
        energy.loc[target_214, "Ener_3"].mean(),
    ]
    temp_se = [
        stats.sem(energy.loc[~target_214, "Ener_3"]),
        stats.sem(energy.loc[target_214, "Ener_3"]),
    ]
    axes[1].bar(["Otros targets", "Target 214"], temp_means, yerr=temp_se, color=[TEAL, ORANGE], capsize=4)
    axes[1].set_title("Temperatura media (Ener_3)")
    axes[1].set_ylabel("Temperatura")
    axes[1].set_ylim(min(temp_means) - 1.2, max(temp_means) + 1.2)
    fig.suptitle("Auditoria de la hipotesis narrativa del nodo 214", color=NAVY, fontsize=14, fontweight="bold")
    fig.savefig(paths["figures"] / "09_nodo214.png", bbox_inches="tight")
    plt.close(fig)

    return {
        "nodes": graph.number_of_nodes(),
        "unique_edges": graph.number_of_edges(),
        "is_directed_acyclic": bool(nx.is_directed_acyclic_graph(graph)),
        "directed_betweenness_max": float(max(betweenness.values())),
        "directed_betweenness_ties_at_max": int(
            sum(np.isclose(value, max(betweenness.values())) for value in betweenness.values())
        ),
        "traffic_bottleneck": traffic_bottleneck,
        "traffic_bottleneck_records": int(traffic[traffic_bottleneck]),
        "sensitivity_bottleneck": sensitivity_bottleneck,
        "sensitivity_betweenness": float(undirected_betweenness[sensitivity_bottleneck]),
        "bridges_undirected": [[int(left), int(right)] for left, right in bridges],
        "node_214": {
            "degree_centrality": float(degree.get(214, 0.0)),
            "directed_betweenness": float(betweenness.get(214, 0.0)),
            "undirected_betweenness": float(undirected_betweenness.get(214, 0.0)),
            "traffic_records": int(traffic.get(214, 0)),
            "spot_price_p95": threshold,
            "normal_price_target_rate": normal_rate,
            "high_price_target_rate": high_rate,
            "high_price_odds_ratio": float(odds_ratio),
            "fisher_p": float(fisher_p),
            "temperature_mean": float(energy.loc[target_214, "Ener_3"].mean()),
            "temperature_others_mean": float(energy.loc[~target_214, "Ener_3"].mean()),
            "temperature_difference": float(
                energy.loc[target_214, "Ener_3"].mean()
                - energy.loc[~target_214, "Ener_3"].mean()
            ),
            "temperature_test_p": float(temp_test.pvalue),
        },
    }


def _granger_result(frame: pd.DataFrame, cause: str, effect: str, lag: int) -> dict[str, float]:
    result = grangercausalitytests(frame[[effect, cause]], maxlag=[lag], verbose=False)[lag][0][
        "ssr_ftest"
    ]
    return {"lag": lag, "f_statistic": float(result[0]), "p_value": float(result[1])}


def analyze_models(
    data: dict[str, pd.DataFrame],
    paths: dict[str, Path],
    stationarity: dict[str, Any],
) -> dict[str, Any]:
    energy = data["ener_clean"]
    graph = _build_weighted_digraph(energy)
    degree = nx.degree_centrality(graph)

    selected = VAR(energy[["Ener_9", "Ener_10"]]).select_order(10)
    selected_lag = max(1, int(selected.selected_orders["aic"] or 1))
    pf_to_voltage = _granger_result(energy, "Ener_10", "Ener_9", selected_lag)
    voltage_to_pf = _granger_result(energy, "Ener_9", "Ener_10", selected_lag)
    pd.DataFrame(
        [
            {"direction": "Ener_10 -> Ener_9", **pf_to_voltage},
            {"direction": "Ener_9 -> Ener_10", **voltage_to_pf},
        ]
    ).to_csv(paths["tables"] / "granger_results.csv", index=False)

    exogenous = pd.DataFrame(
        {
            "temperature": energy["Ener_3"],
            "source_degree_centrality": energy["Source_Node"].map(degree),
        }
    )
    exogenous = (exogenous - exogenous.mean()) / exogenous.std(ddof=0)
    demand_d = 1 if "Ener_1" in stationarity["nonstationary_series"] else 0
    trend = "t" if demand_d == 1 else "c"

    best: tuple[float, int, int, Any] | None = None
    for p_value in range(3):
        for q_value in range(3):
            if p_value == 0 and q_value == 0:
                continue
            try:
                model = SARIMAX(
                    energy["Ener_1"],
                    exog=exogenous[["temperature"]],
                    order=(p_value, demand_d, q_value),
                    trend=trend,
                    enforce_stationarity=False,
                    enforce_invertibility=False,
                ).fit(disp=False, maxiter=200)
                if best is None or model.aic < best[0]:
                    best = (float(model.aic), p_value, q_value, model)
            except (ValueError, np.linalg.LinAlgError):
                continue
    if best is None:
        raise RuntimeError("No fue posible ajustar ningun ARIMAX candidato")
    base_aic, p_order, q_order, base_model = best
    extended_model = SARIMAX(
        energy["Ener_1"],
        exog=exogenous[["temperature", "source_degree_centrality"]],
        order=(p_order, demand_d, q_order),
        trend=trend,
        enforce_stationarity=False,
        enforce_invertibility=False,
    ).fit(disp=False, maxiter=200)

    split = int(0.80 * len(energy))
    train_mean = pd.DataFrame(
        {
            "temperature": energy.loc[: split - 1, "Ener_3"],
            "source_degree_centrality": energy.loc[: split - 1, "Source_Node"].map(degree),
        }
    ).mean()
    train_std = pd.DataFrame(
        {
            "temperature": energy.loc[: split - 1, "Ener_3"],
            "source_degree_centrality": energy.loc[: split - 1, "Source_Node"].map(degree),
        }
    ).std(ddof=0)
    exog_holdout = pd.DataFrame(
        {
            "temperature": energy["Ener_3"],
            "source_degree_centrality": energy["Source_Node"].map(degree),
        }
    )
    exog_holdout = (exog_holdout - train_mean) / train_std

    holdout_results = {}
    holdout_predictions = {}
    for label, columns in (
        ("temperature", ["temperature"]),
        ("temperature_centrality", ["temperature", "source_degree_centrality"]),
    ):
        model = SARIMAX(
            energy["Ener_1"].iloc[:split],
            exog=exog_holdout[columns].iloc[:split],
            order=(p_order, demand_d, q_order),
            trend=trend,
            enforce_stationarity=False,
            enforce_invertibility=False,
        ).fit(disp=False, maxiter=200)
        prediction = model.get_forecast(
            len(energy) - split, exog=exog_holdout[columns].iloc[split:]
        ).predicted_mean.to_numpy()
        truth = energy["Ener_1"].iloc[split:].to_numpy()
        holdout_predictions[label] = prediction
        holdout_results[label] = {
            "rmse": float(np.sqrt(np.mean((prediction - truth) ** 2))),
            "mae": float(np.mean(np.abs(prediction - truth))),
        }

    comparison = pd.DataFrame(
        [
            {
                "model": "ARIMAX temperatura",
                "order": f"({p_order},{demand_d},{q_order})",
                "aic_full": base_aic,
                **holdout_results["temperature"],
            },
            {
                "model": "ARIMAX temperatura + centralidad",
                "order": f"({p_order},{demand_d},{q_order})",
                "aic_full": float(extended_model.aic),
                **holdout_results["temperature_centrality"],
            },
        ]
    )
    comparison.to_csv(paths["tables"] / "arimax_comparison.csv", index=False)

    x_axis = np.arange(split, len(energy))
    fig, ax = plt.subplots(figsize=(11.5, 5.2), constrained_layout=True)
    ax.plot(x_axis, energy["Ener_1"].iloc[split:], color=NAVY, linewidth=2, label="Demanda observada")
    ax.plot(x_axis, holdout_predictions["temperature"], color=GRAY, linestyle="--", label="Temperatura")
    ax.plot(
        x_axis,
        holdout_predictions["temperature_centrality"],
        color=ORANGE,
        linewidth=1.6,
        label="Temperatura + centralidad",
    )
    ax.set_title("Validacion temporal ARIMAX - ultimo 20%")
    ax.set_xlabel("Registro")
    ax.set_ylabel("Demanda (Ener_1)")
    ax.legend(ncol=3)
    fig.savefig(paths["figures"] / "10_arimax.png", bbox_inches="tight")
    plt.close(fig)

    return {
        "granger": {
            "lag_selection": "VAR_AIC",
            "selected_lag": selected_lag,
            "power_factor_to_voltage": pf_to_voltage,
            "voltage_to_power_factor": voltage_to_pf,
        },
        "arimax": {
            "order": [p_order, demand_d, q_order],
            "aic_temperature": base_aic,
            "aic_temperature_centrality": float(extended_model.aic),
            "delta_aic_extended_minus_base": float(extended_model.aic - base_aic),
            "centrality_coefficient": float(extended_model.params["source_degree_centrality"]),
            "centrality_p_value": float(extended_model.pvalues["source_degree_centrality"]),
            "holdout": holdout_results,
        },
    }


def analyze_validation_questions(
    data: dict[str, pd.DataFrame],
    paths: dict[str, Path],
    snr_table: pd.DataFrame,
    geo: dict[str, Any],
    graphs: dict[str, Any],
) -> dict[str, Any]:
    energy = data["ener_clean"]
    agro = data["agro_clean"]
    agro_noise = data["agro_noise"]

    level_correlation = float(energy["Ener_5"].corr(energy["Ener_6"]))
    difference_correlation = float(energy["Ener_5"].diff().corr(energy["Ener_6"].diff()))

    closest_row = snr_table.iloc[(snr_table["snr_db"] - 5.0).abs().argsort()[:1]].iloc[0]
    series = str(closest_row["series"])
    clean_series = agro[series] if series.startswith("Agro") else energy[series]
    noisy_series = agro_noise[series] if series.startswith("Agro") else data["ener_noise"][series]
    clean_model = ARIMA(
        clean_series,
        order=(2, 1, 1),
        trend="t",
        enforce_stationarity=False,
        enforce_invertibility=False,
    ).fit(method_kwargs={"maxiter": 500})
    noisy_model = ARIMA(
        noisy_series,
        order=(2, 1, 1),
        trend="t",
        enforce_stationarity=False,
        enforce_invertibility=False,
    ).fit(method_kwargs={"maxiter": 500})
    coefficient_names = ["ar.L1", "ar.L2", "ma.L1"]
    clean_coefficients = {name: float(clean_model.params[name]) for name in coefficient_names}
    noisy_coefficients = {name: float(noisy_model.params[name]) for name in coefficient_names}
    coefficient_shift = float(
        math.sqrt(
            sum((clean_coefficients[name] - noisy_coefficients[name]) ** 2 for name in coefficient_names)
        )
    )

    coefficient_table = pd.DataFrame(
        {
            "coefficient": coefficient_names,
            "clean": [clean_coefficients[name] for name in coefficient_names],
            "noise": [noisy_coefficients[name] for name in coefficient_names],
        }
    )
    coefficient_table.to_csv(paths["tables"] / "arma_5db_coefficients.csv", index=False)
    positions = np.arange(len(coefficient_names))
    width = 0.36
    fig, ax = plt.subplots(figsize=(8.5, 4.8), constrained_layout=True)
    ax.bar(positions - width / 2, coefficient_table["clean"], width, label="Clean", color=NAVY)
    ax.bar(positions + width / 2, coefficient_table["noise"], width, label="Noise", color=ORANGE)
    ax.axhline(0, color=GRAY, linewidth=0.8)
    ax.set_xticks(positions, coefficient_names)
    ax.set_ylabel("Coeficiente estimado")
    ax.set_title(f"Impacto del ruido de {closest_row['snr_db']:.2f} dB en ARIMA(2,1,1) de {series}")
    ax.legend()
    fig.savefig(paths["figures"] / "11_snr_arma.png", bbox_inches="tight")
    plt.close(fig)

    return {
        "spurious_correlation": {
            "pair": "Ener_5_vs_Ener_6",
            "level_correlation": level_correlation,
            "first_difference_correlation": difference_correlation,
        },
        "snr_5db_arma": {
            "series": series,
            "empirical_snr_db": float(closest_row["snr_db"]),
            "model_order": [2, 1, 1],
            "clean_coefficients": clean_coefficients,
            "noise_coefficients": noisy_coefficients,
            "coefficient_l2_shift": coefficient_shift,
            "clean_aic": float(clean_model.aic),
            "noise_aic": float(noisy_model.aic),
        },
        "topology_bridge": {
            "observed_bridges": graphs["bridges_undirected"],
            "bridge_count": len(graphs["bridges_undirected"]),
            "conditional_interpretation": "A bridge failure would split connectivity, but no bridge is observed.",
        },
        "geo_variance": {
            "wind_variance_levene_p": geo["wind_variance_levene_p"],
            "observed_position_effect": bool(geo["wind_variance_levene_p"] < 0.05),
        },
    }


def _to_builtin(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _to_builtin(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_builtin(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, Path):
        return str(value)
    if pd.isna(value) if not isinstance(value, (list, dict, tuple)) else False:
        return None
    return value


def run_analysis(root: Path) -> dict[str, Any]:
    """Ejecuta el flujo completo y devuelve todas las metricas serializables."""

    # Semilla global explicita (SEED=42): cubre cualquier uso incidental de np.random
    # ademas de los usos locales ya sembrados (KMeans en analyze_geospatial, rng de
    # la prueba por permutaciones). No hay generacion sintetica de ruido en el pipeline:
    # las columnas "noise" provienen integramente de agro_noise.csv / ener_noise.csv.
    np.random.seed(SEED)
    _configure_plots()
    paths = output_paths(root)
    data = load_datasets(root)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        audit = audit_datasets(data, paths)
        snr_table = empirical_snr_table(data, paths)
        geo = analyze_geospatial(data, paths)
        stationarity = analyze_stationarity(data, paths)
        signals = analyze_signals(data, paths, snr_table)
        graphs = analyze_graphs(data, paths)
        models = analyze_models(data, paths, stationarity)
        validation = analyze_validation_questions(data, paths, snr_table, geo, graphs)

    metrics = _to_builtin(
        {
            "metadata": {
                "seed": SEED,
                "time_axis": "row_order",
                "frequency_unit": "cycles_per_record",
                "critical_spot_threshold_rule": "Ener_2_percentile_95",
            },
            "audit": audit,
            "geo": geo,
            "stationarity": stationarity,
            "signals": signals,
            "graphs": graphs,
            "models": models,
            "validation": validation,
        }
    )
    with (paths["output"] / "metrics.json").open("w", encoding="utf-8") as stream:
        json.dump(metrics, stream, ensure_ascii=False, indent=2)
    return metrics


if __name__ == "__main__":
    run_analysis(Path(__file__).resolve().parents[1])

