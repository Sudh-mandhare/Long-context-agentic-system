"""
Context-Aware Bot - Main Orchestrator
Combines all components into a working system
"""

from typing import Dict, List, Optional
from .memory_system import ThreeTierMemorySystem
from .llm_compressor import LLMCompressor
from .clue_generator import ClueGenerator
from .hybrid_retriever import HybridRetriever
from .context_assembler import ContextAssembler

class ContextAwareBot:
    """
    Main bot that handles long-context conversations
    
    Workflow:
    1. User asks question
    2. Generate retrieval clues
    3. Retrieve relevant context
    4. Assemble full context
    5. Generate response
    6. Store in memory
    """
    
    def __init__(self, 
                 main_llm,          # LLM for generating responses (GPT-4)
                 compressor_llm,    # LLM for compression (can be GPT-3.5)
                 clue_llm=None):    # LLM for clues (optional, uses main if None)
        """
        Args:
            main_llm: Main LLM for responses (e.g., GPT-4)
            compressor_llm: LLM for compression (e.g., GPT-3.5)
            clue_llm: LLM for clues (optional, defaults to main_llm)
        """
        # Initialize components
        self.main_llm = main_llm
        self.compressor = LLMCompressor(compressor_llm)
        self.clue_llm = clue_llm or main_llm
        
        # Initialize memory system
        self.memory = ThreeTierMemorySystem(self.compressor)
        
        # Initialize intelligent retrieval
        self.clue_generator = ClueGenerator(self.clue_llm, self.memory)
        self.retriever = HybridRetriever(self.memory)
        self.assembler = ContextAssembler(self.memory)
        
        # Settings
        self.max_retrieved_turns = 5  # How many past turns to retrieve
        self.verbose = False  # Print debug info
    
    def chat(self, user_message: str, entities: Optional[List[str]] = None) -> str:
        """
        Main chat method - handles one conversation turn
        
        Args:
            user_message: User's question/message
            entities: Optional list of entities (auto-extracted if None)
            
        Returns:
            Assistant's response
        """
        if self.verbose:
            print("\n" + "="*60)
            print(f"USER: {user_message}")
            print("="*60)
        
        # Step 1: Generate retrieval clues
        if self.verbose:
            print("\nStep 1: Generating retrieval clues...")
        
        clues = self.clue_generator.generate_clues(
            user_message, 
            verbose=self.verbose
        )
        
        # Step 2: Retrieve relevant context
        if self.verbose:
            print("\nStep 2: Retrieving relevant context...")
        
        retrieved_context = self.retriever.retrieve_context(
            clues,
            max_results=self.max_retrieved_turns,
            verbose=self.verbose
        )
        
        # Step 3: Assemble full context
        if self.verbose:
            print("\nStep 3: Assembling full context...")
        
        full_context = self.assembler.assemble_full_context(
            user_message,
            retrieved_context,
            include_stats=self.verbose
        )
        
        if self.verbose:
            context_stats = self.assembler.get_context_stats(full_context)
            print(f"Context size: {context_stats['total_tokens']} tokens")
        
        # Step 4: Generate response
        if self.verbose:
            print("\nStep 4: Generating response...")
        
        try:
            response = self.main_llm.generate(full_context)
        except AttributeError:
            # Try alternative API
            response = self.main_llm.chat(full_context)
        
        if self.verbose:
            print(f"\nASSISTANT: {response}")
        
        # Step 5: Store in memory
        if self.verbose:
            print("\nStep 5: Storing in memory...")
        
        # Extract entities if not provided
        if entities is None:
            entities = clues['entities']
        
        self.memory.store_turn(
            user_message=user_message,
            assistant_response=response,
            entities=entities
        )
        
        if self.verbose:
            stats = self.memory.get_memory_stats()
            print(f"Memory: {stats['total_active_tokens']} tokens active")
            print("="*60)
        
        return response
    
    def get_conversation_summary(self) -> Dict:
        """Get summary of current conversation state"""
        stats = self.memory.get_memory_stats()
        
        return {
            'turns': stats['current_turn'],
            'active_tokens': stats['total_active_tokens'],
            'entities_tracked': stats['entities_tracked'],
            'sensory_turns': stats['sensory_turns'],
            'shortterm_turns': stats['shortterm_turns'],
            'longterm_memories': stats['longterm_memories']
        }
    
    def export_conversation(self, filepath: str):
        """Export conversation to file"""
        self.memory.export_state(filepath)
        print(f"✓ Conversation exported to {filepath}")
    
    def load_conversation(self, filepath: str):
        """Load conversation from file"""
        self.memory.load_state(filepath)
        print(f"✓ Conversation loaded from {filepath}")


# Testing
if __name__ == "__main__":
    print("Context-Aware Bot - Day 2 Complete System Test")
    print("="*60)
    
    # Mock LLMs for testing
    class MockMainLLM:
        def generate(self, prompt):
            # Simulate intelligent response based on prompt
            if "Q3 revenue" in prompt or "$6M" in prompt:
                return "Q3 revenue was $6M, which represents 20% growth from Q2."
            elif "Q2" in prompt:
                return "Q2 revenue was $5M."
            else:
                return "I don't have that information in the context."
    
    class MockCompressorLLM:
        def chat(self, prompt):
            # Simple compression
            return prompt.split('\n')[0][:100]
    
    # Initialize bot
    main_llm = MockMainLLM()
    compressor_llm = MockCompressorLLM()
    
    bot = ContextAwareBot(
        main_llm=main_llm,
        compressor_llm=compressor_llm
    )
    bot.verbose = True  # Show debug output
    
    # Simulate conversation
    print("\n### Starting Test Conversation ###\n")
    
    # Turn 1
    response1 = bot.chat("What's our Q3 revenue?")
    
    # Turn 2
    response2 = bot.chat("How does that compare to Q2?")
    
    # Turn 3 - vague query (tests clue
    # Turn 3 - vague query (tests clue generation)
    response3 = bot.chat("What was that number again?")
    
    # Turn 4 - More conversation
    response4 = bot.chat("Tell me about our top customers")
    
    # Turn 5
    response5 = bot.chat("What about competitors?")
    
    # Summary
    print("\n\n" + "="*60)
    print("CONVERSATION SUMMARY")
    print("="*60)
    summary = bot.get_conversation_summary()
    print(f"Total turns: {summary['turns']}")
    print(f"Active memory: {summary['active_tokens']} tokens")
    print(f"Entities tracked: {summary['entities_tracked']}")
    print(f"Memory distribution:")
    print(f"  - Sensory: {summary['sensory_turns']} turns")
    print(f"  - Short-term: {summary['shortterm_turns']} turns")
    print(f"  - Long-term: {summary['longterm_memories']} memories")
    
    # Export for later use
    bot.export_conversation("test_conversation.json")
    
    print("\n✓ Day 2 complete system test successful!")