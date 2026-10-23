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
    "Herramienta de campo con registro progresivo en archivo `.txt` por pozo."
)

# --- FUNCIONES DE IMPORTACIÓN / EXPORTACIÓN ---


def exportar_pozo_txt(datos_pozo):
  return json.dumps(datos_pozo, ensure_ascii=False, indent=4)


def importar_pozo_txt(contenido_txt):
  try:
    return json.loads(contenido_txt)
  except Exception as e:
    st.error(f"Error al cargar el archivo .txt: {e}")
    return None


fecha_hoy_default = datetime.now().strftime("%Y-%m-%d")
hora_actual_default = datetime.now().strftime("%H:%M")


def crear_df_base(
    lecturas_list=None,
    fechas_list=None,
    horas_list=None,
    temps_list=None,
    val_l_base=9750.0,
    val_t_base=25.0,
):
  fechas = fechas_list if fechas_list else [fecha_hoy_default] * 10
  horas = horas_list if horas_list else [hora_actual_default] * 10
  lecturas = (
      lecturas_list
      if lecturas_list
      else [val_l_base + i * 0.1 for i in range(10)]
  )
  temps = temps_list if temps_list else [val_t_base] * 10

  return pd.DataFrame({
      "Lectura (#)": [f"Lectura {i}" for i in range(1, 11)],
      "Fecha": fechas,
      "Hora": horas,
      "Lectura (B units)": lecturas,
      "Temperatura (°C)": temps,
  })


# --- ESTADO INICIAL EN SESIÓN ---
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
      "s0_baro": 101.325,
      "s_baro": 101.325,
      "notas": "",  # Campo para observaciones de campo
      "tabla_seco": None,
      "tabla_sat": None,
      "tabla_inm": None,
  }

d = st.session_state.datos_actuales

# --- BARRA LATERAL: CARGAR / GUARDAR SIEMPRE VISIBLES ---
st.sidebar.header("📂 1. Gestión de Ficha (.txt)")

# Botón rápido para limpiar y registrar un sensor nuevo
if st.sidebar.button(
    "✨ Registrar Nuevo Sensor / Pozo Limpio", use_container_width=True
):
  st.session_state.datos_actuales = {
      "id_sensor": "VW-NUEVO",
      "pozo": "Nuevo-Pozo",
      "modelo": "Polinomial",
      "x": 0.0,
      "y": 0.0,
      "z": 0.0,
      "prof_pozo": 30.0,
      "prof_inst": 25.0,
      "naf": 4.0,
      "a": -3.9602e-07,
      "b": -1.9458e-01,
      "cf": 0.0,
      "tk": 1.1566e-02,
      "s0_baro": 101.325,
      "s_baro": 101.325,
      "notas": "",
      "tabla_seco": None,
      "tabla_sat": None,
      "tabla_inm": None,
  }
  st.rerun()

# Cargar Ficha Existente
archivo_subido = st.sidebar.file_uploader(
    "Cargar Ficha de Pozo (.txt)", type=["txt"]
)
if archivo_subido is not None:
  contenido = archivo_subido.getvalue().decode("utf-8")
  datos_cargados = importar_pozo_txt(contenido)
  if datos_cargados:
    st.session_state.datos_actuales = datos_cargados
    d = datos_cargados
    st.sidebar.success(
        f"¡Ficha '{datos_cargados.get('pozo', 'Pozo')}' cargada!"
    )

st.sidebar.divider()
st.sidebar.header("2. Datos Generales y Parámetros")

sensor_id = st.sidebar.text_input(
    "ID / Serial del Sensor", value=d.get("id_sensor", "VW17419")
)
pozo_instalacion = st.sidebar.text_input(
    "Pozo / Ubicación", value=d.get("pozo", "B1-3B")
)

idx_modelo = 0 if d.get("modelo", "Polinomial") == "Polinomial" else 1
tipo_modelo = st.sidebar.selectbox(
    "Modelo de Cálculo", ["Polinomial", "Lineal"], index=idx_modelo
)

st.sidebar.subheader("Ubicación y Geometría")
coord_x = st.sidebar.number_input(
    "Coordenada X", value=float(d.get("x", 0.0)), format="%.2f"
)
coord_y = st.sidebar.number_input(
    "Coordenada Y", value=float(d.get("y", 0.0)), format="%.2f"
)
cota_instalacion = st.sidebar.number_input(
    "Cota Z (m.s.n.m.)", value=float(d.get("z", 0.0)), format="%.3f"
)
prof_pozo_val = st.sidebar.number_input(
    "Prof. Pozo (m)", value=float(d.get("prof_pozo", 35.0)), format="%.2f"
)
prof_inst_val = st.sidebar.number_input(
    "Prof. Inst. (m)", value=float(d.get("prof_inst", 30.0)), format="%.2f"
)
naf_val = st.sidebar.number_input(
    "NAF (m)", value=float(d.get("naf", 5.50)), format="%.2f"
)

