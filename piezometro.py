from datetime import datetime
import json
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Guía y Verificación de Piezómetros VWP",
    page_icon="📊",
    layout="wide",
)

st.title("🚰 Sistema y Protocolo de Verificación de Piezómetros VWP")
st.markdown(
    "Herramienta basada en el procedimiento de campo: En Seco ==> Saturado"
    " (Lectura $L_0$ y Constante $C$) ==> Inmerso (0.5 m de prueba)."
)

# --- FUNCIONES PARA MANEJO DE ARCHIVOS .TXT DE CADA POZO ---


def exportar_pozo_txt(datos_pozo):
  """Convierte el diccionario de datos del pozo a formato JSON estructurado en texto."""
  return json.dumps(datos_pozo, ensure_ascii=False, indent=4)


def importar_pozo_txt(contenido_txt):
  """Lee el contenido del archivo .txt guardado y lo reconvierte a diccionario."""
  try:
    return json.loads(contenido_txt)
  except Exception as e:
    st.error(f"Error al leer el archivo de pozo: {e}")
    return None


# --- ESTADO INICIAL ---
if "datos_actuales" not in st.session_state:
  st.session_state.datos_actuales = {
      "id_sensor": "VW17419",
      "pozo": "B1-3B",
      "modelo": "Polinomial",
      "x": 350120.00,
      "y": 2840500.00,
      "z": 616.500,
      "prof_pozo": 35.0,
      "prof_inst": 30.0,
      "naf": 5.50,
      "a": -3.9602e-07,
      "b": -1.9458e-01,
      "cf": 0.0,
      "tk": 1.1566e-02,
  }

# --- BARRA LATERAL: CARGAR / GUARDAR Y PARÁMETROS ---
st.sidebar.header("📂 Gestión de Fichas de Pozo (.txt)")

# 1. Cargar archivo existente
archivo_subido = st.sidebar.file_uploader(
    "Cargar datos de Pozo (.txt)", type=["txt"]
)
if archivo_subido is not None:
  contenido = archivo_subido.getvalue().decode("utf-8")
  datos_cargados = importar_pozo_txt(contenido)
  if datos_cargados:
    st.session_state.datos_actuales = datos_cargados
    st.sidebar.success(
        f"¡Datos de pozo '{datos_cargados.get('pozo', 'Cargado')}' cargados!"
    )

st.sidebar.divider()
st.sidebar.header("1. Datos Generales y del Sensor")

d = st.session_state.datos_actuales

sensor_id = st.sidebar.text_input("ID / Serial del Sensor", value=d.get("id_sensor", "VW17419"))
pozo_instalacion = st.sidebar.text_input("Pozo / Ubicación Asignada", value=d.get("pozo", "B1-3B"))

idx_modelo = 0 if d.get("modelo", "Polinomial") == "Polinomial" else 1
tipo_modelo = st.sidebar.selectbox("Modelo de Cálculo", ["Polinomial", "Lineal"], index=idx_modelo)

st.sidebar.subheader("Ubicación y Coordenadas")
coord_x = st.sidebar.number_input("Coordenada X", value=float(d.get("x", 0.0)), format="%.2f")
coord_y = st.sidebar.number_input("Coordenada Y", value=float(d.get("y", 0.0)), format="%.2f")
cota_instalacion = st.sidebar.number_input("Elevación Z / Cota (m.s.n.m.)", value=float(d.get("z", 0.0)), format="%.3f")

st.sidebar.subheader("Geometría del Pozo y Niveles")
prof_pozo_val = st.sidebar.number_input("Profundidad del Pozo (m)", value=float(d.get("prof_pozo", 35.0)), format="%.2f")
prof_inst_val = st.sidebar.number_input("Profundidad de Instalación (m)", value=float(d.get("prof_inst", 30.0)), format="%.2f")
naf_val = st.sidebar.number_input("Nivel de Agua Freática - NAF (m)", value=float(d.get("naf", 5.50)), format="%.2f")

st.sidebar.subheader("Constantes del Fabricante")
if tipo_modelo == "Polinomial":
  coef_a = st.sidebar.number_input("Constante A", value=float(d.get("a", -3.9602e-07)), format="%.4e")
  coef_b = st.sidebar.number_input("Constante B", value=float(d.get("b", -1.9458e-01)), format="%.4e")
  cf_factor = 0.0
else:
  cf_factor = st.sidebar.number_input("Factor Lineal (CF)", value=float(d.get("cf", 9.7384e-02)), format="%.4e")
  coef_a, coef_b = 0.0, 0.0

