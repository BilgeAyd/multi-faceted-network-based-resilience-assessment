"""
Network analysis utilities for robustness analyses.

This module provides reusable functions for calculating network metrics
from survey data, enabling perturbation analyses (jackknife, bootstrap).
"""

import pandas as pd
import numpy as np
import networkx as nx
from typing import List, Optional, Tuple, Dict
from itertools import combinations
from scipy.stats import spearmanr


def clean_label_for_matching(text: str) -> str:
    """
    Clean text for matching by removing quotes, dots, and extra whitespace.

    Args:
        text: Text to clean

    Returns:
        Cleaned text in lowercase
    """
    if pd.isna(text):
        return ""

    text = str(text).lower().strip()
    # Remove quotation marks and full stops from start and end
    text = text.strip('"\'.,')

    return text


def calculate_question_averages(df_answers: pd.DataFrame, participant_ids: Optional[List[int]] = None) -> pd.DataFrame:
    """
    Calculate average score for each question.

    Args:
        df_answers: DataFrame with participantId, questionId, score
        participant_ids: Optional list of participant IDs to include (None = all)

    Returns:
        DataFrame with questionId, avg_score, std_score, n_responses
    """
    if participant_ids is not None:
        df_subset = df_answers[df_answers['participantId'].isin(participant_ids)]
    else:
        df_subset = df_answers

    avg_scores = df_subset.groupby('questionId').agg({
        'score': ['mean', 'std', 'count']
    }).reset_index()

    avg_scores.columns = ['questionId', 'avg_score', 'std_score', 'n_responses']

    # Round scores to 2 decimals
    avg_scores['avg_score'] = avg_scores['avg_score'].round(2)
    avg_scores['std_score'] = avg_scores['std_score'].round(2)

    return avg_scores


def match_edges_to_questions(df_edges: pd.DataFrame, df_questions: pd.DataFrame) -> pd.DataFrame:
    """
    Match edges to question IDs by cleaning and matching node labels.

    Args:
        df_edges: DataFrame with Source and Target columns (node labels)
        df_questions: DataFrame with questionId and node_label columns

    Returns:
        DataFrame with columns: source_qid, target_qid, source_label, target_label, original_weight
    """
    # Create a copy to avoid modifying originals
    df_edges_clean = df_edges.copy()

    # Clean edge labels
    df_edges_clean['source_clean'] = df_edges_clean['Source'].apply(clean_label_for_matching)
    df_edges_clean['target_clean'] = df_edges_clean['Target'].apply(clean_label_for_matching)

    # Create question label lookup
    questions_lookup = {}
    for _, row in df_questions.iterrows():
        clean_label = clean_label_for_matching(row['node_label'])
        questions_lookup[clean_label] = row['questionId']

    # Match edges to question IDs
    matched_edges = []
    unmatched_count = 0

    for _, edge in df_edges_clean.iterrows():
        source_qid = questions_lookup.get(edge['source_clean'])
        target_qid = questions_lookup.get(edge['target_clean'])

        if source_qid is not None and target_qid is not None:
            matched_edges.append({
                'source_qid': source_qid,
                'target_qid': target_qid,
                'source_label': edge['Source'],
                'target_label': edge['Target'],
                'original_weight': edge.get('Weight', np.nan)
            })
        else:
            unmatched_count += 1

    if unmatched_count > 0:
        print(f"Warning: {unmatched_count} edges could not be matched to questions")

    return pd.DataFrame(matched_edges)


