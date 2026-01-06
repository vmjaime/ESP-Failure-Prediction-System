"""
Module for calculating production signals and event detection.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from typing import Tuple, Dict

logger = logging.getLogger(__name__)

def calculate_slope_signals(df: pd.DataFrame, production_col: str = "prueba_pozooil_24__prueba_pozowater_24",
                           group_col: str = "name_", time_col: str = "date") -> pd.DataFrame:
    """
    Calculate slope signals using rolling windows.

    Args:
        df: Input DataFrame
        production_col: Production column name
        group_col: Column to group by (well name)
        time_col: Time column for sorting

    Returns:
        DataFrame with slope_7 and slope_14 columns
    """
    df = df.copy()

    def slope_window(y):
        x = np.arange(len(y))
        if len(y) < 2:
            return 0
        m, b = np.polyfit(x, y, 1)
        return m

    # Ensure sorted by well and time
    df = df.sort_values([group_col, time_col])

    # Calculate slopes
    df["slope_7"] = (
        df.groupby(group_col)[production_col]
        .rolling(window=7, min_periods=3)
        .apply(slope_window)
        .reset_index(level=0, drop=True)
    )

    df["slope_14"] = (
        df.groupby(group_col)[production_col]
        .rolling(window=14, min_periods=5)
        .apply(slope_window)
        .reset_index(level=0, drop=True)
    )

    logger.info(f"Calculated slope signals for {df[group_col].nunique()} wells")
    return df

def calculate_delta_signals(df: pd.DataFrame, production_col: str = "prueba_pozooil_24__prueba_pozowater_24",
                           group_col: str = "name_") -> pd.DataFrame:
    """
    Calculate delta (difference) signals.

    Args:
        df: Input DataFrame
        production_col: Production column name
        group_col: Column to group by

    Returns:
        DataFrame with delta_1 and delta_3 columns
    """
    df = df.copy()

    df["delta_1"] = df.groupby(group_col)[production_col].diff()
    df["delta_3"] = df.groupby(group_col)[production_col].diff(3)

    logger.info("Calculated delta signals")
    return df

def calculate_ratio_signals(df: pd.DataFrame, production_col: str = "prueba_pozooil_24__prueba_pozowater_24",
                           group_col: str = "name_") -> pd.DataFrame:
    """
    Calculate ratio signals (relative change over 14 days).

    Args:
        df: Input DataFrame
        production_col: Production column name
        group_col: Column to group by

    Returns:
        DataFrame with ratio14 column
    """
    df = df.copy()

    # Shift by 14 periods to get previous value
    df["Qt_prev14"] = df.groupby(group_col)[production_col].shift(14)

    # Calculate ratio, avoiding division by zero
    df["ratio14"] = np.where(
        df["Qt_prev14"].abs() > 1e-3,
        (df[production_col] - df["Qt_prev14"]) / df["Qt_prev14"].abs(),
        np.nan
    )

    logger.info("Calculated ratio signals")
    return df

def create_hybrid_events(df: pd.DataFrame, production_col: str = "prueba_pozooil_24__prueba_pozowater_24",
                        group_col: str = "name_") -> pd.DataFrame:
    """
    Create hybrid events based on slope and delta thresholds.

    Args:
        df: Input DataFrame with slope_7, delta_1
        production_col: Production column name
        group_col: Column to group by

    Returns:
        DataFrame with evento_hibrido column
    """
    df = df.copy()

    # Calculate per-well thresholds
    stats_slope = df.groupby(group_col)["slope_7"].agg(["mean", "std"])
    stats_slope["umbral_neg"] = stats_slope["mean"] - 2 * stats_slope["std"]
    stats_slope["umbral_pos"] = stats_slope["mean"] + 2 * stats_slope["std"]

    stats_delta = df.groupby(group_col)["delta_1"].quantile([0.10, 0.90]).unstack()
    stats_delta.columns = ["p10", "p90"]

    def classify_event(row):
        well = row[group_col]

        slope_u_neg = stats_slope.loc[well, "umbral_neg"]
        slope_u_pos = stats_slope.loc[well, "umbral_pos"]
        delta_p10 = stats_delta.loc[well, "p10"]
        delta_p90 = stats_delta.loc[well, "p90"]

        # Hybrid rule
        if (row["slope_7"] < slope_u_neg) or (row["delta_1"] < delta_p10):
            return 1  # Severe drop
        if (row["slope_7"] > slope_u_pos) or (row["delta_1"] > delta_p90):
            return 2  # Increase/reconditioning

        return 0  # Normal

    df["evento_hibrido"] = df.apply(classify_event, axis=1)

    logger.info(f"Created hybrid events: {df['evento_hibrido'].value_counts().to_dict()}")
    return df

def calculate_operational_ranges(df: pd.DataFrame, group_cols: list = ["name_", "regimen_id"],
                                production_col: str = "prueba_pozooil_24__prueba_pozowater_24") -> pd.DataFrame:
    """
    Calculate operational ranges using percentiles.

    Args:
        df: Input DataFrame
        group_cols: Columns to group by
        production_col: Production column name

    Returns:
        DataFrame with operational range limits
    """
    def pct_with_min_obs(s, p, min_obs=8):
        s = pd.to_numeric(s, errors="coerce").dropna()
        if len(s) < min_obs:
            return np.nan
        return np.nanpercentile(s, p)

    # Group and calculate percentiles
    ranges = df.groupby(group_cols).agg(
        qtot_lo=(production_col, lambda s: pct_with_min_obs(s, 30)),
        qtot_hi=(production_col, lambda s: pct_with_min_obs(s, 70)),
        gas_hi=("prueba_de_producción_gas_a_24_horas_mcfd", lambda s: pct_with_min_obs(s, 80)),
        hz_hi=("frecuencia_bomba_hz", lambda s: pct_with_min_obs(s, 90)),
        pint_lo=("presion_de_intake_psi", lambda s: pct_with_min_obs(s, 10))
    ).reset_index()

    logger.info(f"Calculated operational ranges for {len(ranges)} groups")
    return ranges

def create_envelope_signals(df: pd.DataFrame, ranges_dict: Dict) -> pd.DataFrame:
    """
    Create envelope signals based on operational ranges.

    Args:
        df: Input DataFrame
        ranges_dict: Dictionary with operational ranges

    Returns:
        DataFrame with envelope signals
    """
    df = df.copy()

    # Create envelope signals using global ranges (simplified version)
    # In production, this should use per-group ranges
    if 'prueba_pozooil_24__prueba_pozowater_24' in df.columns:
        qtot_series = df['prueba_pozooil_24__prueba_pozowater_24']
        qtot_q25 = qtot_series.quantile(0.25)
        qtot_q75 = qtot_series.quantile(0.75)
        df["env_q"] = ((qtot_series >= qtot_q25) & (qtot_series <= qtot_q75)).astype(int)
    else:
        df["env_q"] = 0

    # Gas gate (simplified)
    if 'prueba_de_producción_gas_a_24_horas_mcfd' in df.columns:
        gas_series = df['prueba_de_producción_gas_a_24_horas_mcfd']
        gas_q80 = gas_series.quantile(0.80)
        df["env_gate"] = (gas_series > gas_q80).astype(int)
    else:
        df["env_gate"] = 0

    logger.info("Created envelope signals")
    return df

def calculate_confirmation_stats(df: pd.DataFrame, group_col: str = "name_") -> pd.DataFrame:
    """
    Calculate confirmation statistics per well.

    Args:
        df: Input DataFrame
        group_col: Grouping column

    Returns:
        DataFrame with confirmation stats
    """
    stats = df.groupby(group_col).agg(
        slope7_mean=("slope_7", "mean"),
        slope7_std=("slope_7", "std"),
        d1_p80=("delta_1", lambda x: np.nanpercentile(x.abs(), 80))
    ).reset_index()

    logger.info(f"Calculated confirmation stats for {len(stats)} wells")
    return stats

def create_confirmation_signals(df: pd.DataFrame, stats_df: pd.DataFrame,
                               group_col: str = "name_") -> pd.DataFrame:
    """
    Create confirmation signals based on statistical thresholds.

    Args:
        df: Input DataFrame
        stats_df: DataFrame with stats
        group_col: Grouping column

    Returns:
        DataFrame with confirmation signals
    """
    df = df.copy()
    df = df.merge(stats_df, on=group_col, how="left")

    # Confirmation logic
    df["confirm_drop"] = ((df["slope_7"] - df["slope7_mean"]) < -1 * df["slope7_std"]) | \
                        (df["delta_1"] < -df["d1_p80"])

    df["confirm_rise"] = ((df["slope_7"] - df["slope7_mean"]) > 1 * df["slope7_std"]) | \
                        (df["delta_1"] > df["d1_p80"]) | \
                        (df["ratio14"] > 0.20)

    logger.info("Created confirmation signals")
    return df

def create_alarms(df: pd.DataFrame, group_col: str = "@NAME( )") -> pd.DataFrame:
    """
    Create alarm signals with persistence and refractory periods.

    Args:
        df: Input DataFrame with env_q, env_gate, confirm_drop, confirm_rise

    Returns:
        DataFrame with alarm signals
    """
    df = df.copy()

    # Instantaneous alarm
    df["fuera_inst"] = ((df["env_q"] == 0) | (df["env_gate"] == 1)).astype(int)
    df["alarma_instantanea"] = df["fuera_inst"] & ((df["confirm_drop"] | df["confirm_rise"]))

    # Count valid signals
    df["enough"] = (df[["slope_7", "delta_1", "ratio14"]].notna().sum(axis=1) >= 2).astype(int)
    df["alarma_instantanea"] = df["alarma_instantanea"] & df["enough"]

    # Persistence (minimum 2 consecutive alarms)
    df["persist"] = df.groupby(group_col)["alarma_instantanea"].rolling(2, min_periods=1).sum().reset_index(level=0, drop=True)
    df["persist"] = (df["persist"] >= 2).astype(int)

    # Refractory period
    df["persist_ref"] = df["persist"].copy()
    # Simple refractory: no alarm for 1 period after alarm
    alarm_mask = df["persist_ref"] == 1
    df.loc[alarm_mask.shift(1, fill_value=False), "persist_ref"] = 0

    logger.info("Created alarm signals with persistence and refractory logic")
    return df

def create_pred_evento(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create pred_evento based on alarm direction.

    Args:
        df: Input DataFrame with persist_ref and confirmation signals

    Returns:
        DataFrame with pred_evento column
    """
    df = df.copy()

    def classify_pred(row):
        if row["persist_ref"] == 0:
            return 0  # Normal
        elif row["confirm_drop"]:
            return 1  # Drop
        elif row["confirm_rise"]:
            return 2  # Rise
        else:
            return 0  # Default to normal

    df["pred_evento"] = df.apply(classify_pred, axis=1)

    logger.info(f"Created pred_evento: {df['pred_evento'].value_counts().to_dict()}")
    return df