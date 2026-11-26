"""Guía y verificación de piezómetros de cuerda vibrante (VWP).

Flujo: 1) lecturas en seco -> 2) saturación y lectura cero (L0) ->
3) prueba de inmersión -> 4) instalación en campo -> 5) seguimiento -> 6) resumen.

Los cálculos viven en vwp_calculos.py (deben estar en la misma carpeta).
"""

import json
import math
import os
import re
from datetime import datetime

import pandas as pd
import streamlit as st

import vwp_calculos as vc

try:
    from streamlit.errors import StreamlitAPIException
except Exception:  # pragma: no cover
    StreamlitAPIException = Exception

try:
    import openpyxl  # noqa: F401

    HAY_EXCEL = True
except ImportError:
    HAY_EXCEL = False

st.set_page_config(
    page_title="Guía y Verificación de Piezómetros VWP",
    page_icon="📊",
    layout="wide",
)

st.title("🚰 Sistema y Protocolo de Verificación de Piezómetros VWP")
st.markdown("Herramienta de campo con registro progresivo en archivo `.txt` por pozo.")
VERSION_APP = "2026-11-25 · con bitácora (7 pestañas) · guardado en carpeta y gráficas de inmersión · rev. 4"
st.caption(f"Versión de la app: {VERSION_APP}")
banner = st.empty()  # se llena al final con el estado global

# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
ICONOS = {vc.OK: "✅", vc.ERROR: "❌", vc.AVISO: "⚠️", vc.PENDIENTE: "⏳", vc.OMITIDO: "➖"}
RANGO = {vc.ERROR: 4, vc.PENDIENTE: 3, vc.AVISO: 2, vc.OK: 1, vc.OMITIDO: 0}


def con_ancho_total(funcion, *args, **kwargs):
    """Elemento a todo el ancho, en versiones nuevas y viejas de Streamlit."""
    try:
        return funcion(*args, width="stretch", **kwargs)
    except (TypeError, StreamlitAPIException):
        return funcion(*args, use_container_width=True, **kwargs)


def fmt(x, dec=3, sufijo=""):
    x = vc._num(x)
    return "—" if math.isnan(x) else f"{x:.{dec}f}{sufijo}"


def mostrar_estado(estado, texto):
    funcion = {vc.OK: st.success, vc.ERROR: st.error, vc.AVISO: st.warning}.get(estado, st.info)
    funcion(f"{ICONOS[estado]} {texto}")


def peor(*pares):
    """Del conjunto de (estado, mensaje), el más grave."""
    return max(pares, key=lambda p: RANGO[p[0]])


def con_conocida_y_variacion(tabla, referencia):
    """Agrega 'Conocida (m)' y 'Variación (m)' (calculada - conocida), como en el reporte."""
    t = tabla.copy()
    t["Conocida (m)"] = round(referencia, 3)
    t["Variación (m)"] = (pd.to_numeric(t[vc.COL_MCA], errors="coerce") - referencia).round(3)
    return t


ACTIVIDADES = [
    "Recepción / verificación en seco",
    "Saturación iniciada",
    "Lectura cero (L0)",
    "Prueba de inmersión",
    "Instalación en pozo",
    "Programa CR6 actualizado",
    "Respaldo del CR6",
    "GeoViewer actualizado",
    "Verificación con geólogo",
    "Lectura de seguimiento",
    "Observación / incidencia",
]
COLS_BITACORA = ["Fecha", "Hora", "Responsable", "Actividad", "Detalle"]


def ahora_local():
    """Fecha y hora de México (el servidor puede estar en UTC)."""
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo("America/Mexico_City"))
    except Exception:
        return datetime.now()


def limpiar_bitacora(entradas):
    """Solo entradas válidas, con las columnas esperadas y en texto."""
    limpias = []
    for e in entradas or []:
        if isinstance(e, dict):
            limpias.append({c: str(e.get(c) or "") for c in COLS_BITACORA})
    return limpias


def nombre_archivo(pozo):
    limpio = re.sub(r"[^\w\-.]+", "_", (pozo or "").strip()).strip("_")
    return limpio or "pozo_sin_nombre"


# ---------------------------------------------------------------------------
# Ficha (.txt = JSON)
# ---------------------------------------------------------------------------
def ficha_vacia():
    return {
        "version_ficha": 2,
        "id_sensor": "VW-NUEVO",
        "pozo": "Nuevo-Pozo",
        "modelo": "Polinomial",
        "x": 0.0, "y": 0.0, "z": 0.0,
        "prof_pozo": 0.0, "prof_inst": 0.0, "naf": 0.0,
        # Constantes en 0 a propósito: se capturan del certificado del sensor.
        "a": 0.0, "b": 0.0, "cf": 0.0, "tk": 0.0,
        "s0_baro": 101.325, "s_baro": 101.325,
        "notas": "",
        "lectura_fabrica_seco": 0.0, "temp_fabrica": 0.0,
        "baro_fabrica_hpa": 0.0, "baro_seco_hpa": 0.0,
        "inmersion_fecha": "", "inmersion_hora": "",
        "altura_referencia": 0.30,
        "offset_diafragma_cm": 0.0,
        "l_campo": 0.0, "t_campo": 0.0,
        # Criterios de aceptación (ajústalos a tu procedimiento)
        "crit_n_min": 5, "crit_tol_rango": 1.0, "crit_tol_fabrica": 0.0,
        "crit_horas_sat": 24.0, "crit_tol_inm": 0.05, "crit_tol_campo": 1.0,
        "crit_umbral_salto": 0.5,
        "tabla_seco": None, "tabla_sat": None, "tabla_inm": None, "tabla_seg": None, "tabla_alt": None, "bitacora": None,
    }


CLAVES_NUM = [
    "x", "y", "z", "prof_pozo", "prof_inst", "naf", "a", "b", "cf", "tk",
    "s0_baro", "s_baro", "lectura_fabrica_seco", "temp_fabrica", "baro_fabrica_hpa", "baro_seco_hpa",
    "altura_referencia", "offset_diafragma_cm",
    "l_campo", "t_campo", "crit_n_min", "crit_tol_rango", "crit_tol_fabrica",
    "crit_horas_sat", "crit_tol_inm", "crit_tol_campo", "crit_umbral_salto",
]


