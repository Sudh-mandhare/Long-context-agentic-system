"""
Clue Generator - The Intelligence Layer
Converts vague queries into specific retrieval targets

This is MemoRAG's key innovation:
Instead of searching with user's vague query,
generate a "draft answer" that reveals what's needed.
"""

from typing import Dict, List, Optional
from .memory_system import ThreeTierMemorySystem

class ClueGenerator:
    """
    Generates retrieval clues from user queries
    
    Example:
    User: "What about competitors?"
    Clue: "User wants competitor revenue comparison from Q3 analysis"
    
    The clue is much better for retrieval than the vague question!
    """
    
    def __init__(self, llm_client, memory_system: ThreeTierMemorySystem):
        """
        Args:
            llm_client: LLM for generating clues (can be cheaper model)
            memory_system: Access to conversation memory
        """
        self.llm = llm_client
        self.memory = memory_system
    
    def generate_clues(self, user_query: str, verbose: bool = False) -> Dict:
        """
        Generate retrieval clues from user query
        
        Args:
            user_query: The user's current question
            verbose: Print intermediate steps
            
        Returns:
            Dict with:
            - 'clues': String with retrieval clues
            - 'entities': List of entities to search for
            - 'reasoning': Why these clues were generated
        """
        # Get recent context from memory
        recent_context = self.memory.get_recent_context()
        
        # Get memory stats to understand conversation state
        stats = self.memory.get_memory_stats()
        
        # Build prompt for clue generation
        prompt = self._build_clue_prompt(user_query, recent_context, stats)
        
        if verbose:
            print("\n=== CLUE GENERATION ===")
            print(f"User Query: {user_query}")
            print(f"Context turns: {stats['current_turn']}")
        
        # Generate clues using LLM
        try:
            clue_response = self.llm.generate(prompt)
            
            # Parse the response
            parsed_clues = self._parse_clue_response(clue_response)
            
            if verbose:
                print(f"Generated Clues: {parsed_clues['clues']}")
                print(f"Target Entities: {parsed_clues['entities']}")
                print(f"Reasoning: {parsed_clues['reasoning']}")
            
            return parsed_clues
            
        except Exception as e:
            if verbose:
                print(f"Clue generation failed: {e}")
            
            # Fallback: Use query as-is with extracted entities
            return {
                'clues': user_query,
                'entities': self._extract_entities_simple(user_query),
                'reasoning': 'Fallback: using original query'
            }
    
    def _build_clue_prompt(self, user_query: str, recent_context: str, 
                           stats: Dict) -> str:
        """
        Build the prompt for clue generation
        
        This is where MemoRAG's magic happens:
        We ask the LLM to understand the query in context
        and identify what information is actually needed.
        """
        prompt = f"""You are a retrieval expert. Your job is to understand what information the user needs and generate search clues.

# Conversation History (Recent Context)
{recent_context}

# Conversation Stats
- Total turns: {stats['current_turn']}
- Active memory: {stats['total_active_tokens']} tokens
- Entities tracked: {stats['entities_tracked']}

# User's Current Query
"{user_query}"

# Your Task
Analyze the query in context and generate retrieval clues. Think about:
1. What information is the user actually asking for?
2. What entities (people, companies, metrics, dates) are involved?
3. Which past turn(s) likely contain this information?
4. What keywords would help find it?

# Output Format (JSON)
{{
    "clues": "A detailed description of what information is needed",
    "entities": ["entity1", "entity2", ...],
    "reasoning": "Why these clues will help find the answer",
    "likely_turns": [estimated turn numbers or "recent"]
}}

# Example 1
User Query: "What was that number?"
Output:
{{
    "clues": "User asking about Q3 revenue figure mentioned in recent discussion, specifically the $6M number",
    "entities": ["Q3", "revenue", "6M"],
    "reasoning": "Query is vague but context shows recent revenue discussion",
    "likely_turns": ["recent", 8, 9]
}}

# Example 2
User Query: "How do we compare?"
Output:
{{
    "clues": "User wants comparison of our revenue/performance vs competitors mentioned earlier",
    "entities": ["competitors", "revenue", "comparison"],
    "reasoning": "Implicit comparison question requires competitor data from earlier turns",
    "likely_turns": [5, 6, 7]
}}

Now generate clues for the current query.
"""
        return prompt
    
    def _parse_clue_response(self, response: str) -> Dict:
        """
        Parse LLM response into structured clues
        
        Expected format is JSON, but we handle free-form too
        """
        import json
        import re
        
        try:
            # Try parsing as JSON first
            if '{' in response and '}' in response:
                json_str = response[response.find('{'):response.rfind('}')+1]
                parsed = json.loads(json_str)
                
                return {
                    'clues': parsed.get('clues', response),
                    'entities': parsed.get('entities', []),
                    'reasoning': parsed.get('reasoning', ''),
                    'likely_turns': parsed.get('likely_turns', [])
                }
        except:
            pass
        
        # Fallback: Extract what we can
        entities = self._extract_entities_simple(response)
        
        return {
            'clues': response,
            'entities': entities,
            'reasoning': 'Extracted from free-form response',
            'likely_turns': []
        }
    
    def _extract_entities_simple(self, text: str) -> List[str]:
        """
        Simple entity extraction (fallback)
        
        Looks for:
        - Capitalized words (names, places)
        - Common business terms (revenue, customers, etc.)
        - Numbers with context (Q3, $5M)
        """
        import re
        
        entities = []
        
        # Extract capitalized words
        capitalized = re.findall(r'\b[A-Z][a-z]+\b', text)
        entities.extend(capitalized)
        
        # Extract common business terms
        business_terms = [
            'revenue', 'profit', 'customers', 'growth', 'churn',
            'pricing', 'competitors', 'market', 'sales', 'cost'
        ]
        for term in business_terms:
            if term in text.lower():
                entities.append(term)
        
        # Extract quarter references (Q1, Q2, Q3, Q4)
        quarters = re.findall(r'Q[1-4]', text, re.IGNORECASE)
        entities.extend([q.upper() for q in quarters])
        
        # Extract money amounts ($5M, $6M, etc.)
        money = re.findall(r'\$\d+\.?\d*[KMB]?', text, re.IGNORECASE)
        entities.extend(money)
        
        # Remove duplicates and return
        return list(set(entities))
    
    def generate_simple_clue(self, user_query: str) -> str:
        """
        Quick clue generation without full context
        Useful for testing or when memory is empty
        """
        entities = self._extract_entities_simple(user_query)
        
        if entities:
            return f"Search for information about: {', '.join(entities)}"
        else:
            return user_query


# Example usage and testing
if __name__ == "__main__":
    # Mock LLM for testing
    class MockLLM:
        def generate(self, prompt):
            # Simulate LLM response with JSON
            return '''
            {
                "clues": "User asking about Q3 revenue figure from earlier discussion",
                "entities": ["Q3", "revenue"],
                "reasoning": "Query references recent revenue discussion",
                "likely_turns": ["recent", 8]
            }
            '''
    
    # Test with mock memory
    from memory_system import ThreeTierMemorySystem
    from llm_compressor import LLMCompressor
    
    mock_llm = MockLLM()
    compressor = LLMCompressor(mock_llm)
    memory = ThreeTierMemorySystem(compressor)
    
    # Add some test data
    memory.store_turn(
        "What's our Q3 revenue?",
        "Q3 revenue was $6M, up 20% from Q2.",
        entities=["Q3", "revenue"]
    )
    
    # Test clue generation
    clue_gen = ClueGenerator(mock_llm, memory)
    clues = clue_gen.generate_clues("What was that number?", verbose=True)
    
    print("\n=== RESULTS ===")
    print(f"Clues: {clues['clues']}")
    print(f"Entities: {clues['entities']}")