#!/usr/bin/env python3
"""
data_tools.py

A robust, **one-stop toolbox** for offline data-wrangling tasks.
Features include CSV cleaning, Excel↔JSON conversion, dataset merging,
duplicate removal, missing-value imputation, and column-wise transformations.

Dependencies
------------
* pandas       – core data handling
* openpyxl     – Excel reading/writing
* tqdm         – optional progress bar
* pyarrow      – optional, for Parquet support

Install with:
    pip install pandas openpyxl tqdm pyarrow

Author:   Improved Version
Created:  2026-03-14
"""

import argparse
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Tuple, Union

import pandas as pd

try:
    from tqdm import tqdm
except Exception:
    tqdm = lambda x, **kw: x

# ----------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
log = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Helper utilities
# ----------------------------------------------------------------------
def _as_path(p: Union[Path, str]) -> Path:
    return Path(p).expanduser().resolve()


def _detect_file_type(p: Path) -> str:
    """Return a canonical short type identifier: 'csv', 'excel', 'json', 'parquet'."""
    suffix = p.suffix.lower()
    if suffix in {".csv", ".tsv"}:
        return "csv"
    if suffix in {".xlsx", ".xls"}:
        return "excel"
    if suffix in {".json"}:
        return "json"
    if suffix in {".parquet", ".pq"}:
        return "parquet"
    raise ValueError(f"Unsupported data file extension: {suffix}")


def _read_data(p: Path, **kwargs) -> pd.DataFrame:
    kind = _detect_file_type(p)
    
    # Try to read, handle specific library dependencies
    if kind == "csv":
        # Use python engine to be more robust with weird files
        return pd.read_csv(p, engine='python', **kwargs)
    if kind == "excel":
        return pd.read_excel(p, **kwargs)
    if kind == "json":
        return pd.read_json(p, **kwargs)
    if kind == "parquet":
        try:
            return pd.read_parquet(p, **kwargs)
        except ImportError:
            raise ImportError("Parquet support requires 'pyarrow' or 'fastparquet'. Please install it.")
    raise RuntimeError(f"Unable to read file {p}")


def _write_data(df: pd.DataFrame, p: Path, **kwargs) -> None:
    kind = _detect_file_type(p)
    _as_path(p).parent.mkdir(parents=True, exist_ok=True)
    
    if kind == "csv":
        df.to_csv(p, index=False, **kwargs)
    elif kind == "excel":
        df.to_excel(p, index=False, **kwargs)
    elif kind == "json":
        df.to_json(p, orient="records", force_ascii=False, indent=2, **kwargs)
    elif kind == "parquet":
        try:
            df.to_parquet(p, index=False, **kwargs)
        except ImportError:
            raise ImportError("Parquet support requires 'pyarrow'. Please install it.")
    else:
        raise RuntimeError(f"Unable to write to file {p}")


# ----------------------------------------------------------------------
# 1️⃣ CSV Cleaner
# ----------------------------------------------------------------------
def clean_csv(
    input_path: Path,
    output_path: Path,
    dropna: bool = True,
    fillna: Optional[Any] = None,
    strip_whitespace: bool = True,
    deduplicate: bool = True,
    encoding: str = "utf-8",
    **read_kwargs,
) -> None:
    """
    Load a CSV, optionally strip string whitespace, fill / drop missing values,
    remove duplicate rows and write back to *output_path*.
    """
    log.info(f"Reading CSV {input_path}")
    # Use error_bad_lines=False for older pandas or on_bad_lines='skip' for newer
    # to handle corrupt lines gracefully
    try:
        df = pd.read_csv(input_path, encoding=encoding, **read_kwargs)
    except Exception as e:
        log.error(f"Failed to read CSV: {e}")
        raise

    if strip_whitespace:
        obj_cols = df.select_dtypes(include=["object"]).columns
        # Strip whitespace from all string columns
        df[obj_cols] = df[obj_cols].apply(lambda col: col.str.strip() if col.dtype == "object" else col)
        log.info(f"Stripped whitespace from {len(obj_cols)} columns")

    if fillna is not None:
        log.info(f"Filling missing values with {repr(fillna)}")
        df = df.fillna(fillna)
    elif dropna:
        log.info("Dropping rows with any missing values")
        df = df.dropna()

    if deduplicate:
        before = len(df)
        df = df.drop_duplicates()
        after = len(df)
        log.info(f"Deduplicated rows: {before} → {after} (removed {before - after})")

    log.info(f"Writing cleaned CSV to {output_path}")
    df.to_csv(output_path, index=False, encoding=encoding)
    log.info(f"CSV cleaning completed: {len(df)} rows written")


