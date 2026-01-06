"""
Module for data imputation using various strategies.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

def analyze_missing_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Analyze missing data in DataFrame.

    Args:
        df: Input DataFrame

    Returns:
        DataFrame with missing data statistics
    """
    missing = df.isnull().sum()
    missing_pct = (missing / len(df) * 100).round(2)

    missing_df = pd.DataFrame({
        'column': missing.index,
        'missing_count': missing.values,
        'missing_pct': missing_pct.values
    }).query('missing_count > 0').sort_values('missing_pct', ascending=False).reset_index(drop=True)

    logger.info(f"Found {len(missing_df)} columns with missing data out of {len(df.columns)} total columns")
    return missing_df

def impute_by_group(df: pd.DataFrame, column: str, group_cols: List[str], method: str = 'mean') -> pd.DataFrame:
    """
    Impute missing values using group statistics.

    Args:
        df: Input DataFrame
        column: Column to impute
        group_cols: Columns to group by
        method: Imputation method ('mean', 'median', 'mode')

    Returns:
        DataFrame with imputed values
    """
    df = df.copy()

    if method == 'mean':
        fill_values = df.groupby(group_cols)[column].transform('mean')
    elif method == 'median':
        fill_values = df.groupby(group_cols)[column].transform('median')
    elif method == 'mode':
        fill_values = df.groupby(group_cols)[column].transform(lambda x: x.mode().iloc[0] if not x.mode().empty else np.nan)
    else:
        raise ValueError(f"Unknown method: {method}")

    df[column] = df[column].fillna(fill_values)
    logger.info(f"Imputed {column} using {method} by groups {group_cols}")
    return df

def impute_time_series(df: pd.DataFrame, column: str, time_col: str, group_cols: List[str],
                      method: str = 'interpolate') -> pd.DataFrame:
    """
    Impute missing values in time series data.

    Args:
        df: Input DataFrame
        column: Column to impute
        time_col: Time column for sorting
        group_cols: Columns to group by (e.g., well name)
        method: Imputation method ('interpolate', 'forward_fill', 'backward_fill')

    Returns:
        DataFrame with imputed values
    """
    df = df.copy()

    def impute_group(group):
        group = group.sort_values(time_col)
        if method == 'interpolate':
            group[column] = group[column].interpolate(method='linear')
        elif method == 'forward_fill':
            group[column] = group[column].fillna(method='ffill')
        elif method == 'backward_fill':
            group[column] = group[column].fillna(method='bfill')
        return group

    df = df.groupby(group_cols).apply(impute_group).reset_index(drop=True)
    logger.info(f"Imputed {column} using {method} for time series")
    return df

def impute_missing_values(df: pd.DataFrame, imputation_config: Dict) -> pd.DataFrame:
    """
    Apply imputation strategies based on configuration.

    Args:
        df: Input DataFrame
        imputation_config: Dictionary with imputation settings

    Returns:
        DataFrame with imputed values
    """
    df = df.copy()

    for config in imputation_config:
        column = config['column']
        if column not in df.columns:
            logger.warning(f"Column {column} not found, skipping imputation")
            continue

        missing_before = df[column].isnull().sum()

        if config['method'] == 'group':
            df = impute_by_group(df, column, config['group_cols'], config.get('group_method', 'mean'))
        elif config['method'] == 'time_series':
            df = impute_time_series(df, column, config['time_col'], config['group_cols'],
                                   config.get('ts_method', 'interpolate'))
        elif config['method'] == 'constant':
            df[column] = df[column].fillna(config['value'])
        elif config['method'] == 'drop':
            df = df.dropna(subset=[column])
        else:
            logger.warning(f"Unknown imputation method: {config['method']}")

        missing_after = df[column].isnull().sum()
        logger.info(f"Imputed {missing_before - missing_after} values in {column}")

    return df

def create_imputation_report(df_before: pd.DataFrame, df_after: pd.DataFrame) -> pd.DataFrame:
    """
    Create a report of imputation results.

    Args:
        df_before: DataFrame before imputation
        df_after: DataFrame after imputation

    Returns:
        DataFrame with imputation report
    """
    missing_before = df_before.isnull().sum()
    missing_after = df_after.isnull().sum()

    report = pd.DataFrame({
        'column': missing_before.index,
        'missing_before': missing_before.values,
        'missing_after': missing_after.values,
        'imputed_count': (missing_before - missing_after).values,
        'imputation_rate': (((missing_before - missing_after) / missing_before.replace(0, 1)) * 100).round(2).values
    })

    report = report[report['missing_before'] > 0].sort_values('imputed_count', ascending=False)
    return report