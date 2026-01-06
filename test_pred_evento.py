# === LIBRERÍAS ===
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

pd.set_option("display.float_format", lambda x: f"{x:,.2f}")
sns.set_style("whitegrid")


# === CARGA DE DATOS ===
# Cargar el dataset desde el archivo parquet
data_path = Path("freeze/df2_snapshot_latest.parquet")
if data_path.exists():
    df = pd.read_parquet(data_path)
    print(f"✅ Dataset cargado exitosamente: {len(df):,} filas, {len(df.columns)} columnas")
else:
    print(f"❌ Archivo no encontrado: {data_path}")
    print("Archivos disponibles en freeze/:")
    freeze_path = Path("freeze")
    if freeze_path.exists():
        for file in freeze_path.glob("*"):
            print(f"  - {file.name}")
    exit(1)

# Verificar columnas clave para análisis de tendencias
COL_FECHA = 'date'
COL_POZO = 'name_'  
COL_QTOT = 'prueba_pozooil_24__prueba_pozowater_24'
COL_QGAS = 'prueba_de_producción_gas_a_24_horas_mcfd'

# Verificar si las columnas necesarias existen
required_cols = [COL_FECHA, COL_POZO, COL_QTOT, COL_QGAS, 'pred_evento']
missing_cols = [c for c in required_cols if c not in df.columns]

if missing_cols:
    print(f"⚠️ Columnas faltantes: {missing_cols}")
    print("Columnas disponibles en df:")
    print([c for c in df.columns if 'prueba' in c.lower() or 'name' in c.lower() or 'date' in c.lower() or 'pred' in c.lower()])
    can_continue = False
else:
    print("✅ Todas las columnas necesarias están disponibles")
    can_continue = True