def normalizar_ficha(datos):
    """Completa una ficha (también las antiguas) con los valores por defecto."""
    base = ficha_vacia()
    if not isinstance(datos, dict):
        return base
    ficha = dict(base)
    ficha.update({k: v for k, v in datos.items() if v is not None})
    for k in CLAVES_NUM:
        x = vc._num(ficha.get(k))
        ficha[k] = base[k] if math.isnan(x) else x
    for k in ("id_sensor", "pozo", "notas", "inmersion_fecha", "inmersion_hora"):
        ficha[k] = str(ficha.get(k) or "")
    if ficha.get("modelo") not in ("Polinomial", "Lineal"):
        ficha["modelo"] = "Polinomial"
    return ficha


def exportar_pozo_txt(datos_pozo):
    return json.dumps(vc.limpiar_para_json(datos_pozo), ensure_ascii=False, indent=4, allow_nan=False)


def importar_pozo_txt(contenido_txt):
    try:
        datos = json.loads(contenido_txt)
        if not isinstance(datos, dict):
            raise ValueError("el archivo no contiene una ficha de pozo")
        return datos
    except Exception as e:
        st.sidebar.error(f"Error al cargar el archivo .txt: {e}")
        return None


# ---------------------------------------------------------------------------
# Estado de sesión
# ---------------------------------------------------------------------------
if "datos_actuales" not in st.session_state:
    st.session_state.datos_actuales = ficha_vacia()
if "version" not in st.session_state:
    st.session_state.version = 0

# Completa la ficha de la sesión con los campos nuevos (por ejemplo, si la página
# quedó abierta con una versión anterior de la app).
st.session_state.datos_actuales = normalizar_ficha(st.session_state.datos_actuales)
d = st.session_state.datos_actuales
v = st.session_state.version  # cambia al cargar/crear una ficha: reinicia los widgets


def base_tabla(nombre, columnas):
    """Tabla inicial estable durante la sesión de una ficha (no cambia en cada recarga)."""
    clave = f"base_{nombre}_{v}"
    if clave not in st.session_state:
        st.session_state[clave] = vc.df_desde_registros(d.get("tabla_" + nombre), columnas)
    return st.session_state[clave]


def editor(nombre, columnas, dinamico=False):
    base = base_tabla(nombre, columnas)
    cfg = {
        vc.COL_FECHA: st.column_config.TextColumn(vc.COL_FECHA, help="AAAA-MM-DD"),
        vc.COL_HORA: st.column_config.TextColumn(vc.COL_HORA, help="HH:MM (24 h)"),
        vc.COL_L: st.column_config.NumberColumn(vc.COL_L, format="%.3f", step=0.1),
        vc.COL_T: st.column_config.NumberColumn(vc.COL_T, format="%.2f", step=0.1),
        vc.COL_ALT: st.column_config.NumberColumn(
            vc.COL_ALT, format="%.1f", step=0.5, help="Altura del agua medida desde el punto de referencia que uses"
        ),
        vc.COL_BARO: st.column_config.NumberColumn(
            vc.COL_BARO, format="%.3f", help="Opcional. Vacío = usa la S actual de la ficha"
        ),
    }
    kwargs = {
        "num_rows": "dynamic" if dinamico else "fixed",
        "key": f"ed_{nombre}_{v}",
        "column_config": {c: cfg[c] for c in base.columns if c in cfg},
    }
    if vc.COL_NUM in base.columns:
        kwargs["disabled"] = [vc.COL_NUM]
    return con_ancho_total(st.data_editor, base, **kwargs)


# ---------------------------------------------------------------------------
# Barra lateral
# ---------------------------------------------------------------------------
st.sidebar.header("📂 1. Gestión de Ficha (.txt)")

if con_ancho_total(st.sidebar.button, "✨ Registrar Nuevo Sensor / Pozo Limpio"):
    st.session_state.datos_actuales = ficha_vacia()
    st.session_state.version += 1
    st.rerun()

archivo_subido = st.sidebar.file_uploader("Cargar Ficha de Pozo (.txt)", type=["txt"], key=f"subida_{v}")
if archivo_subido is not None:
    datos_cargados = importar_pozo_txt(archivo_subido.getvalue().decode("utf-8", errors="replace"))
    if datos_cargados:
        st.session_state.datos_actuales = normalizar_ficha(datos_cargados)
        st.session_state.version += 1
        st.session_state.msg_carga = f"¡Ficha '{datos_cargados.get('pozo', 'Pozo')}' cargada!"
        st.rerun()
if st.session_state.get("msg_carga"):
    st.sidebar.success(st.session_state.pop("msg_carga"))

st.sidebar.divider()
st.sidebar.header("2. Datos Generales y Parámetros")

sensor_id = st.sidebar.text_input("ID / Serial del Sensor", value=d["id_sensor"], key=f"id_{v}")
pozo_instalacion = st.sidebar.text_input("Pozo / Ubicación", value=d["pozo"], key=f"pozo_{v}")
tipo_modelo = st.sidebar.selectbox(
    "Modelo de Cálculo (principal)", ["Polinomial", "Lineal"],
    index=0 if d["modelo"] == "Polinomial" else 1, key=f"modelo_{v}",
)

st.sidebar.subheader("Ubicación y Geometría")
coord_x = st.sidebar.number_input("Coordenada X", value=float(d["x"]), format="%.2f", key=f"x_{v}")
coord_y = st.sidebar.number_input("Coordenada Y", value=float(d["y"]), format="%.2f", key=f"y_{v}")
cota_instalacion = st.sidebar.number_input(
    "Cota Z del sensor (m.s.n.m.)", value=float(d["z"]), format="%.3f", key=f"z_{v}"
)
prof_pozo_val = st.sidebar.number_input("Prof. Pozo (m)", value=float(d["prof_pozo"]), format="%.2f", key=f"pp_{v}")
prof_inst_val = st.sidebar.number_input(
    "Prof. Inst. del sensor (m)", value=float(d["prof_inst"]), format="%.2f", key=f"pi_{v}"
)
naf_val = st.sidebar.number_input(
    "NAF medido con sonda (m)", value=float(d["naf"]), format="%.2f", key=f"naf_{v}",
    help="Profundidad al nivel de agua medida con sonda eléctrica antes de instalar.",
)

