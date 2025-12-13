

from pathlib import Path
from typing import List, Dict, Tuple
import pandas as pd
import numpy as np
from sklearn.metrics import adjusted_rand_score
from scipy.stats import spearmanr
import matplotlib.pyplot as plt
import seaborn as sns



def compute_pairwise_ari(runs_data: List[pd.DataFrame], cluster_column: str = 'class') -> np.ndarray:
    """
    Compute pairwise Adjusted Rand Index (ARI) for all runs.

    The ARI measures the similarity between two clusterings, adjusted for chance.
    Values range from -1 to 1, where 1 indicates perfect agreement.

    Parameters:
    -----------
    runs_data : List[pd.DataFrame]
        List of DataFrames with Id and cluster assignment columns
    cluster_column : str
        Name of the column containing cluster assignments (default: 'class')

    Returns:
    --------
    np.ndarray
        Square matrix of pairwise ARI values (num_runs x num_runs)

    Examples:
    ---------
    >>> ari_matrix = compute_pairwise_ari(runs_data)
    >>> print(f"Mean ARI: {np.mean(ari_matrix[np.triu_indices_from(ari_matrix, k=1)]):.3f}")
    >>> # For k-means results with 'cluster' column
    >>> ari_matrix = compute_pairwise_ari(runs_data, cluster_column='cluster')
    """
    num_runs = len(runs_data)
    ari_matrix = np.zeros((num_runs, num_runs))

    for i in range(num_runs):
        for j in range(num_runs):
            if i == j:
                ari_matrix[i, j] = 1.0  # Perfect agreement with itself
            else:
                # Ensure both dataframes are aligned by Id
                df_i = runs_data[i].sort_values('Id').reset_index(drop=True)
                df_j = runs_data[j].sort_values('Id').reset_index(drop=True)

                # Compute ARI
                ari = adjusted_rand_score(
                    df_i[cluster_column],
                    df_j[cluster_column]
                )
                ari_matrix[i, j] = ari

    return ari_matrix


