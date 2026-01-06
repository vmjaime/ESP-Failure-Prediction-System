"""
ESP Project Data Pipeline
Main script to process ESP well data from raw to prediction-ready format.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from typing import Optional

# Import project modules
from eda.ranges import calculate_operational_ranges, calculate_strict_ranges, apply_ranges_to_data, create_regimen_column
from eda.imputation import analyze_missing_data, impute_missing_values, create_imputation_report
from eda.signals import (calculate_slope_signals, calculate_delta_signals, calculate_ratio_signals,
                        create_hybrid_events, create_envelope_signals, calculate_confirmation_stats,
                        create_confirmation_signals, create_alarms, create_pred_evento)
from evaluation.evaluate_predictions import comprehensive_evaluation

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "Datos"
OUTPUT_DIR = PROJECT_ROOT / "processed_data"

# Column mappings (after cleaning)
COL_POZO = "@NAME( )"
COL_FECHA = "DATE"
COL_QOIL = "PRUEBA DE PRODUCCION PETRÓLEO A 24 HORAS BBL/D"
COL_QWATER = "PRUEBA DE PRODUCCIÓN AGUA A 24 HORAS BBL/D"
COL_QTOT = "PRUEBA_POZO.OIL_24 + PRUEBA_POZO.WATER_24"
COL_QGAS = "PRUEBA DE PRODUCCIÓN GAS A 24 HORAS MCF/D"
COL_BSW = "BSW %"
COL_API = "GRAVEDAD API DEL PETROLEO"
COL_SALINITY = "SALINIDAD PPM PU"
COL_PINT = "PRESION DE INTAKE PSI"
COL_HZ = "FRECUENCIA BOMBA HZ"
COL_AMPS = "AMPERAJE BOMBA AMP"
COL_PTUB = "PRESION DE TUBING PSI"
COL_PCAS = "PRESION DE CASING PSI"
COL_BOMBA = "TIPO DE BOMBA"
COL_TEMP = "TEMPERATURA DE LA BOMBA DEG. F"
COL_ETAPAS = "ETAPAS DE LA BOMBA"
COL_CAMPO = "CAMPO"
COL_EVENTO = "evento_hibrido"  # May not exist in raw data
COL_PRED_EVENTO = "pred_evento"  # Will be created

def load_raw_data(file_path: str) -> pd.DataFrame:
    """
    Load raw ESP data from Excel file with multiple sheets.

    Args:
        file_path: Path to the Excel file

    Returns:
        DataFrame with concatenated data from all relevant sheets
    """
    logger.info(f"Loading raw data from {file_path}")
    xls = pd.ExcelFile(file_path)

    # Skip first 4 sheets (metadata) and 'POTENCIAL', 'IMPRIMIR', etc.
    skip_sheets = {'POTENCIAL', 'IMPRIMIR', 'FORECAST', 'Reporte1_1', 'Pozos mas productores'}
    relevant_sheets = [sheet for sheet in xls.sheet_names[4:] if sheet not in skip_sheets]

    logger.info(f"Processing {len(relevant_sheets)} well sheets")

    dfs = []
    for sheet in relevant_sheets:
        try:
            df_sheet = pd.read_excel(xls, sheet_name=sheet)
            if not df_sheet.empty:
                # Add well name column
                df_sheet['WELL_NAME'] = sheet
                dfs.append(df_sheet)
                logger.debug(f"Loaded sheet {sheet}: {len(df_sheet)} rows")
        except Exception as e:
            logger.warning(f"Error loading sheet {sheet}: {e}")

    if not dfs:
        raise ValueError("No data loaded from any sheet")

    # Concatenate all sheets
    df = pd.concat(dfs, ignore_index=True)

    # Clean column names
    df.columns = (df.columns
                  .str.strip()
                  .str.upper()
                  .str.replace(r" +", " ", regex=True))

    logger.info(f"Loaded {len(df)} total rows with {len(df.columns)} columns from {len(dfs)} sheets")
    return df

def clean_dates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and convert date columns.

    Args:
        df: Input DataFrame

    Returns:
        DataFrame with cleaned dates
    """
    logger.info("Cleaning date columns")

    # Detect date column
    date_cols = [col for col in df.columns if "DATE" in col or "FECHA" in col]
    if not date_cols:
        raise ValueError("No date column found")

    col_fecha = date_cols[0]
    logger.info(f"Using date column: {col_fecha}")

    # Convert dates
    fecha_base_excel = pd.to_datetime("1899-12-30")

    def convertir_fecha(x):
        try:
            if isinstance(x, (int, float)):
                return fecha_base_excel + pd.to_timedelta(x, unit="D")
            return pd.to_datetime(x, dayfirst=True, errors="coerce")
        except:
            return pd.NaT

    df[COL_FECHA] = df[col_fecha].apply(convertir_fecha)

    # Sort by well and date
    df = df.sort_values([COL_POZO, COL_FECHA], na_position="last").reset_index(drop=True)

    logger.info(f"Date cleaning completed. Date range: {df[COL_FECHA].min()} to {df[COL_FECHA].max()}")
    return df

def remove_unnecessary_columns(df: pd.DataFrame, columns_to_remove: list) -> pd.DataFrame:
    """
    Remove unnecessary columns from DataFrame.

    Args:
        df: Input DataFrame
        columns_to_remove: List of columns to remove

    Returns:
        DataFrame with columns removed
    """
    logger.info(f"Removing columns: {columns_to_remove}")
    df = df.drop(columns=[col for col in columns_to_remove if col in df.columns], errors='ignore')
    logger.info(f"Remaining columns: {len(df.columns)}")
    return df