# ----------------------------------------------------------------------
# 2️⃣ Excel ↔ JSON & JSON ↔ CSV
# ----------------------------------------------------------------------
def excel_to_json(
    excel_path: Path,
    json_path: Path,
    sheet_name: Optional[str] = None,
    orient: str = "records",
    **read_kwargs,
) -> None:
    """
    Convert an Excel workbook (or a single sheet) to a JSON file.
    """
    log.info(f"Reading Excel file {excel_path} (sheet={sheet_name or 'first'})")
    df = pd.read_excel(excel_path, sheet_name=sheet_name, **read_kwargs)
    
    # If sheet_name is None, pandas returns a dict of DataFrames
    if isinstance(df, dict):
        log.warning("Multiple sheets detected. Converting only the first sheet.")
        df = list(df.values())[0]

    log.info(f"Writing JSON to {json_path} (orient={orient})")
    _as_path(json_path).parent.mkdir(parents=True, exist_ok=True)
    json_str = df.to_json(orient=orient, force_ascii=False, indent=2)
    _as_path(json_path).write_text(json_str, encoding="utf-8")
    log.info(f"Excel → JSON conversion finished, {len(df)} rows written")


def json_to_csv(
    json_path: Path,
    csv_path: Path,
    orient: str = "records",
    encoding: str = "utf-8",
    **read_kwargs,
) -> None:
    """
    Turn a JSON document into a CSV file.
    """
    log.info(f"Reading JSON {json_path} (orient={orient})")
    df = pd.read_json(json_path, orient=orient, **read_kwargs)
    log.info(f"Writing CSV to {csv_path}")
    df.to_csv(csv_path, index=False, encoding=encoding)
    log.info(f"JSON → CSV conversion finished, {len(df)} rows written")


# ----------------------------------------------------------------------
# 3️⃣ Dataset Merger
# ----------------------------------------------------------------------
def merge_datasets(
    input_paths: Iterable[Path],
    output_path: Path,
    on: Optional[str] = None,
    how: str = "outer",
    ignore_index: bool = False,
    **read_kwargs,
) -> None:
    """
    Merge multiple tabular files into a single DataFrame.
    If *on* is provided, performs a relational merge (join).
    Otherwise, concatenates files vertically.
    """
    dfs = []
    for p in input_paths:
        log.info(f"Reading {p}")
        df = _read_data(_as_path(p), **read_kwargs)
        dfs.append(df)

    merged = pd.DataFrame()
    
    if on:
        log.info(f"Performing relational merge on column '{on}' with method '{how}'")
        merged = dfs[0]
        for df in dfs[1:]:
            merged = merged.merge(df, on=on, how=how)
    else:
        log.info(f"Concatenating {len(dfs)} tables (ignore_index={ignore_index})")
        merged = pd.concat(dfs, ignore_index=ignore_index)

    log.info(f"Writing merged data to {output_path}")
    _write_data(merged, _as_path(output_path))
    log.info(f"Merge complete – {merged.shape[0]} rows, {merged.shape[1]} columns")


