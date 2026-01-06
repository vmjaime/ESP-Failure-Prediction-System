"""
Module for evaluating prediction quality and data trends.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

# Set plot style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (10, 6)

def analyze_prediction_distribution(df: pd.DataFrame, pred_col: str = 'pred_evento') -> pd.DataFrame:
    """
    Analyze the distribution of prediction values.

    Args:
        df: Input DataFrame
        pred_col: Prediction column name

    Returns:
        DataFrame with distribution statistics
    """
    if pred_col not in df.columns:
        raise ValueError(f"Column {pred_col} not found in data")

    counts = df[pred_col].value_counts().sort_index()
    percentages = (counts / len(df) * 100).round(2)

    dist_df = pd.DataFrame({
        'category': counts.index,
        'count': counts.values,
        'percentage': percentages.values
    })

    logger.info(f"Prediction distribution for {pred_col}:")
    for _, row in dist_df.iterrows():
        logger.info(".1f")

    return dist_df

def analyze_trends_by_prediction(df: pd.DataFrame, trend_vars: List[str],
                                pred_col: str = 'pred_evento') -> pd.DataFrame:
    """
    Analyze trends in variables by prediction categories.

    Args:
        df: Input DataFrame
        trend_vars: Variables to analyze trends for
        pred_col: Prediction column name

    Returns:
        DataFrame with trend statistics
    """
    available_vars = [v for v in trend_vars if v in df.columns]

    if not available_vars:
        logger.warning("No trend variables found in data")
        return pd.DataFrame()

    # Calculate statistics by prediction group
    stats = df.groupby(pred_col)[available_vars].agg(['mean', 'median', 'std', 'count']).round(2)

    logger.info(f"Trend analysis completed for {len(available_vars)} variables by {pred_col}")
    return stats

def plot_prediction_distribution(dist_df: pd.DataFrame, pred_col: str = 'pred_evento'):
    """
    Plot prediction distribution.

    Args:
        dist_df: Distribution DataFrame from analyze_prediction_distribution
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # Bar chart
    bars = ax1.bar(dist_df['category'].astype(str), dist_df['count'],
                   color=['green', 'orange', 'red'])
    ax1.set_title(f'Distribution of {pred_col}')
    ax1.set_xlabel(f'Category {pred_col}')
    ax1.set_ylabel('Count')

    for bar, pct in zip(bars, dist_df['percentage']):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 50,
                f'{pct:.1f}%', ha='center', va='bottom')

    # Pie chart
    ax2.pie(dist_df['percentage'],
            labels=[f'{v}\n{pct:.1f}%' for v, pct in zip(dist_df['category'], dist_df['percentage'])],
            colors=['green', 'orange', 'red'], autopct='%1.1f%%', startangle=90)
    ax2.set_title('Percentage Distribution')

    plt.tight_layout()
    plt.show()

def plot_trends_by_prediction(df: pd.DataFrame, trend_vars: List[str],
                             pred_col: str = 'pred_evento'):
    """
    Plot trends by prediction categories.

    Args:
        df: Input DataFrame
        trend_vars: Variables to plot
        pred_col: Prediction column name
    """
    available_vars = [v for v in trend_vars if v in df.columns]

    if not available_vars:
        return

    n_vars = len(available_vars)
    fig, axes = plt.subplots(1, n_vars, figsize=(6*n_vars, 5))

    if n_vars == 1:
        axes = [axes]

    for ax, var in zip(axes, available_vars):
        # Box plot
        sns.boxplot(data=df, x=pred_col, y=var, ax=ax, palette=['green', 'orange', 'red'])
        ax.set_title(f'{var} by {pred_col}')
        ax.set_xlabel(pred_col)
        ax.set_ylabel(var)

    plt.tight_layout()
    plt.show()

def calculate_correlations(df: pd.DataFrame, target_col: str,
                          vars_list: List[str] = None) -> pd.DataFrame:
    """
    Calculate correlations with target variable.

    Args:
        df: Input DataFrame
        target_col: Target column for correlation
        vars_list: List of variables to correlate (if None, uses all numeric)

    Returns:
        DataFrame with correlation results
    """
    if vars_list is None:
        vars_list = df.select_dtypes(include=[np.number]).columns.tolist()

    if target_col not in df.columns:
        raise ValueError(f"Target column {target_col} not found")

    correlations = []

    for col in vars_list:
        if col != target_col and col in df.columns:
            valid_idx = df[col].notna() & df[target_col].notna()
            if valid_idx.sum() > 100:  # Minimum observations
                corr_val = df.loc[valid_idx, col].corr(df.loc[valid_idx, target_col])
                if not pd.isna(corr_val):
                    correlations.append({
                        'variable': col,
                        'correlation': corr_val,
                        'abs_correlation': abs(corr_val)
                    })

    corr_df = pd.DataFrame(correlations).sort_values('abs_correlation', ascending=False)

    logger.info(f"Calculated correlations for {len(corr_df)} variables with {target_col}")
    return corr_df

def plot_correlations(corr_df: pd.DataFrame, target_col: str, top_n: int = 15):
    """
    Plot correlations with target.

    Args:
        corr_df: Correlation DataFrame
        target_col: Target column name
        top_n: Number of top correlations to plot
    """
    if corr_df.empty:
        return

    top_corr = corr_df.head(top_n)

    fig, ax = plt.subplots(figsize=(10, 6))
    colors = ['green' if x > 0 else 'red' for x in top_corr['correlation']]
    bars = ax.barh(top_corr['variable'], top_corr['correlation'], color=colors)
    ax.set_xlabel(f'Correlation with {target_col}')
    ax.set_title(f'Top {top_n} Variables Correlated with {target_col}')
    ax.axvline(0, color='black', linewidth=0.8)
    ax.invert_yaxis()

    plt.tight_layout()
    plt.show()

def comprehensive_evaluation(df: pd.DataFrame, pred_col: str = 'pred_evento',
                           trend_vars: List[str] = None) -> Dict:
    """
    Perform comprehensive evaluation of predictions.

    Args:
        df: Input DataFrame
        pred_col: Prediction column name
        trend_vars: Variables for trend analysis

    Returns:
        Dictionary with evaluation results
    """
    if trend_vars is None:
        trend_vars = ['PRUEBA_POZO.OIL_24 + PRUEBA_POZO.WATER_24',
                     'PRUEBA DE PRODUCCIÓN GAS A 24 HORAS MCF/D']

    results = {}

    # Distribution analysis
    dist_df = analyze_prediction_distribution(df, pred_col)
    results['distribution'] = dist_df

    # Trend analysis
    trend_stats = analyze_trends_by_prediction(df, trend_vars, pred_col)
    results['trend_stats'] = trend_stats

    # Correlation analysis
    corr_df = calculate_correlations(df, pred_col)
    results['correlations'] = corr_df

    logger.info("Comprehensive evaluation completed")
    return results