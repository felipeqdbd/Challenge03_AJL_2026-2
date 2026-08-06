"""Construccion del informe tecnico ejecutivo en PDF."""

from __future__ import annotations

import json
from pathlib import Path
from xml.sax.saxutils import escape

from matplotlib import font_manager
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


NAVY = colors.HexColor("#003B70")
BLUE = colors.HexColor("#1479B8")
ORANGE = colors.HexColor("#D05A00")
TEAL = colors.HexColor("#188977")
PALE_BLUE = colors.HexColor("#EAF2F8")
PALE_ORANGE = colors.HexColor("#FFF2E8")
LIGHT_GRAY = colors.HexColor("#F2F4F7")
MID_GRAY = colors.HexColor("#667085")
DARK = colors.HexColor("#172B4D")


def _register_fonts() -> None:
    regular = font_manager.findfont("DejaVu Sans")
    bold = font_manager.findfont(font_manager.FontProperties(family="DejaVu Sans", weight="bold"))
    italic = font_manager.findfont(font_manager.FontProperties(family="DejaVu Sans", style="italic"))
    pdfmetrics.registerFont(TTFont("DV", regular))
    pdfmetrics.registerFont(TTFont("DV-Bold", bold))
    pdfmetrics.registerFont(TTFont("DV-Italic", italic))


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ReportTitle",
            parent=base["Title"],
            fontName="DV-Bold",
            fontSize=25,
            leading=30,
            textColor=NAVY,
            alignment=TA_CENTER,
            spaceAfter=12,
        ),
        "subtitle": ParagraphStyle(
            "ReportSubtitle",
            parent=base["Normal"],
            fontName="DV-Bold",
            fontSize=15,
            leading=19,
            textColor=ORANGE,
            alignment=TA_CENTER,
        ),
        "h1": ParagraphStyle(
            "ReportH1",
            parent=base["Heading1"],
            fontName="DV-Bold",
            fontSize=17,
            leading=21,
            textColor=NAVY,
            spaceBefore=8,
            spaceAfter=7,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "ReportH2",
            parent=base["Heading2"],
            fontName="DV-Bold",
            fontSize=12.5,
            leading=16,
            textColor=ORANGE,
            spaceBefore=7,
            spaceAfter=5,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "ReportBody",
            parent=base["BodyText"],
            fontName="DV",
            fontSize=9.3,
            leading=13.2,
            textColor=DARK,
            alignment=TA_JUSTIFY,
            spaceAfter=6,
        ),
        "small": ParagraphStyle(
            "ReportSmall",
            parent=base["BodyText"],
            fontName="DV",
            fontSize=7.7,
            leading=10.2,
            textColor=DARK,
        ),
        "caption": ParagraphStyle(
            "ReportCaption",
            parent=base["BodyText"],
            fontName="DV-Italic",
            fontSize=7.8,
            leading=10.5,
            textColor=MID_GRAY,
            alignment=TA_CENTER,
            spaceBefore=3,
            spaceAfter=7,
        ),
        "callout": ParagraphStyle(
            "ReportCallout",
            parent=base["BodyText"],
            fontName="DV-Bold",
            fontSize=9.4,
            leading=13,
            textColor=NAVY,
            alignment=TA_LEFT,
        ),
        "cover": ParagraphStyle(
            "ReportCover",
            parent=base["BodyText"],
            fontName="DV",
            fontSize=11,
            leading=16,
            textColor=DARK,
            alignment=TA_CENTER,
        ),
    }


def _paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text, style)


def _format_p_value(value: float, spec: str) -> str:
    """Formatea un p-valor; si hizo underflow a 0.0 lo marca como '< 1e-30'."""
    if value == 0.0:
        return "< 1e-30"
    return format(value, spec)


def _section_title(number: str, title: str, styles: dict[str, ParagraphStyle]):
    return [
        _paragraph(f"{number} {title}", styles["h1"]),
        HRFlowable(width="100%", thickness=0.8, color=NAVY, spaceAfter=7),
    ]


