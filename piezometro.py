import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(page_title="Gestión y Verificación de Piezómetros VWP", page_icon="📊", layout="wide")

st.title("🚰 Sistema de Verificación y Calibración de Piezómetros VWP")
st.markdown("Gestión multi-sensor para el control de piezómetros de cuerda vibrante (Lineal y Polinómico).")

# --- BASE DE DATOS DE SENSORES EN MEMORIA (STATE) ---
if "sensores_db" not in st.session_state:
    # Creamos un catálogo inicial de ejemplo con varios sensores
    st.session_state.sensores_db = {
        "VWP-01": {
            "modelo": "Polinomial", "cota": 616.500, 
            "a": 4.9327e-08, "b": -9.8039e-02, "cf": 0.0, "tk": 1.2270e-01
        },
        "VWP-02": {
            "modelo": "Polinomial", "cota": 612.100, 
            "a": 1.4917e-07, "b": -9.9531e-02, "cf": 0.0, "tk": 1.1566e-02
        },
        "VWP-03": {
            "modelo": "Lineal", "cota": 620.000, 
            "a": 0.0, "b": 0.0, "cf": 9.7384e-02, "tk": 1.2270e-01
        }
    }

# --- BARRA LATERAL: SELECCIÓN Y ADMINISTRACIÓN DE SENSORES ---
st.sidebar.header("1. Catálogo de Sensores")
sensor_seleccionado = st.sidebar.selectbox("Seleccione el Piezómetro", list(st.session_state.sensores_db.keys()))

with st.sidebar.expander("➕ Agregar nuevo sensor al proyecto"):
    nuevo_id = st.text_input("ID del Nuevo Sensor", value="VWP-04")
    nuevo_modelo = st.selectbox("Modelo", ["Polinomial", "Lineal"], key="n_mod")
    nueva_cota = st.number_input("Cota de Instalación (m.s.n.m.)", value=615.0, format="%.3f", key="n_cot")
    if st.button("Guardar Sensor"):
        if nuevo_id not in st.session_state.sensores_db:
            st.session_state.sensores_db[nuevo_id] = {
                "modelo": nuevo_modelo, "cota": nueva_cota,
                "a": 1.0e-07, "b": -0.1, "cf": 0.09, "tk": 0.05
            }
            st.success(f"¡Sensor {nuevo_id} agregado con éxito! Seleccionalo arriba.")
            st.rerun()
        else:
            st.error("El ID del sensor ya existe.")

# Cargar los datos del sensor activo seleccionado
datos_sensor = st.session_state.sensores_db[sensor_seleccionado]

st.sidebar.divider()
st.sidebar.header(f"Parámetros: {sensor_seleccionado}")
tipo_modelo = st.sidebar.selectbox("Modelo de Cálculo", ["Polinomial", "Lineal"], index=0 if datos_sensor["modelo"]=="Polinomial" else 1, key="act_mod")
cota_instalacion = st.sidebar.number_input("Cota de Instalación (m.s.n.m.)", value=datos_sensor["cota"], format="%.3f", key="act_cot")

if tipo_modelo == "Polinomial":
    coef_a = st.sidebar.number_input("Constante A", value=datos_sensor["a"], format="%.4e", key="act_a")
    coef_b = st.sidebar.number_input("Constante B", value=datos_sensor["b"], format="%.4f", key="act_b")
    cf_factor = 0.0
else:
    cf_factor = st.sidebar.number_input("Factor Lineal (CF) [kPa/B unit]", value=datos_sensor["cf"] if datos_sensor["cf"]>0 else 9.7384e-02, format="%.4e", key="act_cf")
    coef_a, coef_b = 0.0, 0.0

tk_factor = st.sidebar.number_input("Coeficiente Térmico (Tk) [kPa/°C]", value=datos_sensor["tk"], format="%.4e", key="act_tk")

st.sidebar.subheader("Presión Barométrica (Opcional)")
s0_baro = st.sidebar.number_input("Presión Inicial S0 (kPa)", value=101.325, format="%.3f")
s_baro = st.sidebar.number_input("Presión Actual S (kPa)", value=101.325, format="%.3f")

# --- PESTAÑAS DE TRABAJO ---
tab1, tab2 = st.tabs([f"2. Fase a) En Seco ({sensor_seleccionado})", f"3. Fase b) Saturado y Resultados"])

fecha_hoy = datetime.now().strftime("%Y-%m-%d")
hora_actual = datetime.now().strftime("%H:%M")

