#!/usr/bin/env python3
"""
visualization_utils.py

Advanced visualization toolkit for CSV/Excel/JSON data:
* Smart Time-Series Plotting (auto-date formatting)
* Missing Values Heatmap
* Outlier Boxplots
* Auto-Dashboard (HTML report)

Usage:
    python visualization_utils.py plot data.csv --x date --y value --time-series
    python visualization_utils.py missing data.csv
    python visualization_utils.py dashboard data.csv --out report.html
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Tuple, Optional

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

log = logging.getLogger(__name__)

try:
    import seaborn as sns
    _SEABORN = True
except ImportError:
    sns = None
    _SEABORN = False

# --- Loading & Setup ---

def _load_data(path: Path) -> pd.DataFrame:
    path = Path(path).resolve()
    ext = path.suffix.lower()
    if ext == ".csv": return pd.read_csv(path)
    if ext in {".xlsx", ".xls"}: return pd.read_excel(path)
    if ext == ".json": return pd.read_json(path)
    raise ValueError(f"Unsupported extension: {ext}")

def _save_fig(fig, out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Support PDF, SVG, PNG based on extension
    fig.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    log.info(f"Saved -> {out_path}")

# --- Plotting Functions ---

def plot_data(df: pd.DataFrame, x: str, y: str, kind: str = "line", 
              time_series: bool = False, out_path: Optional[Path] = None, **kwargs):
    fig, ax = plt.subplots(figsize=(10, 6))
    
    if kind == "line":
        ax.plot(df[x], df[y], marker='o', markersize=4, linewidth=1)
    elif kind == "scatter":
        ax.scatter(df[x], df[y], alpha=0.7)
    elif kind == "bar":
        ax.bar(df[x], df[y])
    
    ax.set_xlabel(x)
    ax.set_ylabel(y)
    ax.set_title(kwargs.get('title', f"{y} vs {x}"))
    
    # Auto-format date axis if time_series is set
    if time_series:
        try:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            fig.autofmt_xdate()
        except Exception:
            log.warning("Could not format dates. Ensure X column contains datetime objects.")
    
    if out_path:
        _save_fig(fig, out_path)
    else:
        plt.show()
    return out_path

def plot_missing(df: pd.DataFrame, out_path: Optional[Path] = None):
    """Heatmap showing where data is missing."""
    fig, ax = plt.subplots(figsize=(12, 8))
    # Seaborn heatmap is better, but fallback to matplotlib
    null_data = df.isnull().sum()
    
    if _SEABORN:
        sns.heatmap(df.isnull(), cbar=False, yticklabels=False, cmap='viridis', ax=ax)
        ax.set_title("Missing Data Heatmap (Yellow=Missing)")
    else:
        # Fallback: Bar chart of missing counts
        ax.bar(null_data.index, null_data.values)
        ax.set_ylabel("Missing Count")
        ax.set_title("Missing Values per Column")
        ax.tick_params(axis='x', rotation=45)
    
    if out_path:
        _save_fig(fig, out_path)
    else:
        plt.show()
    return out_path

def plot_outliers(df: pd.DataFrame, columns: Optional[List[str]] = None, out_path: Optional[Path] = None):
    """Boxplot for numeric columns to visualize outliers."""
    numeric = df.select_dtypes(include='number')
    cols = columns if columns else numeric.columns.tolist()
    
    if not cols:
        log.warning("No numeric columns to plot.")
        return None

    fig, ax = plt.subplots(figsize=(12, 6))
    if _SEABORN:
        sns.boxplot(data=numeric[cols], ax=ax)
    else:
        ax.boxplot(numeric[cols].values, labels=cols)
    
    ax.set_title("Outlier Detection (Boxplots)")
    ax.tick_params(axis='x', rotation=45)
    
    if out_path:
        _save_fig(fig, out_path)
    else:
        plt.show()
    return out_path

def auto_dashboard(data_path: Path, out_path: Path):
    df = _load_data(data_path)
    img_dir = out_path.parent / f"{out_path.stem}_assets"
    img_dir.mkdir(exist_ok=True)
    
    # 1. Basic Plots
    plot_missing(df, img_dir / "missing.png")
    plot_outliers(df, out_path=img_dir / "outliers.png")
    
    # 2. Histograms
    numeric = df.select_dtypes(include='number')
    for col in numeric.columns:
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.hist(df[col].dropna(), bins=30, color='#4c72b0', edgecolor='black')
        ax.set_title(f"Histogram: {col}")
        _save_fig(fig, img_dir / f"hist_{col}.png")
    
    # 3. Correlation
    if numeric.shape[1] > 1:
        corr = numeric.corr()
        fig, ax = plt.subplots(figsize=(10, 8))
        if _SEABORN:
            sns.heatmap(corr, annot=True, fmt=".2f", cmap='coolwarm', ax=ax)
        else:
            im = ax.imshow(corr, cmap='coolwarm', vmin=-1, vmax=1)
            fig.colorbar(im, ax=ax)
        ax.set_title("Correlation Matrix")
        _save_fig(fig, img_dir / "correlation.png")

    # 4. HTML Report
    html = f"""<!DOCTYPE html>
<html>
<head><title>Dashboard: {data_path.name}</title>
<style>
body {{ font-family: sans-serif; padding: 20px; background: #f4f4f4; }}
.container {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(400px, 1fr)); gap: 20px; }}
.card {{ background: white; padding: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
h1, h2 {{ color: #333; }}
img {{ width: 100%; height: auto; }}
</style>
</head>
<body>
<h1>Data Report: {data_path.name}</h1>
<p>Rows: {len(df)} | Columns: {len(df.columns)}</p>

<h2>Missing Values</h2>
<div class="card"><img src="assets/missing.png"></div>

<h2>Outliers</h2>
<div class="card"><img src="assets/outliers.png"></div>

<h2>Correlation</h2>
<div class="card"><img src="assets/correlation.png"></div>

<h2>Distributions</h2>
<div class="container">
"""
    for col in numeric.columns:
        html += f'<div class="card"><h4>{col}</h4><img src="assets/hist_{col}.png"></div>'
    
    html += "</div></body></html>"
    
    out_path.write_text(html)
    log.info(f"Dashboard generated: {out_path}")

# --- CLI ---

def main():
    parser = argparse.ArgumentParser(description="Data Visualization Utilities")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # Plot
    p_plot = sub.add_parser("plot", help="Plot x vs y")
    p_plot.add_argument("csv", type=Path)
    p_plot.add_argument("--x", required=True)
    p_plot.add_argument("--y", required=True)
    p_plot.add_argument("--kind", choices=["line", "scatter", "bar"], default="line")
    p_plot.add_argument("--time-series", action="store_true", help="Format X axis as dates")
    p_plot.add_argument("--out", type=Path)
    
    # Missing
    p_missing = sub.add_parser("missing", help="Plot missing data heatmap")
    p_missing.add_argument("csv", type=Path)
    p_missing.add_argument("--out", type=Path)
    
    # Dashboard
    p_dash = sub.add_parser("dashboard", help="Generate full HTML report")
    p_dash.add_argument("csv", type=Path)
    p_dash.add_argument("--out", type=Path, required=True)

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    try:
        df = _load_data(args.csv)
        
        if args.cmd == "plot":
            plot_data(df, args.x, args.y, kind=args.kind, time_series=args.time_series, out_path=args.out)
        elif args.cmd == "missing":
            plot_missing(df, out_path=args.out)
        elif args.cmd == "dashboard":
            auto_dashboard(args.csv, args.out)
            
    except Exception as e:
        log.error(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
