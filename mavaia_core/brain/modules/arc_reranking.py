from __future__ import annotations
"""
ARC Reranking Module

Aggregates and reranks predictions from multiple transformations.
Uses frequency and beam search scores to select best predictions.

Based on "Combining Induction and Transduction for Abstract Reasoning" (arxiv:2411.02272)
"""

from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class ARCReranking:
    """Reranking system for ARC predictions"""
    
    def __init__(self, frequency_priority: bool = True):
        """
        Initialize reranking system.
        
        Args:
            frequency_priority: If True, frequency takes precedence over scores
        """
        self.frequency_priority = frequency_priority
    
    def _grid_to_hashable(self, grid: List[List[Any]]) -> str:
        """
        Convert grid to hashable representation for comparison.
        
        Args:
            grid: Grid to convert
            
        Returns:
            String representation suitable for hashing/comparison
        """
        # Convert to numpy array, then to tuple of tuples for hashing
        np_grid = np.array(grid)
        return str(np_grid.tolist())
    
    def _grids_equal(self, grid1: List[List[Any]], grid2: List[List[Any]]) -> bool:
        """
        Check if two grids are equal.
        
        Args:
            grid1: First grid
            grid2: Second grid
            
        Returns:
            True if grids are equal
        """
        try:
            np1 = np.array(grid1)
            np2 = np.array(grid2)
            return np.array_equal(np1, np2)
        except Exception:
            # Fallback to string comparison
            return self._grid_to_hashable(grid1) == self._grid_to_hashable(grid2)
    
    def compute_frequency_scores(
        self, 
        candidates: List[List[List[Any]]]
    ) -> Dict[str, Tuple[List[List[Any]], int]]:
        """
        Compute frequency of each unique candidate.
        
        Args:
            candidates: List of candidate grids
            
        Returns:
            Dictionary mapping hashable grid -> (grid, frequency)
        """
        frequency_map = {}
        
        for candidate in candidates:
            grid_hash = self._grid_to_hashable(candidate)
            
            if grid_hash not in frequency_map:
                frequency_map[grid_hash] = (candidate, 0)
            
            # Increment frequency
            grid, freq = frequency_map[grid_hash]
            frequency_map[grid_hash] = (grid, freq + 1)
        
        return frequency_map
    
    def compute_average_scores(
        self,
        candidates: List[List[List[Any]]],
        scores: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Compute average scores for each unique candidate.
        
        Args:
            candidates: List of candidate grids
            scores: Dictionary mapping candidate indices or hashes to scores
            
        Returns:
            Dictionary mapping grid hash -> average score
        """
        # Group scores by grid
        grid_scores = {}
        
        for idx, candidate in enumerate(candidates):
            grid_hash = self._grid_to_hashable(candidate)
            
            # Get score for this candidate
            score_key = str(idx) if str(idx) in scores else grid_hash
            score = scores.get(score_key, scores.get(grid_hash, 0.0))
            
            if grid_hash not in grid_scores:
                grid_scores[grid_hash] = []
            
            grid_scores[grid_hash].append(score)
        
        # Compute averages
        avg_scores = {}
        for grid_hash, score_list in grid_scores.items():
            avg_scores[grid_hash] = sum(score_list) / len(score_list) if score_list else 0.0
        
        return avg_scores
    
    def rerank(
        self,
        candidates: List[List[List[Any]]],
        scores: Optional[Dict[str, float]] = None,
        frequency_priority: Optional[bool] = None
    ) -> List[Tuple[List[List[Any]], float]]:
        """
        Rerank candidates by frequency and average score.
        
        Args:
            candidates: List of candidate grids
            scores: Optional dictionary mapping candidates to scores
            frequency_priority: Override frequency priority setting
            
        Returns:
            Sorted list of (candidate, combined_score) tuples, highest score first
        """
        if not candidates:
            return []
        
        if frequency_priority is None:
            frequency_priority = self.frequency_priority
        
        # Compute frequencies
        frequency_map = self.compute_frequency_scores(candidates)
        
        # Compute average scores if provided
        avg_scores = {}
        if scores is not None:
            avg_scores = self.compute_average_scores(candidates, scores)
        
        # Combine frequency and scores
        combined_scores = []
        
        for grid_hash, (grid, freq) in frequency_map.items():
            avg_score = avg_scores.get(grid_hash, 0.0)
            
            if frequency_priority:
                # Frequency takes precedence: use frequency * 1000 + avg_score
                # This ensures higher frequency always wins even with lower score
                combined_score = freq * 1000.0 + avg_score
            else:
                # Average score takes precedence: use avg_score * 1000 + freq
                combined_score = avg_score * 1000.0 + freq
            
            combined_scores.append((grid, combined_score, freq, avg_score))
        
        # Sort by combined score (descending)
        combined_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Return (grid, combined_score) tuples
        return [(grid, score) for grid, score, _, _ in combined_scores]
    
    def aggregate_across_transformations(
        self,
        transformation_results: Dict[str, List[Tuple[List[List[Any]], float]]]
    ) -> List[Tuple[List[List[Any]], float]]:
        """
        Aggregate results from multiple transformations.
        
        Args:
            transformation_results: Dictionary mapping transformation name -> 
                list of (candidate, score) tuples from that transformation
            
        Returns:
            Aggregated and reranked list of (candidate, score) tuples
        """
        # Collect all candidates from all transformations
        all_candidates = []
        all_scores = {}
        
        for transform_name, results in transformation_results.items():
            for idx, (candidate, score) in enumerate(results):
                all_candidates.append(candidate)
                # Use transform name + index as score key
                score_key = f"{transform_name}_{idx}"
                all_scores[score_key] = score
        
        # Rerank all candidates together
        return self.rerank(all_candidates, all_scores)
    
    def get_top_k(
        self,
        ranked_candidates: List[Tuple[List[List[Any]], float]],
        k: int = 1
    ) -> List[List[List[Any]]]:
        """
        Get top k candidates from ranked list.
        
        Args:
            ranked_candidates: List of (candidate, score) tuples sorted by score
            k: Number of top candidates to return
            
        Returns:
            List of top k candidate grids
        """
        return [candidate for candidate, _ in ranked_candidates[:k]]
    
    def get_top_with_confidence(
        self,
        ranked_candidates: List[Tuple[List[List[Any]], float]],
        min_confidence: float = 0.0
    ) -> List[Tuple[List[List[Any]], float]]:
        """
        Get candidates above minimum confidence threshold.
        
        Args:
            ranked_candidates: List of (candidate, score) tuples
            min_confidence: Minimum confidence score threshold
            
        Returns:
            List of (candidate, score) tuples above threshold
        """
        return [(cand, score) for cand, score in ranked_candidates if score >= min_confidence]

