"""
Three-Tier Memory System for Long Context Handling
Implements: Sensory → Short-Term → Long-Term memory hierarchy
"""

import tiktoken
from typing import Dict, List, Optional
from datetime import datetime
import json

class TokenCounter:
    """Utility for counting tokens"""
    def __init__(self, model="gpt-4"):
        self.encoder = tiktoken.encoding_for_model(model)
    
    def count(self, text: str) -> int:
        return len(self.encoder.encode(text))
    
    def truncate(self, text: str, max_tokens: int) -> str:
        tokens = self.encoder.encode(text)
        if len(tokens) <= max_tokens:
            return text
        return self.encoder.decode(tokens[:max_tokens])


class SensoryMemory:
    """
    Tier 1: Sensory Memory
    - Stores last 1-2 turns verbatim
    - No compression
    - Always included in context
    """
    def __init__(self, max_turns: int = 2):
        self.turns = []
        self.max_turns = max_turns
        self.token_counter = TokenCounter()
    
    def store(self, turn_data: Dict):
        """Store a new turn"""
        self.turns.append({
            'turn_number': turn_data['turn_number'],
            'user_message': turn_data['user_message'],
            'assistant_response': turn_data['assistant_response'],
            'tool_output': turn_data.get('tool_output', ''),
            'timestamp': datetime.now().isoformat(),
            'tokens': self.token_counter.count(
                f"{turn_data['user_message']} {turn_data['assistant_response']}"
            )
        })
        
        # Keep only last N turns
        if len(self.turns) > self.max_turns:
            return self.turns.pop(0)  # Return oldest for promotion
        return None
    
    def get_context(self) -> str:
        """Get all sensory memory as context string"""
        if not self.turns:
            return ""
        
        context_parts = []
        for turn in self.turns:
            context_parts.append(f"""
[Turn {turn['turn_number']} - Recent]
User: {turn['user_message']}
Assistant: {turn['assistant_response']}
""")
        return "\n".join(context_parts)
    
    def get_token_count(self) -> int:
        """Total tokens in sensory memory"""
        return sum(turn['tokens'] for turn in self.turns)
    
    def clear(self):
        """Clear all sensory memory"""
        self.turns = []


class ShortTermMemory:
    """
    Tier 2: Short-Term Memory
    - Stores last 3-5 turns compressed to ~50%
    - Maintains conversation theme
    - Progressively compressed
    """
    def __init__(self, max_turns: int = 5, compression_ratio: float = 0.5):
        self.compressed_turns = []
        self.max_turns = max_turns
        self.compression_ratio = compression_ratio
        self.token_counter = TokenCounter()
    
    def compress_and_store(self, turn_data: Dict, llm_compressor) -> Optional[Dict]:
        """
        Compress a turn and store it
        Returns: oldest turn if we need to promote to long-term
        """
        # Compress the turn
        compressed = self._compress_turn(turn_data, llm_compressor)
        
        self.compressed_turns.append({
            'turn_number': turn_data['turn_number'],
            'original_tokens': self.token_counter.count(
                f"{turn_data['user_message']} {turn_data['assistant_response']}"
            ),
            'compressed_summary': compressed,
            'compressed_tokens': self.token_counter.count(compressed),
            'entities': turn_data.get('entities', []),
            'timestamp': datetime.now().isoformat()
        })
        
        # Promote oldest if exceeded limit
        if len(self.compressed_turns) > self.max_turns:
            return self.compressed_turns.pop(0)
        return None
    
    def _compress_turn(self, turn_data: Dict, llm_compressor) -> str:
        """
        MemoRAG-style compression: 50% reduction
        Keeps main points, removes verbosity
        """
        prompt = f"""Summarize this conversation turn concisely, keeping all key facts:

User Query: {turn_data['user_message']}
Assistant Response: {turn_data['assistant_response']}
Tool Output: {turn_data.get('tool_output', 'None')[:500]}

Requirements:
- Preserve: entities, numbers, decisions, questions
- Remove: verbose explanations, filler words
- Target length: {int(self.token_counter.count(turn_data['user_message'] + turn_data['assistant_response']) * self.compression_ratio)} tokens

Format:
User asked: [concise question]
Response: [key points only]
Key info: [entities, numbers]
"""
        
        try:
            compressed = llm_compressor.generate(prompt)
            return compressed
        except Exception as e:
            # Fallback: simple truncation
            combined = f"User: {turn_data['user_message']}\nAssistant: {turn_data['assistant_response']}"
            target_tokens = int(self.token_counter.count(combined) * self.compression_ratio)
            return self.token_counter.truncate(combined, target_tokens)
    
    def get_context(self) -> str:
        """Get all short-term memory as context string"""
        if not self.compressed_turns:
            return ""
        
        context_parts = []
        for turn in self.compressed_turns:
            context_parts.append(f"""
[Turn {turn['turn_number']} - Compressed Summary]
{turn['compressed_summary']}
Entities: {', '.join(turn.get('entities', []))}
""")
        return "\n".join(context_parts)
    
    def get_token_count(self) -> int:
        """Total tokens in short-term memory"""
        return sum(turn['compressed_tokens'] for turn in self.compressed_turns)
    
    def get_all_turns(self) -> List[Dict]:
        """Get all compressed turns"""
        return self.compressed_turns.copy()