with tab1:
    st.header(f"a) Verificación en Seco — {sensor_seleccionado}")
    st.write("Ingrese las 10 lecturas consecutivas al aire, su temperatura y hora (B units).")
    
    df_seco_default = pd.DataFrame({
        "Lectura (#)": [f"Lectura {i}" for i in range(1, 11)],
        "Fecha": [fecha_hoy] * 10,
        "Hora": [hora_actual] * 10,
        "Lectura (B units)": [7502.300 + i*0.1 for i in range(10)],
        "Temperatura (°C)": [28.0] * 10
    })
    
    df_seco_editado = st.data_editor(
        df_seco_default, 
        num_rows="fixed", 
        use_container_width=True,
        column_config={
            "Lectura (#)": st.column_config.TextColumn("Lectura (#)", width="small"),
            "Fecha": st.column_config.TextColumn("Fecha", width="medium"),
            "Hora": st.column_config.TextColumn("Hora", width="small"),
            "Lectura (B units)": st.column_config.NumberColumn("Lectura (B units)", format="%.3f", width="medium"),
            "Temperatura (°C)": st.column_config.NumberColumn("Temperatura (°C)", format="%.2f", width="medium")
        },
        key=f"editor_seco_{sensor_seleccionado}"
    )
    
    prom_seco_l0 = df_seco_editado["Lectura (B units)"].mean()
    prom_seco_t0 = df_seco_editado["Temperatura (°C)"].mean()
    
    c_constante = 0.0
    if tipo_modelo == "Polinomial":
        c_constante = - (coef_a * (prom_seco_l0 ** 2) + coef_b * prom_seco_l0)
    
    st.success(f"**Promedio Fase en Seco ($L_0$):** **{prom_seco_l0:.3f} B units** | **$T_0$:** **{prom_seco_t0:.2f} °C**")
    if tipo_modelo == "Polinomial":
        st.info(f"**Constante C calculada ($C = -[A(L_0^2) + B(L_0)]$):** `{c_constante:.4f}` kPa")

with tab2:
    st.header(f"b) Verificación Saturado — {sensor_seleccionado}")
    st.write("Sensor saturado tras 1 hora sin filtro poroso, con el filtro colocado de nuevo en el contenedor de agua.")
    
    df_sat_default = pd.DataFrame({
        "Lectura (#)": [f"Lectura {i}" for i in range(1, 11)],
        "Fecha": [fecha_hoy] * 10,
        "Hora": [hora_actual] * 10,
        "Lectura (B units)": [prom_seco_l0 + 150.0 + (i*0.2) for i in range(10)],
        "Temperatura (°C)": [28.0] * 10
    })
    
    df_sat_editado = st.data_editor(
        df_sat_default, 
        num_rows="fixed", 
        use_container_width=True,
        column_config={
            "Lectura (#)": st.column_config.TextColumn("Lectura (#)", width="small"),
            "Fecha": st.column_config.TextColumn("Fecha", width="medium"),
            "Hora": st.column_config.TextColumn("Hora", width="small"),
            "Lectura (B units)": st.column_config.NumberColumn("Lectura (B units)", format="%.3f", width="medium"),
            "Temperatura (°C)": st.column_config.NumberColumn("Temperatura (°C)", format="%.2f", width="medium")
        },
        key=f"editor_sat_{sensor_seleccionado}"
    )
    
    prom_sat_l = df_sat_editado["Lectura (B units)"].mean()
    prom_sat_t = df_sat_editado["Temperatura (°C)"].mean()
    
    delta_baro = s0_baro - s_baro
    efecto_termico = tk_factor * (prom_seco_t0 - prom_sat_t)
    
    if tipo_modelo == "Polinomial":
        termino_a = coef_a * (prom_sat_l ** 2)
        termino_b = coef_b * prom_sat_l
        presion_kPa = termino_a + termino_b + c_constante - efecto_termico + delta_baro
    else:
        presion_kPa = cf_factor * (prom_seco_l0 - prom_sat_l) - efecto_termico + delta_baro
        
    altura_mca = presion_kPa / 9.81
    elevacion_agua_msnm = cota_instalacion + altura_mca

    st.divider()
    st.subheader(f"Resultados de Verificación: {sensor_seleccionado}")
    
    res_c1, res_c2, res_c3, res_c4 = st.columns(4)
    res_c1.metric("Presión (kPa)", f"{presion_kPa:.2f}")
    res_c2.metric("Presión (bar)", f"{presion_kPa / 100:.3f}")
    res_c3.metric("Columna de Agua (m)", f"{altura_mca:.3f}")
    res_c4.metric("Elevación del Agua (m.s.n.m.)", f"{elevacion_agua_msnm:.3f}")

# Botón para exportar reporte resumido en CSV del sensor activo
st.divider()
if st.button(f"📥 Generar Reporte CSV de {sensor_seleccionado}"):
    data_resumen = {
        "Sensor": [sensor_seleccionado],
        "Cota_Instalacion_msnm": [cota_instalacion],
        "Modelo": [tipo_modelo],
        "L0_Seco": [prom_seco_l0],
        "L_Saturado": [prom_sat_l],
        "Presion_kPa": [presion_kPa],
        "Columna_Agua_m": [altura_mca],
        "Elevacion_Agua_msnm": [elevacion_agua_msnm]
    }
    df_export = pd.DataFrame(data_resumen)
    st.download_button(
        label=f"Descargar CSV de {sensor_seleccionado}",
        data=df_export.to_csv(index=False).encode('utf-8'),
        file_name=f"verificacion_{sensor_seleccionado}.csv",
        mime="text/csv",
    )
