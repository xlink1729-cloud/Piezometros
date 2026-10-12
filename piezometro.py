import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(page_title="Guía y Verificación de Piezómetros VWP", page_icon="📊", layout="wide")

st.title("🚰 Sistema y Protocolo de Verificación de Piezómetros VWP")
st.markdown("Herramienta basada en el procedimiento de campo: En Seco ==> Saturado (Lectura $L_0$ y Constante $C$) ==> Inmerso (a $0.5 m$ de prueba).")

# --- BASE DE DATOS DE SENSORES EN MEMORIA (STATE) ---
if "sensores_db" not in st.session_state:
    st.session_state.sensores_db = {
        "VW17419": {
            "modelo": "Polinomial", "x": 350120.00, "y": 2840500.00, "z": 616.500, 
            "a": -3.9602e-07, "b": -1.9458e-01, "cf": 0.0, "tk": 1.1566e-02
        }
    }

# --- BARRA LATERAL: CATÁLOGO Y PARÁMETROS ---
st.sidebar.header("1. Catálogo de Sensores")
lista_sensores = list(st.session_state.sensores_db.keys())
sensor_seleccionado = st.sidebar.selectbox("Seleccione el Piezómetro", lista_sensores)

with st.sidebar.expander("➕ Agregar nuevo sensor"):
    nuevo_id = st.text_input("ID del Sensor", value="VW-02")
    nuevo_modelo = st.selectbox("Modelo", ["Polinomial", "Lineal"], key="n_mod")
    col_nx, col_ny, col_nz = st.columns(3)
    with col_nx:
        nueva_x = st.number_input("Coordenada X", value=350000.0, format="%.2f", key="n_x")
    with col_ny:
        nueva_y = st.number_input("Coordenada Y", value=2840000.0, format="%.2f", key="n_y")
    with col_nz:
        nueva_z = st.number_input("Elevación Z", value=615.0, format="%.3f", key="n_z")
        
    if st.button("Guardar Sensor"):
        if nuevo_id not in st.session_state.sensores_db:
            st.session_state.sensores_db[nuevo_id] = {
                "modelo": nuevo_modelo, "x": nueva_x, "y": nueva_y, "z": nueva_z,
                "a": -3.9602e-07, "b": -1.9458e-01, "cf": 0.0, "tk": 0.01
            }
            st.success(f"¡Sensor {nuevo_id} guardado!")
            st.rerun()
        else:
            st.error("El ID ya existe.")

datos_sensor = st.session_state.sensores_db[sensor_seleccionado]

st.sidebar.divider()
st.sidebar.header(f"Parámetros: {sensor_seleccionado}")

idx_modelo = 0 if datos_sensor.get("modelo", "Polinomial") == "Polinomial" else 1
tipo_modelo = st.sidebar.selectbox("Modelo de Cálculo", ["Polinomial", "Lineal"], index=idx_modelo)

st.sidebar.subheader("Ubicación y Coordenadas")
coord_x = st.sidebar.number_input("Coordenada X", value=float(datos_sensor.get("x", 0.0)), format="%.2f")
coord_y = st.sidebar.number_input("Coordenada Y", value=float(datos_sensor.get("y", 0.0)), format="%.2f")
cota_instalacion = st.sidebar.number_input("Elevación Z / Cota (m.s.n.m.)", value=float(datos_sensor.get("z", 0.0)), format="%.3f")

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

# --- PESTAÑAS DEL PROTOCOLO DE 3 FASES ---
tab1, tab2, tab3 = st.tabs([
    "1. Fase En Seco", 
    "2. Fase Saturado (Lectura L0 Oficial)", 
    "3. Fase Inmerso (Prueba 0.5m)"
])

fecha_hoy = datetime.now().strftime("%Y-%m-%d")
hora_actual = datetime.now().strftime("%H:%M")

with tab1:
    st.header(f"a) Registro Inicial En Seco — {sensor_seleccionado}")
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
    st.header(f"b) Registro Saturado (Lectura Cero $L_0$ Oficial) — {sensor_seleccionado}")
    st.info("💡 **Guía:** Se toman tras saturar el sensor. De aquí se obtiene el **$L_0$ oficial** y se calcula la **Constante C** ($C = -[A(L_0^2) + B(L_0)]$).")
    
    df_sat_default = pd.DataFrame({
        "Lectura (#)": [f"Lectura {i}" for i in range(1, 11)],
        "Fecha": [fecha_hoy] * 10,
        "Hora": [hora_actual] * 10,
        "Lectura (B units)": [9757.488 + i*0.1 for i in range(10)],
        "Temperatura (°C)": [25.75] * 10
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
    st.header(f"c) Registro Inmerso (Prueba de 0.5 m) — {sensor_seleccionado}")
    st.info("💡 **Guía:** Sensor colocado en el tubo de PVC con **0.5 metros de columna de agua** para verificar la precisión del instrumento.")
    
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
    
    # Cálculos finales usando L0 y T0 de la fase saturada
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

    st.divider()
    st.subheader("Resultados de la Verificación (Prueba de 0.5 m)")
    
    res_c1, res_c2, res_c3, res_c4 = st.columns(4)
    res_c1.metric("Presión Calculada", f"{presion_kPa:.2f} kPa")
    res_c2.metric("Presión en Bar", f"{presion_kPa / 100:.3f} bar")
    res_c3.metric("Columna de Agua Medida", f"{altura_mca:.3f} mca", delta=f"{altura_mca - 0.5:.3f} m vs 0.5m patrón")
    res_c4.metric("Elevación del Agua", f"{elevacion_agua_msnm:.3f} m.s.n.m.")

# Botón para exportar reporte
st.divider()
if st.button(f"📥 Generar Reporte de Verificación — {sensor_seleccionado}"):
    data_resumen = {
        "Sensor": [sensor_seleccionado],
        "Coord_X": [coord_x],
        "Coord_Y": [coord_y],
        "Cota_Z_msnm": [cota_instalacion],
        "Modelo": [tipo_modelo],
        "L0_Saturado": [prom_sat_l0],
        "T0_Saturado": [prom_sat_t0],
        "Constante_C": [c_constante if tipo_modelo == "Polinomial" else "N/A"],
        "L_Inmerso": [prom_inm_l],
        "Presion_kPa": [presion_kPa],
        "Columna_Agua_m": [altura_mca],
        "Elevacion_Agua_msnm": [elevacion_agua_msnm]
    }
    df_export = pd.DataFrame(data_resumen)
    st.download_button(
        label="Descargar CSV de Resultados",
        data=df_export.to_csv(index=False).encode('utf-8'),
        file_name=f"verificacion_{sensor_seleccionado}.csv",
        mime="text/csv",
    )
