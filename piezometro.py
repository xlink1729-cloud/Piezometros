import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(page_title="Verificación de Piezómetros VWP", page_icon="📊", layout="wide")

st.title("🚰 Protocolo de Verificación de Piezómetros de Cuerda Vibrante")
st.markdown("Herramienta basada en el procedimiento de verificación (En Seco / Saturado) y **Fórmula Polinómica**.")

# Configuración general y constantes del fabricante en la barra lateral
st.sidebar.header("1. Datos y Constantes del Sensor")
sensor_id = st.sidebar.text_input("ID del Piezómetro", value="VW17419")

st.sidebar.subheader("Coeficientes Polinomiales")
# Valores por defecto basados en la imagen de ejemplo
coef_a = st.sidebar.number_input("Constante A", value=-3.9602e-07, format="%.4e")
coef_b = st.sidebar.number_input("Constante B", value=-1.9458e-01, format="%.4f")
tk_factor = st.sidebar.number_input("Coeficiente Térmico (TK) [kPa/°C]", value=0.0500, format="%.4f")

tab1, tab2 = st.tabs(["2. Fase a) En Seco (L0, T0)", "3. Fase b) Saturado y Resultados"])

fecha_hoy = datetime.now().strftime("%Y-%m-%d")
hora_actual = datetime.now().strftime("%H:%M")

with tab1:
    st.header("a) Verificación en Seco (Determinación de Cero)")
    st.write("Ingrese las 10 lecturas consecutivas al aire, su temperatura y la hora correspondiente (intervalos de 1 min).")
    
    df_seco_default = pd.DataFrame({
        "Lectura (#)": [f"Lectura {i}" for i in range(1, 11)],
        "Fecha": [fecha_hoy] * 10,
        "Hora": [hora_actual] * 10,
        "Lectura (dígitos)": [9758.205 + i*0.1 for i in range(10)], # Ejemplo base
        "Temperatura (°C)": [25.75] * 10
    })
    
    df_seco_editado = st.data_editor(
        df_seco_default, 
        num_rows="fixed", 
        use_container_width=True,
        column_config={
            "Lectura (#)": st.column_config.TextColumn("Lectura (#)", width="small"),
            "Fecha": st.column_config.TextColumn("Fecha", width="medium"),
            "Hora": st.column_config.TextColumn("Hora", width="small"),
            "Lectura (dígitos)": st.column_config.NumberColumn("Lectura (dígitos)", format="%.3f", width="medium"),
            "Temperatura (°C)": st.column_config.NumberColumn("Temperatura (°C)", format="%.2f", width="medium")
        },
        key="editor_seco"
    )
    
    prom_seco_r = df_seco_editado["Lectura (dígitos)"].mean()
    prom_seco_t = df_seco_editado["Temperatura (°C)"].mean()
    
    # Cálculo automático de la constante C basada en L0 (prom_seco_r)
    c_constante = -coef_a * (prom_seco_r ** 2) - coef_b * prom_seco_r
    
    st.success(f"**Promedio Fase en Seco ($L_0$):** **{prom_seco_r:.3f} dígitos** | **$T_0$:** **{prom_seco_t:.2f} °C**")
    st.info(f"**Constante C calculada:** `{c_constante:.3f}`")

with tab2:
    st.header("b) Verificación Saturado")
    st.write("Sensor saturado tras 1 hora sin filtro poroso, con el filtro colocado de nuevo en el contenedor de agua.")
    
    df_sat_default = pd.DataFrame({
        "Lectura (#)": [f"Lectura {i}" for i in range(1, 11)],
        "Fecha": [fecha_hoy] * 10,
        "Hora": [hora_actual] * 10,
        "Lectura (dígitos)": [prom_seco_r + 150.0 + (i*0.2) for i in range(10)],
        "Temperatura (°C)": [25.0] * 10
    })
    
    df_sat_editado = st.data_editor(
        df_sat_default, 
        num_rows="fixed", 
        use_container_width=True,
        column_config={
            "Lectura (#)": st.column_config.TextColumn("Lectura (#)", width="small"),
            "Fecha": st.column_config.TextColumn("Fecha", width="medium"),
            "Hora": st.column_config.TextColumn("Hora", width="small"),
            "Lectura (dígitos)": st.column_config.NumberColumn("Lectura (dígitos)", format="%.3f", width="medium"),
            "Temperatura (°C)": st.column_config.NumberColumn("Temperatura (°C)", format="%.2f", width="medium")
        },
        key="editor_sat"
    )
    
    prom_sat_r = df_sat_editado["Lectura (dígitos)"].mean()
    prom_sat_t = df_sat_editado["Temperatura (°C)"].mean()
    
    # Aplicación de la fórmula polinómica completa: P = A*(L^2) + B*L + C - TK*(T0 - T)
    l_act = prom_sat_r
    t_act = prom_sat_t
    
    termino_a = coef_a * (l_act ** 2)
    termino_b = coef_b * l_act
    termino_termico = tk_factor * (prom_seco_t - t_act)
    
    presion_kPa = termino_a + termino_b + c_constante - termino_termico
    altura_mca = presion_kPa / 9.81

    st.divider()
    st.subheader("Resultados de la Verificación Polinómica")
    
    res_c1, res_c2, res_c3 = st.columns(3)
    res_c1.metric("Presión Calculada (kPa)", f"{presion_kPa:.2f}")
    res_c2.metric("Presión Calculada (bar)", f"{presion_kPa / 100:.3f}")
    res_c3.metric("Columna de Agua (mca)", f"{altura_mca:.2f}")

    with st.expander("Ver desglose de la fórmula polinómica"):
        st.write(f"- **Lectura Inicial ($L_0$):** {prom_seco_r:.3f} dig")
        st.write(f"- **Lectura Actual ($L$ / Saturado):** {prom_sat_r:.3f} dig")
        st.write(f"- **Temperatura Inicial ($T_0$):** {prom_seco_t:.2f} °C")
        st.write(f"- **Temperatura Actual ($T$):** {prom_sat_t:.2f} °C")
        st.write(f"- **Constante C:** {c_constante:.3f}")
        st.write(f"- **Efecto Térmico ($TK \cdot (T_0 - T)$):** {termino_termico:.3f} kPa")

# Botón para exportar reporte resumido en CSV
st.divider()
if st.button("📥 Generar Resumen para Reporte"):
    data_resumen = {
        "Sensor": [sensor_id],
        "Prom_Seco_L0": [prom_seco_r],
        "Prom_Seco_T0": [prom_seco_t],
        "Prom_Saturado_L": [prom_sat_r],
        "Prom_Saturado_T": [prom_sat_t],
        "Constante_C": [c_constante],
        "Presion_kPa": [presion_kPa],
        "Presion_mca": [altura_mca]
    }
    df_export = pd.DataFrame(data_resumen)
    st.download_button(
        label="Descargar CSV de Verificación",
        data=df_export.to_csv(index=False).encode('utf-8'),
        file_name=f"verificacion_polinomial_{sensor_id}.csv",
        mime="text/csv",
    )