class LongTermMemory:
    """
    Tier 3: Long-Term Memory
    - Stores ALL past turns ultra-compressed (~5% original)
    - Searchable via vector embeddings
    - Retrieved on-demand
    """
    def __init__(self, max_memories: int = 300):
        self.memories = []  # In-memory storage (use ChromaDB in production)
        self.max_memories = max_memories
        self.token_counter = TokenCounter()
        self.entity_index = {}  # Entity → [memory_ids]
    
    def archive_turn(self, turn_data: Dict, llm_compressor) -> None:
        """
        Archive a turn with ultra-compression (95% reduction)
        """
        # Ultra-compress
        ultra_compressed = self._ultra_compress(turn_data, llm_compressor)
        
        memory_id = len(self.memories)
        
        memory_entry = {
            'id': memory_id,
            'turn_number': turn_data['turn_number'],
            'ultra_summary': ultra_compressed,
            'entities': turn_data.get('entities', []),
            'timestamp': turn_data.get('timestamp', datetime.now().isoformat()),
            'tokens': self.token_counter.count(ultra_compressed)
        }
        
        self.memories.append(memory_entry)
        
        # Update entity index
        for entity in turn_data.get('entities', []):
            if entity not in self.entity_index:
                self.entity_index[entity] = []
            self.entity_index[entity].append(memory_id)
        
        # Manage memory limit (FIFO)
        if len(self.memories) > self.max_memories:
            oldest = self.memories.pop(0)
            # Remove from entity index
            for entity in oldest.get('entities', []):
                if entity in self.entity_index:
                    self.entity_index[entity] = [
                        mid for mid in self.entity_index[entity] if mid != oldest['id']
                    ]
    
    def _ultra_compress(self, turn_data: Dict, llm_compressor) -> str:
        """
        MemoRAG-style ultra-compression: 95% reduction
        Extract only critical facts
        """
        # If already compressed (from short-term), compress further
        if 'compressed_summary' in turn_data:
            input_text = turn_data['compressed_summary']
        else:
            input_text = f"{turn_data['user_message']}\n{turn_data['assistant_response']}"
        
        prompt = f"""Extract ONLY the most critical facts as bullet points:

{input_text}

Format (be extremely concise):
- Asked: [1-2 words]
- Answer: [key fact only]
- Entities: [list]
- Numbers/Decisions: [if any]

Maximum 4 bullets, 100 tokens total.
"""
        
        try:
            ultra_compressed = llm_compressor.generate(prompt)
            return ultra_compressed
        except Exception as e:
            # Fallback: extreme truncation
            return self.token_counter.truncate(input_text, 100)
    
    def search_by_entity(self, entity: str) -> List[Dict]:
        """Find all memories mentioning an entity"""
        memory_ids = self.entity_index.get(entity, [])
        return [self.memories[mid] for mid in memory_ids if mid < len(self.memories)]
    
    def get_recent(self, n: int = 10) -> List[Dict]:
        """Get N most recent memories"""
        return self.memories[-n:] if len(self.memories) > n else self.memories.copy()
    
    def get_all(self) -> List[Dict]:
        """Get all memories"""
        return self.memories.copy()
    
    def get_token_count(self) -> int:
        """Total tokens in long-term memory"""
        return sum(mem['tokens'] for mem in self.memories)