st.sidebar.subheader("Constantes del Fabricante (certificado)")
st.sidebar.caption("Captura A y B (polinomial) y/o CF (lineal). Si capturas ambos modelos, la app los compara.")
coef_a = st.sidebar.number_input("Constante A", value=float(d["a"]), format="%.4e", key=f"a_{v}")
coef_b = st.sidebar.number_input("Constante B", value=float(d["b"]), format="%.4e", key=f"b_{v}")
cf_factor = st.sidebar.number_input("Factor Lineal (CF)", value=float(d["cf"]), format="%.4e", key=f"cf_{v}")
tk_factor = st.sidebar.number_input("Coef. Térmico (Tk)", value=float(d["tk"]), format="%.4e", key=f"tk_{v}")

st.sidebar.subheader("Presión Barométrica")
s0_baro = st.sidebar.number_input(
    "S0 Inicial (kPa)", value=float(d["s0_baro"]), format="%.3f", key=f"s0_{v}",
    help="Presión barométrica medida al tomar la lectura cero (L0), no el valor a nivel del mar.",
)
s_baro = st.sidebar.number_input("S Actual (kPa)", value=float(d["s_baro"]), format="%.3f", key=f"s_{v}")
if abs(s0_baro - s_baro) > 3.0:
    st.sidebar.warning(
        "S0 y S difieren más de 3 kPa (≈0.3 m). Si no es un cambio real de clima, "
        "revisa que ambas sean presión del sitio y no el valor estándar 101.325."
    )

with st.sidebar.expander("⚙️ Criterios de aceptación"):
    st.caption("Valores sugeridos: ajústalos a tu procedimiento o a la especificación del proyecto.")
    crit_n_min = st.number_input(
        "Lecturas mínimas por fase", min_value=1, max_value=50, value=int(d["crit_n_min"]), step=1, key=f"c1_{v}"
    )
    crit_tol_rango = st.number_input(
        "Rango máx. entre lecturas (B). 0 = no evaluar", min_value=0.0, value=float(d["crit_tol_rango"]),
        step=0.1, format="%.2f", key=f"c2_{v}",
    )
    crit_tol_fabrica = st.number_input(
        "Tolerancia vs. lectura de fábrica (B). 0 = no evaluar", min_value=0.0,
        value=float(d["crit_tol_fabrica"]), step=0.5, format="%.2f", key=f"c3_{v}",
    )
    crit_horas_sat = st.number_input(
        "Horas mínimas de saturación", min_value=0.0, value=float(d["crit_horas_sat"]), step=1.0,
        format="%.1f", key=f"c4_{v}",
    )
    crit_tol_inm = st.number_input(
        "Tolerancia prueba de inmersión (m)", min_value=0.0, value=float(d["crit_tol_inm"]),
        step=0.01, format="%.2f", key=f"c5_{v}",
    )
    crit_tol_campo = st.number_input(
        "Tolerancia instalación vs. sonda (m)", min_value=0.0, value=float(d["crit_tol_campo"]),
        step=0.1, format="%.2f", key=f"c6_{v}",
    )
    crit_umbral_salto = st.number_input(
        "Salto entre lecturas de seguimiento (m). 0 = no alertar", min_value=0.0,
        value=float(d["crit_umbral_salto"]), step=0.1, format="%.2f", key=f"c7_{v}",
    )

st.sidebar.subheader("📝 Observaciones / Notas de Campo")
notas_campo = st.sidebar.text_area(
    "Registro de novedades en pozo:", value=d["notas"], placeholder="Ej: Pozo B1-3A asolvado...",
    height=100, key=f"notas_{v}",
)

cal = vc.Calibracion(tipo_modelo, a=coef_a, b=coef_b, cf=cf_factor, tk=tk_factor, s0_baro=s0_baro)
cal_alterno = cal.alterno()
if not cal.tiene_constantes():
    st.warning(
        f"⚠️ Faltan las constantes del modelo **{tipo_modelo}** (barra lateral). "
        "Sin ellas no se calculan presiones."
    )

# ---------------------------------------------------------------------------
# Pestañas
# ---------------------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "1. Fase En Seco",
    "2. Fase Saturado (L0)",
    "3. Fase Inmerso",
    "4. Instalación en Campo",
    "5. Seguimiento",
    "6. Bitácora",
    "7. Resumen y Verificación",
])

NOTA_TABLA = "Escribe fecha (AAAA-MM-DD) y hora (HH:MM) de cada lectura. Las filas sin lectura se ignoran."

# --- TAB 1: SECO -----------------------------------------------------------
with tab1:
    st.header(f"a) Registro En Seco — Pozo: {pozo_instalacion}")
    st.caption(NOTA_TABLA)
    df_seco = editor("seco", vc.COLS_BASE)
    res_seco = vc.resumir_tabla(df_seco)
    prom_seco_l, prom_seco_t = res_seco["prom_l"], res_seco["prom_t"]

    st.markdown("**Comparación con la lectura cero de fábrica** (certificado, 'Shipped Zero Readings')")
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        lectura_fabrica_seco = st.number_input(
            "Lectura cero de fábrica (B) — 0 = no capturada", value=float(d["lectura_fabrica_seco"]),
            format="%.1f", step=0.1, key=f"fab_{v}",
        )
    with f2:
        temp_fabrica = st.number_input(
            "Temperatura de fábrica (°C)", value=float(d["temp_fabrica"]), format="%.1f", step=0.1, key=f"tfab_{v}"
        )
    with f3:
        baro_fabrica_hpa = st.number_input(
            "Barométrica de fábrica (hPa o mbar)", value=float(d["baro_fabrica_hpa"]), format="%.1f",
            step=0.1, key=f"bfab_{v}",
        )
    with f4:
        baro_seco_hpa = st.number_input(
            "Barométrica durante estas lecturas (hPa)", value=float(d["baro_seco_hpa"]), format="%.1f",
            step=0.1, key=f"bseco_{v}",
            help="Presión ACTUAL (de la estación), no la relativa a nivel del mar.",
        )
    esperada_seco = math.nan
    if (lectura_fabrica_seco > 0 and temp_fabrica > 0 and baro_fabrica_hpa > 0 and baro_seco_hpa > 0
            and cal.tiene_constantes() and not math.isnan(prom_seco_t)):
        esperada_seco = vc.lectura_esperada_en_aire(
            cal, lectura_fabrica_seco, temp_fabrica, baro_fabrica_hpa / 10.0, prom_seco_t, baro_seco_hpa / 10.0
        )
    est_seco = vc.evaluar_estabilidad(res_seco, crit_n_min, crit_tol_rango)
    est_fab = vc.comparar_con_esperada(prom_seco_l, esperada_seco, crit_tol_fabrica)
    if not math.isnan(esperada_seco):
        st.caption(
            "La lectura esperada corrige por temperatura y por presión del aire (1 kPa ≈ 10 dígitos). "
            "Compararla directamente con la lectura de fábrica daría una diferencia engañosa."
        )

    if res_seco["n"]:
        st.success(f"Promedio En Seco — Lectura: **{fmt(prom_seco_l)} B** | Temp: **{fmt(prom_seco_t, 2)} °C**")
    mostrar_estado(*est_seco)
    if est_fab[0] != vc.OMITIDO:
        mostrar_estado(*est_fab)
    elif not math.isnan(esperada_seco):
        st.info(f"ℹ️ {est_fab[1]}")