def build_network_and_calculate_metrics(
    df_answers: pd.DataFrame,
    df_questions: pd.DataFrame,
    df_edges: pd.DataFrame,
    score_cutoff: int = None
) -> pd.DataFrame:
    """
    Build network from answers and calculate weighted degree for all nodes.

    This is the core function for network analysis. It:
    1. Calculates average scores from answers
    2. Matches edges to questions
    3. Recalculates edge weights based on node avg_scores
    4. Builds NetworkX graph
    5. Calculates weighted degree for all nodes

    Args:
        df_answers: DataFrame with participantId, questionId, score
        df_questions: DataFrame with questionId, node_label, and node_type columns
        df_edges: DataFrame with Source, Target, and Weight columns

    Returns:
        Enriched df_questions with added columns: avg_score, std_score, weighted_degree
    """
    # Step 1: Calculate average scores
    avg_scores = calculate_question_averages(df_answers)

    # Step 2: Merge avg_scores into questions (create a copy)
    df_questions_enriched = df_questions.copy()
    df_questions_enriched = df_questions_enriched.merge(
        avg_scores[['questionId', 'avg_score', 'std_score']],
        on='questionId',
        how='left'
    )

    # Step 3: Match edges to questions
    df_edges_matched = match_edges_to_questions(df_edges, df_questions_enriched)

    if len(df_edges_matched) == 0:
        print("Warning: No edges matched. Returning questions with 0 weighted degree.")
        df_questions_enriched['weighted_degree'] = 0.0
        return df_questions_enriched

    # Step 4: Recalculate edge weights based on avg_scores
    # Create lookup for avg_scores
    score_lookup = dict(zip(df_questions_enriched['questionId'], df_questions_enriched['avg_score']))

    edges_with_weights = []
    for _, edge in df_edges_matched.iterrows():
        source_avg = score_lookup.get(edge['source_qid'], 0)
        target_avg = score_lookup.get(edge['target_qid'], 0)
        # print(f"Source: {edge['source_qid']} Avg: {source_avg}, Target: {edge['target_qid']} Avg: {target_avg}")
        #print(f"Edge: {edge['source_qid']} - {edge['target_qid']}, Source Avg: {source_avg}, Target Avg: {target_avg}")

        # Recalculate weight as average of source and target avg_scores
        weight = (source_avg + target_avg) / 2
        if score_cutoff != None and (source_avg < score_cutoff or target_avg < score_cutoff):
           #print(f"Edge weight below 2.5 for edge {edge['source_qid']} - {edge['target_qid']}: {weight}")
           weight = 0.0

        
        weight = round(weight, 2)

        edges_with_weights.append({
            'source_qid': edge['source_qid'],
            'target_qid': edge['target_qid'],
            'weight': weight
        })

    df_edges_weighted = pd.DataFrame(edges_with_weights)

    # Step 5: Build NetworkX graph
    G = nx.Graph()

    # Add all questions as nodes
    for _, row in df_questions_enriched.iterrows():
        G.add_node(
            row['questionId'],
            label=row['node_label'],
            avg_score=row['avg_score'],
            node_type=row.get('node_type', '')
        )

    # Add edges with weights
    for _, edge in df_edges_weighted.iterrows():
        G.add_edge(
            edge['source_qid'],
            edge['target_qid'],
            weight=edge['weight']
        )

    # Step 6: Calculate weighted degree for all nodes
    weighted_degrees = {}
    for node in G.nodes():
        # Sum of weights of all edges connected to this node
        degree = 0
        for neighbor in G.neighbors(node):
            edge_weight = G[node][neighbor]['weight']
            degree += edge_weight
        weighted_degrees[node] = round(degree, 2)

    # Add weighted degree to questions dataframe
    df_questions_enriched['weighted_degree'] = df_questions_enriched['questionId'].map(weighted_degrees)
    df_questions_enriched['weighted_degree'] = df_questions_enriched['weighted_degree'].fillna(0.0)

    return df_questions_enriched


def rank_solutions(df_questions_enriched: pd.DataFrame) -> pd.DataFrame:
    """
    Filter and rank solutions by weighted degree.

    Args:
        df_questions_enriched: DataFrame with node_type and weighted_degree columns

    Returns:
        DataFrame with only Solutions, sorted by weighted_degree (descending), with rank column
    """
    # Filter for Solutions only
    df_solutions = df_questions_enriched[
        df_questions_enriched['node_type'] == 'Solutions'
    ].copy()

    # Sort by weighted degree (descending)
    df_solutions = df_solutions.sort_values('weighted_degree', ascending=False)

    # Add rank column
    df_solutions['rank'] = range(1, len(df_solutions) + 1)

    # Reset index
    df_solutions = df_solutions.reset_index(drop=True)

    return df_solutions