# ----------------------------------------------------------------------
# 4️⃣ Duplicate remover
# ----------------------------------------------------------------------
def deduplicate_dataset(
    input_path: Path,
    output_path: Path,
    subset: Optional[Iterable[str]] = None,
    keep: str = "first",
    **read_kwargs,
) -> None:
    """
    Load a dataset and drop duplicate rows.
    """
    log.info(f"Loading data from {input_path}")
    df = _read_data(_as_path(input_path), **read_kwargs)
    before = len(df)
    df = df.drop_duplicates(subset=subset, keep=keep)
    after = len(df)

    log.info(f"Removed {before - after} duplicate rows ( {before} → {after} )")
    _write_data(df, _as_path(output_path))
    log.info(f"Deduplicated dataset written to {output_path}")


# ----------------------------------------------------------------------
# 5️⃣ Missing‑value filler / imputer
# ----------------------------------------------------------------------
def fill_missing(
    input_path: Path,
    output_path: Path,
    strategy: str = "mean",
    fill_value: Optional[Any] = None,
    columns: Optional[Iterable[str]] = None,
    **read_kwargs,
) -> None:
    """
    Impute missing values using a specified strategy.
    Supported strategies: mean, median, mode, constant, ffill, bfill.
    """
    log.info(f"Reading {input_path} for missing‑value imputation")
    df = _read_data(_as_path(input_path), **read_kwargs)

    target_cols = columns or df.columns
    log.info(f"Imputing {len(target_cols)} column(s) with strategy='{strategy}'")

    for col in target_cols:
        if col not in df.columns:
            log.warning(f"Column {col} not found – skipping")
            continue

        # Safety check for mean/median
        if strategy in ["mean", "median"]:
            if not pd.api.types.is_numeric_dtype(df[col]):
                log.warning(f"Column {col} is not numeric. Cannot use strategy '{strategy}'. Skipping.")
                continue

        if strategy == "mean":
            value = df[col].mean()
            df[col] = df[col].fillna(value)
        elif strategy == "median":
            value = df[col].median()
            df[col] = df[col].fillna(value)
        elif strategy == "mode":
            mode_series = df[col].mode()
            value = mode_series.iloc[0] if not mode_series.empty else None
            df[col] = df[col].fillna(value)
        elif strategy == "constant":
            if fill_value is None:
                raise ValueError("fill_value must be supplied when using constant strategy")
            df[col] = df[col].fillna(fill_value)
        elif strategy == "ffill":
            df[col] = df[col].ffill()
        elif strategy == "bfill":
            df[col] = df[col].bfill()
        else:
            raise ValueError(f"Unsupported strategy: {strategy}")

        log.info(f"Filled column {col}")

    _write_data(df, _as_path(output_path))
    log.info(f"Missing‑value imputation complete – written to {output_path}")


# ----------------------------------------------------------------------
# 6️⃣ Column transformer (config‑driven)
# ----------------------------------------------------------------------
def _load_transform_config(config_path: Path) -> Dict[str, Any]:
    """Read a JSON transformation spec."""
    cfg_path = _as_path(config_path)
    with cfg_path.open("r", encoding="utf-8") as f:
        return json.load(f)

