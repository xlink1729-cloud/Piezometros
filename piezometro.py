import streamlit as st
import pandas as pd

st.set_page_config(page_title="Calculadora Piezómetros Cuerda Vibrante", page_icon="📊", layout="centered")

st.title("🚰 Calibración y Lectura de Piezómetros")
st.markdown("Herramienta para el procesamiento de datos de piezómetros de cuerda vibrante (presión y temperatura).")

# Barra lateral para configuración de parámetros del sensor
st.sidebar.header("Parámetros del Sensor")
sensor_id = st.sidebar.text_input("ID del Piezómetro", value="PZ-01")
g_factor = st.sidebar.number_input("Factor de Calibración (G) [kPa/dígito]", value=0.1500, format="%.4f")
k_factor = st.sidebar.number_input("Coeficiente Térmico (K) [kPa/°C]", value=0.0500, format="%.4f")

# Sección 1: Definición del Cero (R0 y T0)
st.header("1. Lectura de Referencia (Cero / R0)")
col1, col2 = st.columns(2)
with col1:
    r0 = st.number_input("Lectura Inicial (R0) [dígitos]", value=7500.0, format="%.1f")
with col2:
    t0 = st.number_input("Temperatura Inicial (T0) [°C]", value=20.0, format="%.1f")

st.divider()

# Sección 2: Lectura Actual en Campo / Tubería
st.header("2. Lectura Actual de Operación")
col3, col4 = st.columns(2)
with col3:
    r1 = st.number_input("Lectura Actual (R1) [dígitos]", value=8200.0, format="%.1f")
with col4:
    t1 = st.number_input("Temperatura Actual (T1) [°C]", value=22.5, format="%.1f")

# Cálculos
delta_r = r1 - r0
delta_t = t1 - t0

presion_cruda = delta_r * g_factor
correccion_termica = delta_t * k_factor
presion_final = presion_cruda + correccion_termica

# Opciones de conversión de unidades de presión
st.divider()
st.header("3. Resultados")

# Métricas principales
m_col1, m_col2, m_col3 = st.columns(3)
m_col1.metric("Presión (kPa)", f"{presion_final:.2f}")
m_col2.metric("Presión (bar)", f"{presion_final / 100:.3f}")
m_col3.metric("mca (Metros Columna Agua)", f"{presion_final / 9.81:.2f}")

with st.expander("Ver detalles del cálculo"):
    st.write(f"**Sensor:** {sensor_id}")
    st.write(f"Diferencia de dígitos ($\Delta R$): {delta_r}")
    st.write(f"Diferencia de temperatura ($\Delta T$): {delta_t} °C")
    st.write(f"Presión sin corrección térmica: {presion_cruda:.3f} kPa")
    st.write(f"Efecto térmico aplicado: {correccion_termica:.3f} kPa")