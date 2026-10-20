import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(page_title="Guía y Verificación de Piezómetros VWP", page_icon="📊", layout="wide")

st.title("🚰 Sistema y Protocolo de Verificación de Piezómetros VWP")
st.markdown("Herramienta basada en el procedimiento de campo: En Seco $\rightarrow$ Saturado (Lectura $L_0$ y Constante $C$) $\rightarrow$ Inmerso ($0.5\text{ m}$ de prueba).")

# --- BASE DE DATOS DE SENSORES EN MEMORIA (STATE) ---
if "sensores_db" not in st.session_state:
    st.session_state.sensores_db = {
        "VW17419": {
            "pozo": "B1-3B", "modelo": "Polinomial", "x": 350120.00, "y": 2840500.00, "z": 616.500, 
            "prof_pozo": 35.0, "prof_inst": 30.0, "naf": 5.50,
            "a": -3.9602e-07, "b": -1.9458e-01, "cf": 0.0, "tk": 1.1566e-02
        }
    }

# --- BARRA LATERAL: CATÁLOGO Y PARÁMETROS ---
st.sidebar.header("1. Catálogo de Sensores")
lista_sensores = list(st.session_state.sensores_db.keys())
sensor_seleccionado = st.sidebar.selectbox("Seleccione el Piezómetro (ID)", lista_sensores)

with st.sidebar.expander("➕ Agregar nuevo sensor"):
    nuevo_id = st.text_input("ID del Sensor (Serial)", value="VW-02")
    nuevo_pozo = st.text_input("Pozo / Ubicación de Instalación", value="B2-4A")
    nuevo_modelo = st.selectbox("Modelo", ["Polinomial", "Lineal"], key="n_mod")
    col_nx, col_ny, col_nz = st.columns(3)
    with col_nx:
        nueva_x = st.number_input("Coordenada X", value=350000.0, format="%.2f", key="n_x")
    with col_ny:
        nueva_y = st.number_input("Coordenada Y", value=2840000.0, format="%.2f", key="n_y")
    with col_nz:
        nueva_z = st.number_input("Elevación Z", value=615.0, format="%.3f", key="n_z")
        
    col_np1, col_np2, col_np3 = st.columns(3)
    with col_np1:
        n_prof_pozo = st.number_input("Prof. Pozo (m)", value=30.0, format="%.2f", key="n_pp")
    with col_np2:
        n_prof_inst = st.number_input("Prof. Inst. (m)", value=25.0, format="%.2f", key="n_pi")
    with col_np3:
        n_naf = st.number_input("NAF (m)", value=4.0, format="%.2f", key="n_naf")
        
    if st.button("Guardar Sensor"):
        if nuevo_id not in st.session_state.sensores_db:
            st.session_state.sensores_db[nuevo_id] = {
                "pozo": nuevo_pozo, "modelo": nuevo_modelo, "x": nueva_x, "y": nueva_y, "z": nueva_z,
                "prof_pozo": n_prof_pozo, "prof_inst": n_prof_inst, "naf": n_naf,
                "a": -3.9602e-07, "b": -1.9458e-01, "cf": 0.0, "tk": 0.01
            }
            st.success(f"¡Sensor {nuevo_id} guardado!")
            st.rerun()
        else:
            st.error("El ID ya existe.")

datos_sensor = st.session_state.sensores_db[sensor_seleccionado]

st.sidebar.divider()
st.sidebar.header(f"Parámetros: {sensor_seleccionado}")

# Campo editable para el pozo del sensor seleccionado
pozo_instalacion = st.sidebar.text_input("Pozo / Ubicación Asignada", value=str(datos_sensor.get("pozo", "B1-3B")))

idx_modelo = 0 if datos_sensor.get("modelo", "Polinomial") == "Polinomial" else 1
tipo_modelo = st.sidebar.selectbox("Modelo de Cálculo", ["Polinomial", "Lineal"], index=idx_modelo)

st.sidebar.subheader("Ubicación y Coordenadas")
coord_x = st.sidebar.number_input("Coordenada X", value=float(datos_sensor.get("x", 0.0)), format="%.2f")
coord_y = st.sidebar.number_input("Coordenada Y", value=float(datos_sensor.get("y", 0.0)), format="%.2f")
cota_instalacion = st.sidebar.number_input("Elevación Z / Cota (m.s.n.m.)", value=float(datos_sensor.get("z", 0.0)), format="%.3f")

st.sidebar.subheader("Geometría del Pozo y Niveles")
prof_pozo_val = st.sidebar.number_input("Profundidad del Pozo (m)", value=float(datos_sensor.get("prof_pozo", 35.0)), format="%.2f")
prof_inst_val = st.sidebar.number_input("Profundidad de Instalación (m)", value=float(datos_sensor.get("prof_inst", 30.0)), format="%.2f")
naf_val = st.sidebar.number_input("Nivel de Agua Freática - NAF (m)", value=float(datos_sensor.get("naf", 5.50)), format="%.2f")