tk_factor = st.sidebar.number_input("Coeficiente Térmico (Tk) [kPa/°C]", value=float(d.get("tk", 1.1566e-02)), format="%.4e")

st.sidebar.subheader("Presión Barométrica (Opcional)")
s0_baro = st.sidebar.number_input("Presión Inicial S0 (kPa)", value=101.325, format="%.3f")
s_baro = st.sidebar.number_input("Presión Actual S (kPa)", value=101.325, format="%.3f")

# --- PESTAÑAS DEL PROTOCOLO DE 3 FASES + RESUMEN ---
tab1, tab2, tab3, tab4 = st.tabs([
    "1. Fase En Seco",
    "2. Fase Saturado (Lectura L0)",
    "3. Fase Inmerso (Prueba 0.5m)",
    "4. Resumen Ejecutivo y Exportación",
])

fecha_hoy = datetime.now().strftime("%Y-%m-%d")
hora_actual = datetime.now().strftime("%H:%M")

with tab1:
  st.header(f"a) Registro Inicial En Seco — Sensor: {sensor_id} | Pozo: {pozo_instalacion}")
  st.info("💡 **Guía:** Lecturas al aire libre previas a la saturación del sensor.")

  df_seco_default = pd.DataFrame({
      "Lectura (#)": [f"Lectura {i}" for i in range(1, 11)],
      "Fecha": [fecha_hoy] * 10,
      "Hora": [hora_actual] * 10,
      "Lectura (B units)": [9756.774 + i * 0.1 for i in range(10)],
      "Temperatura (°C)": [25.23] * 10,
  })

  df_seco_editado = st.data_editor(
      df_seco_default, num_rows="fixed", use_container_width=True, key=f"sec_{sensor_id}_{pozo_instalacion}"
  )
  prom_seco_l = df_seco_editado["Lectura (B units)"].mean()
  prom_seco_t = df_seco_editado["Temperatura (°C)"].mean()
  st.success(f"Promedio En Seco — Lectura: **{prom_seco_l:.3f} B units** | Temp: **{prom_seco_t:.2f} °C**")

with tab2:
  st.header(f"b) Registro Saturado (Lectura Cero $L_0$ Oficial) — Pozo: {pozo_instalacion}")
  st.info("💡 **Guía:** Se toman tras saturar el sensor. De aquí se obtiene el **$L_0$ oficial** y se calcula la **Constante C**.")

  df_sat_default = pd.DataFrame({
      "Lectura (#)": [f"Lectura {i}" for i in range(1, 11)],
      "Fecha": ["31/03/2025"] * 10,
      "Hora": ["16:23", "16:24", "16:25", "16:26", "16:27", "16:28", "16:29", "16:30", "16:31", "16:32"],
      "Lectura (B units)": [9757.488, 9757.667, 9758.308, 9758.378, 9758.414, 9758.466, 9758.210, 9758.213, 9758.494, 9758.415],
      "Temperatura (°C)": [26.07, 25.85, 25.75, 25.70, 25.68, 25.67, 25.68, 25.68, 25.69, 25.69],
  })

  df_sat_editado = st.data_editor(
      df_sat_default, num_rows="fixed", use_container_width=True, key=f"sat_{sensor_id}_{pozo_instalacion}"
  )

  prom_sat_l0 = df_sat_editado["Lectura (B units)"].mean()
  prom_sat_t0 = df_sat_editado["Temperatura (°C)"].mean()

  c_constante = 0.0
  if tipo_modelo == "Polinomial":
    c_constante = -(coef_a * (prom_sat_l0**2) + coef_b * prom_sat_l0)

  st.success(f"**Lectura Cero Oficial ($L_0$):** **{prom_sat_l0:.3f} B units** | **$T_0$:** **{prom_sat_t0:.2f} °C**")
  if tipo_modelo == "Polinomial":
    st.warning(f"🔧 **Constante C Calculada:** `{c_constante:.3f}` kPa")

with tab3:
  st.header(f"c) Registro Inmerso (Prueba de 0.5 m) — Pozo: {pozo_instalacion}")
  st.info("💡 **Guía:** Sensor colocado en el recipiente con **0.5 metros de columna de agua**.")

  df_inm_default = pd.DataFrame({
      "Lectura (#)": [f"Lectura {i}" for i in range(1, 11)],
      "Fecha": [fecha_hoy] * 10,
      "Hora": [hora_actual] * 10,
      "Lectura (B units)": [9742.884 + i * 0.05 for i in range(10)],
      "Temperatura (°C)": [29.31] * 10,
  })

  df_inm_editado = st.data_editor(
      df_inm_default, num_rows="fixed", use_container_width=True, key=f"inm_{sensor_id}_{pozo_instalacion}"
  )

  prom_inm_l = df_inm_editado["Lectura (B units)"].mean()
  prom_inm_t = df_inm_editado["Temperatura (°C)"].mean()