st.sidebar.subheader("Constantes del Fabricante")
if tipo_modelo == "Polinomial":
  coef_a = st.sidebar.number_input(
      "Constante A", value=float(d.get("a", -3.9602e-07)), format="%.4e"
  )
  coef_b = st.sidebar.number_input(
      "Constante B", value=float(d.get("b", -1.9458e-01)), format="%.4e"
  )
  cf_factor = 0.0
else:
  cf_factor = st.sidebar.number_input(
      "Factor Lineal (CF)",
      value=float(d.get("cf", 9.7384e-02)),
      format="%.4e",
  )
  coef_a, coef_b = 0.0, 0.0

tk_factor = st.sidebar.number_input(
    "Coef. Térmico (Tk)", value=float(d.get("tk", 1.1566e-02)), format="%.4e"
)

st.sidebar.subheader("Presión Barométrica")
s0_baro = st.sidebar.number_input(
    "S0 Inicial (kPa)", value=float(d.get("s0_baro", 101.325)), format="%.3f"
)
s_baro = st.sidebar.number_input(
    "S Actual (kPa)", value=float(d.get("s_baro", 101.325)), format="%.3f"
)

# RECUADRO DE NOTAS / OBSERVACIONES EN LA BARRA LATERAL
st.sidebar.subheader("📝 Observaciones / Notas de Campo")
notas_campo = st.sidebar.text_area(
    "Registro de novedades en pozo:",
    value=d.get("notas", ""),
    placeholder="Ej: Pozo B1-3A asolvado a los 22m, freatímetro indica obstrucción...",
    height=100,
)


# --- PESTAÑAS DE REGISTRO ---
tab1, tab2, tab3, tab4 = st.tabs([
    "1. Fase En Seco",
    "2. Fase Saturado (L0)",
    "3. Fase Inmerso (0.5m)",
    "4. Resumen Ejecutivo y Observaciones",
])

# --- TAB 1: SECO ---
with tab1:
  st.header(f"a) Registro En Seco — Pozo: {pozo_instalacion}")

  df_seco_init = (
      pd.DataFrame(d["tabla_seco"])
      if d.get("tabla_seco")
      else crear_df_base(val_l_base=9756.0, val_t_base=25.2)
  )
  df_seco_editado = st.data_editor(
      df_seco_init,
      num_rows="fixed",
      use_container_width=True,
      key=f"ed_sec_{pozo_instalacion}",
  )

  # --- LÍNEA CLAVE PARA CONGELAR TUS DATOS Y HORA EN SECO ---
  st.session_state.datos_actuales["tabla_seco"] = df_seco_editado.to_dict(
      orient="records"
  )

  prom_seco_l = df_seco_editado["Lectura (B units)"].mean()
  prom_seco_t = df_seco_editado["Temperatura (°C)"].mean()
  st.success(
      f"Promedio En Seco — Lectura: **{prom_seco_l:.3f} B** | Temp:"
      f" **{prom_seco_t:.2f} °C**"
  )
    
# --- TAB 2: SATURADO ---
with tab2:
  st.header(f"b) Registro Saturado (Lectura Cero L0) — Pozo: {pozo_instalacion}")

  df_sat_init = (
      pd.DataFrame(d["tabla_sat"])
      if d.get("tabla_sat")
      else crear_df_base(val_l_base=9758.0, val_t_base=25.7)
  )
  df_sat_editado = st.data_editor(
      df_sat_init,
      num_rows="fixed",
      use_container_width=True,
      key=f"ed_sat_{pozo_instalacion}",
  )

  # --- LÍNEA CLAVE PARA CONGELAR TUS DATOS Y HORA ---
  st.session_state.datos_actuales["tabla_sat"] = df_sat_editado.to_dict(
      orient="records"
  )

  prom_sat_l0 = df_sat_editado["Lectura (B units)"].mean()
  prom_sat_t0 = df_sat_editado["Temperatura (°C)"].mean()

  c_constante = 0.0
  if tipo_modelo == "Polinomial":
    c_constante = -(coef_a * (prom_sat_l0**2) + coef_b * prom_sat_l0)

  st.success(
      f"**L0 Oficial:** **{prom_sat_l0:.3f} B** | **T0:**"
      f" **{prom_sat_t0:.2f} °C**"
  )
  if tipo_modelo == "Polinomial":
    st.warning(f"🔧 **Constante C:** `{c_constante:.3f}` kPa")
      
