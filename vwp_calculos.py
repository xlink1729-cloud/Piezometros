"""Cálculos para piezómetros de cuerda vibrante (VWP).

Funciones puras (sin Streamlit): se pueden probar con pytest y reutilizar
más adelante desde otras apps o desde un agente.

Convención de las fórmulas (la misma que usaba la versión anterior de la app):
    Polinomial: P = A*L^2 + B*L + C - Tk*(T0 - T) + (S0 - S)
                con C = -(A*L0^2 + B*L0)   (P = 0 en la lectura cero)
    Lineal:     P = CF*(L0 - L) - Tk*(T0 - T) + (S0 - S)
    Columna de agua (m) = P (kPa) * 0.101974
Verifica que esta convención (signos de CF y Tk) coincida con el certificado
de calibración de tu fabricante.
"""

from __future__ import annotations

import io
import math
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Optional

import pandas as pd

FACTOR_KPA_MCA = 0.101974  # 1 kPa = 0.101974 m de columna de agua

COL_NUM = "Lectura (#)"
COL_FECHA = "Fecha"
COL_HORA = "Hora"
COL_L = "Lectura (B units)"
COL_T = "Temperatura (°C)"
COL_BARO = "Baro (kPa)"
COL_ALT = "Altura medida (cm)"
COL_P = "Presión (kPa)"
COL_MCA = "Columna (mca)"
COL_NIVEL = "Nivel agua (m.s.n.m.)"
COL_PROF = "Prof. al agua (m)"
COL_DELTA = "Δ nivel vs anterior (m)"
COL_ALERTA = "Alerta"

COLS_BASE = [COL_NUM, COL_FECHA, COL_HORA, COL_L, COL_T]
COLS_SEGUIMIENTO = [COL_FECHA, COL_HORA, COL_L, COL_T, COL_BARO]
COLS_ALTURAS = [COL_ALT, COL_L, COL_T]

# Estados de cada verificación
OK, ERROR, AVISO, PENDIENTE, OMITIDO = "ok", "error", "aviso", "pendiente", "omitido"


def _num(x) -> float:
    """Convierte a float; None, texto vacío o inválido -> NaN."""
    try:
        if x is None:
            return math.nan
        if isinstance(x, str) and not x.strip():
            return math.nan
        return float(x)
    except (TypeError, ValueError):
        return math.nan


def _nan(x) -> bool:
    return isinstance(x, float) and math.isnan(x)


# --------------------------------------------------------------------------
# Calibración y presión
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Calibracion:
    modelo: str = "Polinomial"  # "Polinomial" | "Lineal"
    a: float = 0.0
    b: float = 0.0
    cf: float = 0.0
    tk: float = 0.0
    s0_baro: float = 101.325  # kPa, presión barométrica al tomar L0

    def con_modelo(self, modelo: str) -> "Calibracion":
        return replace(self, modelo=modelo)

    def alterno(self) -> Optional["Calibracion"]:
        """Cálculo con el otro modelo, si sus constantes están capturadas."""
        if self.modelo == "Polinomial":
            return self.con_modelo("Lineal") if self.cf != 0 else None
        return self.con_modelo("Polinomial") if (self.a != 0 or self.b != 0) else None

    def tiene_constantes(self) -> bool:
        if self.modelo == "Polinomial":
            return self.a != 0 or self.b != 0
        return self.cf != 0


def constante_c(a: float, b: float, l0: float) -> float:
    """Constante C del modelo polinomial: hace P = 0 en la lectura cero."""
    return -(a * l0**2 + b * l0)


def presion_kpa(cal: Calibracion, l, t, l0, t0, s_actual) -> float:
    """Presión (kPa) para una lectura l (B) a temperatura t (°C)."""
    l, t, l0, t0, s = (_num(v) for v in (l, t, l0, t0, s_actual))
    if any(_nan(v) for v in (l, t, l0, t0, s)):
        return math.nan
    efecto_termico = cal.tk * (t0 - t)
    delta_baro = cal.s0_baro - s
    if cal.modelo == "Polinomial":
        c = constante_c(cal.a, cal.b, l0)
        return cal.a * l**2 + cal.b * l + c - efecto_termico + delta_baro
    return cal.cf * (l0 - l) - efecto_termico + delta_baro