st.sidebar.subheader("Constantes del Fabricante")
if tipo_modelo == "Polinomial":
    coef_a = st.sidebar.number_input("Constante A", value=float(datos_sensor.get("a", -3.9602e-07)), format="%.4e")
    coef_b = st.sidebar.number_input("Constante B", value=float(datos_sensor.get("b", -1.9458e-01)), format="%.4e")
    cf_factor = 0.0
else:
    cf_factor = st.sidebar.number_input("Factor Lineal (CF)", value=float(datos_sensor.get("cf", 9.7384e-02)), format="%.4e")
    coef_a, coef_b = 0.0, 0.0

tk_factor = st.sidebar.number_input("Coeficiente Térmico (Tk) [kPa/°C]", value=float(datos_sensor.get("tk", 1.1566e-02)), format="%.4e")

st.sidebar.subheader("Presión Barométrica (Opcional)")
s0_baro = st.sidebar.number_input("Presión Inicial S0 (kPa)", value=101.325, format="%.3f")
s_baro = st.sidebar.number_input("Presión Actual S (kPa)", value=101.325, format="%.3f")

# --- PESTAÑAS DEL PROTOCOLO DE 3 FASES + RESUMEN ---
tab1, tab2, tab3, tab4 = st.tabs([
    "1. Fase En Seco", 
    "2. Fase Saturado (Lectura L0)", 
    "3. Fase Inmerso (Prueba 0.5m)",
    "4. Resumen Ejecutivo"
])

fecha_hoy = datetime.now().strftime("%Y-%m-%d")
hora_actual = datetime.now().strftime("%H:%M")

with tab1:
    st.header(f"a) Registro Inicial En Seco — Sensor: {sensor_seleccionado} | Pozo: {pozo_instalacion}")
    st.info("💡 **Guía:** Lecturas al aire libre previas a la saturación del sensor.")
    
    df_seco_default = pd.DataFrame({
        "Lectura (#)": [f"Lectura {i}" for i in range(1, 11)],
        "Fecha": [fecha_hoy] * 10,
        "Hora": [hora_actual] * 10,
        "Lectura (B units)": [9756.774 + i*0.1 for i in range(10)],
        "Temperatura (°C)": [25.23] * 10
    })
    
    df_seco_editado = st.data_editor(df_seco_default, num_rows="fixed", use_container_width=True, key=f"sec_{sensor_seleccionado}")
    prom_seco_l = df_seco_editado["Lectura (B units)"].mean()
    prom_seco_t = df_seco_editado["Temperatura (°C)"].mean()
    st.success(f"Promedio En Seco — Lectura: **{prom_seco_l:.3f} B units** | Temp: **{prom_seco_t:.2f} °C**")

with tab2:
    st.header(f"b) Registro Saturado (Lectura Cero $L_0$ Oficial) — Pozo: {pozo_instalacion}")
    st.info("💡 **Guía:** Se toman tras saturar el sensor. De aquí se obtiene el **$L_0$ oficial** y se calcula la **Constante C** ($C = -[A(L_0^2) + B(L_0)]$).")
    
    df_sat_default = pd.DataFrame({
        "Lectura (#)": [f"Lectura {i}" for i in range(1, 11)],
        "Fecha": ["31/03/2025"] * 10,
        "Hora": ["16:23", "16:24", "16:25", "16:26", "16:27", "16:28", "16:29", "16:30", "16:31", "16:32"],
        "Lectura (B units)": [9757.488, 9757.667, 9758.308, 9758.378, 9758.414, 9758.466, 9758.210, 9758.213, 9758.494, 9758.415],
        "Temperatura (°C)": [26.07, 25.85, 25.75, 25.70, 25.68, 25.67, 25.68, 25.68, 25.69, 25.69]
    })
    
    df_sat_editado = st.data_editor(df_sat_default, num_rows="fixed", use_container_width=True, key=f"sat_{sensor_seleccionado}")
    
    prom_sat_l0 = df_sat_editado["Lectura (B units)"].mean()
    prom_sat_t0 = df_sat_editado["Temperatura (°C)"].mean()
    
    c_constante = 0.0
    if tipo_modelo == "Polinomial":
        c_constante = - (coef_a * (prom_sat_l0 ** 2) + coef_b * prom_sat_l0)
        
    st.success(f"**Lectura Cero Oficial ($L_0$):** **{prom_sat_l0:.3f} B units** | **$T_0$:** **{prom_sat_t0:.2f} °C**")
    if tipo_modelo == "Polinomial":
        st.warning(f"🔧 **Constante C Calculada:** `{c_constante:.3f}` kPa")

with tab3:
    st.header(f"c) Registro Inmerso (Prueba de 0.5 m) — Pozo: {pozo_instalacion}")
    st.info("💡 **Guía:** Sensor colocado en el recipiente con **0.5 metros de columna de agua** para verificar la precisión del instrumento.")
    
    df_inm_default = pd.DataFrame({
        "Lectura (#)": [f"Lectura {i}" for i in range(1, 11)],
        "Fecha": [fecha_hoy] * 10,
        "Hora": [hora_actual] * 10,
        "Lectura (B units)": [9742.884 + i*0.05 for i in range(10)],
        "Temperatura (°C)": [29.31] * 10
    })
    
    df_inm_editado = st.data_editor(df_inm_default, num_rows="fixed", use_container_width=True, key=f"inm_{sensor_seleccionado}")
    
    prom_inm_l = df_inm_editado["Lectura (B units)"].mean()
    prom_inm_t = df_inm_editado["Temperatura (°C)"].mean()