# --- TAB 3: INMERSO ---
with tab3:
  st.header(f"c) Registro Inmerso (0.5 m) — Pozo: {pozo_instalacion}")

  df_inm_init = (
      pd.DataFrame(d["tabla_inm"])
      if d.get("tabla_inm")
      else crear_df_base(val_l_base=9743.0, val_t_base=29.3)
  )
  df_inm_editado = st.data_editor(
      df_inm_init,
      num_rows="fixed",
      use_container_width=True,
      key=f"ed_inm_{pozo_instalacion}",
  )

  # --- LÍNEA CLAVE PARA CONGELAR TUS DATOS Y HORA EN INMERSO ---
  st.session_state.datos_actuales["tabla_inm"] = df_inm_editado.to_dict(
      orient="records"
  )

  prom_inm_l = df_inm_editado["Lectura (B units)"].mean()
  prom_inm_t = df_inm_editado["Temperatura (°C)"].mean()

  # --- VALIDACIÓN AUTOMÁTICA DE LA PRUEBA DE 0.5M ---
  st.divider()
  st.subheader("🎯 Validación de la Prueba (Columna Esperada: 0.50 m)")

  # Nota: 'altura_mca' se calcula con las variables globales de abajo, 
  # por lo que podemos calcular una vista previa aquí mismo para mostrarlo en la pestaña:
  _delta_baro = s0_baro - s_baro
  _efecto_termico = tk_factor * (prom_sat_t0 - prom_inm_t)
  if tipo_modelo == "Polinomial":
    _presion_kPa = (coef_a * (prom_inm_l**2)) + (coef_b * prom_inm_l) + c_constante - _efecto_termico + _delta_baro
  else:
    _presion_kPa = cf_factor * (prom_sat_l0 - prom_inm_l) - _efecto_termico + _delta_baro
  
  _altura_mca_preview = _presion_kPa / 9.81
  diferencia_m = abs(_altura_mca_preview - 0.50)

  col_v1, col_v2 = st.columns(2)
  with col_v1:
    st.metric(
        label="Columna Calculada vs Real",
        value=f"{_altura_mca_preview:.3f} mca",
        delta=f"{_altura_mca_preview - 0.50:+.3f} m",
    )

  with col_v2:
    if diferencia_m <= 0.05:
      st.success(
          "✅ **PRUEBA APROBADA**: El sensor responde correctamente a la columna de 0.5m (±5 cm)."
      )
    else:
      st.error(
          "⚠️ **REVISAR**: La lectura difiere más de 5 cm de la columna real. Verifique constantes o posibles burbujas."
      )
        
# CÁLCULOS GLOBALES
delta_baro = s0_baro - s_baro
efecto_termico = tk_factor * (prom_sat_t0 - prom_inm_t)

if tipo_modelo == "Polinomial":
  termino_a = coef_a * (prom_inm_l**2)
  termino_b = coef_b * prom_inm_l
  presion_kPa = termino_a + termino_b + c_constante - efecto_termico + delta_baro
else:
  presion_kPa = (
      cf_factor * (prom_sat_l0 - prom_inm_l) - efecto_termico + delta_baro
  )

altura_mca = presion_kPa / 9.81
elevacion_agua_msnm = cota_instalacion + altura_mca

# --- EMPAQUETADO COMPLETO PARA GUARDAR ---
datos_guardar = {
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
    "s0_baro": s0_baro,
    "s_baro": s_baro,
    "notas": notas_campo,  # Guarda la nota en la ficha .txt
    "tabla_seco": df_seco_editado.to_dict(orient="records"),
    "tabla_sat": df_sat_editado.to_dict(orient="records"),
    "tabla_inm": df_inm_editado.to_dict(orient="records"),
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

# --- SECCIÓN DE GUARDADO CONTINUO EN LA BARRA LATERAL ---
st.sidebar.divider()
st.sidebar.subheader("💾 Guardar Avances del Pozo")
string_txt = exportar_pozo_txt(datos_guardar)
nombre_archivo_txt = f"{pozo_instalacion}.txt"

st.sidebar.download_button(
    label=f"💾 Descargar / Guardar ({nombre_archivo_txt})",
    data=string_txt,
    file_name=nombre_archivo_txt,
    mime="text/plain",
    use_container_width=True,
)

# --- TAB 4: RESUMEN Y NOTAS ---
with tab4:
  st.header(
      f"📋 Resumen Ejecutivo — Pozo: {pozo_instalacion} | Sensor: {sensor_id}"
  )

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

  # VISUALIZACIÓN DE NOTAS EN EL RESUMEN
  st.subheader("📌 Observaciones / Novedades de Campo Registradas")
  if notas_campo.strip():
    st.info(f"✍️ **Nota:** {notas_campo}")
  else:
    st.caption("No se han registrado observaciones adicionales para este pozo.")

  st.divider()

  # EXPORTACIÓN EXCEL / CSV (incluye la columna de notas)
  df_export = pd.DataFrame([datos_guardar])
  st.download_button(
      label="📥 Descargar Reporte en Excel / CSV",
      data=df_export.to_csv(index=False).encode("utf-8"),
      file_name=f"reporte_{pozo_instalacion}.csv",
      mime="text/csv",
  )