def kpa_a_mca(p) -> float:
    p = _num(p)
    return math.nan if _nan(p) else p * FACTOR_KPA_MCA


# --------------------------------------------------------------------------
# Tablas de lecturas
# --------------------------------------------------------------------------
def tabla_vacia(n: int = 10) -> pd.DataFrame:
    """Tabla de n lecturas SIN valores de ejemplo (nada inventado)."""
    return pd.DataFrame({
        COL_NUM: [f"Lectura {i}" for i in range(1, n + 1)],
        COL_FECHA: [""] * n,
        COL_HORA: [""] * n,
        COL_L: [math.nan] * n,
        COL_T: [math.nan] * n,
    })


def tabla_seguimiento_vacia(n: int = 3) -> pd.DataFrame:
    return pd.DataFrame({
        COL_FECHA: [""] * n,
        COL_HORA: [""] * n,
        COL_L: [math.nan] * n,
        COL_T: [math.nan] * n,
        COL_BARO: [math.nan] * n,
    })


def tabla_alturas_vacia(n: int = 9) -> pd.DataFrame:
    """Calibración con varias alturas: una fila por lectura (repite la altura)."""
    return pd.DataFrame({
        COL_ALT: [math.nan] * n,
        COL_L: [math.nan] * n,
        COL_T: [math.nan] * n,
    })


def df_desde_registros(registros, columnas, n_default: int = 10) -> pd.DataFrame:
    """Reconstruye una tabla desde una lista de dicts (ficha .txt).

    Acepta fichas antiguas (con columnas calculadas de más) y valores nulos.
    """
    if not registros:
        if columnas == COLS_BASE:
            return tabla_vacia(n_default)
        if columnas == COLS_ALTURAS:
            return tabla_alturas_vacia()
        return tabla_seguimiento_vacia()
    df = pd.DataFrame(registros)
    for col in columnas:
        if col not in df.columns:
            df[col] = "" if col in (COL_FECHA, COL_HORA, COL_NUM) else math.nan
    df = df[columnas].copy()
    for col in (COL_L, COL_T, COL_BARO, COL_ALT):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in (COL_FECHA, COL_HORA):
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str)
    if COL_NUM in df.columns:
        df[COL_NUM] = df[COL_NUM].fillna("").astype(str)
    return df.reset_index(drop=True)


def serie_numerica(df, col) -> pd.Series:
    if df is None or col not in getattr(df, "columns", []):
        return pd.Series(dtype=float)
    return pd.to_numeric(df[col], errors="coerce")


def resumir_tabla(df, k_atipico: float = 3.5, min_atipico: float = 0.5) -> dict:
    """Estadísticos de una tabla de lecturas (solo filas con lectura válida)."""
    vacio = {"n": 0, "n_sin_temp": 0, "prom_l": math.nan, "prom_t": math.nan,
             "rango": math.nan, "desv": math.nan, "deriva": math.nan, "atipicos": []}
    l = serie_numerica(df, COL_L)
    t = serie_numerica(df, COL_T)
    validas = l.dropna()
    if validas.empty:
        return vacio
    t_val = t[l.notna()]
    n = len(validas)
    return {
        "n": n,
        "n_sin_temp": int(t_val.isna().sum()),
        "prom_l": float(validas.mean()),
        "prom_t": float(t_val.mean()) if t_val.notna().any() else math.nan,
        "rango": float(validas.max() - validas.min()),
        "desv": float(validas.std(ddof=1)) if n >= 2 else 0.0,
        "deriva": float(validas.iloc[-1] - validas.iloc[0]),
        "atipicos": detectar_atipicos(validas, k_atipico, min_atipico),
    }


