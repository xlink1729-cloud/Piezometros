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
    st.write("Ingrese las 10 lecturas consecutivas al aire y temperatura ambiente (intervalos de 1 min).")
    
    # Crear entradas para 10 lecturas en seco
    cols_seco = st.columns(5)
    lecturas_seco_r = []
    lecturas_seco_t = []
    
    for i in range(10):
        col_idx = i % 5
        with cols_seco[col_idx]:
            r = st.number_input(f"Seco R{i+1} (dig)", value=7500.0 + i*0.5, key=f"seco_r_{i}")
            t = st.number_input(f"Seco T{i+1} (°C)", value=22.0, key=f"seco_t_{i}")
            lecturas_seco_r.append(r)
            lecturas_seco_t.append(t)
            
    prom_seco_r = np.mean(lecturas_seco_r)
    prom_seco_t = np.mean(lecturas_seco_t)
    
    st.info(f"**Promedio Fase en Seco:** Lectura ($R_0$) = **{prom_seco_r:.2f} dígitos** | Temperatura ($T_0$) = **{prom_seco_t:.2f} °C**")

with tab2:
    st.header("b) Verificación Saturado")
    st.write("Sensor saturado tras 1 hora sin filtro poroso, con el filtro colocado de nuevo.")
    st.write("Ingrese las 10 lecturas consecutivas (en el contenedor de agua a temperatura estable):")
    
    cols_sat = st.columns(5)
    lecturas_sat_r = []
    lecturas_sat_t = []
    
    for i in range(10):
        col_idx = i % 5
        with cols_sat[col_idx]:
            r = st.number_input(f"Sat R{i+1} (dig)", value=prom_seco_r + 2.0, key=f"sat_r_{i}")
            t = st.number_input(f"Sat T{i+1} (°C)", value=20.5, key=f"sat_t_{i}")
            lecturas_sat_r.append(r)
            lecturas_sat_t.append(t)
            
    prom_sat_r = np.mean(lecturas_sat_r)
    prom_sat_t = np.mean(lecturas_sat_t)
    
    # Cálculos aplicando corrección térmica respecto al seco (o base)
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
