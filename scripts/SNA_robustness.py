#!/usr/bin/env python3
"""
robustness_suite.py

Run two robustness checks for undirected weighted settlement networks:
  1) Binary adjacency (0/1)
  2) Exponential emphasis (w' = 2^(w-1): 1,2,4,8,16,…)

For each input matrix (.xlsx):
  - Reads & symmetrizes A by max(A, A^T); zeros diagonal
  - Computes weighted degree for baseline, binary, and exp2
  - Reports:
      * Spearman rho of degree ranks (baseline vs variant)
      * Top-K hubs of each and Jaccard overlap
  - Saves:
      * *_binary.xlsx, *_exp2.xlsx
      * *_binary_summary.csv, *_exp2_summary.csv
      * *_degrees_baseline_vs_{variant}.csv
  - Appends one row per variant to a MASTER CSV

Usage examples:
  python robustness_suite.py --in_glob "matrices/*.xlsx" --outdir out --k 10
  python robustness_suite.py --in_glob "/mnt/data/Babaeski_matrix.xlsx" --sheet 0 --outdir out

Dependencies: pandas, numpy, openpyxl (read xlsx), xlsxwriter (optional for writing xlsx)
"""

import argparse
from pathlib import Path
import glob
import pandas as pd
import numpy as np

# ---------- IO helpers ----------
def read_square_matrix(xlsx_path: Path, sheet) -> pd.DataFrame:
    """Load a square weighted adjacency from Excel, make numeric, symmetrize by max, zero diagonal."""
    try:
        df = pd.read_excel(xlsx_path, sheet_name=sheet, header=0, index_col=0)
    except Exception:
        df = pd.read_excel(xlsx_path, sheet_name=sheet, header=0)
        # fall through to choose index below
    # If index like 0..n-1 → choose first object column (names) as index
    if isinstance(df.index, pd.RangeIndex):
        obj_cols = [c for c in df.columns if df[c].dtype == object]
        if obj_cols:
            df = df.set_index(obj_cols[0])
        else:
            df = df.set_index(df.columns[0])
    # numeric, NaN→0
    df = df.apply(pd.to_numeric, errors="coerce").fillna(0.0)
    if df.shape[0] != df.shape[1]:
        raise ValueError(f"{xlsx_path.name}: matrix must be square; got {df.shape}.")
    arr = df.values.astype(float)
    arr = np.maximum(arr, arr.T)  # symmetrize
    np.fill_diagonal(arr, 0.0)
    return pd.DataFrame(arr, index=df.index, columns=df.columns)

# ---------- metrics ----------
def weighted_degree(A: pd.DataFrame) -> pd.Series:
    M = A.values.copy()
    np.fill_diagonal(M, 0.0)
    return pd.Series(M.sum(axis=1), index=A.index)

def spearman_rho(a: pd.Series, b: pd.Series) -> float:
    ra = a.rank(method="average", ascending=False)
    rb = b.rank(method="average", ascending=False)
    ra = (ra - ra.mean()) / (ra.std(ddof=0) if ra.std(ddof=0) != 0 else 1)
    rb = (rb - rb.mean()) / (rb.std(ddof=0) if rb.std(ddof=0) != 0 else 1)
    return float(np.corrcoef(ra, rb)[0, 1])

def top_k(series: pd.Series, k=10) -> pd.Index:
    # Deterministic: by value desc; ties broken by name asc
    return (series.sort_values(ascending=False)
                  .sort_index(kind="mergesort"))[:k].index

def jaccard_overlap(A: pd.Index, B: pd.Index) -> float:
    a, b = set(A), set(B)
    inter = len(a & b)
    union = len(a | b) if (a | b) else 1
    return inter / union

# ---------- transforms ----------
def to_binary(A: pd.DataFrame) -> pd.DataFrame:
    return (A > 0).astype(float)

def to_exp2(A: pd.DataFrame) -> pd.DataFrame:
    # w' = 2^(w-1) for w>0, else 0; handles fractional weights naturally
    M = A.values
    out = np.zeros_like(M, dtype=float)
    mask = M > 0
    out[mask] = np.power(2.0, M[mask] - 1.0)
    np.fill_diagonal(out, 0.0)
    return pd.DataFrame(out, index=A.index, columns=A.columns)

# ---------- per-file runner ----------
def run_one(xlsx_path: Path, sheet, outdir: Path, k: int) -> list[dict]:
    A = read_square_matrix(xlsx_path, sheet=sheet)
    deg_base = weighted_degree(A)

    results = []

    variants = [
        ("binary", to_binary(A)),
        ("exp2",   to_exp2(A)),
    ]

    for tag, Avar in variants:
        deg_var = weighted_degree(Avar)
        rho = spearman_rho(deg_base, deg_var)
        top_base = top_k(deg_base, k=k)
        top_var  = top_k(deg_var,  k=k)
        jac = jaccard_overlap(top_base, top_var)

        # Save matrices and summaries
        stem = xlsx_path.stem
        # matrix
        out_matrix = outdir / f"{stem}_{tag}.xlsx"
        try:
            Avar.to_excel(out_matrix, engine="xlsxwriter")
        except Exception:
            Avar.to_excel(out_matrix)
        # summary
        summary_rows = [
            {"Metric": "Spearman_rho_degree_ranks", "Value": rho},
            {"Metric": f"Top{k}_Jaccard", "Value": jac},
            {"Metric": "Top_base", "Value": ", ".join(map(str, top_base))},
            {"Metric": f"Top_{tag}", "Value": ", ".join(map(str, top_var))},
        ]
        pd.DataFrame(summary_rows).to_csv(outdir / f"{stem}_{tag}_summary.csv", index=False)
        # degrees
        pd.DataFrame({"deg_baseline": deg_base, f"deg_{tag}": deg_var}).to_csv(
            outdir / f"{stem}_degrees_baseline_vs_{tag}.csv"
        )

        results.append({
            "case": stem,
            "variant": tag,
            "spearman_rho": rho,
            f"top{k}_jaccard": jac
        })

        # Console
        print(f"[{stem}] {tag}: rho={rho:.3f}, Jaccard(top-{k})={jac:.3f}")

    return results

# ---------- CLI ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in_glob", required=True, help='Glob of input .xlsx files, e.g. "matrices/*.xlsx"')
    ap.add_argument("--sheet", default=0, help="Sheet name or index (default: 0)")
    ap.add_argument("--outdir", default="out", help="Directory for outputs")
    ap.add_argument("--k", type=int, default=10, help="Top-K hubs (default: 10)")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    files = sorted(glob.glob(args.in_glob))
    if not files:
        raise SystemExit(f"No files match: {args.in_glob}")

    all_rows = []
    for f in files:
        rows = run_one(Path(f), sheet=args.sheet, outdir=outdir, k=args.k)
        all_rows.extend(rows)

    # Master summary
    master = pd.DataFrame(all_rows)
    master_cols = ["case", "variant", "spearman_rho", f"top{args.k}_jaccard"]
    master = master[master_cols].sort_values(["case", "variant"])
    master.to_csv(outdir / "robustness_master_summary.csv", index=False)
    print(f"\nWrote master summary: {outdir / 'robustness_master_summary.csv'}")

if __name__ == "__main__":
    main()