def detectar_atipicos(serie: pd.Series, k: float = 3.5, minimo: float = 0.5) -> list:
    """Índices de lecturas lejanas a la mediana (MAD robusto).

    Una lectura es atípica si se aleja de la mediana más de
    max(k * 1.4826 * MAD, minimo) unidades B.
    """
    s = serie.dropna()
    if len(s) < 4:
        return []
    med = float(s.median())
    mad = float((s - med).abs().median())
    umbral = max(k * 1.4826 * mad, minimo)
    return [int(i) for i, v in s.items() if abs(v - med) > umbral]


def evaluar_estabilidad(res: dict, n_min: int, tol_rango: float) -> tuple[str, str]:
    n = res["n"]
    if n < n_min:
        return PENDIENTE, f"{n} de {n_min} lecturas capturadas."
    if res["n_sin_temp"] > 0:
        return PENDIENTE, f"Faltan {res['n_sin_temp']} temperatura(s) en lecturas capturadas."
    if tol_rango > 0 and res["rango"] > tol_rango:
        return ERROR, (f"Rango entre lecturas {res['rango']:.2f} B "
                       f"(máx. permitido {tol_rango:.2f} B). Espera a que se estabilice.")
    msg = f"{n} lecturas, rango {res['rango']:.2f} B, desv. est. {res['desv']:.3f} B."
    if res["atipicos"]:
        return AVISO, msg + f" Posible(s) lectura(s) atípica(s): fila(s) {[i + 1 for i in res['atipicos']]}."
    return OK, msg


def comparar_con_fabrica(prom, fabrica, tol) -> tuple[str, str]:
    """Compara un promedio contra la lectura del certificado. fabrica=0 -> omitido."""
    prom, fabrica, tol = _num(prom), _num(fabrica), _num(tol)
    if _nan(fabrica) or fabrica == 0 or _nan(tol) or tol <= 0:
        return OMITIDO, "Sin lectura de fábrica o sin tolerancia: no se evalúa."
    if _nan(prom):
        return PENDIENTE, "Faltan lecturas para comparar."
    dif = prom - fabrica
    if abs(dif) <= tol:
        return OK, f"Diferencia con fábrica {dif:+.2f} B (tolerancia ±{tol:.2f} B)."
    return ERROR, f"Diferencia con fábrica {dif:+.2f} B supera ±{tol:.2f} B."


# --------------------------------------------------------------------------
# Fechas y tiempos
# --------------------------------------------------------------------------
_FORMATOS_DT = ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S")


def construir_dt(fecha, hora) -> Optional[datetime]:
    def limpio(x):
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return ""
        return str(x).strip()

    f, h = limpio(fecha), limpio(hora)
    if not f or not h or f.lower() in ("nan", "none", "nat"):
        return None
    for fmt in _FORMATOS_DT:
        try:
            return datetime.strptime(f"{f} {h}", fmt)
        except ValueError:
            continue
    return None


def fechas_de_lecturas(df) -> list:
    """Fecha-hora de cada fila con lectura válida y fecha/hora legible."""
    if df is None or len(df) == 0:
        return []
    l = serie_numerica(df, COL_L)
    out = []
    for i in df.index:
        if _nan(float(l.loc[i])):
            continue
        dt = construir_dt(df.at[i, COL_FECHA] if COL_FECHA in df else "",
                          df.at[i, COL_HORA] if COL_HORA in df else "")
        if dt is not None:
            out.append(dt)
    return out


def horas_saturacion(inicio: Optional[datetime], df_sat) -> Optional[float]:
    dts = fechas_de_lecturas(df_sat)
    if inicio is None or not dts:
        return None
    return (min(dts) - inicio).total_seconds() / 3600.0


def evaluar_saturacion(horas: Optional[float], minimo: float) -> tuple[str, str]:
    if horas is None:
        return PENDIENTE, ("Captura fecha/hora de inicio de inmersión y fecha/hora de la "
                           "primera lectura saturada (AAAA-MM-DD y HH:MM).")
    if horas < 0:
        return ERROR, "La primera lectura es anterior al inicio de la inmersión: revisa fechas."
    if horas < minimo:
        return ERROR, f"Solo {horas:.1f} h de saturación (mínimo {minimo:.0f} h). L0 aún no es confiable."
    return OK, f"{horas:.1f} h de saturación antes de la primera lectura (mínimo {minimo:.0f} h)."