# --- TAB 2: SATURADO -------------------------------------------------------
with tab2:
    st.header(f"b) Registro Saturado (Lectura Cero L0) — Pozo: {pozo_instalacion}")
    st.info(
        "**Procedimiento del fabricante (RST, manual VW2100, secc. 4.3 y 5.2):** 1) quita el filtro y sumerge "
        "el sensor en agua reposada (unas 24 h); 2) arma el filtro bajo el agua; 3) la lectura cero (L0) se toma "
        "**al aire libre**, con el filtro saturado y colocado, **sin sumergir** el sensor; 4) espera 20–30 min de "
        "equilibrio térmico y anota la temperatura y la presión barométrica (S0) de ese momento. "
        "Verifícalo en tu copia del manual."
    )
    st.markdown("Registra cuándo sumergiste el sensor para saturarlo:")
    c_f, c_h = st.columns(2)
    with c_f:
        inmersion_fecha = st.text_input(
            "Inicio de inmersión: fecha (AAAA-MM-DD)", value=d["inmersion_fecha"], key=f"if_{v}"
        )
    with c_h:
        inmersion_hora = st.text_input("Inicio de inmersión: hora (HH:MM)", value=d["inmersion_hora"], key=f"ih_{v}")
    st.caption(NOTA_TABLA)
    df_sat = editor("sat", vc.COLS_BASE)
    res_sat = vc.resumir_tabla(df_sat)
    prom_sat_l0, prom_sat_t0 = res_sat["prom_l"], res_sat["prom_t"]
    l0_ok = not (math.isnan(prom_sat_l0) or math.isnan(prom_sat_t0))

    c_constante = math.nan
    if l0_ok and tipo_modelo == "Polinomial":
        c_constante = vc.constante_c(coef_a, coef_b, prom_sat_l0)

    if res_sat["n"]:
        st.success(f"**L0 Oficial:** **{fmt(prom_sat_l0)} B** | **T0:** **{fmt(prom_sat_t0, 2)} °C**")
    if not math.isnan(c_constante):
        st.warning(f"🔧 **Constante C:** `{c_constante:.3f}` kPa")

    est_sat_h = vc.evaluar_saturacion(
        vc.horas_saturacion(vc.construir_dt(inmersion_fecha, inmersion_hora), df_sat), crit_horas_sat
    )
    est_sat_l0 = vc.evaluar_estabilidad(res_sat, crit_n_min, crit_tol_rango)
    mostrar_estado(*est_sat_h)
    mostrar_estado(*est_sat_l0)