def calculate_statistics(df: pd.DataFrame, group_col: str) -> dict:
    """
    Calculate basic statistics for numerical columns grouped by a column.

    Args:
        df: Input DataFrame
        group_col: Column to group by

    Returns:
        Dictionary with statistics
    """
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    stats = {}

    for col in numeric_cols:
        if col != group_col:
            stats[col] = {
                'mean': df.groupby(group_col)[col].mean(),
                'std': df.groupby(group_col)[col].std(),
                'min': df.groupby(group_col)[col].min(),
                'max': df.groupby(group_col)[col].max(),
                'q25': df.groupby(group_col)[col].quantile(0.25),
                'q75': df.groupby(group_col)[col].quantile(0.75)
            }

    return stats

def save_processed_data(df: pd.DataFrame, filename: str, output_dir: Path = OUTPUT_DIR):
    """
    Save processed DataFrame to file.

    Args:
        df: DataFrame to save
        filename: Output filename
        output_dir: Output directory
    """
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / filename

    if filename.endswith('.parquet'):
        df.to_parquet(output_path, index=False)
    elif filename.endswith('.csv'):
        df.to_csv(output_path, index=False)
    elif filename.endswith('.xlsx'):
        df.to_excel(output_path, index=False)
    else:
        raise ValueError("Unsupported file format")

    logger.info(f"Data saved to {output_path}")

def main():
    """Main pipeline execution."""
    logger.info("Starting ESP Data Pipeline")

    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Load raw data
    raw_file = DATA_DIR / "DATOS_ESP.xlsx"
    if not raw_file.exists():
        raise FileNotFoundError(f"Raw data file not found: {raw_file}")

    df = load_raw_data(raw_file)

    # Clean dates
    df = clean_dates(df)

    # Remove unnecessary columns
    columns_to_remove = ['pozo', 'fecha']  # Add more as needed
    df = remove_unnecessary_columns(df, columns_to_remove)

    # Create regimen column
    df = create_regimen_column(df)

    # Convert numeric columns
    numeric_cols = [COL_QOIL, COL_QWATER, COL_QTOT, COL_QGAS, COL_BSW, COL_API, COL_SALINITY,
                   COL_PINT, COL_HZ, COL_AMPS, COL_PTUB, COL_PCAS, COL_TEMP, COL_ETAPAS,
                   'delta_1', 'delta_3', 'slope_7', 'slope_14']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    logger.info("Converted numeric columns")

    # Calculate production signals
    df = calculate_slope_signals(df, COL_QTOT, COL_POZO, COL_FECHA)
    df = calculate_delta_signals(df, COL_QTOT, COL_POZO)
    df = calculate_ratio_signals(df, COL_QTOT, COL_POZO)
    logger.info("Calculated production signals")

    # Create hybrid events (original classification)
    df = create_hybrid_events(df, COL_QTOT, COL_POZO)
    logger.info("Created hybrid events")

    # Calculate operational ranges
    operational_ranges_dict = calculate_operational_ranges(df)
    logger.info("Calculated operational ranges")

    # Create envelope signals
    df = create_envelope_signals(df, operational_ranges_dict)
    logger.info("Created envelope signals")

    # Calculate confirmation statistics
    confirmation_stats = calculate_confirmation_stats(df, COL_POZO)
    logger.info("Calculated confirmation statistics")

    # Create confirmation signals
    df = create_confirmation_signals(df, confirmation_stats, COL_POZO)
    logger.info("Created confirmation signals")

    # Create alarms with persistence
    df = create_alarms(df, COL_POZO)
    logger.info("Created alarm signals")

    # Create pred_evento (robust classification)
    df = create_pred_evento(df)
    logger.info("Created pred_evento")

    # Analyze missing data
    missing_analysis = analyze_missing_data(df)
    logger.info("Missing data analysis completed")

    # Define imputation configuration
    imputation_config = [
        # Example: impute production variables by regimen
        {'column': COL_QTOT, 'method': 'group', 'group_cols': ['regimen_id'], 'group_method': 'median'},
        {'column': COL_QGAS, 'method': 'group', 'group_cols': ['regimen_id'], 'group_method': 'median'},
        # Add more imputation rules as needed
    ]

    # Impute missing values
    df_before_impute = df.copy()
    df = impute_missing_values(df, imputation_config)

    # Create imputation report
    imputation_report = create_imputation_report(df_before_impute, df)
    logger.info("Imputation completed")

    # Comprehensive evaluation (only if pred_evento exists)
    if COL_PRED_EVENTO in df.columns:
        evaluation_results = comprehensive_evaluation(df, COL_PRED_EVENTO)
        logger.info("Evaluation completed")
    else:
        logger.info(f"Column {COL_PRED_EVENTO} not found, skipping evaluation")
        evaluation_results = {}

    # Remove duplicate columns before saving
    df = df.loc[:, ~df.columns.duplicated()]
    logger.info(f"Removed duplicate columns, remaining: {len(df.columns)}")

    # Save processed data
    save_processed_data(df, "processed_data.parquet")

    # Save intermediate results
    save_processed_data(pd.DataFrame.from_dict(operational_ranges_dict, orient='index'), "operational_ranges.parquet")
    # if strict_ranges:
    #     save_processed_data(pd.DataFrame.from_dict(strict_ranges, orient='index'), "strict_ranges.parquet")
    save_processed_data(missing_analysis, "missing_data_analysis.parquet")
    save_processed_data(imputation_report, "imputation_report.parquet")

    logger.info("Data pipeline completed successfully")

if __name__ == "__main__":
    main()