# --------------------------------------------------------------------------
# Pruebas
# --------------------------------------------------------------------------
def calcular_tabla_presion(df, cal: Calibracion, l0, t0, s_actual) -> pd.DataFrame:
    """Agrega Presión (kPa) y Columna (mca) a una tabla de lecturas."""
    out = df.copy().reset_index(drop=True)
    pres = [presion_kpa(cal, r.get(COL_L), r.get(COL_T), l0, t0, s_actual)
            for _, r in out.iterrows()]
    out[COL_P] = [round(p, 3) if not _nan(p) else math.nan for p in pres]
    out[COL_MCA] = [round(kpa_a_mca(p), 3) if not _nan(p) else math.nan for p in pres]
    return out


def validar_inmersion(mca_medida, mca_referencia, tol) -> tuple[str, str]:
    mca_medida = _num(mca_medida)
    if _nan(mca_medida):
        return PENDIENTE, "Captura las lecturas de la prueba de inmersión."
    dif = mca_medida - mca_referencia
    if abs(dif) <= tol:
        return OK, (f"Columna medida {mca_medida:.3f} m vs referencia {mca_referencia:.2f} m "
                    f"(dif. {dif:+.3f} m, tolerancia ±{tol:.2f} m).")
    return ERROR, (f"Columna medida {mca_medida:.3f} m vs referencia {mca_referencia:.2f} m: "
                   f"dif. {dif:+.3f} m supera ±{tol:.2f} m. Revisa constantes, L0, burbujas o la altura real.")


def analizar_columnas(columnas, mca_ref, tol, etiquetas=None) -> dict:
    """Detalle de una prueba de inmersión: cada lectura, rango y tendencia.

    columnas: columna de agua (m) calculada por lectura, en orden de captura.
    Tendencia: se avisa si >= 80 % de los pasos van en el mismo sentido y la
    deriva total (última - primera) supera max(tol/2, 1 cm).
    """
    vals = [(i, _num(c)) for i, c in enumerate(columnas)]
    vals = [(i, c) for i, c in vals if not _nan(c)]
    etiquetas = etiquetas or [f"Lectura {i + 1}" for i in range(len(columnas))]
    res = {"n": len(vals), "prom": math.nan, "minimo": math.nan, "maximo": math.nan,
           "fuera": [], "tendencia": None, "deriva": math.nan}
    if not vals:
        return res
    serie = [c for _, c in vals]
    res["prom"] = sum(serie) / len(serie)
    res["minimo"], res["maximo"] = min(serie), max(serie)
    res["fuera"] = [etiquetas[i] for i, c in vals if abs(c - mca_ref) > tol]
    if len(serie) >= 4:
        pasos = [b - a for a, b in zip(serie, serie[1:])]
        res["deriva"] = serie[-1] - serie[0]
        subiendo = sum(1 for p in pasos if p > 0)
        bajando = sum(1 for p in pasos if p < 0)
        umbral = max(tol / 2, 0.01)
        if abs(res["deriva"]) >= umbral:
            if subiendo >= 0.8 * len(pasos):
                res["tendencia"] = "subiendo"
            elif bajando >= 0.8 * len(pasos):
                res["tendencia"] = "bajando"
    return res


def validar_inmersion_detallada(columnas, mca_ref, tol, etiquetas=None) -> tuple[str, str]:
    """Aprueba solo si el promedio Y cada lectura están dentro de la tolerancia.

    Además avisa si las lecturas van en una sola dirección (sensor sin estabilizar).
    """
    det = analizar_columnas(columnas, mca_ref, tol, etiquetas)
    if det["n"] == 0:
        return PENDIENTE, "Captura las lecturas de la prueba de inmersión."
    estado, msg = validar_inmersion(det["prom"], mca_ref, tol)
    rango = f" Rango de lecturas: {det['minimo']:.3f} a {det['maximo']:.3f} m."
    if estado == ERROR:
        return ERROR, msg + rango
    if det["fuera"]:
        return ERROR, (f"El promedio cumple, pero {len(det['fuera'])} lectura(s) quedan fuera de "
                       f"±{tol:.2f} m: {', '.join(det['fuera'])}." + rango)
    if det["tendencia"]:
        return AVISO, (msg + rango + f" Las lecturas van {det['tendencia']} ({det['deriva']:+.3f} m): "
                       "puede haber burbujas o el sensor no se ha estabilizado.")
    return OK, msg + rango