# --- TAB 3: INMERSO --------------------------------------------------------
with tab3:
    st.header(f"c) Registro Inmerso — Pozo: {pozo_instalacion}")
    altura_referencia = st.slider(
        "Altura de la columna de agua de prueba (m):",
        min_value=0.0, max_value=1.0,
        value=float(min(max(d["altura_referencia"], 0.0), 1.0)), step=0.05, format="%.2f m",
        key=f"alt_{v}",
    )
    offset_diafragma_cm = st.number_input(
        "Distancia del diafragma bajo tu punto de medición (cm)",
        value=float(d["offset_diafragma_cm"]), step=0.5, format="%.1f", key=f"off_{v}",
        help=(
            "Mides la altura del agua desde la piedra porosa, pero el sensor mide en el diafragma. "
            "Positivo si el diafragma queda más profundo que tu punto de medición (piedra hacia arriba); "
            "negativo si queda más somero. Se estima en la calibración con varias alturas, más abajo."
        ),
    )
    referencia_efectiva = altura_referencia + offset_diafragma_cm / 100.0
    st.caption(NOTA_TABLA)
    df_inm = editor("inm", vc.COLS_BASE)
    res_inm = vc.resumir_tabla(df_inm)
    prom_inm_l, prom_inm_t = res_inm["prom_l"], res_inm["prom_t"]

    presion_inm = altura_inm = math.nan
    est_inm_val = (vc.PENDIENTE, "Captura las lecturas de la prueba de inmersión.")
    listo_calculo = l0_ok and cal.tiene_constantes()
    if res_inm["n"] and listo_calculo:
        tabla_inm = vc.calcular_tabla_presion(df_inm, cal, prom_sat_l0, prom_sat_t0, s_baro)
        tabla_inm = tabla_inm[pd.to_numeric(tabla_inm[vc.COL_L], errors="coerce").notna()].copy()
        tabla_inm[f"¿Dentro de ±{crit_tol_inm:.2f} m?"] = [
            "✅" if abs(c - referencia_efectiva) <= crit_tol_inm else "❌"
            for c in tabla_inm[vc.COL_MCA]
        ]
        tabla_inm = con_conocida_y_variacion(tabla_inm, referencia_efectiva)
        st.markdown("**Columna de agua: conocida vs. calculada, por cada lectura**")
        con_ancho_total(
            st.dataframe,
            tabla_inm[[vc.COL_NUM, vc.COL_L, vc.COL_T, vc.COL_P, "Conocida (m)", vc.COL_MCA, "Variación (m)",
                       f"¿Dentro de ±{crit_tol_inm:.2f} m?"]],
            hide_index=True,
        )
        grafica_lecturas = pd.DataFrame(
            {
                "Calculada (m)": [float(x) for x in tabla_inm[vc.COL_MCA]],
                "Conocida (m)": [float(referencia_efectiva)] * len(tabla_inm),
            },
            index=pd.RangeIndex(1, len(tabla_inm) + 1, name="Lectura"),
        )
        st.caption("Columna calculada en cada lectura frente a la conocida (línea plana): deberían quedar juntas.")
        st.line_chart(grafica_lecturas)
        presion_inm = float(tabla_inm[vc.COL_P].mean())
        altura_inm = float(tabla_inm[vc.COL_MCA].mean())
        det_inm = vc.analizar_columnas(
            list(tabla_inm[vc.COL_MCA]), referencia_efectiva, crit_tol_inm, list(tabla_inm[vc.COL_NUM])
        )
        est_inm_val = vc.validar_inmersion_detallada(
            list(tabla_inm[vc.COL_MCA]), referencia_efectiva, crit_tol_inm, list(tabla_inm[vc.COL_NUM])
        )
    elif res_inm["n"]:
        est_inm_val = (vc.PENDIENTE, "Falta la lectura cero (L0 y T0) o las constantes del modelo.")

    st.divider()
    if offset_diafragma_cm:
        st.subheader(
            f"🎯 Validación de la Prueba (Referencia: {altura_referencia:.2f} m "
            f"{offset_diafragma_cm:+.1f} cm = {referencia_efectiva:.3f} m)"
        )
    else:
        st.subheader(f"🎯 Validación de la Prueba (Referencia: {altura_referencia:.2f} m)")
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        st.metric("Promedio Presión / Columna", f"{fmt(altura_inm)} mca", delta=f"{fmt(presion_inm, 2)} kPa")
        if res_inm["n"] and not math.isnan(altura_inm):
            st.caption(f"Mínimo – máximo de las lecturas: {det_inm['minimo']:.3f} – {det_inm['maximo']:.3f} mca")
    with col_v2:
        est_inm_estab = vc.evaluar_estabilidad(res_inm, crit_n_min, crit_tol_rango)
        mostrar_estado(*est_inm_val)
        if est_inm_estab[0] in (vc.ERROR, vc.AVISO):
            mostrar_estado(*est_inm_estab)
    est_inm = peor(est_inm_val, est_inm_estab)

    if cal_alterno is not None and res_inm["n"] and listo_calculo:
        t_alt = vc.calcular_tabla_presion(df_inm, cal_alterno, prom_sat_l0, prom_sat_t0, s_baro)
        mca_alt = float(t_alt[vc.COL_MCA].mean())
        st.caption(
            f"Contraste con el modelo {cal_alterno.modelo}: {fmt(mca_alt)} mca "
            f"(diferencia con el principal: {mca_alt - altura_inm:+.3f} m)."
        )
    if not math.isnan(prom_inm_l) and not math.isnan(prom_sat_l0) and prom_inm_l >= prom_sat_l0:
        st.warning("⚠️ La lectura inmersa es mayor o igual que L0; con una columna de agua extra debería ser menor.")

    st.divider()
    st.subheader("🔬 Calibración de la distancia piedra–diafragma (varias alturas)")
    st.caption(
        "Repite la prueba a 2 o 3 alturas (p. ej. 20, 30 y 50 cm). Escribe en cada fila la altura medida y la "
        "lectura (puedes repetir la altura en varias filas). Si el sensor mide a una distancia fija del punto "
        "donde mides, la diferencia sale casi igual en todas las alturas: ese es el valor para el campo de arriba."
    )
    df_alt = editor("alt", vc.COLS_ALTURAS)
    det_alt = None
    if vc.serie_numerica(df_alt, vc.COL_L).notna().any():
        if listo_calculo:
            tabla_alt = vc.calcular_tabla_presion(df_alt, cal, prom_sat_l0, prom_sat_t0, s_baro)
            det_alt = vc.analizar_calibracion_alturas(
                [h / 100.0 for h in vc.serie_numerica(tabla_alt, vc.COL_ALT)], list(tabla_alt[vc.COL_MCA]),
            )
            if det_alt["por_altura"]:
                filas = pd.DataFrame({
                    "Altura (cm)": [round(h * 100, 1) for h in det_alt["por_altura"]],
                    "Columna − altura (cm)": [round(x * 100, 2) for x in det_alt["por_altura"].values()],
                })
                con_ancho_total(st.dataframe, filas, hide_index=True)
                prom_por_altura = {
                    round(h * 100, 1): float(h + dif) for h, dif in det_alt["por_altura"].items()
                }
                grafica_alturas = pd.DataFrame(
                    {
                        "Calculada (m)": list(prom_por_altura.values()),
                        "Ideal: igual a la altura medida (m)": [a / 100.0 for a in prom_por_altura],
                    },
                    index=pd.Index(list(prom_por_altura), name="Altura medida (cm)"),
                ).sort_index()
                st.caption(
                    "Columna calculada frente a la altura medida. Una línea paralela a la ideal indica un "
                    "desfase fijo; una línea que se abre o se cierra indica error de constantes."
                )
                st.line_chart(grafica_alturas)
            mostrar_estado(det_alt["estado"], det_alt["mensaje"])
            if det_alt["estado"] == vc.OK:
                st.info(
                    f"👉 Escribe **{det_alt['offset_m'] * 100:.1f}** en 'Distancia del diafragma bajo tu punto "
                    "de medición (cm)' y, desde entonces, la prueba usará esa corrección."
                )
        else:
            st.info("⏳ Falta la lectura cero (L0 y T0) o las constantes del modelo.")