# Cálculos finales globales para usar en el resumen
delta_baro = s0_baro - s_baro
efecto_termico = tk_factor * (prom_sat_t0 - prom_inm_t)

if tipo_modelo == "Polinomial":
    termino_a = coef_a * (prom_inm_l ** 2)
    termino_b = coef_b * prom_inm_l
    presion_kPa = termino_a + termino_b + c_constante - efecto_termico + delta_baro
else:
    presion_kPa = cf_factor * (prom_sat_l0 - prom_inm_l) - efecto_termico + delta_baro
    
altura_mca = presion_kPa / 9.81
elevacion_agua_msnm = cota_instalacion + altura_mca

with tab4:
    st.header(f"📋 Resumen Ejecutivo y QA/QC — {sensor_seleccionado}")
    st.markdown(f"**Ubicación / Pozo:** `{pozo_instalacion}`")
    
    col_sum1, col_sum2, col_sum3 = st.columns(3)
    
    with col_sum1:
        st.subheader("📍 Geometría y Sitio")
        st.write(f"**Coordenada X:** {coord_x:.2f}")
        st.write(f"**Coordenada Y:** {coord_y:.2f}")
        st.write(f"**Cota / Elevación Z:** {cota_instalacion:.3f} m.s.n.m.")
        st.write(f"**Profundidad del Pozo:** {prof_pozo_val:.2f} m")
        st.write(f"**Profundidad de Inst.:** {prof_inst_val:.2f} m")
        st.write(f"**NAF (Nivel Agua):** {naf_val:.2f} m")
        st.write(f"**Modelo de Cálculo:** {tipo_modelo}")
        
    with col_sum2:
        st.subheader("⚙️ Parámetros Metrológicos")
        st.write(f"**Lectura Cero ($L_0$):** {prom_sat_l0:.3f} B")
        st.write(f"**Temperatura Cero ($T_0$):** {prom_sat_t0:.2f} °C")
        if tipo_modelo == "Polinomial":
            st.write(f"**Constante A:** {coef_a:.4e}")
            st.write(f"**Constante B:** {coef_b:.4e}")
            st.write(f"**Constante C:** {c_constante:.3f} kPa")
        else:
            st.write(f"**Factor Lineal (CF):** {cf_factor:.4e}")
        st.write(f"**Coeficiente Térmico ($Tk$):** {tk_factor:.4e}")

    with col_sum3:
        st.subheader("📊 Resultados de Prueba (0.5m)")
        st.write(f"**Lectura Inmerso ($L$):** {prom_inm_l:.3f} B")
        st.write(f"**Temp. Inmerso ($T$):** {prom_inm_t:.2f} °C")
        st.write(f"**Presión Calculada:** {presion_kPa:.2f} kPa")
        st.write(f"**Columna de Agua:** {altura_mca:.3f} mca")
        st.write(f"**Elevación del Agua:** {elevacion_agua_msnm:.3f} m.s.n.m.")

    st.divider()
    
    # Botón para exportar reporte completo desde el resumen
    col_exp1, col_exp2 = st.columns([1, 2])
    with col_exp1:
        data_resumen = {
            "Sensor_ID": [sensor_seleccionado],
            "Pozo_Ubicacion": [pozo_instalacion],
            "Coord_X": [coord_x],
            "Coord_Y": [coord_y],
            "Cota_Z_msnm": [cota_instalacion],
            "Profundidad_Pozo_m": [prof_pozo_val],
            "Profundidad_Inst_m": [prof_inst_val],
            "NAF_m": [naf_val],
            "Modelo": [tipo_modelo],
            "L0_Saturado": [prom_sat_l0],
            "T0_Saturado": [prom_sat_t0],
            "Constante_A": [coef_a if tipo_modelo == "Polinomial" else "N/A"],
            "Constante_B": [coef_b if tipo_modelo == "Polinomial" else "N/A"],
            "Constante_C": [c_constante if tipo_modelo == "Polinomial" else "N/A"],
            "Factor_CF": [cf_factor if tipo_modelo == "Lineal" else "N/A"],
            "Tk_Termico": [tk_factor],
            "L_Inmerso": [prom_inm_l],
            "Presion_kPa": [presion_kPa],
            "Columna_Agua_m": [altura_mca],
            "Elevacion_Agua_msnm": [elevacion_agua_msnm]
        }
        df_export = pd.DataFrame(data_resumen)
        st.download_button(
            label="📥 Descargar Reporte Completo (CSV)",
            data=df_export.to_csv(index=False).encode('utf-8'),
            file_name=f"resumen_verificacion_{sensor_seleccionado}_{pozo_instalacion}.csv",
            mime="text/csv",
            use_container_width=True
        )