def _figure(
    path: Path,
    caption: str,
    styles: dict[str, ParagraphStyle],
    width: float = 17.0 * cm,
    height: float | None = None,
):
    if height is None:
        with PILImage.open(path) as source:
            pixel_width, pixel_height = source.size
        height = width * pixel_height / pixel_width
    image = Image(str(path), width=width, height=height)
    image.hAlign = "CENTER"
    return [image, _paragraph(caption, styles["caption"])]


def _data_table(
    rows: list[list[object]],
    styles: dict[str, ParagraphStyle],
    widths: list[float] | None = None,
    header: bool = True,
    font_size: float = 7.5,
) -> Table:
    converted = []
    for row_index, row in enumerate(rows):
        converted.append(
            [
                _paragraph(
                    escape(str(cell)),
                    ParagraphStyle(
                        f"table-{row_index}-{column_index}",
                        parent=styles["small"],
                        fontName="DV-Bold" if header and row_index == 0 else "DV",
                        fontSize=font_size,
                        leading=font_size + 2.1,
                        textColor=colors.white if header and row_index == 0 else DARK,
                    ),
                )
                for column_index, cell in enumerate(row)
            ]
        )
    table = Table(converted, colWidths=widths, repeatRows=1 if header else 0, hAlign="CENTER")
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D0D5DD")),
    ]
    if header:
        commands.append(("BACKGROUND", (0, 0), (-1, 0), NAVY))
        if len(rows) > 1:
            commands.append(("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]))
    table.setStyle(TableStyle(commands))
    return table


def _callout(text: str, styles: dict[str, ParagraphStyle], color=PALE_BLUE) -> Table:
    table = Table([[_paragraph(text, styles["callout"])]], colWidths=[17.0 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), color),
                ("BOX", (0, 0), (-1, -1), 0.8, NAVY if color == PALE_BLUE else ORANGE),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


def _bullet_list(items: list[str], styles: dict[str, ParagraphStyle]) -> ListFlowable:
    return ListFlowable(
        [ListItem(_paragraph(item, styles["body"]), leftIndent=12) for item in items],
        bulletType="bullet",
        start="circle",
        leftIndent=18,
        bulletFontName="DV",
        bulletFontSize=7,
        spaceAfter=4,
    )


def _header_footer(canvas, doc) -> None:
    canvas.saveState()
    width, height = A4
    if doc.page > 1:
        canvas.setFont("DV-Bold", 7.5)
        canvas.setFillColor(NAVY)
        canvas.drawString(2.0 * cm, height - 1.15 * cm, "Challenge 03 - Inteligencia Geo-Temporal y de Redes")
        canvas.setStrokeColor(colors.HexColor("#D0D5DD"))
        canvas.line(2.0 * cm, height - 1.35 * cm, width - 2.0 * cm, height - 1.35 * cm)
    canvas.setFont("DV", 7.2)
    canvas.setFillColor(MID_GRAY)
    canvas.drawString(2.0 * cm, 1.0 * cm, "EAFIT - Maestria en Ciencia de los Datos - Periodo 2026-1")
    canvas.drawRightString(width - 2.0 * cm, 1.0 * cm, f"Pagina {doc.page}")
    canvas.restoreState()


def build_report(root: Path, metrics: dict | None = None) -> Path:
    """Genera el PDF final y devuelve su ruta."""

    _register_fonts()
    styles = _styles()
    if metrics is None:
        with (root / "output" / "metrics.json").open(encoding="utf-8") as stream:
            metrics = json.load(stream)

    figures = root / "output" / "figures"
    destination = root / "output" / "pdf" / "informe_tecnico.pdf"
    destination.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(destination),
        pagesize=A4,
        leftMargin=2.0 * cm,
        rightMargin=2.0 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.6 * cm,
        title="Informe tecnico - Challenge 03",
        author="Entrega academica EAFIT",
        subject="Inteligencia Geo-Temporal y de Redes",
    )

    geo = metrics["geo"]
    stationary = metrics["stationarity"]
    ener5 = stationary["ener5"]
    signals = metrics["signals"]
    filt = signals["agro3_filter"]
    graph = metrics["graphs"]
    node214 = graph["node_214"]
    models = metrics["models"]
    validation = metrics["validation"]

    story = []

    # Portada
    story += [Spacer(1, 2.0 * cm)]
    story.append(_paragraph("INFORME TECNICO EJECUTIVO", styles["subtitle"]))
    story.append(Spacer(1, 0.35 * cm))
    story.append(_paragraph("Inteligencia Geo-Temporal y de Redes", styles["title"]))
    story.append(_paragraph("Optimizacion de Activos Criticos - TechLogistics S.A.", styles["subtitle"]))
    story.append(Spacer(1, 1.2 * cm))
    story.append(HRFlowable(width="75%", thickness=2, color=NAVY, hAlign="CENTER"))
    story.append(Spacer(1, 0.8 * cm))
    story.append(
        _paragraph(
            "Metodologia: CRISP-DM / Analisis multicapa<br/>"
            "Curso: Analisis de Datos Avanzado<br/>"
            "Docente: Jorge Ivan Padilla-Buritica<br/>"
            "Universidad EAFIT - Periodo 2026-1",
            styles["cover"],
        )
    )
    story.append(Spacer(1, 1.3 * cm))
    story.append(
        _callout(
            "Integrantes: Juan Jose Restrepo (C.C. 1193082063), Luis Felipe Quesada (C.C. 1005755239), "
            "Andres Velez Rendon (C.C. 1001371042)<br/>Fecha del analisis: agosto de 2026",
            styles,
            PALE_ORANGE,
        )
    )
    story.append(Spacer(1, 1.2 * cm))
    story.append(
        _paragraph(
            "Este documento separa evidencia observada, supuestos del enunciado y recomendaciones. "
            "Todas las cifras se regeneran desde los cuatro CSV mediante el pipeline incluido en el repositorio.",
            styles["cover"],
        )
    )
    story.append(PageBreak())

    # Resumen ejecutivo
    story += _section_title("1.", "Resumen ejecutivo", styles)
    summary_rows = [
        ["Dimension", "Resultado", "Decision"],
        [
            "Geo",
            f"eta^2 = {geo['eta_squared']:.4f}; p permutacion = {geo['permutation_p']:.3f}",
            "No declarar un hotspot espacial concluyente; priorizar una prueba piloto en el cluster de riesgo.",
        ],
        [
            "Tiempo",
            f"{len(stationary['nonstationary_series'])} de 10 series son I(1)",
            "Diferenciar antes de modelar y vigilar drift en el costo del gas.",
        ],
        [
            "Senal",
            f"RMSE Agro_3: {filt['raw_rmse']:.2f} -> {filt['filtered_rmse']:.2f}",
            "Usar Butterworth para reconstruccion offline; no asumir mejora predictiva.",
        ],
        [
            "Red",
            f"Nodo {graph['traffic_bottleneck']} lidera trafico; betweenness dirigido = 0",
            "Monitorear el nodo de mayor trafico y modelar enlaces bidireccionales si se requiere propagacion.",
        ],
        [
            "ARIMAX",
            f"Delta AIC al agregar centralidad = {models['arimax']['delta_aic_extended_minus_base']:+.2f}",
            "La centralidad no mejora el AIC; conservar el modelo parsimonioso.",
        ],
    ]
    story.append(_data_table(summary_rows, styles, [2.1 * cm, 5.2 * cm, 9.7 * cm], font_size=7.3))
    story.append(Spacer(1, 0.3 * cm))
    story.append(
        _callout(
            "Conclusión ejecutiva: la prioridad no es automatizar una alarma sobre el nodo 214, sino mejorar la "
            "instrumentación de flujo/interrupción, conservar el nodo 119 bajo observación y separar los filtros "
            "offline de los modelos que operan en tiempo real.",
            styles,
        )
    )
    story.append(Spacer(1, 0.35 * cm))
    story.append(_paragraph("Alcance y calidad de los datos", styles["h2"]))
    story.append(
        _paragraph(
            "Cada dataset contiene 2.000 filas y 14 columnas, sin nulos ni duplicados. El orden de fila se toma "
            "como eje temporal porque no existe timestamp. Las frecuencias se expresan en ciclos por registro. "
            "Las versiones clean y noise tienen exactamente las mismas aristas y los mismos nodos por fila; el "
            "jitter GPS afecta la latitud, no la topologia declarada.",
            styles["body"],
        )
    )
    story.append(
        _bullet_list(
            [
                "Umbral critico de Precio Spot: percentil 95 de Ener_2, porque el enunciado no entrega un valor numerico.",
                "Trafico: numero de registros incidentes por nodo; las aristas unicas se usan para centralidad.",
                "Significancia: alfa = 0.05; los resultados no significativos se reportan como ausencia de evidencia, no como prueba de inexistencia.",
            ],
            styles,
        )
    )
    story.append(PageBreak())

    # Geoespacial
    story += _section_title("2.", "Fase 1 - Geo-visualizacion y estacionariedad", styles)
    story.append(_paragraph("2.1 Exploracion espacial de NDVI y humedad", styles["h2"]))
    story += _figure(
        figures / "01_mapa_agro.png",
        "Figura 1. Color = NDVI (Agro_5); tamano = humedad (Agro_1). El repositorio tambien incluye la version interactiva HTML.",
        styles,
        width=16.5 * cm,
    )
    story.append(
        _paragraph(
            f"Los seis clusters K-means explican solo {100 * geo['eta_squared']:.2f}% de la varianza del NDVI. "
            f"La prueba por 499 permutaciones produce p = {geo['permutation_p']:.3f}; por tanto, no se identifica "
            "un cluster con biomasa consistentemente baja al 5%. El cluster de menor promedio y el de mayor "
            "riesgo operativo se muestran como priorizacion exploratoria, no como causalidad territorial.",
            styles["body"],
        )
    )
    story += _figure(
        figures / "02_prioridad_geo_agronoma.png",
        f"Figura 2. El cluster {geo['priority_cluster']} combina NDVI relativamente bajo y mayor varianza de viento bajo el supuesto de pendiente del enunciado.",
        styles,
        width=14.8 * cm,
    )
    story.append(PageBreak())

    story.append(_paragraph("2.2 ADF, ventana movil y naturaleza de Ener_5", styles["h2"]))
    adf_rows = [["Serie", "p nivel", "p primera diferencia", "Orden"]]
    for row in stationary["adf_table"]:
        adf_rows.append(
            [
                row["series"],
                _format_p_value(row["p_level"], ".4f"),
                _format_p_value(row["p_first_difference"], ".4g"),
                f"I({row['integration_order']})",
            ]
        )
    story.append(_data_table(adf_rows, styles, [3.2 * cm, 4.0 * cm, 5.4 * cm, 2.4 * cm], font_size=7.2))
    story.append(Spacer(1, 0.25 * cm))
    story.append(
        _paragraph(
            "Las series I(1) son " + ", ".join(stationary["nonstationary_series"]) + ". Se calcula media y "
            "varianza movil de 50 registros para todas ellas y se usa d = 1 en la Demanda antes del ARIMAX.",
            styles["body"],
        )
    )
    ener4_row = next(row for row in stationary["adf_table"] if row["series"] == "Ener_4")
    story.append(
        _paragraph(
            f"Nota metodologica sobre Ener_4: su estadistico ADF en nivel ({ener4_row['adf_level']:.3g}) tiene una "
            "magnitud fuera de escala frente a las demas nueve series y no es estable entre entornos de ejecucion "
            "(varia en miles de millones al reejecutar con otra version de las librerias numericas). La causa no "
            "es varianza casi nula (Ener_4 tiene varianza normal, en torno a 200): es una trayectoria muy suave y "
            "casi deterministica registro a registro, lo que casi colineariza la regresion interna del ADF y "
            "amplifica el redondeo de punto flotante en un estadistico que ya diverge. El p-valor asociado se "
            "satura en 0.0 en todos los entornos probados y la conclusion de estacionariedad (integration_order = "
            "0) no cambia: solo la magnitud cruda del estadistico depende del entorno, no la decision.",
            styles["body"],
        )
    )
    story += _figure(
        figures / "03_estacionariedad_ener5.png",
        "Figura 3. Ener_5 no rechaza raiz unitaria en nivel; sus incrementos son estacionarios y compatibles con ruido blanco alrededor de un drift positivo.",
        styles,
        width=15.7 * cm,
    )
    story.append(
        _callout(
            f"Diagnostico: ADF nivel p = {ener5['adf_level_p']:.3f}; ADF diferencia p < 0.001; "
            f"drift medio = {ener5['mean_increment']:.4f}; Ljung-Box(10) p = {ener5['ljung_box_lag10_p']:.3f}. "
            "La evidencia favorece random walk con drift positivo, no una tendencia determinista con errores independientes.",
            styles,
        )
    )
    story.append(PageBreak())

    # Senales
    story += _section_title("3.", "Fase 2 - Procesamiento de senales", styles)
    story.append(_paragraph("3.1 FFT, PSD y espectrogramas de Ener_4", styles["h2"]))
    story += _figure(
        figures / "04_fft_ener4.png",
        "Figura 4. Densidad espectral de potencia por Welch, equivalente a una FFT segmentada con menor varianza.",
        styles,
        width=15.8 * cm,
    )
    band = signals["ener4"]["excess_power_90_band"]
    story.append(
        _paragraph(
            f"El SNR empirico de Ener_4 es {signals['ener4']['empirical_snr_db']:.2f} dB. El 90% de la potencia "
            f"espectral excedente se distribuye entre {band[0]:.4f} y {band[1]:.4f} ciclos por registro, sobre un "
            "Nyquist de 0.5. La banda amplia y la ganancia de alta frecuencia son consistentes con AWGN, no con "
            "una interferencia sinusoidal localizada.",
            styles["body"],
        )
    )
    story += _figure(
        figures / "05_espectrogramas_ener4.png",
        "Figura 5. Escala de potencia comun: la version noise eleva el piso espectral a lo largo del tiempo y de casi toda la banda.",
        styles,
        width=16.3 * cm,
    )
    story.append(PageBreak())

    story.append(_paragraph("3.2 Butterworth y reconstruccion de Agro_3", styles["h2"]))
    story += _figure(
        figures / "06_filtro_agro3.png",
        "Figura 6. Butterworth paso bajo de orden 4; el corte se calibra en el primer 60% y se evalua contra la serie clean.",
        styles,
        width=16.3 * cm,
    )
    story.append(
        _paragraph(
            f"El corte seleccionado es {filt['selected_cutoff_cycles_per_record']:.4f} ciclos por registro. El "
            f"RMSE de reconstruccion cae de {filt['raw_rmse']:.3f} a {filt['filtered_rmse']:.3f}, una reduccion de "
            f"{filt['reconstruction_improvement_pct']:.1f}%. Sin embargo, en un AR(24) de un paso que solo usa "
            f"historia disponible, el RMSE cambia de {filt['prediction_raw_rmse']:.3f} a "
            f"{filt['prediction_filtered_rmse']:.3f}. El filtrado offline no mejora la capacidad predictiva "
            "desplegable y no debe evaluarse con filtfilt sobre todo el holdout, pues eso introduciria fuga temporal.",
            styles["body"],
        )
    )
    order_cmp = {row["order"]: row for row in filt["order_comparison"]}
    story.append(
        _paragraph(
            "Justificacion del orden 4 (tabla completa en output/tables/butterworth_orden.csv, ordenes 2, 4 y 6 "
            f"evaluados con el mismo corte de {filt['selected_cutoff_cycles_per_record']:.4f} ciclos por registro): "
            f"el orden 2 obtiene el RMSE de reconstruccion mas bajo ({order_cmp[2]['reconstruction_rmse']:.3f}), "
            f"pero atenua apenas {abs(order_cmp[2]['attenuation_at_2x_cutoff_db']):.1f} dB al doble del corte, "
            f"contra {abs(order_cmp[4]['attenuation_at_2x_cutoff_db']):.1f} dB del orden 4 y "
            f"{abs(order_cmp[6]['attenuation_at_2x_cutoff_db']):.1f} dB del orden 6. Esto importa porque el 98.2% "
            "de la potencia del error noise-clean de Agro_3 esta por encima del corte seleccionado (ruido de banda "
            "ancha, igual que Ener_4): un orden bajo deja pasar mas de ese ruido fuera de banda aunque su RMSE "
            "global se vea mejor. El costo de subir el orden es el sobreimpulso (ringing) de la respuesta al "
            f"escalon, que crece de {order_cmp[2]['step_overshoot_pct']:.1f}% (orden 2) a "
            f"{order_cmp[4]['step_overshoot_pct']:.1f}% (orden 4) y {order_cmp[6]['step_overshoot_pct']:.1f}% "
            "(orden 6); sosfiltfilt aplica el filtro dos veces (adelante y atras) y cancela el desfase neto, pero "
            "no elimina ese sobreimpulso transitorio. El orden 4 se elige como punto medio: duplica la atenuacion "
            "fuera de banda del orden 2 sin llegar al RMSE mas alto ni al mayor sobreimpulso del orden 6.",
            styles["body"],
        )
    )
    story.append(PageBreak())

    # Grafos
    story += _section_title("4.", "Fase 3 - Grafos y topologia", styles)
    story.append(
        _paragraph(
            f"La red energetica contiene {graph['nodes']} nodos y {graph['unique_edges']} aristas unicas. Como los "
            "Source_Node (100-119) y Target_Node (200-249) son conjuntos disjuntos y todas las aristas apuntan de "
            "Source a Target, no existen caminos dirigidos de longitud mayor que uno. En consecuencia, los "
            f"{graph['directed_betweenness_ties_at_max']} nodos empatan con betweenness dirigido igual a cero.",
            styles["body"],
        )
    )
    story += _figure(
        figures / "07_centralidad_red.png",
        f"Figura 7. El nodo {graph['traffic_bottleneck']} es cuello de botella por trafico y tambien lidera la sensibilidad no dirigida.",
        styles,
        width=16.5 * cm,
    )
    story += _figure(
        figures / "08_red_energia.png",
        "Figura 8. Topologia bipartita dirigida. El tamano representa trafico; no se inventan enlaces de retorno ausentes en los datos.",
        styles,
        width=14.8 * cm,
    )
    story.append(
        _callout(
            f"Reto del cuello de botella: el nodo {graph['traffic_bottleneck']} acumula "
            f"{graph['traffic_bottleneck_records']} registros. En la sensibilidad no dirigida su betweenness es "
            f"{graph['sensitivity_betweenness']:.4f}. No existen bridges en esa proyeccion, lo que sugiere rutas "
            "alternativas en conectividad, aunque no prueba redundancia electrica real.",
            styles,
        )
    )
    story.append(PageBreak())

    # Negocio
    story += _section_title("5.", "Fase 4 - Preguntas de negocio", styles)
    story.append(_paragraph("P1. Causalidad y redes", styles["h2"]))
    granger = models["granger"]
    story.append(
        _paragraph(
            f"El VAR selecciona rezago {granger['selected_lag']} por AIC. El test Ener_10 -> Ener_9 produce "
            f"F = {granger['power_factor_to_voltage']['f_statistic']:.3f}, "
            f"p = {granger['power_factor_to_voltage']['p_value']:.3f}; la direccion inversa da "
            f"p = {granger['voltage_to_power_factor']['p_value']:.3f}. No hay evidencia de causalidad de Granger "
            "en ninguna direccion. Condicionalmente, un fallo en un nodo de alta betweenness podria interrumpir "
            "rutas y propagar inestabilidad; la topologia dirigida disponible no representa esas rutas, por lo que "
            "el escenario debe validarse con flujos bidireccionales y estados de interruptores.",
            styles["body"],
        )
    )
    story.append(_paragraph("P2. Optimizacion geo-agronoma", styles["h2"]))
    story.append(
        _paragraph(
            f"Bajo el supuesto explicito de que la varianza de Agro_10 aproxima pendiente/exposicion, se prioriza "
            f"un piloto en el cluster {geo['priority_cluster']} alrededor de "
            f"({geo['priority_cluster_latitude']:.4f}, {geo['priority_cluster_longitude']:.4f}). La recomendacion es "
            "riego por goteo sectorizado, almacenamiento local, regulacion de presion, zanjas de infiltracion y "
            "proteccion contra viento; antes de CAPEX a escala se requiere levantamiento topografico y prueba A/B. "
            f"La heterogeneidad de varianzas de viento no es significativa (Levene p = {geo['wind_variance_levene_p']:.3f}), "
            "por lo que la evidencia territorial actual es debil.",
            styles["body"],
        )
    )
    story.append(_paragraph("P3. Analitica predictiva", styles["h2"]))
    arimax = models["arimax"]
    story.append(
        _paragraph(
            f"El mejor orden con temperatura es ARIMAX{tuple(arimax['order'])}. Su AIC es "
            f"{arimax['aic_temperature']:.2f}; al agregar centralidad aumenta a "
            f"{arimax['aic_temperature_centrality']:.2f} (Delta = "
            f"{arimax['delta_aic_extended_minus_base']:+.2f}). Aunque el coeficiente estandarizado de centralidad "
            f"es {arimax['centrality_coefficient']:.3f} con p = {arimax['centrality_p_value']:.3f}, la penalizacion "
            "del AIC no se compensa. Por el criterio solicitado, la centralidad no mejora el modelo.",
            styles["body"],
        )
    )
    story += _figure(
        figures / "10_arimax.png",
        "Figura 9. Holdout temporal del 20%. La centralidad produce una diferencia marginal y no resuelve la incertidumbre de horizonte largo.",
        styles,
        width=16.2 * cm,
    )
    story.append(PageBreak())

    # Nodo 214
    story += _section_title("6.", "Auditoria del caso Nodo 214", styles)
    story += _figure(
        figures / "09_nodo214.png",
        "Figura 10. Los registros disponibles no muestran interrupcion de telemetria ni anomalia termica estadisticamente detectable para el Target 214.",
        styles,
        width=15.5 * cm,
    )
    node_rows = [
        ["Indicador", "Resultado", "Lectura"],
        ["Umbral critico Ener_2", f"P95 = {node214['spot_price_p95']:.2f}", "Regla operacional documentada"],
        [
            "Frecuencia Target 214",
            f"{100*node214['normal_price_target_rate']:.2f}% normal vs {100*node214['high_price_target_rate']:.2f}% alta",
            f"Fisher p = {node214['fisher_p']:.3f}",
        ],
        [
            "Temperatura Ener_3",
            f"Delta = {node214['temperature_difference']:+.3f}",
            f"Welch p = {node214['temperature_test_p']:.3f}",
        ],
        [
            "Centralidad",
            f"Betweenness no dirigido = {node214['undirected_betweenness']:.4f}",
            "No es bridge ni cuello de botella",
        ],
    ]
    story.append(_data_table(node_rows, styles, [4.1 * cm, 6.0 * cm, 6.9 * cm], font_size=7.4))
    story.append(Spacer(1, 0.3 * cm))
    story.append(
        _callout(
            "La hipotesis del enunciado no puede confirmarse porque no existe una columna de flujo, estado, "
            "interrupcion o timestamp. La ausencia de registros tampoco equivale automaticamente a una falla. "
            "Se recomienda instrumentar estado del interruptor, potencia activa, corriente, calidad GPS y eventos de comunicacion.",
            styles,
            PALE_ORANGE,
        )
    )
    story.append(PageBreak())

    # Autoevaluacion
    story += _section_title("7.", "Preguntas de validacion", styles)
    spurious = validation["spurious_correlation"]
    story.append(_paragraph("1. Estacionariedad y correlacion", styles["h2"]))
    story.append(
        _paragraph(
            f"Pearson en niveles puede capturar tendencias compartidas y producir correlacion espuria. Por ejemplo, "
            f"Ener_5 y Ener_6 correlacionan {spurious['level_correlation']:.3f} en nivel, pero solo "
            f"{spurious['first_difference_correlation']:.3f} tras diferenciar. La inferencia debe realizarse sobre "
            "series estacionarias, residuos o modelos de cointegracion cuando corresponda.",
            styles["body"],
        )
    )
    snr = validation["snr_5db_arma"]
    story.append(_paragraph("2. Impacto de SNR cercano a 5 dB", styles["h2"]))
    story.append(
        _paragraph(
            f"La serie mas cercana es {snr['series']} con {snr['empirical_snr_db']:.3f} dB. En ARIMA(2,1,1), "
            f"la distancia L2 entre los coeficientes AR/MA clean y noise es {snr['coefficient_l2_shift']:.3f}. "
            "El ruido desplaza la dinamica estimada hacia componentes de corto plazo y vuelve inestables las "
            "conclusiones sobre persistencia; por eso el filtrado y la validacion fuera de muestra son necesarios.",
            styles["body"],
        )
    )
    story += _figure(
        figures / "11_snr_arma.png",
        "Figura 11. Cambio de coeficientes por AWGN con SNR empirico cercano a 5 dB.",
        styles,
        width=13.8 * cm,
    )
    story.append(_paragraph("3. Interpretacion de un bridge", styles["h2"]))
    story.append(
        _paragraph(
            "Un bridge es una arista cuya remocion aumenta el numero de componentes conexas. Un sensor asociado "
            "deja de ser un punto local y se convierte en riesgo sistemico porque su fallo aisla un segmento. En la "
            "sensibilidad no dirigida de estos datos no se observan bridges; esto reduce el riesgo topologico "
            "aparente, pero no demuestra redundancia fisica ni capacidad electrica alternativa.",
            styles["body"],
        )
    )
    story.append(_paragraph("4. Geo-inteligencia y varianza", styles["h2"]))
    story.append(
        _paragraph(
            f"La posicion puede modificar varianza por microclima, pendiente, exposicion al viento, suelo y calidad "
            f"de comunicacion. Aqui, Levene entre clusters para Agro_10 produce p = "
            f"{validation['geo_variance']['wind_variance_levene_p']:.3f}; no se detecta efecto espacial. La "
            "recomendacion agronoma usa el supuesto del caso, pero exige validacion topografica antes de invertir.",
            styles["body"],
        )
    )
    story.append(PageBreak())

    # Recomendaciones y cierre
    story += _section_title("8.", "Plan de accion y limitaciones", styles)
    action_rows = [
        ["Horizonte", "Accion", "Indicador de exito"],
        [
            "0-30 dias",
            f"Monitorear nodo {graph['traffic_bottleneck']} y auditar telemetria del 214.",
            "Cobertura de eventos, latencia y perdida de paquetes por nodo.",
        ],
        [
            "30-60 dias",
            f"Piloto hidrico en cluster {geo['priority_cluster']} con control comparable.",
            "Delta NDVI, humedad y consumo de agua con intervalo de confianza.",
        ],
        [
            "60-90 dias",
            "Desplegar filtro causal calibrado y reentrenar ARIMAX con calendario/flujo.",
            "RMSE temporal y AIC fuera de muestra frente a baseline.",
        ],
        [
            "Continuo",
            "Versionar datos, pruebas y grafo fisico bidireccional.",
            "Pipeline reproducible y alertas sin fuga temporal.",
        ],
    ]
    story.append(_data_table(action_rows, styles, [2.4 * cm, 7.5 * cm, 7.1 * cm], font_size=7.4))
    story.append(Spacer(1, 0.35 * cm))
    story.append(_paragraph("Limitaciones materiales", styles["h2"]))
    story.append(
        _bullet_list(
            [
                "No hay timestamp ni unidad de muestreo: no se convierten frecuencias a Hz ni se modela estacionalidad de calendario.",
                "La red es una lista bipartita de telemetria, no un modelo fisico de flujo de potencia; betweenness dirigido queda degenerado.",
                "Las coordenadas clean cambian por registro incluso dentro de un mismo Source_Node; un rolling median espacial degrada el RMSE de latitud.",
                "El umbral P95 y la frecuencia de registros son proxies documentados, no sustitutos de estado de falla o caudal.",
                "Los p-valores describen este dataset simulado y no deben interpretarse como causalidad fisica sin diseno experimental.",
            ],
            styles,
        )
    )
    story.append(Spacer(1, 0.2 * cm))
    story.append(_paragraph("Fuentes del encargo", styles["h2"]))
    story.append(
        _paragraph(
            "agro_clean.csv; agro_noise.csv; ener_clean.csv; ener_noise.csv. Los cuatro se conservan en la raiz del repositorio.",
            styles["body"],
        )
    )
    story.append(
        _callout(
            "Cierre: la entrega cumple las cuatro fases, responde las preguntas de negocio y autoevaluacion, y deja "
            "evidencia reproducible.",
            styles,
        )
    )

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return destination


if __name__ == "__main__":
    build_report(Path(__file__).resolve().parents[1])