def transform_columns(
    input_path: Path,
    output_path: Path,
    config_path: Path,
    **read_kwargs,
) -> None:
    """
    Apply a series of column‑wise transformations described in a JSON file.
    
    Supported operation types:
    * cast      – Cast to dtype ('to': 'int', 'str', 'float').
    * apply     – Apply lambda function ('func': 'lambda x: x*2').
    * date      – Parse date string ('format': '%Y-%m-%d').
    * strip     – Strip whitespace.
    * lower/upper – Case conversion.
    * replace   – Regex substitution ('pattern', 'repl').
    * rename    – Rename column ('to': 'new_name').
    * drop      – Drop the column.
    * map       – Map values using dict ('map': {"M": "Male"}).
    """
    log.info(f"Loading data from {input_path}")
    df = _read_data(_as_path(input_path), **read_kwargs)

    log.info(f"Reading transformation config {config_path}")
    cfg = _load_transform_config(config_path)

    # We iterate columns, but 'drop' and 'rename' might require list management
    cols_to_drop = []
    rename_map = {}

    for col, ops in cfg.items():
        if col not in df.columns:
            log.warning(f"Column {col} not present in the data – skipping")
            continue

        op_type = ops.get("type")
        log.info(f"Applying '{op_type}' transformation on column '{col}'")

        try:
            if op_type == "cast":
                target = ops["to"]
                df[col] = df[col].astype(target)
            
            elif op_type == "apply":
                func_str = ops["func"]
                # Security Note: eval is used here. Only run trusted configs.
                func = eval(func_str, {"__builtins__": {}}, {"pd": pd})
                df[col] = df[col].apply(func)
            
            elif op_type == "date":
                fmt = ops["format"]
                df[col] = pd.to_datetime(df[col], format=fmt, errors="coerce")
            
            elif op_type == "strip":
                df[col] = df[col].astype(str).str.strip()
            
            elif op_type == "lower":
                df[col] = df[col].astype(str).str.lower()
            
            elif op_type == "upper":
                df[col] = df[col].astype(str).str.upper()
            
            elif op_type == "replace":
                pattern = ops["pattern"]
                repl = ops.get("repl", "")
                df[col] = df[col].astype(str).apply(lambda v: re.sub(pattern, repl, v))
            
            elif op_type == "rename":
                rename_map[col] = ops["to"]
            
            elif op_type == "drop":
                cols_to_drop.append(col)
            
            elif op_type == "map":
                mapping = ops["map"]
                df[col] = df[col].map(mapping)

            else:
                raise ValueError(f"Unsupported transformation type: {op_type}")
        
        except Exception as e:
            log.error(f"Failed to transform column '{col}' with op '{op_type}': {e}")
            # Decide: continue or raise? We choose to continue for robustness

    # Apply deferred operations
    if rename_map:
        df.rename(columns=rename_map, inplace=True)
        log.info(f"Renamed {len(rename_map)} columns")
    
    if cols_to_drop:
        df.drop(columns=cols_to_drop, inplace=True)
        log.info(f"Dropped {len(cols_to_drop)} columns")

    _write_data(df, _as_path(output_path))
    log.info(f"All transformations applied – output written to {output_path}")


