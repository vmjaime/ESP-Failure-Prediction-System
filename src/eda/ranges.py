"""
Module for defining operational ranges using statistical methods.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

# Constants
COL_QTOT = "PRUEBA_POZO.OIL_24 + PRUEBA_POZO.WATER_24"
COL_QGAS = "PRUEBA DE PRODUCCIÓN GAS A 24 HORAS MCF/D"
COL_HZ = "FRECUENCIA BOMBA HZ"
COL_PINT = "PRESION DE INTAKE PSI"
COL_AMPS = "AMPERAJE BOMBA AMP"
COL_PTUB = "PRESION DE TUBING PSI"
COL_PCAS = "PRESION DE CASING PSI"
COL_TEMP = "TEMPERATURA DE LA BOMBA DEG. F"
COL_EVENTO = "evento_hibrido"

OPERATIONAL_VARS = [COL_HZ, COL_PINT, COL_AMPS, COL_PTUB, COL_PCAS, COL_TEMP]

def calculate_operational_ranges(df: pd.DataFrame, variables: list = None) -> Dict[str, Dict[str, float]]:
    """
    Calculate operational ranges using IQR method.

    Args:
        df: Input DataFrame
        variables: List of variables to calculate ranges for

    Returns:
        Dictionary with ranges for each variable
    """
    if variables is None:
        variables = OPERATIONAL_VARS

    ranges = {}

    for var in variables:
        if var not in df.columns:
            logger.warning(f"Variable {var} not found in data")
            continue

        # Ensure numeric and calculate quartiles
        series = pd.to_numeric(df[var], errors='coerce').dropna()
        if len(series) < 10:
            logger.warning(f"Insufficient data for {var}")
            continue

        Q1 = series.quantile(0.25)
        Q3 = series.quantile(0.75)
        IQR = Q3 - Q1

        # Normal range
        normal_low = Q1 - 1.5 * IQR
        normal_high = Q3 + 1.5 * IQR

        # Alert range (extended)
        alert_low = Q1 - 3.0 * IQR
        alert_high = Q3 + 3.0 * IQR

        ranges[var] = {
            'Q1': Q1,
            'Q3': Q3,
            'IQR': IQR,
            'normal_low': normal_low,
            'normal_high': normal_high,
            'alert_low': alert_low,
            'alert_high': alert_high
        }

        logger.info(".2f")

    return ranges

def calculate_strict_ranges(df: pd.DataFrame, normal_condition: str = None) -> Dict[str, Dict[str, float]]:
    """
    Calculate strict ranges using only normal operation data.

    Args:
        df: Input DataFrame
        normal_condition: Condition to filter normal operations

    Returns:
        Dictionary with strict ranges
    """
    if normal_condition is None:
        normal_condition = f"{COL_EVENTO} == 0"

    # Filter normal operations
    df_normal = df.query(normal_condition)

    logger.info(f"Using {len(df_normal)} normal operation records for strict ranges")

    ranges = {}

    # Critical variables for strict ranges
    critical_vars = [COL_QTOT, COL_QGAS, COL_HZ, COL_PINT]

    for var in critical_vars:
        if var not in df_normal.columns:
            logger.warning(f"Variable {var} not found in data")
            continue

        # Calculate quartiles on normal data
        Q1 = df_normal[var].quantile(0.25)
        Q3 = df_normal[var].quantile(0.75)
        IQR = Q3 - Q1

        # Strict normal range (tighter)
        strict_normal_low = Q1 - 0.5 * IQR
        strict_normal_high = Q3 + 0.5 * IQR

        # Strict alert range
        strict_alert_low = Q1 - 1.0 * IQR
        strict_alert_high = Q3 + 1.0 * IQR

        ranges[var] = {
            'strict_Q1': Q1,
            'strict_Q3': Q3,
            'strict_IQR': IQR,
            'strict_normal_low': strict_normal_low,
            'strict_normal_high': strict_normal_high,
            'strict_alert_low': strict_alert_low,
            'strict_alert_high': strict_alert_high
        }

        logger.info(".2f")

    return ranges

def apply_ranges_to_data(df: pd.DataFrame, ranges: Dict) -> pd.DataFrame:
    """
    Apply calculated ranges to create flag columns.

    Args:
        df: Input DataFrame
        ranges: Dictionary with ranges

    Returns:
        DataFrame with range flags
    """
    df = df.copy()

    for var, range_dict in ranges.items():
        if var not in df.columns:
            continue

        # Normal range flags
        df[f'{var}_normal'] = ((df[var] >= range_dict['normal_low']) &
                               (df[var] <= range_dict['normal_high']))

        # Alert range flags
        df[f'{var}_alert'] = ((df[var] >= range_dict['alert_low']) &
                              (df[var] <= range_dict['alert_high']))

    logger.info("Range flags applied to data")
    return df

def create_regimen_column(df: pd.DataFrame, col_pozo: str = "@NAME( )", col_bomba: str = "TIPO DE BOMBA") -> pd.DataFrame:
    """
    Create regimen_id column combining well and pump type.

    Args:
        df: Input DataFrame
        col_pozo: Well name column
        col_bomba: Pump type column

    Returns:
        DataFrame with regimen_id column
    """
    df = df.copy()

    # Normalize pump type
    bomba_norm = (df[col_bomba].astype(str)
                  .str.strip()
                  .replace({"": np.nan, "nan": np.nan}))

    df["regimen_id"] = df[col_pozo].astype(str) + "||" + bomba_norm.fillna("NA")

    logger.info(f"Created regimen_id column with {df['regimen_id'].nunique()} unique regimens")
    return df