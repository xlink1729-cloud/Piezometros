import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Verificación de Piezómetros VWP", page_icon="📊", layout="wide")

st.title("🚰 Protocolo de Verificación de Piezómetros de Cuerda Vibrante")
st.markdown("Herramienta basada en el procedimiento de verificación: **En Seco** y **Saturado**.")

# Configuración general en la barra lateral
st.sidebar.header("1. Datos Generales del Sensor")
sensor_id = st.sidebar.text_input("ID del Piezómetro", value="PZ-01")
g_factor = st.sidebar.number_input("Factor de Calibración (G) [kPa/dígito]", value=0.1500, format="%.4f")
k_factor = st.sidebar.number_input("Coeficiente Térmico (K) [kPa/°C]", value=0.0500, format="%.4f")

tab1, tab2 = st.tabs(["2. Fase a) En Seco", "3. Fase b) Saturado"])

with tab1:
    st.header("a) Verificación en Seco")
    st.write("Modifique directamente las celdas de la tabla con las 10 lecturas consecutivas (intervalos de 1 min).")
    
    # Crear un DataFrame por defecto para las 10 lecturas en seco
    df_seco_default = pd.DataFrame({
        "Lectura (#)": [f"Lectura {i}" for i in range(1, 11)],
        "Lectura (dígitos)": [7500.0 + i*0.5 for i in range(10)],
        "Temperatura (°C)": [22.0] * 10
    })
    
    # Tabla interactiva
    df_seco_editado = st.data_editor(
        df_seco_default, 
        num_rows="fixed", 
        use_container_width=True,
        key="editor_seco"
    )
    
    # Calcular promedios de la tabla editable
    prom_seco_r = df_seco_editado["Lectura (dígitos)"].mean()
    prom_seco_t = df_seco_editado["Temperatura (°C)"].mean()
    
    st.success(f"**Promedio Fase en Seco:** Lectura ($R_0$) = **{prom_seco_r:.2f} dígitos** | Temperatura ($T_0$) = **{prom_seco_t:.2f} °C**")

with tab2:
    st.header("b) Verificación Saturado")
    st.write("Sensor saturado tras 1 hora sin filtro poroso, con el filtro colocado de nuevo.")
    st.write("Modifique la tabla con las 10 lecturas consecutivas en el contenedor de agua:")
    
    df_sat_default = pd.DataFrame({
        "Lectura (#)": [f"Lectura {i}" for i in range(1, 11)],
        "Lectura (dígitos)": [prom_seco_r + 2.0 + (i*0.1) for i in range(10)],
        "Temperatura (°C)": [20.5] * 10
    })
    
    df_sat_editado = st.data_editor(
        df_sat_default, 
        num_rows="fixed", 
        use_container_width=True,
        key="editor_sat"
    )
    
    prom_sat_r = df_sat_editado["Lectura (dígitos)"].mean()
    prom_sat_t = df_sat_editado["Temperatura (°C)"].mean()
    
    # Cálculos aplicando corrección térmica
    delta_r = prom_sat_r - prom_seco_r
    delta_t = prom_sat_t - prom_seco_t
    presion_cruda = delta_r * g_factor
    efecto_termico = delta_t * k_factor
    presion_final = presion_cruda + efecto_termico

    st.divider()
    st.subheader("Resultados de la Verificación Saturado")
    
    res_c1, res_c2, res_c3 = st.columns(3)
    res_c1.metric("Presión Calculada (kPa)", f"{presion_final:.2f}")
    res_c2.metric("Presión Calculada (bar)", f"{presion_final / 100:.3f}")
    res_c3.metric("Altura Piezométrica (mca)", f"{presion_final / 9.81:.2f}")

    with st.expander("Ver resumen técnico y validación"):
        st.write(f"- **Promedio Lecturas Seco (R0):** {prom_seco_r:.2f} dig")
        st.write(f"- **Promedio Lecturas Saturado (R1):** {prom_sat_r:.2f} dig")
        st.write(f"- **Delta de Dígitos ($\Delta R$):** {delta_r:.2f}")
        st.write(f"- **Delta de Temperatura ($\Delta T$):** {delta_t:.2f} °C")
        st.write(f"- **Presión corregida por temperatura:** {presion_final:.3f} kPa")

# Botón para exportar reporte resumido en CSV
st.divider()
if st.button("📥 Generar Resumen para Reporte"):
    data_resumen = {
        "Sensor": [sensor_id],
        "Prom_Seco_Digitos": [prom_seco_r],
        "Prom_Seco_Temp": [prom_seco_t],
        "Prom_Saturado_Digitos": [prom_sat_r],
        "Prom_Saturado_Temp": [prom_sat_t],
        "Presion_kPa": [presion_final],
        "Presion_mca": [presion_final / 9.81]
    }
    df_export = pd.DataFrame(data_resumen)
    st.download_button(
        label="Descargar CSV de Verificación",
        data=df_export.to_csv(index=False).encode('utf-8'),
        file_name=f"verificacion_{sensor_id}.csv",
        mime="text/csv",
    )