# ----------------------------------------------------------------------
# Command‑line interface
# ----------------------------------------------------------------------
def _build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Data‑processing toolbox – CSV cleaner, converters, merge, dedupe, imputer, column transformer.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # ---- csv‑clean ----------------------------------------------------
    p_clean = sub.add_parser("csv-clean", help="Clean up a CSV file")
    p_clean.add_argument("input", type=_as_path, help="Source CSV")
    p_clean.add_argument("output", type=_as_path, help="Destination CSV")
    p_clean.add_argument("--dropna", action="store_true", help="Drop rows with any missing values")
    p_clean.add_argument("--fillna", default=None, help="Fill missing values with the supplied constant")
    p_clean.add_argument("--strip", action="store_true", help="Strip whitespace from string columns")
    p_clean.add_argument("--dedup", action="store_true", help="Remove duplicate rows")
    p_clean.add_argument("--encoding", default="utf-8", help="File encoding")

    # ---- excel2json ---------------------------------------------------
    p_x2j = sub.add_parser("excel2json", help="Convert Excel → JSON")
    p_x2j.add_argument("excel", type=_as_path, help="Source .xlsx/.xls")
    p_x2j.add_argument("json", type=_as_path, help="Destination .json")
    p_x2j.add_argument("--sheet", default=None, help="Sheet name (defaults to first)")

    # ---- json2csv -----------------------------------------------------
    p_j2c = sub.add_parser("json2csv", help="Convert JSON → CSV")
    p_j2c.add_argument("json", type=_as_path, help="Source .json")
    p_j2c.add_argument("csv", type=_as_path, help="Destination .csv")

    # ---- merge ---------------------------------------------------------
    p_merge = sub.add_parser("merge", help="Merge multiple tabular files")
    p_merge.add_argument(
        "inputs",
        nargs="+",
        type=_as_path,
        help="Input files (CSV/Excel/JSON/Parquet)",
    )
    p_merge.add_argument("-o", "--output", type=_as_path, required=True, help="Output file")
    p_merge.add_argument("--on", default=None, help="Column name for relational merge")
    p_merge.add_argument(
        "--how",
        default="outer",
        choices=["inner", "outer", "left", "right"],
        help="Join method for relational merges",
    )
    p_merge.add_argument(
        "--ignore-index",
        action="store_true",
        help="When concatenating, reset the index in the result",
    )

    # ---- dedup ---------------------------------------------------------
    p_dedup = sub.add_parser("dedup", help="Remove duplicate rows from a dataset")
    p_dedup.add_argument("input", type=_as_path, help="Source file")
    p_dedup.add_argument("output", type=_as_path, help="Destination file")
    p_dedup.add_argument("--subset", nargs="+", help="Column(s) to consider for duplicate detection")
    p_dedup.add_argument(
        "--keep",
        default="first",
        choices=["first", "last", "false"],
        help="Which duplicate to keep",
    )

    # ---- fillna --------------------------------------------------------
    p_fill = sub.add_parser("fillna", help="Impute missing values")
    p_fill.add_argument("input", type=_as_path, help="Source file")
    p_fill.add_argument("output", type=_as_path, help="Destination file")
    p_fill.add_argument(
        "--strategy",
        default="mean",
        choices=["mean", "median", "mode", "constant", "ffill", "bfill"],
        help="Imputation strategy",
    )
    p_fill.add_argument("--value", default=None, help="Constant for 'constant' strategy")
    p_fill.add_argument("--columns", nargs="+", help="Specific columns to fill (default: all)")

    # ---- transform ------------------------------------------------------
    p_trans = sub.add_parser(
        "transform",
        help="Apply a config‑driven column transformation pipeline",
    )
    p_trans.add_argument("input", type=_as_path, help="Source file")
    p_trans.add_argument("output", type=_as_path, help="Destination file")
    p_trans.add_argument(
        "config",
        type=_as_path,
        help="JSON file describing per‑column transformations",
    )

    return parser


def _dispatch(args: argparse.Namespace) -> None:
    """Call the appropriate function based on the parsed arguments."""
    try:
        if args.cmd == "csv-clean":
            clean_csv(
                input_path=args.input,
                output_path=args.output,
                dropna=args.dropna,
                fillna=args.fillna,
                strip_whitespace=args.strip,
                deduplicate=args.dedup,
                encoding=args.encoding,
            )

        elif args.cmd == "excel2json":
            excel_to_json(
                excel_path=args.excel,
                json_path=args.json,
                sheet_name=args.sheet,
            )

        elif args.cmd == "json2csv":
            json_to_csv(json_path=args.json, csv_path=args.csv)

        elif args.cmd == "merge":
            merge_datasets(
                input_paths=args.inputs,
                output_path=args.output,
                on=args.on,
                how=args.how,
                ignore_index=args.ignore_index,
            )

        elif args.cmd == "dedup":
            deduplicate_dataset(
                input_path=args.input,
                output_path=args.output,
                subset=args.subset,
                keep=args.keep if args.keep != "false" else False,
            )

        elif args.cmd == "fillna":
            fill_missing(
                input_path=args.input,
                output_path=args.output,
                strategy=args.strategy,
                fill_value=args.value,
                columns=args.columns,
            )

        elif args.cmd == "transform":
            transform_columns(
                input_path=args.input,
                output_path=args.output,
                config_path=args.config,
            )

        else:
            raise RuntimeError(f"Unhandled command: {args.cmd}")

    except Exception as e:
        log.error(f"Error: {e}")
        sys.exit(1)


def main() -> None:
    parser = _build_cli_parser()
    args = parser.parse_args()
    _dispatch(args)


if __name__ == "__main__":
    main()