def analizar_calibracion_alturas(alturas_m, columnas_m, tol_consistencia: float = 0.01,
                                 tol_pendiente: float = 0.03) -> dict:
    """Estima la distancia fija entre el punto de medición y el diafragma.

    alturas_m: altura medida (m) de cada lectura, desde el punto de referencia
    que uses (p. ej. la piedra porosa). columnas_m: columna calculada (m) para
    cada lectura. Si el sensor mide a una distancia fija d del punto medido:
        columna = altura + d      (d > 0 si el diafragma queda más profundo)
    Con varias alturas: d debe salir casi igual en todas (consistencia) y la
    pendiente columna-vs-altura debe ser ~1. Si no, el problema no es una
    distancia fija: revisa constantes, L0, burbujas o la altura medida.
    """
    pares = []
    for h, c in zip(alturas_m, columnas_m):
        h, c = _num(h), _num(c)
        if not _nan(h) and not _nan(c) and h > 0:
            pares.append((h, c))
    res = {"n": len(pares), "n_alturas": 0, "offset_m": math.nan, "por_altura": {},
           "dispersion": math.nan, "pendiente": math.nan, "estado": PENDIENTE, "mensaje": ""}
    if not pares:
        res["mensaje"] = "Captura la altura medida y las lecturas de cada altura."
        return res
    grupos: dict = {}
    for h, c in pares:
        grupos.setdefault(round(h, 4), []).append(c - h)
    por_altura = {h: sum(v) / len(v) for h, v in grupos.items()}
    res["por_altura"] = por_altura
    res["n_alturas"] = len(por_altura)
    res["offset_m"] = sum(por_altura.values()) / len(por_altura)
    if len(por_altura) < 2:
        res["mensaje"] = ("Con una sola altura no se puede separar una distancia fija de un error de "
                          "constantes o de L0. Prueba al menos 2 alturas distintas.")
        return res
    res["dispersion"] = max(por_altura.values()) - min(por_altura.values())
    hm = sum(h for h, _ in pares) / len(pares)
    cm = sum(c for _, c in pares) / len(pares)
    sxx = sum((h - hm) ** 2 for h, _ in pares)
    res["pendiente"] = sum((h - hm) * (c - cm) for h, c in pares) / sxx if sxx > 0 else math.nan
    avisos = []
    if res["dispersion"] > tol_consistencia:
        avisos.append(f"la diferencia cambia {res['dispersion'] * 100:.1f} cm entre alturas "
                      f"(máx. {tol_consistencia * 100:.1f} cm)")
    if not _nan(res["pendiente"]) and abs(res["pendiente"] - 1) > tol_pendiente:
        avisos.append(f"la pendiente columna/altura es {res['pendiente']:.3f} (debería ser ≈1)")
    if avisos:
        res["estado"] = AVISO
        res["mensaje"] = ("No parece una distancia fija: " + "; ".join(avisos) +
                          ". Revisa constantes, L0, burbujas o la altura medida.")
    else:
        res["estado"] = OK
        res["mensaje"] = (f"Distancia estimada: {res['offset_m'] * 100:+.1f} cm, consistente en "
                          f"{len(por_altura)} alturas.")
    return res


def columna_teorica(prof_inst, naf) -> float:
    """Columna de agua esperada sobre el sensor según sonda manual (m)."""
    return max(0.0, float(prof_inst) - float(naf))