# Cálculos globales
delta_baro = s0_baro - s_baro
efecto_termico = tk_factor * (prom_sat_t0 - prom_inm_t)

if tipo_modelo == "Polinomial":
  termino_a = coef_a * (prom_inm_l**2)
  termino_b = coef_b * prom_inm_l
  presion_kPa = termino_a + termino_b + c_constante - efecto_termico + delta_baro
else:
  presion_kPa = cf_factor * (prom_sat_l0 - prom_inm_l) - efecto_termico + delta_baro

altura_mca = presion_kPa / 9.81
elevacion_agua_msnm = cota_instalacion + altura_mca

# Armar estructura completa del pozo para exportar
datos_pozo_completos = {
    "id_sensor": sensor_id,
    "pozo": pozo_instalacion,
    "modelo": tipo_modelo,
    "x": coord_x,
    "y": coord_y,
    "z": cota_instalacion,
    "prof_pozo": prof_pozo_val,
    "prof_inst": prof_inst_val,
    "naf": naf_val,
    "a": coef_a,
    "b": coef_b,
    "cf": cf_factor,
    "tk": tk_factor,
    "prom_seco_l": prom_seco_l,
    "prom_seco_t": prom_seco_t,
    "prom_sat_l0": prom_sat_l0,
    "prom_sat_t0": prom_sat_t0,
    "c_constante": c_constante,
    "prom_inm_l": prom_inm_l,
    "prom_inm_t": prom_inm_t,
    "presion_kPa": presion_kPa,
    "altura_mca": altura_mca,
    "elevacion_agua_msnm": elevacion_agua_msnm,
}

with tab4:
  st.header(f"📋 Resumen Ejecutivo — Pozo: {pozo_instalacion} | Sensor: {sensor_id}")

  col_sum1, col_sum2, col_sum3 = st.columns(3)

  with col_sum1:
    st.subheader("📍 Geometría y Sitio")
    st.write(f"**Coordenada X:** {coord_x:.2f}")
    st.write(f"**Coordenada Y:** {coord_y:.2f}")
    st.write(f"**Cota Z:** {cota_instalacion:.3f} m.s.n.m.")
    st.write(f"**Profundidad Pozo:** {prof_pozo_val:.2f} m")
    st.write(f"**Profundidad Inst.:** {prof_inst_val:.2f} m")
    st.write(f"**NAF:** {naf_val:.2f} m")

  with col_sum2:
    st.subheader("⚙️ Metrología")
    st.write(f"**Lectura Cero ($L_0$):** {prom_sat_l0:.3f} B")
    st.write(f"**Temp Cero ($T_0$):** {prom_sat_t0:.2f} °C")
    if tipo_modelo == "Polinomial":
      st.write(f"**Constante C:** {c_constante:.3f} kPa")
    st.write(f"**Coef. Térmico ($Tk$):** {tk_factor:.4e}")

  with col_sum3:
    st.subheader("📊 Resultados Prueba (0.5m)")
    st.write(f"**Lectura Inmerso ($L$):** {prom_inm_l:.3f} B")
    st.write(f"**Presión Calculada:** {presion_kPa:.2f} kPa")
    st.write(f"**Columna de Agua:** {altura_mca:.3f} mca")
    st.write(f"**Elevación Agua:** {elevacion_agua_msnm:.3f} m.s.n.m.")

  st.divider()

  # BOTONES DE GUARDADO / DESCARGA
  st.subheader("💾 Guardar y Exportar Datos del Pozo")
  col_btn1, col_btn2 = st.columns(2)

  with col_btn1:
    # Generar el archivo .txt para descargar (Ideal para Online y Offline)
    string_txt = exportar_pozo_txt(datos_pozo_completos)
    nombre_archivo = f"{pozo_instalacion}.txt"

    st.download_button(
        label=f"💾 Guardar / Descargar Ficha ({nombre_archivo})",
        data=string_txt,
        file_name=nombre_archivo,
        mime="text/plain",
        use_container_width=True,
    )

  with col_btn2:
    # Exportar también el CSV de reporte
    df_export = pd.DataFrame([datos_pozo_completos])
    st.download_button(
        label="📥 Descargar Reporte Tabular (CSV)",
        data=df_export.to_csv(index=False).encode("utf-8"),
        file_name=f"reporte_{pozo_instalacion}.csv",
        mime="text/csv",
        use_container_width=True,
    )
