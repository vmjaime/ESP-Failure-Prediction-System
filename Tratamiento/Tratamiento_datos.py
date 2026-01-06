import pandas as pd
import os
import re

# === Ruta del archivo base
ruta = r"C:\Users\Vìctor\OneDrive\Desktop\ESP_Project\Datos\DATOS_ESP.xlsx"

# === Leer nombres de hojas
hojas = pd.ExcelFile(ruta).sheet_names

# === Inicializar lista para almacenar resultados por pozo
pozos = []

# === Fecha base para seriales Excel
fecha_base_excel = pd.to_datetime("1899-12-30")

# === Función de limpieza de columnas
def limpiar_columnas(df):
    df.columns = (
        df.columns
        .str.strip()
        .str.upper()
        .str.replace(" +", " ", regex=True)
    )
    return df

# === Función de detección y conversión robusta de fechas
def convertir_fecha(x):
    try:
        if isinstance(x, (int, float)):
            return fecha_base_excel + pd.to_timedelta(x, unit="D")
        return pd.to_datetime(x, dayfirst=True, errors="coerce")
    except:
        return pd.NaT

# === Recorrer hojas desde la posición 4 (índice)
for hoja in hojas[4:]:
    try:
        df = pd.read_excel(ruta, sheet_name=hoja)
        df = limpiar_columnas(df)

        # Detectar columna de fecha (usamos heurística)
        col_fecha = next((col for col in df.columns if "DATE" in col or "FECHA" in col), None)
        if col_fecha is None:
            print(f"❌ No se encontró columna de fecha en hoja: {hoja}")
            continue

        # Aplicar conversión de fecha
        df["DATE"] = df[col_fecha].apply(convertir_fecha)

        # Ordenar y eliminar valores vacíos
        df = df[df["DATE"].notna()]
        df = df.sort_values("DATE").reset_index(drop=True)

        # Agregar columna con nombre del pozo
        df["POZO"] = hoja

        pozos.append(df)

    except Exception as e:
        print(f"⚠️ Error en hoja {hoja}: {e}")

# === Unir todos los pozos
df_total = pd.concat(pozos, ignore_index=True)

# === Mostrar resumen
print("✅ Dataset combinado:")
print(df_total[["POZO", "DATE"]].head())

# === Guardar archivo final
df_total.to_excel("df_total_pozos_limpio.xlsx", index=False)
