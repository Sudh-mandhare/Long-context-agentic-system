"""
Context Assembler - Packages Everything for LLM
Takes retrieved context + recent memory and formats for the LLM
"""

from typing import List, Dict
from .memory_system import ThreeTierMemorySystem

class ContextAssembler:
    """
    Assembles complete context for LLM prompt
    
    Includes:
    1. Recent context (sensory + short-term)
    2. Retrieved context (from hybrid retriever)
    3. User query
    """
    
    def __init__(self, memory_system: ThreeTierMemorySystem):
        self.memory = memory_system
    
    def assemble_full_context(self, user_query: str, 
                              retrieved_context: List[Dict],
                              include_stats: bool = False) -> str:
        """
        Assemble complete context for LLM
        
        Args:
            user_query: Current user question
            retrieved_context: Context from hybrid retriever
            include_stats: Include memory statistics (for debugging)
            
        Returns:
            Formatted context string ready for LLM
        """
        parts = []
        
        # Part 1: System instruction
        parts.append(self._get_system_instruction())
        
        # Part 2: Recent context (always included)
        recent = self.memory.get_recent_context()
        if recent.strip():
            parts.append("# Recent Conversation")
            parts.append(recent)
        
        # Part 3: Retrieved relevant context
        if retrieved_context:
            parts.append("\n# Relevant Past Context")
            parts.append(self._format_retrieved_context(retrieved_context))
        
        # Part 4: Memory stats (optional, for debugging)
        if include_stats:
            stats = self.memory.get_memory_stats()
            parts.append(f"\n# Memory Stats")
            parts.append(f"Total conversation turns: {stats['current_turn']}")
            parts.append(f"Active context tokens: {stats['total_active_tokens']}")
        
        # Part 5: Current query
        parts.append("\n# Current User Query")
        parts.append(f'User: "{user_query}"')
        parts.append("\nGenerate a helpful, accurate response using the provided context.")
        
        return "\n".join(parts)
    
    def _get_system_instruction(self) -> str:
        """System instruction for the LLM"""
        return """# System Instructions
You are a helpful AI assistant with excellent memory. You have access to the full conversation history through:
- Recent context (last few turns, verbatim)
- Past context (relevant earlier turns, compressed)

When answering:
1. Reference specific turns when appropriate (e.g., "As mentioned in Turn 5...")
2. Synthesize information from multiple turns if needed
3. If information isn't in the context, say so clearly
4. Be concise but comprehensive
"""
    
    def _format_retrieved_context(self, retrieved: List[Dict]) -> str:
        """Format retrieved context nicely"""
        if not retrieved:
            return "(No relevant past context found)"
        
        formatted = []
        for item in retrieved:
            formatted.append(f"\n[Turn {item['turn_number']} - Retrieved from {item['source']}]")
            formatted.append(item['summary'])
        
        return "\n".join(formatted)
    
    def get_context_stats(self, assembled_context: str) -> Dict:
        """Get statistics about assembled context"""
        from memory_system import TokenCounter
        counter = TokenCounter()
        
        return {
            'total_tokens': counter.count(assembled_context),
            'total_characters': len(assembled_context),
            'total_lines': assembled_context.count('\n') + 1
        }