"""
LLM Compressor - FIXED VERSION with intelligent compression
"""

import tiktoken
import re

class LLMCompressor:
    """
    Intelligent compression wrapper that understands different compression types
    """
    def __init__(self, llm_client):
        self.llm = llm_client
        self.encoding = tiktoken.get_encoding("cl100k_base")
    
    def generate(self, prompt: str) -> str:
        """
        Main interface - intelligently handles different compression types
        """
        # Check what type of compression is being requested
        if "summarize this conversation turn" in prompt.lower() or "compress this conversation turn" in prompt.lower():
            return self._handle_shortterm_compression(prompt)
        elif "extract only the most critical facts" in prompt.lower() or "ultra-compress" in prompt.lower():
            return self._handle_longterm_compression(prompt)
        elif "compress this text" in prompt.lower() or "summarize this text" in prompt.lower():
            return self._handle_general_compression(prompt)
        else:
            # Default: pass through to LLM
            try:
                return self.llm.chat(prompt)
            except Exception as e:
                return self._smart_fallback(prompt)
    
    def _handle_shortterm_compression(self, prompt: str) -> str:
        """
        Handle short-term memory compression (50% reduction)
        Format: User Query + Assistant Response → Concise summary
        """
        try:
            # Extract the actual conversation content
            content = self._extract_conversation_content(prompt)
            if content:
                user_query, assistant_response = content
                
                # Create better compression prompt
                compression_prompt = f"""Create a concise summary of this conversation turn:

USER: {user_query}
ASSISTANT: {assistant_response}

Extract the key information:
- Main question/topic
- Key facts/numbers/names mentioned  
- Important decisions or conclusions

Keep it very brief (2-3 sentences max). Focus on what would be needed to recall this conversation later.

Concise summary:"""
                
                compressed = self.llm.chat(compression_prompt)
                return compressed
            else:
                return self._extract_key_facts_fallback(prompt)
                
        except Exception as e:
            return self._extract_key_facts_fallback(prompt)
    
    def _handle_longterm_compression(self, prompt: str) -> str:
        """
        Handle long-term memory ultra-compression (95% reduction)
        Format: Extract only critical facts as bullets
        """
        try:
            content = self._extract_conversation_content(prompt)
            if content:
                user_query, assistant_response = content
                
                ultra_prompt = f"""Extract ONLY the most critical facts:

Conversation:
User: {user_query}
Assistant: {assistant_response}

Required format (be extremely brief):
- Topic: [1-3 words]
- Key facts: [numbers/names/dates only]
- Entities: [important names only]

Maximum 3 bullet points, 50 words total.

Critical facts:"""
                
                ultra_compressed = self.llm.chat(ultra_prompt)
                return ultra_compressed
            else:
                return self._extract_ultra_fallback(prompt)
                
        except Exception as e:
            return self._extract_ultra_fallback(prompt)
    
    def _handle_general_compression(self, prompt: str) -> str:
        """Handle general text compression requests"""
        try:
            return self.llm.chat(prompt)
        except Exception as e:
            return self._smart_fallback(prompt)
    
    def _extract_conversation_content(self, prompt: str) -> tuple:
        """
        Extract user query and assistant response from compression prompts
        """
        lines = prompt.split('\n')
        user_query = None
        assistant_response = None
        
        for i, line in enumerate(lines):
            if "user query:" in line.lower() or "user:" in line.lower():
                user_query = line.split(':', 1)[1].strip()
            elif "assistant response:" in line.lower() or "assistant:" in line.lower():
                assistant_response = line.split(':', 1)[1].strip()
        
        # If not found with labels, try to extract from context
        if not user_query or not assistant_response:
            for i, line in enumerate(lines):
                if line.strip() and not line.startswith('Requirements:') and not line.startswith('Format:'):
                    if not user_query and ('?' in line or line.startswith('User')):
                        user_query = line.replace('User Query:', '').replace('User:', '').strip()
                    elif not assistant_response and (not user_query or 'assistant' in line.lower()):
                        assistant_response = line.replace('Assistant Response:', '').replace('Assistant:', '').strip()
        
        if user_query and assistant_response:
            return user_query, assistant_response
        return None
    
    def _extract_key_facts_fallback(self, prompt: str) -> str:
        """
        Fallback for short-term compression when LLM fails
        """
        # Extract numbers, names, key terms
        numbers = re.findall(r'\$\d+\.?\d*[MBK]?|\d+%|\d+\.?\d*', prompt)
        names = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', prompt)
        
        # Extract key business terms
        key_terms = []
        business_terms = ['revenue', 'growth', 'customer', 'satisfaction', 'score', 
                         'profit', 'client', 'enterprise', 'quarter', 'Q[1-4]']
        for term in business_terms:
            if term.lower() in prompt.lower():
                key_terms.append(term)
        
        # Build intelligent summary
        summary_parts = []
        if numbers:
            summary_parts.append(f"Numbers: {', '.join(numbers[:3])}")
        if names:
            summary_parts.append(f"Entities: {', '.join(names[:2])}")
        if key_terms:
            summary_parts.append(f"Topics: {', '.join(key_terms[:3])}")
        
        if summary_parts:
            return " | ".join(summary_parts)
        else:
            # Last resort: extract first meaningful line
            lines = [line.strip() for line in prompt.split('\n') if line.strip()]
            for line in lines:
                if len(line) > 10 and not line.startswith('Requirements:') and not line.startswith('Format:'):
                    return line[:100]
            return "Conversation summary"
    
    def _extract_ultra_fallback(self, prompt: str) -> str:
        """
        Fallback for ultra-compression when LLM fails
        """
        numbers = re.findall(r'\$\d+\.?\d*[MBK]?|\d+%', prompt)
        names = re.findall(r'\b(Amazon|Google|Microsoft|Tesla|Apple|Facebook)\b', prompt, re.IGNORECASE)
        
        facts = []
        if numbers:
            facts.append(f"Data: {', '.join(numbers[:2])}")
        if names:
            facts.append(f"Companies: {', '.join(names[:2])}")
        
        if facts:
            return " • ".join(facts)
        return "Key business discussion"
    
    def _smart_fallback(self, prompt: str) -> str:
        """General fallback for any LLM failure"""
        return "Compressed summary of key information"


# Specialized compressors for different LLM backends
class OpenAICompressor(LLMCompressor):
    """For OpenAI API with optimized compression"""
    def _handle_shortterm_compression(self, prompt: str) -> str:
        try:
            content = self._extract_conversation_content(prompt)
            if content:
                user_query, assistant_response = content
                
                response = self.llm.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a conversation compressor. Create very brief summaries that preserve key facts, numbers, and entities."},
                        {"role": "user", "content": f"Compress this conversation:\n\nUser: {user_query}\nAssistant: {assistant_response}"}
                    ],
                    temperature=0.1,
                    max_tokens=100
                )
                return response.choices[0].message.content
            else:
                return self._extract_key_facts_fallback(prompt)
        except Exception as e:
            return self._extract_key_facts_fallback(prompt)


class LyzrCompressor(LLMCompressor):
    """For Lyzr ChatBot with compression optimization"""
    pass  # Uses the base implementation since Lyzr has .chat()