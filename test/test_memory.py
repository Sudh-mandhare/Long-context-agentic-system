"""
Test the three-tier memory system
"""

from memory_system import ThreeTierMemorySystem, TokenCounter
from llm_compressor import LLMCompressor

# Mock LLM for testing (replace with real Lyzr ChatBot)
class MockLLM:
    def chat(self, prompt):
        # Simple mock compression: take first 50% of words
        if "ultra" in prompt.lower():
            # Ultra compression: extract key facts
            return "• Asked about revenue\n• Answer: $5M Q3\n• Entities: company, Q3\n• Decision: approved"
        else:
            # Normal compression
            lines = prompt.split('\n')
            return ' '.join(lines[:len(lines)//2])

def test_memory_system():
    """Test the three-tier memory system"""
    
    # Initialize
    mock_llm = MockLLM()
    compressor = LLMCompressor(mock_llm)
    memory = ThreeTierMemorySystem(compressor)
    token_counter = TokenCounter()
    
    print("=" * 60)
    print("Testing Three-Tier Memory System")
    print("=" * 60)
    
    # Simulate 10 conversation turns
    conversations = [
        ("What's our Q1 revenue?", "Q1 revenue was $4.5M, up 10% from last year.", ["Q1", "revenue"]),
        ("How about Q2?", "Q2 revenue reached $5.2M, showing 15% growth.", ["Q2", "revenue"]),
        ("Tell me about our top customers", "Our top customers include Acme Corp ($1M) and TechStart ($800K).", ["Acme Corp", "TechStart"]),
        ("What's the churn rate?", "Current churn rate is 3.2%, down from 4.5% last quarter.", ["churn rate"]),
        ("Analyze competitor pricing", "Competitors price 20% higher on average. We have a cost advantage.", ["competitors", "pricing"]),
        ("What about Q3 projections?", "Q3 projected at $6M based on current pipeline.", ["Q3", "projections"]),
        ("Who are our main competitors?", "Main competitors are CompX, DataCo, and CloudTech.", ["CompX", "DataCo", "CloudTech"]),
        ("What was Q2 revenue again?", "As mentioned earlier, Q2 revenue was $5.2M.", ["Q2", "revenue"]),
        ("Compare Q1 and Q2", "Q2 ($5.2M) was 15.5% higher than Q1 ($4.5M).", ["Q1", "Q2", "comparison"]),
        ("What's our pricing strategy?", "We use value-based pricing, 15-20% below competitors.", ["pricing", "strategy"]),
    ]
    
    # Process each turn
    for i, (user_msg, assistant_msg, entities) in enumerate(conversations, 1):
        print(f"\n--- Turn {i} ---")
        print(f"User: {user_msg}")
        print(f"Assistant: {assistant_msg}")
        
        memory.store_turn(
            user_message=user_msg,
            assistant_response=assistant_msg,
            entities=entities
        )
        
        # Show memory stats
        stats = memory.get_memory_stats()
        print(f"\nMemory Stats:")
        print(f"  Sensory: {stats['sensory_turns']} turns, {stats['sensory_tokens']} tokens")
        print(f"  Short-term: {stats['shortterm_turns']} turns, {stats['shortterm_tokens']} tokens")
        print(f"  Long-term: {stats['longterm_memories']} memories, {stats['longterm_tokens']} tokens")
        print(f"  Total Active: {stats['total_active_tokens']} tokens")
        print(f"  Entities: {stats['entities_tracked']} unique")
    
    # Test context retrieval
    print("\n" + "=" * 60)
    print("Testing Context Retrieval")
    print("=" * 60)
    
    context = memory.get_recent_context()
    print("\nRecent Context (would be sent to LLM):")
    print(context)
    print(f"\nContext token count: {token_counter.count(context)}")
    
    # Test entity search
    print("\n" + "=" * 60)
    print("Testing Entity Search")
    print("=" * 60)
    
    revenue_memories = memory.long_term.search_by_entity("revenue")
    print(f"\nMemories mentioning 'revenue': {len(revenue_memories)}")
    for mem in revenue_memories[:3]:
        print(f"\nTurn {mem['turn_number']}:")
        print(mem['ultra_summary'])
    
    # Export state
    print("\n" + "=" * 60)
    print("Exporting Memory State")
    print("=" * 60)
    
    memory.export_state("memory_state.json")
    print("✓ Memory state exported to memory_state.json")
    
    # Final summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    final_stats = memory.get_memory_stats()
    print(f"""
Successfully processed {final_stats['current_turn']} turns!

Memory Distribution:
- Sensory (verbatim): {final_stats['sensory_tokens']} tokens
- Short-term (50% compressed): {final_stats['shortterm_tokens']} tokens  
- Long-term (95% compressed): {final_stats['longterm_tokens']} tokens
- Total active in context: {final_stats['total_active_tokens']} tokens

Compression Achievement:
- Original estimate: ~{final_stats['current_turn'] * 200} tokens (if kept all verbatim)
- Actual usage: {final_stats['total_active_tokens']} tokens
- Savings: {((1 - final_stats['total_active_tokens']/(final_stats['current_turn']*200)) * 100):.1f}%

Entity tracking: {final_stats['entities_tracked']} unique entities indexed
""")

if __name__ == "__main__":
    test_memory_system()