def compute_spearman_consistency(runs_data: List[pd.DataFrame]) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute Spearman correlation matrix for modularity class assignment consistency.

    This measures how consistently nodes are assigned to modularity classes
    (treating class Ids as ordinal values) across runs.

    Parameters:
    -----------
    runs_data : List[pd.DataFrame]
        List of DataFrames with Id and modularity_class columns

    Returns:
    --------
    Tuple[np.ndarray, np.ndarray]
        - correlation_matrix: Square matrix of Spearman correlation coefficients
        - pvalue_matrix: Square matrix of p-values

    Examples:
    ---------
    >>> corr_matrix, pval_matrix = compute_spearman_consistency(runs_data)
    >>> print(f"Mean correlation: {np.mean(corr_matrix[np.triu_indices_from(corr_matrix, k=1)]):.3f}")
    """
    num_runs = len(runs_data)
    correlation_matrix = np.zeros((num_runs, num_runs))
    pvalue_matrix = np.zeros((num_runs, num_runs))

    for i in range(num_runs):
        for j in range(num_runs):
            if i == j:
                correlation_matrix[i, j] = 1.0
                pvalue_matrix[i, j] = 0.0
            else:
                # Ensure both dataframes are aligned by Id
                df_i = runs_data[i].sort_values('Id').reset_index(drop=True)
                df_j = runs_data[j].sort_values('Id').reset_index(drop=True)

                # Compute Spearman correlation
                corr, pval = spearmanr(
                    df_i['modularity_class'],
                    df_j['modularity_class']
                )
                correlation_matrix[i, j] = corr
                pvalue_matrix[i, j] = pval

    return correlation_matrix, pvalue_matrix


def generate_summary_statistics(ari_matrix: np.ndarray,
                                spearman_matrix: np.ndarray) -> Dict[str, float]:
    """
    Generate summary statistics for ARI and Spearman correlation matrices.

    Parameters:
    -----------
    ari_matrix : np.ndarray
        Pairwise ARI matrix
    spearman_matrix : np.ndarray
        Pairwise Spearman correlation matrix

    Returns:
    --------
    Dict[str, float]
        Dictionary containing summary statistics

    Examples:
    ---------
    >>> stats = generate_summary_statistics(ari_matrix, spearman_matrix)
    >>> print(f"ARI Mean: {stats['ari_mean']:.3f}, Std: {stats['ari_std']:.3f}")
    """
    # Extract upper triangle (excluding diagonal) for off-diagonal values
    upper_tri_indices = np.triu_indices_from(ari_matrix, k=1)

    ari_values = ari_matrix[upper_tri_indices]
    spearman_values = spearman_matrix[upper_tri_indices]

    stats = {
        'ari_mean': np.mean(ari_values),
        'ari_std': np.std(ari_values),
        'ari_min': np.min(ari_values),
        'ari_max': np.max(ari_values),
        'ari_median': np.median(ari_values),
        'spearman_mean': np.mean(spearman_values),
        'spearman_std': np.std(spearman_values),
        'spearman_min': np.min(spearman_values),
        'spearman_max': np.max(spearman_values),
        'spearman_median': np.median(spearman_values),
    }

    return stats


def plot_ari_heatmap(ari_matrix: np.ndarray, location_name: str,
                     figsize: Tuple[int, int] = (10, 8)) -> plt.Figure:
    """
    Create a heatmap visualization of the ARI matrix.

    Parameters:
    -----------
    ari_matrix : np.ndarray
        Pairwise ARI matrix
    location_name : str
        Name of the location for the title
    figsize : Tuple[int, int]
        Figure size (default: (10, 8))

    Returns:
    --------
    plt.Figure
        Matplotlib figure object

    Examples:
    ---------
    >>> fig = plot_ari_heatmap(ari_matrix, 'Babaeski')
    >>> plt.show()
    """
    fig, ax = plt.subplots(figsize=figsize)

    # Create heatmap
    sns.heatmap(ari_matrix, annot=True, fmt='.3f', cmap='RdYlGn',
                vmin=0, vmax=1, square=True, cbar_kws={'label': 'ARI'},
                ax=ax)

    ax.set_title(f'Pairwise Adjusted Rand Index (ARI) - {location_name}',
                 fontsize=14, fontweight='bold')
    ax.set_xlabel('Run Number', fontsize=12)
    ax.set_ylabel('Run Number', fontsize=12)

    # Set tick labels
    num_runs = ari_matrix.shape[0]
    tick_labels = [f'Run {i+1}' for i in range(num_runs)]
    ax.set_xticklabels(tick_labels, rotation=45, ha='right')
    ax.set_yticklabels(tick_labels, rotation=0)

    plt.tight_layout()
    return fig


def plot_ari_distribution(ari_matrix: np.ndarray, location_name: str,
                         figsize: Tuple[int, int] = (14, 5)) -> plt.Figure:
    """
    Create distribution plots (histogram and boxplot) for ARI values.

    Parameters:
    -----------
    ari_matrix : np.ndarray
        Pairwise ARI matrix
    location_name : str
        Name of the location for the title
    figsize : Tuple[int, int]
        Figure size (default: (14, 5))

    Returns:
    --------
    plt.Figure
        Matplotlib figure object

    Examples:
    ---------
    >>> fig = plot_ari_distribution(ari_matrix, 'Babaeski')
    >>> plt.show()
    """
    # Extract upper triangle (excluding diagonal)
    upper_tri_indices = np.triu_indices_from(ari_matrix, k=1)
    ari_values = ari_matrix[upper_tri_indices]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)

    # Histogram
    ax1.hist(ari_values, bins=20, edgecolor='black', alpha=0.7, color='skyblue')
    ax1.axvline(np.mean(ari_values), color='red', linestyle='--',
                linewidth=2, label=f'Mean: {np.mean(ari_values):.3f}')
    ax1.axvline(np.median(ari_values), color='green', linestyle='--',
                linewidth=2, label=f'Median: {np.median(ari_values):.3f}')
    ax1.set_xlabel('Adjusted Rand Index', fontsize=12)
    ax1.set_ylabel('Frequency', fontsize=12)
    ax1.set_title(f'ARI Distribution - {location_name}', fontsize=13, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Boxplot
    box = ax2.boxplot(ari_values, vert=True, patch_artist=True,
                      labels=['ARI Values'])
    box['boxes'][0].set_facecolor('lightblue')
    ax2.set_ylabel('Adjusted Rand Index', fontsize=12)
    ax2.set_title(f'ARI Boxplot - {location_name}', fontsize=13, fontweight='bold')
    ax2.grid(True, alpha=0.3, axis='y')

    # Add statistical annotations
    stats_text = f"Min: {np.min(ari_values):.3f}\nMax: {np.max(ari_values):.3f}\n"
    stats_text += f"Std: {np.std(ari_values):.3f}"
    ax2.text(1.15, 0.5, stats_text, transform=ax2.transAxes,
             fontsize=10, verticalalignment='center',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()
    return fig


def plot_correlation_heatmap(spearman_matrix: np.ndarray, location_name: str,
                            figsize: Tuple[int, int] = (10, 8)) -> plt.Figure:
    """
    Create a heatmap visualization of the Spearman correlation matrix.

    Parameters:
    -----------
    spearman_matrix : np.ndarray
        Pairwise Spearman correlation matrix
    location_name : str
        Name of the location for the title
    figsize : Tuple[int, int]
        Figure size (default: (10, 8))

    Returns:
    --------
    plt.Figure
        Matplotlib figure object

    Examples:
    ---------
    >>> fig = plot_correlation_heatmap(spearman_matrix, 'Lüneburg')
    >>> plt.show()
    """
    fig, ax = plt.subplots(figsize=figsize)

    # Create heatmap
    sns.heatmap(spearman_matrix, annot=True, fmt='.3f', cmap='coolwarm',
                vmin=-1, vmax=1, center=0, square=True,
                cbar_kws={'label': 'Spearman Correlation'},
                ax=ax)

    ax.set_title(f'Spearman Correlation - Modularity Class Consistency - {location_name}',
                 fontsize=14, fontweight='bold')
    ax.set_xlabel('Run Number', fontsize=12)
    ax.set_ylabel('Run Number', fontsize=12)

    # Set tick labels
    num_runs = spearman_matrix.shape[0]
    tick_labels = [f'Run {i+1}' for i in range(num_runs)]
    ax.set_xticklabels(tick_labels, rotation=45, ha='right')
    ax.set_yticklabels(tick_labels, rotation=0)

    plt.tight_layout()
    return fig


def create_summary_table(stats_dict: Dict[str, float], location_name: str) -> pd.DataFrame:
    """
    Create a formatted summary statistics table.

    Parameters:
    -----------
    stats_dict : Dict[str, float]
        Dictionary of summary statistics from generate_summary_statistics
    location_name : str
        Name of the location

    Returns:
    --------
    pd.DataFrame
        Formatted summary table

    Examples:
    ---------
    >>> stats = generate_summary_statistics(ari_matrix, spearman_matrix)
    >>> table = create_summary_table(stats, 'Babaeski')
    >>> print(table)
    """
    data = {
        'Metric': [
            'ARI Mean',
            'ARI Std Dev',
            'ARI Median',
            'ARI Min',
            'ARI Max',
            'Spearman Mean',
            'Spearman Std Dev',
            'Spearman Median',
            'Spearman Min',
            'Spearman Max'
        ],
        'Value': [
            stats_dict['ari_mean'],
            stats_dict['ari_std'],
            stats_dict['ari_median'],
            stats_dict['ari_min'],
            stats_dict['ari_max'],
            stats_dict['spearman_mean'],
            stats_dict['spearman_std'],
            stats_dict['spearman_median'],
            stats_dict['spearman_min'],
            stats_dict['spearman_max']
        ]
    }

    df = pd.DataFrame(data)
    df['Location'] = location_name
    df = df[['Location', 'Metric', 'Value']]

    return df