def validar_campo(mca_calc, mca_teorica, tol) -> tuple[str, str]:
    mca_calc = _num(mca_calc)
    if _nan(mca_calc):
        return PENDIENTE, "Captura la lectura y temperatura de campo."
    dif = mca_calc - mca_teorica
    if abs(dif) <= tol:
        return OK, f"Diferencia {dif:+.3f} m respecto al nivel con sonda (tolerancia ±{tol:.2f} m)."
    return ERROR, (f"Diferencia {dif:+.3f} m respecto al nivel con sonda supera ±{tol:.2f} m. "
                   "Verifica recarga reciente, la cota Z, el NAF medido o las constantes.")


# --------------------------------------------------------------------------
# Seguimiento posterior a la instalación
# --------------------------------------------------------------------------
def calcular_seguimiento(df, cal: Calibracion, l0, t0, cota, prof_inst, s_ficha,
                         umbral_salto: float = 0.0) -> pd.DataFrame:
    """Nivel de agua por lectura, con salto respecto a la lectura previa."""
    nuevas = [COL_P, COL_MCA, COL_NIVEL, COL_PROF, COL_DELTA, COL_ALERTA, "_dt"]
    if df is None or len(df) == 0:
        return pd.DataFrame(columns=list(COLS_SEGUIMIENTO) + nuevas)
    out = df.copy().reset_index(drop=True)
    n = len(out)
    pres, mca, nivel, prof, dts = [], [], [], [], []
    for _, r in out.iterrows():
        baro = _num(r.get(COL_BARO))
        if _nan(baro):
            baro = s_ficha
        p = presion_kpa(cal, r.get(COL_L), r.get(COL_T), l0, t0, baro)
        m = kpa_a_mca(p)
        pres.append(p)
        mca.append(m)
        nivel.append(cota + m if not _nan(m) else math.nan)
        prof.append(prof_inst - m if not _nan(m) else math.nan)
        dts.append(construir_dt(r.get(COL_FECHA), r.get(COL_HORA)))

    validos = [i for i in range(n) if not _nan(nivel[i])]
    if validos and all(dts[i] is not None for i in validos):
        validos.sort(key=lambda i: dts[i])
    delta = [math.nan] * n
    alerta = [""] * n
    for ant, act in zip(validos, validos[1:]):
        d = nivel[act] - nivel[ant]
        delta[act] = d
        if umbral_salto > 0 and abs(d) > umbral_salto:
            alerta[act] = f"⚠️ salto {d:+.2f} m"

    def r3(v):
        return round(v, 3) if not _nan(v) else math.nan

    out[COL_P] = [r3(v) for v in pres]
    out[COL_MCA] = [r3(v) for v in mca]
    out[COL_NIVEL] = [r3(v) for v in nivel]
    out[COL_PROF] = [r3(v) for v in prof]
    out[COL_DELTA] = [r3(v) for v in delta]
    out[COL_ALERTA] = alerta
    out["_dt"] = pd.to_datetime(pd.Series(dts, dtype="object"), errors="coerce")
    return out


# --------------------------------------------------------------------------
# Exportación
# --------------------------------------------------------------------------
def limpiar_para_json(obj):
    """NaN -> None y tipos numpy -> tipos nativos, para guardar JSON válido."""
    if isinstance(obj, dict):
        return {str(k): limpiar_para_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [limpiar_para_json(v) for v in obj]
    if hasattr(obj, "item") and not isinstance(obj, (str, bytes)):
        try:
            obj = obj.item()
        except (ValueError, AttributeError):
            pass
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if isinstance(obj, (datetime, pd.Timestamp)):
        return obj.isoformat()
    return obj


def construir_excel(hojas: dict) -> bytes:
    """Excel con una hoja por DataFrame. Requiere openpyxl."""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for nombre, df in hojas.items():
            df.to_excel(writer, sheet_name=nombre[:31], index=False)
            ws = writer.sheets[nombre[:31]]
            for col in ws.columns:
                ancho = max(len(str(c.value)) if c.value is not None else 0 for c in col)
                ws.column_dimensions[col[0].column_letter].width = min(max(ancho + 2, 10), 60)
    return buffer.getvalue()