# --- TAB 4: INSTALACIÓN EN CAMPO ------------------------------------------
with tab4:
    st.header(f"d) Monitoreo e Instalación Real en Campo — Pozo: {pozo_instalacion}")
    st.subheader("1. Parámetros Geométricos (de la barra lateral)")
    g1, g2, g3 = st.columns(3)
    g1.metric("Profundidad de instalación", f"{prof_inst_val:.2f} m")
    g2.metric("Cota Z del sensor", f"{cota_instalacion:.3f} m.s.n.m.")
    g3.metric("NAF con sonda", f"{naf_val:.2f} m")
    if prof_inst_val > 0 and naf_val >= prof_inst_val:
        st.warning(
            "⚠️ El NAF medido es igual o mayor que la profundidad del sensor: el sensor quedaría sobre "
            "el nivel de agua (columna esperada 0)."
        )

    st.divider()
    st.subheader("2. Lectura In Situ del Sensor de Cuerda Vibrante")
    cl1, cl2 = st.columns(2)
    with cl1:
        l_campo = st.number_input(
            "Lectura en campo (B units) — 0 = no capturada", value=float(d["l_campo"]), step=0.1,
            format="%.3f", key=f"lc_{v}",
        )
    with cl2:
        t_campo = st.number_input(
            "Temperatura en campo (°C)", value=float(d["t_campo"]), step=0.1, format="%.2f", key=f"tc_{v}"
        )

    mca_teorico = vc.columna_teorica(prof_inst_val, naf_val)
    elev_teorica = cota_instalacion + mca_teorico
    campo_capturado = l_campo > 0
    p_campo = mca_campo = elev_campo = prof_agua_campo = math.nan
    if campo_capturado and l0_ok and cal.tiene_constantes():
        p_campo = vc.presion_kpa(cal, l_campo, t_campo, prom_sat_l0, prom_sat_t0, s_baro)
        mca_campo = vc.kpa_a_mca(p_campo)
        elev_campo = cota_instalacion + mca_campo
        prof_agua_campo = prof_inst_val - mca_campo

    st.divider()
    st.subheader("3. Comparativa y Resultados de Validación")
    m1, m2 = st.columns(2)
    m1.metric("Nivel Teórico (Sonda Manual)", f"{elev_teorica:.3f} m.s.n.m.", delta=f"Columna: {mca_teorico:.2f} m")
    m2.metric(
        f"Cálculo Fórmula {tipo_modelo}", f"{fmt(elev_campo)} m.s.n.m.", delta=f"Presión: {fmt(p_campo, 2)} kPa"
    )
    if not math.isnan(prof_agua_campo):
        st.caption(f"Profundidad al agua calculada desde superficie: **{prof_agua_campo:.2f} m**.")
    if cal_alterno is not None and not math.isnan(p_campo):
        p_alt = vc.presion_kpa(cal_alterno, l_campo, t_campo, prom_sat_l0, prom_sat_t0, s_baro)
        st.caption(
            f"Contraste con el modelo {cal_alterno.modelo}: "
            f"{cota_instalacion + vc.kpa_a_mca(p_alt):.3f} m.s.n.m. (Presión: {p_alt:.2f} kPa)."
        )

    st.markdown("### 📋 Diagnóstico de Verificación in Situ")
    if not campo_capturado:
        est_campo = (vc.PENDIENTE, "Captura la lectura de campo del sensor.")
    elif not (l0_ok and cal.tiene_constantes()):
        est_campo = (vc.PENDIENTE, "Falta la lectura cero (L0 y T0) o las constantes del modelo.")
    else:
        est_campo = vc.validar_campo(mca_campo, mca_teorico, crit_tol_campo)
    mostrar_estado(*est_campo)

# --- TAB 5: SEGUIMIENTO ----------------------------------------------------
with tab5:
    st.header(f"e) Seguimiento posterior a la instalación — Pozo: {pozo_instalacion}")
    st.caption(
        "Agrega una fila por visita o descarga de datos. Con 'Baro (kPa)' vacío se usa la S actual de la ficha. "
        "Usa el botón + de la tabla para añadir filas."
    )
    df_seg = editor("seg", vc.COLS_SEGUIMIENTO, dinamico=True)
    tabla_seg = pd.DataFrame()
    est_seg = (vc.OMITIDO, "Aún no hay lecturas de seguimiento.")
    if vc.serie_numerica(df_seg, vc.COL_L).notna().any():
        if l0_ok and cal.tiene_constantes():
            tabla_seg = vc.calcular_seguimiento(
                df_seg, cal, prom_sat_l0, prom_sat_t0, cota_instalacion, prof_inst_val, s_baro, crit_umbral_salto
            )
            mostrar_cols = [c for c in tabla_seg.columns if c != "_dt"]
            st.markdown("**Nivel de agua calculado**")
            con_ancho_total(st.dataframe, tabla_seg[mostrar_cols], hide_index=True)
            n_alertas = int((tabla_seg[vc.COL_ALERTA] != "").sum())
            serie = tabla_seg.dropna(subset=["_dt", vc.COL_NIVEL]).sort_values("_dt")
            if len(serie) >= 2:
                st.line_chart(serie.set_index("_dt")[vc.COL_NIVEL])
            elif tabla_seg[vc.COL_NIVEL].notna().sum() >= 1:
                st.caption("Para ver la gráfica se necesitan al menos 2 lecturas con fecha y hora válidas.")
            n_validas = int(tabla_seg[vc.COL_NIVEL].notna().sum())
            est_seg = (
                (vc.AVISO, f"{n_alertas} salto(s) mayores a {crit_umbral_salto:.2f} m entre lecturas.")
                if n_alertas else (vc.OK, f"{n_validas} lectura(s) de seguimiento sin saltos bruscos.")
            )
        else:
            est_seg = (vc.PENDIENTE, "Falta la lectura cero (L0 y T0) o las constantes del modelo.")
        mostrar_estado(*est_seg)

