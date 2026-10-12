import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(page_title="Verificación de Piezómetros VWP", page_icon="📊", layout="wide")

st.title("🚰 Protocolo de Verificación de Piezómetros de Cuerda Vibrante")
st.markdown("Herramienta de verificación en taller/campo (En Seco, Saturado / Inmerso a 0.5m) con control de Pozo y NAF.")

# Configuración general, del pozo y constantes en la barra lateral
st.sidebar.header("1. Identificación y Pozo")
sensor_id = st.sidebar.text_input("ID del Piezómetro", value="VWP-01")
nombre_pozo = st.sidebar.text_input("Nombre / ID del Pozo", value="Pozo-PZ-05")
ubicacion_sitio = st.sidebar.text_input("Sitio / Proyecto", value="Obra Hidráulica")
naf_inicial = st.sidebar.number_input("Nivel de Agua Freática (NAF) [m]", value=12.50, format="%.2f")

st.sidebar.header("2. Configuración de Cálculo")
tipo_modelo = st.sidebar.selectbox("Modelo de Cálculo", ["Polinomial", "Lineal"])

if tipo_modelo == "Polinomial":
    coef_a = st.sidebar.number_input("Constante A", value=1.4917e-07, format="%.4e")
    coef_b = st.sidebar.number_input("Constante B", value=-9.9531e-02, format="%.4f")
else:
    cf_factor = st.sidebar.number_input("Factor Lineal (CF) [kPa/B unit]", value=9.7398e-02, format="%.4e")

tk_factor = st.sidebar.number_input("Coeficiente Térmico (Tk) [kPa/°C]", value=1.1566e-02, format="%.4e")

st.sidebar.subheader("Presión Barométrica (Opcional)")
s0_baro = st.sidebar.number_input("Presión Inicial S0 (kPa)", value=101.325, format="%.3f")
s_baro = st.sidebar.number_input("Presión Actual S (kPa)", value=101.325, format="%.3f")

tab1, tab2 = st.tabs(["3. Fase a) En Seco (L0, T0)", "4. Fase b) Inmerso / Saturado y Resultados"])

fecha_hoy = datetime.now().strftime("%Y-%m-%d")
hora_actual = datetime.now().strftime("%H:%M")

with tab1:
    st.header("a) Verificación en Seco (Lectura Inicial / L0)")
    st.write(f"**Sitio:** {ubicacion_sitio} | **Pozo:** {nombre_pozo} | **NAF de referencia:** {naf_inicial} m")
    st.write("Ingrese las 10 lecturas consecutivas al aire, su temperatura y hora (B units = $Hz^2 / 1000$).")
    
    df_seco_default = pd.DataFrame({
        "Lectura (#)": [f"Lectura {i}" for i in range(1, 11)],
        "Fecha": [fecha_hoy] * 10,
        "Hora": [hora_actual] * 10,
        "Lectura (B units)": [2890.0 + i*0.2 for i in range(10)],
        "Temperatura (°C)": [22.0] * 10
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
        st.info(f"**Constante C calculada ($C = -[A(L_0^2) + B(L_0)]$):** `{c_constante:.4f}` kPa[cite: 5, 6]")

with tab2:
    st.header("b) Verificación Inmerso / Saturado (Prueba a 0.5 m o Tubo)")
    st.write("Sensor saturado e inmerso en el tubo de prueba (columna de referencia de 0.5 m o contenedor).")
    
    df_sat_default = pd.DataFrame({
        "Lectura (#)": [f"Lectura {i}" for i in range(1, 11)],
        "Fecha": [fecha_hoy] * 10,
        "Hora": [hora_actual] * 10,
        "Lectura (B units)": [prom_seco_l0 + 150.0 + (i*0.2) for i in range(10)],
        "Temperatura (°C)": [20.5] * 10
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

    st.divider()
    st.subheader("Resultados de la Verificación")
    
    res_c1, res_c2, res_c3 = st.columns(3)
    res_c1.metric("Presión Calculada (kPa)", f"{presion_kPa:.2f}")
    res_c2.metric("Presión Calculada (bar)", f"{presion_kPa / 100:.3f}")
    res_c3.metric("Columna de Agua (mca)", f"{altura_mca:.2f}")

    with st.expander("Ver resumen técnico y datos del pozo"):
        st.write(f"- **Sitio / Proyecto:** {ubicacion_sitio}")
        st.write(f"- **Pozo destino:** {nombre_pozo}")
        st.write(f"- **NAF registrada:** {naf_inicial} m")
        st.write(f"- **Modelo utilizado:** {tipo_modelo}[cite: 5]")
        st.write(f"- **Lectura Inicial ($L_0$):** {prom_seco_l0:.3f} B units[cite: 5]")
        st.write(f"- **Lectura Actual ($L$):** {prom_sat_l:.3f} B units[cite: 5]")
        if tipo_modelo == "Polinomial":
            st.write(f"- **Constante C:** {c_constante:.4f} kPa[cite: 5, 6]")

# Botón para exportar reporte resumido en CSV con datos de pozo y NAF
st.divider()
if st.button("📥 Generar Resumen para Reporte"):
    data_resumen = {
        "Sitio": [ubicacion_sitio],
        "Pozo": [nombre_pozo],
        "Sensor": [sensor_id],
        "NAF_m": [naf_inicial],
        "Modelo": [tipo_modelo],
        "L0_Seco": [prom_seco_l0],
        "T0_Seco": [prom_seco_t0],
        "L_Saturado": [prom_sat_l],
        "T_Saturado": [prom_sat_t],
        "Presion_kPa": [presion_kPa],
        "Presion_mca": [altura_mca]
    }
    df_export = pd.DataFrame(data_resumen)
    st.download_button(
        label="Descargar CSV de Verificación",
        data=df_export.to_csv(index=False).encode('utf-8'),
        file_name=f"verificacion_{nombre_pozo}_{sensor_id}.csv",
        mime="text/csv",
    )
