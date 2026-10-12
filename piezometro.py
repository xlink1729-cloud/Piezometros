import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(page_title="Verificación de Piezómetros VWP", page_icon="📊", layout="wide")

st.title("🚰 Protocolo de Verificación de Piezómetros de Cuerda Vibrante")
st.markdown("Herramienta de verificación con cálculo de Columna de Agua y Elevación ($m.s.n.m.$).")

# Configuración general y constantes en la barra lateral
st.sidebar.header("1. Configuración del Sensor y Cota")
sensor_id = st.sidebar.text_input("ID del Piezómetro", value="VWP-01")
tipo_modelo = st.sidebar.selectbox("Modelo de Cálculo", ["Polinomial", "Lineal"])

# Parámetro clave extraído de la hoja de cálculo
cota_instalacion = st.sidebar.number_input("Cota / Elevación de Instalación (m.s.n.m.)", value=616.500, format="%.3f")

st.sidebar.subheader("Parámetros de Calibración")
if tipo_modelo == "Polinomial":
    coef_a = st.sidebar.number_input("Constante A", value=4.9327e-08, format="%.4e")
    coef_b = st.sidebar.number_input("Constante B", value=-9.8039e-02, format="%.4f")
else:
    cf_factor = st.sidebar.number_input("Factor Lineal (CF) [kPa/B unit]", value=9.7384e-02, format="%.4e")

tk_factor = st.sidebar.number_input("Coeficiente Térmico (Tk) [kPa/°C]", value=1.2270e-01, format="%.4e")

st.sidebar.subheader("Presión Barométrica (Opcional)")
s0_baro = st.sidebar.number_input("Presión Inicial S0 (kPa)", value=101.325, format="%.3f")
s_baro = st.sidebar.number_input("Presión Actual S (kPa)", value=101.325, format="%.3f")

tab1, tab2 = st.tabs(["2. Fase a) En Seco (L0, T0)", "3. Fase b) Saturado y Resultados"])

fecha_hoy = datetime.now().strftime("%Y-%m-%d")
hora_actual = datetime.now().strftime("%H:%M")

with tab1:
    st.header("a) Verificación en Seco (Lectura Inicial / L0)")
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
        key="editor_seco"
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
    st.header("b) Verificación Saturado (Lectura Actual / L)")
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
        key="editor_sat"
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
    st.subheader("Resultados de la Verificación y Elevación")
    
    res_c1, res_c2, res_c3, res_c4 = st.columns(4)
    res_c1.metric("Presión (kPa)", f"{presion_kPa:.2f}")
    res_c2.metric("Presión (bar)", f"{presion_kPa / 100:.3f}")
    res_c3.metric("Columna de Agua (m)", f"{altura_mca:.3f}")
    res_c4.metric("Elevación del Agua (m.s.n.m.)", f"{elevacion_agua_msnm:.3f}")

    with st.expander("Ver desglose técnico de la ecuación"):
        st.write(f"- **Cota de Instalación:** {cota_instalacion:.3f} m.s.n.m.")
        st.write(f"- **Modelo utilizado:** {tipo_modelo}[cite: 5]")
        st.write(f"- **Lectura Inicial ($L_0$):** {prom_seco_l0:.3f} B units[cite: 5]")
        st.write(f"- **Lectura Actual ($L$):** {prom_sat_l:.3f} B units[cite: 5]")
        if tipo_modelo == "Polinomial":
            st.write(f"- **Constante C:** {c_constante:.4f} kPa[cite: 5]")
        st.write(f"- **Corrección Térmica:** {-efecto_termico:.3f} kPa[cite: 5]")

# Botón para exportar reporte resumido en CSV
st.divider()
if st.button("📥 Generar Resumen para Reporte"):
    data_resumen = {
        "Sensor": [sensor_id],
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
        label="Descargar CSV de Verificación",
        data=df_export.to_csv(index=False).encode('utf-8'),
        file_name=f"verificacion_{sensor_id}.csv",
        mime="text/csv",
    )