class ThreeTierMemorySystem:
    """
    Orchestrates all three memory tiers
    Handles promotion between tiers
    """
    def __init__(self, llm_compressor):
        self.sensory = SensoryMemory(max_turns=2)
        self.short_term = ShortTermMemory(max_turns=5, compression_ratio=0.5)
        self.long_term = LongTermMemory(max_memories=300)
        self.llm_compressor = llm_compressor
        self.current_turn = 0
    
    def store_turn(self, user_message: str, assistant_response: str, 
                   tool_output: str = "", entities: List[str] = None) -> None:
        """
        Store a new conversation turn
        Automatically handles tier promotions
        """
        self.current_turn += 1
        
        turn_data = {
            'turn_number': self.current_turn,
            'user_message': user_message,
            'assistant_response': assistant_response,
            'tool_output': tool_output,
            'entities': entities or []
        }
        
        # Store in sensory memory
        promoted_from_sensory = self.sensory.store(turn_data)
        
        # If sensory is full, promote to short-term
        if promoted_from_sensory:
            promoted_from_shortterm = self.short_term.compress_and_store(
                promoted_from_sensory, 
                self.llm_compressor
            )
            
            # If short-term is full, promote to long-term
            if promoted_from_shortterm:
                self.long_term.archive_turn(
                    promoted_from_shortterm,
                    self.llm_compressor
                )
    
    def get_recent_context(self) -> str:
        """
        Get context from sensory + short-term memory
        This is always included in the prompt
        """
        sensory_context = self.sensory.get_context()
        shortterm_context = self.short_term.get_context()
        
        return f"""
# Recent Conversation Context

## Immediate Context (Verbatim)
{sensory_context}

## Short-Term Context (Compressed)
{shortterm_context}
"""
    
    def get_memory_stats(self) -> Dict:
        """Get statistics about memory usage"""
        return {
            'current_turn': self.current_turn,
            'sensory_turns': len(self.sensory.turns),
            'sensory_tokens': self.sensory.get_token_count(),
            'shortterm_turns': len(self.short_term.compressed_turns),
            'shortterm_tokens': self.short_term.get_token_count(),
            'longterm_memories': len(self.long_term.memories),
            'longterm_tokens': self.long_term.get_token_count(),
            'total_active_tokens': (
                self.sensory.get_token_count() + 
                self.short_term.get_token_count()
            ),
            'entities_tracked': len(self.long_term.entity_index)
        }
    
    def export_state(self, filepath: str) -> None:
        """Export memory state to file"""
        state = {
            'current_turn': self.current_turn,
            'sensory': self.sensory.turns,
            'short_term': self.short_term.compressed_turns,
            'long_term': self.long_term.memories,
            'entity_index': self.long_term.entity_index
        }
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)
    
    def load_state(self, filepath: str) -> None:
        """Load memory state from file"""
        with open(filepath, 'r') as f:
            state = json.load(f)
        
        self.current_turn = state['current_turn']
        self.sensory.turns = state['sensory']
        self.short_term.compressed_turns = state['short_term']
        self.long_term.memories = state['long_term']
        self.long_term.entity_index = state['entity_index']