"""
Complete example showing the system in action
with a realistic multi-turn conversation
"""

from lyzr_one.day_2.context_aware_bot import ContextAwareBot

def run_financial_analysis_conversation():
    """
    Example: Financial analysis conversation
    Tests the system's ability to handle complex, multi-turn discussions
    """
    
    # Mock LLMs (replace with real Lyzr in production)
    class SmartMockLLM:
        """More intelligent mock that actually processes the context"""
        def __init__(self, role="main"):
            self.role = role
            self.knowledge = {
                'Q1': '$4.5M revenue, 10% growth',
                'Q2': '$5M revenue, 11% growth from Q1', 
                'Q3': '$6M revenue, 20% growth from Q2',
                'customers': 'Acme Corp ($1M), TechStart ($800K)',
                'competitors': 'CompX ($5.5M), DataCo ($5M)',
                'churn': '3.2%, down from 4.5%'
            }
        
        def generate(self, prompt):
            return self._smart_response(prompt)
        
        def chat(self, prompt):
            return self.generate(prompt)
        
        def _smart_response(self, prompt):
            prompt_lower = prompt.lower()
            
            # Check what's being asked
            for key, info in self.knowledge.items():
                if key in prompt_lower:
                    return f"Based on our records, {info}."
            
            # Default response
            if 'compress' in prompt_lower or self.role == 'compressor':
                # Extract first meaningful line
                lines = [l.strip() for l in prompt.split('\n') if l.strip()]
                return lines[0][:100] if lines else "Summary"
            
            return "I don't have that information in the provided context."
    
    # Initialize bot
    print("="*60)
    print("FINANCIAL ANALYSIS CONVERSATION")
    print("="*60)
    
    bot = ContextAwareBot(
        main_llm=SmartMockLLM("main"),
        compressor_llm=SmartMockLLM("compressor"),
        clue_llm=SmartMockLLM("clue")
    )
    bot.verbose = True  # Show all steps
    
    # Conversation turns
    conversations = [
        ("What was our Q1 revenue?", ["Q1", "revenue"]),
        ("How about Q2?", ["Q2", "revenue"]),
        ("Tell me about Q3 performance", ["Q3", "revenue", "performance"]),
        ("Who are our top customers?", ["customers"]),
        ("What's our churn rate?", ["churn", "rate"]),
        ("How do we compare to competitors?", ["competitors", "comparison"]),
        ("What was that Q3 number again?", ["Q3"]),  # Vague query!
        ("Compare Q1 and Q3", ["Q1", "Q3", "comparison"]),
        ("Tell me about customer acquisition", ["customers", "acquisition"]),
        ("What were our best performing quarters?", ["Q1", "Q2", "Q3", "performance"]),
    ]
    
    print("\n### Starting 10-turn conversation ###\n")
    
    for i, (question, entities) in enumerate(conversations, 1):
        print(f"\n{'='*60}")
        print(f"TURN {i}")
        print(f"{'='*60}")
        
        response = bot.chat(question, entities=entities)
        
        # Show memory stats after each turn
        stats = bot.get_conversation_summary()
        print(f"\nMemory: {stats['active_tokens']} tokens | "
              f"Sensory: {stats['sensory_turns']} | "
              f"Short-term: {stats['shortterm_turns']} | "
              f"Long-term: {stats['longterm_memories']}")
    
    # Final summary
    print("\n\n" + "="*60)
    print("FINAL CONVERSATION SUMMARY")
    print("="*60)
    
    summary = bot.get_conversation_summary()
    print(f"""
Conversation Stats:
- Total turns: {summary['turns']}
- Active memory: {summary['active_tokens']} tokens
- Entities tracked: {summary['entities_tracked']}

Memory Distribution:
- Sensory (verbatim): {summary['sensory_turns']} turns
- Short-term (50% compressed): {summary['shortterm_turns']} turns
- Long-term (95% compressed): {summary['longterm_memories']} memories

Estimated Token Savings:
- Without compression: ~{summary['turns'] * 200} tokens
- With compression: {summary['active_tokens']} tokens
- Savings: {((1 - summary['active_tokens']/(summary['turns']*200)) * 100):.1f}%
""")
    
    # Test vague query retrieval
    print("\n" + "="*60)
    print("TESTING VAGUE QUERY RETRIEVAL")
    print("="*60)
    print("\nTurn 11: Testing if system can handle vague reference...")
    
    response = bot.chat("What was that number we discussed at the beginning?")
    print(f"\nResponse: {response}")
    print("\n(Should retrieve Q1 revenue from Turn 1 via clue generation!)")
    
    # Export
    print("\n" + "="*60)
    bot.export_conversation("financial_analysis.json")
    
    print("\n✓ Example conversation complete!")


def run_quick_test():
    """Quick test to verify everything works"""
    
    print("Quick Test - Verifying Day 2 Components")
    print("="*60)
    
    class SimpleMockLLM:
        def generate(self, prompt):
            return "Mock response"
        def chat(self, prompt):
            return "Mock response"
    
    # Test each component
    print("\n1. Testing ContextAwareBot initialization...")
    bot = ContextAwareBot(
        main_llm=SimpleMockLLM(),
        compressor_llm=SimpleMockLLM()
    )
    print("✓ Bot initialized")
    
    print("\n2. Testing conversation...")
    response = bot.chat("Test message")
    print(f"✓ Got response: {response[:50]}...")
    
    print("\n3. Testing memory...")
    summary = bot.get_conversation_summary()
    print(f"✓ Turns: {summary['turns']}, Tokens: {summary['active_tokens']}")
    
    print("\n4. Testing export...")
    bot.export_conversation("test.json")
    print("✓ Export successful")
    
    print("\n✓ All components working!")


if __name__ == "__main__":
    # Run the full example
    run_financial_analysis_conversation()
    
    # Or run quick test
    # run_quick_test()
