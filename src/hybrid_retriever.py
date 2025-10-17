"""
Hybrid Retriever - Multi-Strategy Search
Combines 3 complementary retrieval methods:
1. Semantic similarity (vector search)
2. Entity matching (exact entity overlap)
3. Recency bias (recent = more relevant)

This is HMT's approach to context selection.
"""

from typing import Dict, List, Tuple, Optional
from .memory_system import ThreeTierMemorySystem
import math

class HybridRetriever:
    """
    Retrieves relevant context using hybrid scoring
    
    Scoring formula:
    score = 0.4 * semantic_similarity + 
            0.3 * entity_overlap + 
            0.3 * recency_score
    """
    
    def __init__(self, memory_system: ThreeTierMemorySystem,
                 weights: Optional[Dict[str, float]] = None):
        """
        Args:
            memory_system: The three-tier memory system
            weights: Custom scoring weights (default: 0.4, 0.3, 0.3)
        """
        self.memory = memory_system
        
        # Default weights (from HMT paper)
        self.weights = weights or {
            'semantic': 0.4,
            'entity': 0.3,
            'recency': 0.3
        }
    
    def retrieve_context(self, clues: Dict, max_results: int = 5,
                        verbose: bool = False) -> List[Dict]:
        """
        Retrieve most relevant context using hybrid scoring
        
        Args:
            clues: Output from ClueGenerator
            max_results: Maximum number of turns to retrieve
            verbose: Print scoring details
            
        Returns:
            List of relevant turn data, sorted by relevance score
        """
        if verbose:
            print("\n=== HYBRID RETRIEVAL ===")
            print(f"Search clues: {clues['clues']}")
            print(f"Target entities: {clues['entities']}")
        
        # Get all searchable memories
        candidates = self._get_candidate_memories()
        
        if not candidates:
            if verbose:
                print("No memories to search")
            return []
        
        # Score each candidate
        scored_candidates = []
        for candidate in candidates:
            score = self._compute_hybrid_score(
                candidate, clues, verbose=verbose
            )
            scored_candidates.append((candidate, score))
        
        # Sort by score (highest first)
        scored_candidates.sort(key=lambda x: -x[1])
        
        # Return top results
        top_results = scored_candidates[:max_results]
        
        if verbose:
            print(f"\n=== TOP {max_results} RESULTS ===")
            for i, (candidate, score) in enumerate(top_results, 1):
                print(f"{i}. Turn {candidate['turn_number']}: {score:.3f}")
                print(f"   {candidate['summary'][:100]}...")
        
        return [candidate for candidate, score in top_results]
    
    def _get_candidate_memories(self) -> List[Dict]:
        """
        Get all searchable memories from the system
        
        Returns memories from:
        - Short-term (already compressed, recent)
        - Long-term (ultra-compressed, archived)
        
        Note: Sensory memory is always in context, no need to retrieve
        """
        candidates = []
        
        # Get from short-term memory
        for turn in self.memory.short_term.compressed_turns:
            candidates.append({
                'turn_number': turn['turn_number'],
                'summary': turn['compressed_summary'],
                'entities': turn.get('entities', []),
                'tokens': turn['compressed_tokens'],
                'source': 'short_term'
            })
        
        # Get from long-term memory
        for mem in self.memory.long_term.memories:
            candidates.append({
                'turn_number': mem['turn_number'],
                'summary': mem['ultra_summary'],
                'entities': mem.get('entities', []),
                'tokens': mem['tokens'],
                'source': 'long_term'
            })
        
        return candidates
    
    def _compute_hybrid_score(self, candidate: Dict, clues: Dict,
                              verbose: bool = False) -> float:
        """
        Compute hybrid relevance score
        
        Components:
        1. Semantic: How similar is the text?
        2. Entity: How many entities overlap?
        3. Recency: How recent is this turn?
        """
        # 1. Semantic similarity
        semantic_score = self._semantic_similarity(
            candidate['summary'], clues['clues']
        )
        
        # 2. Entity overlap
        entity_score = self._entity_overlap(
            candidate['entities'], clues['entities']
        )
        
        # 3. Recency score
        recency_score = self._recency_score(
            candidate['turn_number'], self.memory.current_turn
        )
        
        # Weighted combination
        total_score = (
            self.weights['semantic'] * semantic_score +
            self.weights['entity'] * entity_score +
            self.weights['recency'] * recency_score
        )
        
        if verbose:
            print(f"\nTurn {candidate['turn_number']}:")
            print(f"  Semantic: {semantic_score:.3f}")
            print(f"  Entity: {entity_score:.3f}")
            print(f"  Recency: {recency_score:.3f}")
            print(f"  Total: {total_score:.3f}")
        
        return total_score
    
    def _semantic_similarity(self, text1: str, text2: str) -> float:
        """
        Compute semantic similarity between two texts
        
        Simple implementation using word overlap (Jaccard similarity)
        In production, use embeddings (OpenAI, Sentence Transformers)
        """
        # Convert to lowercase word sets
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 
                     'to', 'for', 'of', 'with', 'by', 'from', 'as', 'is', 'was',
                     'are', 'were', 'been', 'be', 'have', 'has', 'had'}
        words1 -= stop_words
        words2 -= stop_words
        
        if not words1 or not words2:
            return 0.0
        
        # Jaccard similarity: intersection / union
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def _entity_overlap(self, entities1: List[str], entities2: List[str]) -> float:
        """
        Compute entity overlap score
        
        Returns 1.0 if all query entities are in the candidate,
        0.0 if no overlap, proportional otherwise
        """
        if not entities2:  # No entities in query
            return 0.5  # Neutral score
        
        # Convert to lowercase sets
        set1 = {e.lower() for e in entities1}
        set2 = {e.lower() for e in entities2}
        
        if not set1:  # No entities in candidate
            return 0.0
        
        # How many query entities are in the candidate?
        overlap = len(set1 & set2)
        
        # Score based on query entities found
        return overlap / len(set2)
    
    def _recency_score(self, turn_number: int, current_turn: int) -> float:
        """
        Compute recency score
        
        Recent turns score higher (exponential decay)
        
        Formula: e^(-distance / scale)
        Where distance = current_turn - turn_number
        """
        distance = current_turn - turn_number
        
        # Scale factor (adjust for steepness of decay)
        scale = 5.0  # Half-relevance after 5 turns
        
        # Exponential decay
        score = math.exp(-distance / scale)
        
        return score
    
    def search_by_entity_only(self, entity: str) -> List[Dict]:
        """
        Quick search for specific entity (shortcut)
        Uses the entity index for fast lookup
        """
        # Search long-term memory's entity index
        memories = self.memory.long_term.search_by_entity(entity)
        
        # Also check short-term
        for turn in self.memory.short_term.compressed_turns:
            if entity.lower() in [e.lower() for e in turn.get('entities', [])]:
                memories.append({
                    'turn_number': turn['turn_number'],
                    'summary': turn['compressed_summary'],
                    'entities': turn['entities'],
                    'source': 'short_term'
                })
        
        return memories