def generate_jackknife_exclusions(participant_ids: List[int], exclusion_count: int) -> List[Tuple[int, ...]]:
    """
    Generate all possible combinations of participants to exclude for jackknife analysis.

    Uses combinatorics to generate exclusion sets:
    - exclusion_count=1 with 20 participants: C(20,1) = 20 combinations
    - exclusion_count=2 with 20 participants: C(20,2) = 190 combinations

    Args:
        participant_ids: List of all participant IDs
        exclusion_count: Number of participants to exclude in each combination

    Returns:
        List of tuples, where each tuple contains participant IDs to exclude

    Example:
        >>> generate_jackknife_exclusions([1, 2, 3], 1)
        [(1,), (2,), (3,)]
        >>> generate_jackknife_exclusions([1, 2, 3], 2)
        [(1, 2), (1, 3), (2, 3)]
    """
    if exclusion_count > len(participant_ids):
        raise ValueError(f"exclusion_count ({exclusion_count}) cannot exceed number of participants ({len(participant_ids)})")

    if exclusion_count < 1:
        raise ValueError(f"exclusion_count must be at least 1, got {exclusion_count}")

    return list(combinations(participant_ids, exclusion_count))


def jaccard_similarity_top_n(
    baseline_df: pd.DataFrame,
    perturbed_df: pd.DataFrame,
    n: int,
    id_column: str = 'questionId',
    rank_column: str = 'rank'
) -> float:
    """
    Calculate Jaccard similarity for top N ranked items.

    Jaccard similarity = |A ∩ B| / |A ∪ B|
    where A and B are sets of top N item IDs from baseline and perturbed rankings.

    Args:
        baseline_df: Baseline rankings DataFrame
        perturbed_df: Perturbed rankings DataFrame
        n: Number of top items to compare
        id_column: Column name containing item identifiers
        rank_column: Column name containing ranks

    Returns:
        Jaccard similarity score (0.0 to 1.0)
    """
    # Get top N items from baseline
    top_n_baseline = set(
        baseline_df.nsmallest(n, rank_column)[id_column].values
    )

    # Get top N items from perturbed
    top_n_perturbed = set(
        perturbed_df.nsmallest(n, rank_column)[id_column].values
    )

    # Calculate Jaccard similarity
    intersection = len(top_n_baseline & top_n_perturbed)
    union = len(top_n_baseline | top_n_perturbed)

    if union == 0:
        return 0.0

    return intersection / union


def spearman_correlation_ranks(
    baseline_df: pd.DataFrame,
    perturbed_df: pd.DataFrame,
    id_column: str = 'questionId',
    rank_column: str = 'rank'
) -> float:
    """
    Calculate Spearman rank correlation between baseline and perturbed rankings.

    Args:
        baseline_df: Baseline rankings DataFrame
        perturbed_df: Perturbed rankings DataFrame
        id_column: Column name containing item identifiers
        rank_column: Column name containing ranks

    Returns:
        Spearman correlation coefficient (-1.0 to 1.0)
    """
    # Merge the two dataframes on id_column
    merged = baseline_df[[id_column, rank_column]].merge(
        perturbed_df[[id_column, rank_column]],
        on=id_column,
        suffixes=('_baseline', '_perturbed')
    )

    # Calculate Spearman correlation
    if len(merged) < 2:
        return np.nan

    correlation, _ = spearmanr(
        merged[f'{rank_column}_baseline'],
        merged[f'{rank_column}_perturbed']
    )

    return correlation


def compare_rankings(
    baseline_df: pd.DataFrame,
    perturbed_df: pd.DataFrame,
    top_n_values: List[int] = [3, 5],
    id_column: str = 'questionId',
    rank_column: str = 'rank'
) -> Dict[str, float]:
    """
    Comprehensive comparison of baseline and perturbed rankings.

    Calculates multiple similarity metrics:
    - Jaccard similarity for top N items (for each N in top_n_values)
    - Spearman rank correlation

    Args:
        baseline_df: Baseline rankings DataFrame
        perturbed_df: Perturbed rankings DataFrame
        top_n_values: List of N values for top-N Jaccard similarity
        id_column: Column name containing item identifiers
        rank_column: Column name containing ranks

    Returns:
        Dictionary with keys like 'jaccard_top_3', 'jaccard_top_5', 'spearman'
    """
    results = {}

    # Calculate Jaccard similarity for each top-N value
    for n in top_n_values:
        jaccard = jaccard_similarity_top_n(
            baseline_df, perturbed_df, n, id_column, rank_column
        )
        results[f'jaccard_top_{n}'] = jaccard

    # Calculate Spearman correlation
    spearman = spearman_correlation_ranks(
        baseline_df, perturbed_df, id_column, rank_column
    )
    results['spearman'] = spearman

    return results