# --- TAB 6: BITÁCORA -------------------------------------------------------
with tab6:
    st.header(f"g) Bitácora del sensor — Pozo: {pozo_instalacion} | Sensor: {sensor_id}")
    st.caption(
        "Registra cada actividad (saturación, L0, instalación, cambios en el CR6, verificaciones). "
        "La bitácora se guarda **dentro de la ficha .txt**: después de agregar entradas, "
        "descarga el archivo desde la barra lateral. Si recargas la página sin descargar, se pierden."
    )
    clave_bit = f"bitacora_{v}"
    if clave_bit not in st.session_state:
        st.session_state[clave_bit] = limpiar_bitacora(d.get("bitacora"))
    bitacora = st.session_state[clave_bit]

    with st.form(f"form_bitacora_{v}", clear_on_submit=True):
        bf1, bf2, bf3 = st.columns(3)
        with bf1:
            bit_fecha = st.text_input("Bitácora: fecha (AAAA-MM-DD, vacío = hoy)", value="")
        with bf2:
            bit_hora = st.text_input("Bitácora: hora (HH:MM, vacío = ahora)", value="")
        with bf3:
            bit_resp = st.text_input("Bitácora: responsable", value="")
        bit_act = st.selectbox("Bitácora: actividad", ACTIVIDADES)
        bit_detalle = st.text_area(
            "Bitácora: detalle", value="", height=90,
            placeholder="Ej: Constantes A, B, Tk capturadas del certificado; respaldo guardado como ...",
        )
        agregar = st.form_submit_button("➕ Agregar a la bitácora")
    if agregar:
        if not bit_resp.strip():
            st.warning("Escribe quién realizó la actividad.")
        else:
            ahora = ahora_local()
            bitacora.append({
                "Fecha": bit_fecha.strip() or ahora.strftime("%Y-%m-%d"),
                "Hora": bit_hora.strip() or ahora.strftime("%H:%M"),
                "Responsable": bit_resp.strip(),
                "Actividad": bit_act,
                "Detalle": bit_detalle.strip(),
            })
            st.success("Entrada agregada. Descarga la ficha para guardarla.")

    if bitacora:
        con_ancho_total(st.dataframe, pd.DataFrame(bitacora, columns=COLS_BITACORA), hide_index=True)
        if st.button("🗑️ Eliminar la última entrada", key=f"del_bit_{v}"):
            bitacora.pop()
            st.rerun()
    else:
        st.info("Aún no hay entradas en la bitácora.")

_acts = {e["Actividad"] for e in bitacora}
_faltan_bit = [a for a in ("Programa CR6 actualizado", "Verificación con geólogo") if a not in _acts]
if not bitacora:
    est_bit = (vc.OMITIDO, "Sin entradas en la bitácora.")
elif _faltan_bit:
    est_bit = (vc.OMITIDO, "Falta registrar: " + ", ".join(_faltan_bit) + ".")
else:
    est_bit = (vc.OK, f"{len(bitacora)} entrada(s), con actualización del CR6 y verificación con geólogo.")

# ---------------------------------------------------------------------------
# Verificación global
# ---------------------------------------------------------------------------
if not (sensor_id.strip() and pozo_instalacion.strip() and cal.tiene_constantes()):
    faltan = [
        t for t, ok in (
            ("ID del sensor", bool(sensor_id.strip())),
            ("nombre del pozo", bool(pozo_instalacion.strip())),
            (f"constantes del modelo {tipo_modelo}", cal.tiene_constantes()),
        ) if not ok
    ]
    est_datos = (vc.PENDIENTE, "Falta: " + ", ".join(faltan) + ".")
else:
    est_datos = (vc.OK, "ID, pozo y constantes capturados.")

checklist = [
    ("Datos del sensor y constantes", *est_datos),
    ("Lecturas en seco estables", *est_seco),
    ("Seco vs. lectura de fábrica, corregida (opcional)", *est_fab),
    (f"Saturación ≥ {crit_horas_sat:.0f} h", *est_sat_h),
    ("Lectura cero (L0) estable", *est_sat_l0),
    ("Prueba de inmersión", *est_inm),
    ("Instalación validada con sonda", *est_campo),
    ("Seguimiento post-instalación (opcional)", *est_seg),
    ("Bitácora: CR6 y verificación con geólogo (opcional)", *est_bit),
]
estados = [e for _, e, _ in checklist]
n_err, n_pend = estados.count(vc.ERROR), estados.count(vc.PENDIENTE)
if n_err:
    estado_global = (vc.ERROR, f"{n_err} punto(s) a corregir y {n_pend} pendiente(s).")
elif n_pend:
    estado_global = (vc.PENDIENTE, f"En proceso: faltan {n_pend} punto(s) por completar.")
elif vc.AVISO in estados:
    estado_global = (vc.AVISO, "Validado, con avisos por revisar.")
else:
    estado_global = (vc.OK, "Todo el protocolo está validado.")
with banner.container():
    mostrar_estado(*estado_global)

# ---------------------------------------------------------------------------
# Empaquetado para guardar
# ---------------------------------------------------------------------------
datos_guardar = {
    "version_ficha": 2,
    "guardado": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "id_sensor": sensor_id,
    "pozo": pozo_instalacion,
    "modelo": tipo_modelo,
    "x": coord_x, "y": coord_y, "z": cota_instalacion,
    "prof_pozo": prof_pozo_val, "prof_inst": prof_inst_val, "naf": naf_val,
    "a": coef_a, "b": coef_b, "cf": cf_factor, "tk": tk_factor,
    "s0_baro": s0_baro, "s_baro": s_baro,
    "notas": notas_campo,
    "lectura_fabrica_seco": lectura_fabrica_seco, "temp_fabrica": temp_fabrica,
    "baro_fabrica_hpa": baro_fabrica_hpa, "baro_seco_hpa": baro_seco_hpa,
    "inmersion_fecha": inmersion_fecha, "inmersion_hora": inmersion_hora,
    "altura_referencia": altura_referencia,
    "offset_diafragma_cm": offset_diafragma_cm,
    "l_campo": l_campo, "t_campo": t_campo,
    "crit_n_min": crit_n_min, "crit_tol_rango": crit_tol_rango, "crit_tol_fabrica": crit_tol_fabrica,
    "crit_horas_sat": crit_horas_sat, "crit_tol_inm": crit_tol_inm, "crit_tol_campo": crit_tol_campo,
    "crit_umbral_salto": crit_umbral_salto,
    "tabla_seco": df_seco.to_dict(orient="records"),
    "tabla_sat": df_sat.to_dict(orient="records"),
    "tabla_inm": df_inm.to_dict(orient="records"),
    "tabla_seg": df_seg.to_dict(orient="records"),
    "tabla_alt": df_alt.to_dict(orient="records"),
    "bitacora": list(bitacora),
    # Resultados calculados (referencia; al cargar se recalculan)
    "prom_seco_l": prom_seco_l, "prom_seco_t": prom_seco_t,
    "prom_sat_l0": prom_sat_l0, "prom_sat_t0": prom_sat_t0,
    "c_constante": c_constante,
    "prom_inm_l": prom_inm_l, "prom_inm_t": prom_inm_t,
    "presion_kPa": presion_inm, "altura_mca": altura_inm,
    "elevacion_nivel_campo_msnm": elev_campo,
    "prof_agua_campo_m": prof_agua_campo,
    "checklist": [{"item": n, "estado": e, "detalle": t} for n, e, t in checklist],
    "estado_global": estado_global[0],
}