# Testing
if __name__ == "__main__":
    from memory_system import ThreeTierMemorySystem
    from llm_compressor import LLMCompressor
    
    # Mock setup
    class MockLLM:
        def chat(self, prompt):
            return "Compressed summary"
    
    mock_llm = MockLLM()
    compressor = LLMCompressor(mock_llm)
    memory = ThreeTierMemorySystem(compressor)
    
    # Add test data
    test_conversations = [
        ("What's Q1 revenue?", "Q1 was $4.5M", ["Q1", "revenue"]),
        ("What about Q2?", "Q2 reached $5.2M", ["Q2", "revenue"]),
        ("Top customers?", "Acme Corp and TechStart", ["Acme Corp", "TechStart"]),
        ("Churn rate?", "Churn is 3.2%", ["churn"]),
        ("Competitors?", "CompX and DataCo", ["CompX", "DataCo"]),
    ]
    
    for user, assistant, entities in test_conversations:
        memory.store_turn(user, assistant, entities=entities)
    
    # Test retrieval
    retriever = HybridRetriever(memory)
    
    # Simulate clues
    clues = {
        'clues': "User asking about Q2 revenue figure",
        'entities': ["Q2", "revenue"]
    }
    
    results = retriever.retrieve_context(clues, max_results=3, verbose=True)
    
    print("\n=== RETRIEVED CONTEXT ===")
    for result in results:
        print(f"Turn {result['turn_number']}: {result['summary']}")