st.sidebar.divider()
st.sidebar.subheader("💾 Guardar Avances del Pozo")
nombre_base = nombre_archivo(pozo_instalacion)
con_ancho_total(
    st.sidebar.download_button,
    label=f"💾 Descargar / Guardar ({nombre_base}.txt)",
    data=exportar_pozo_txt(datos_guardar),
    file_name=f"{nombre_base}.txt",
    mime="text/plain",
)

st.sidebar.caption("O guárdala directo en una carpeta que elijas (sirve sin internet):")
try:
    carpeta_defecto = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fichas")
except NameError:
    carpeta_defecto = os.path.join(os.getcwd(), "fichas")
carpeta_guardado = st.sidebar.text_input(
    "Carpeta de guardado (ruta completa)", value=carpeta_defecto, key="carpeta_guardado"
)
fecha_en_nombre = st.sidebar.checkbox(
    "Agregar fecha y hora al nombre (no sobrescribe)", value=True, key="fecha_en_nombre"
)
if st.sidebar.button("📁 Guardar en esa carpeta", key="btn_guardar_carpeta"):
    try:
        ruta_guardada = vc.guardar_texto_en_carpeta(
            carpeta_guardado, nombre_base, exportar_pozo_txt(datos_guardar), con_fecha=fecha_en_nombre
        )
        st.sidebar.success(f"Guardado en: {ruta_guardada}")
    except (OSError, ValueError) as exc:
        st.sidebar.error(f"No se pudo guardar: {exc}")

# --- TAB 7: RESUMEN --------------------------------------------------------
with tab7:
    st.header(f"📋 Resumen Ejecutivo — Pozo: {pozo_instalacion} | Sensor: {sensor_id}")

    st.subheader("✔️ Lista de verificación")
    for nombre, estado, detalle in checklist:
        st.markdown(f"{ICONOS[estado]} **{nombre}** — {detalle}")

    st.divider()
    s1, s2, s3 = st.columns(3)
    with s1:
        st.subheader("📍 Geometría y Sitio")
        st.write(f"**Coordenada X:** {coord_x:.2f}")
        st.write(f"**Coordenada Y:** {coord_y:.2f}")
        st.write(f"**Cota Z del sensor:** {cota_instalacion:.3f} m.s.n.m.")
        st.write(f"**Profundidad Pozo:** {prof_pozo_val:.2f} m")
        st.write(f"**Profundidad Inst.:** {prof_inst_val:.2f} m")
        st.write(f"**NAF (sonda):** {naf_val:.2f} m")
    with s2:
        st.subheader("⚙️ Metrología")
        st.write(f"**Lectura en seco:** {fmt(prom_seco_l)} B")
        st.write(f"**Lectura Cero ($L_0$):** {fmt(prom_sat_l0)} B")
        st.write(f"**Temp Cero ($T_0$):** {fmt(prom_sat_t0, 2)} °C")
        if not math.isnan(c_constante):
            st.write(f"**Constante C:** {c_constante:.3f} kPa")
        st.write(f"**Coef. Térmico ($Tk$):** {tk_factor:.4e}")
    with s3:
        st.subheader("📊 Resultados")
        st.write(f"**Prueba inmersión:** {fmt(altura_inm)} mca (ref. {referencia_efectiva:.3f} m)")
        st.write(f"**Lectura de campo:** {fmt(l_campo if campo_capturado else math.nan)} B")
        st.write(f"**Nivel de agua en campo:** {fmt(elev_campo)} m.s.n.m.")
        st.write(f"**Prof. al agua:** {fmt(prof_agua_campo, 2)} m")

    st.divider()
    st.subheader("📌 Observaciones / Novedades de Campo Registradas")
    if notas_campo.strip():
        st.info(f"✍️ **Nota:** {notas_campo}")
    else:
        st.caption("No se han registrado observaciones adicionales para este pozo.")

    st.divider()
    resumen_df = pd.DataFrame(
        [(k, v_) for k, v_ in vc.limpiar_para_json(datos_guardar).items()
         if not k.startswith("tabla_") and k not in ("checklist", "bitacora")],
        columns=["Campo", "Valor"],
    )
    resumen_df["Valor"] = resumen_df["Valor"].astype(str)
    checklist_df = pd.DataFrame(checklist, columns=["Verificación", "Estado", "Detalle"])
    if HAY_EXCEL:
        hojas = {
            "Resumen": resumen_df,
            "Verificacion": checklist_df,
            "Seco": df_seco,
            "Saturado": df_sat,
            "Inmerso": (con_conocida_y_variacion(
                            vc.calcular_tabla_presion(df_inm, cal, prom_sat_l0, prom_sat_t0, s_baro),
                            referencia_efectiva)
                        if listo_calculo else df_inm),
            "Seguimiento": (tabla_seg.drop(columns=["_dt"]) if not tabla_seg.empty else df_seg),
            "Bitacora": pd.DataFrame(bitacora, columns=COLS_BITACORA),
        }
        con_ancho_total(
            st.download_button,
            label="📥 Descargar Reporte en Excel",
            data=vc.construir_excel(hojas),
            file_name=f"reporte_{nombre_base}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        st.download_button(
            label="📥 Descargar Resumen en CSV",
            data=resumen_df.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"reporte_{nombre_base}.csv",
            mime="text/csv",
        )
        st.caption("Para exportar a Excel agrega `openpyxl` a requirements.txt.")
