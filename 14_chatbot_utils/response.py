from __future__ import annotations

import os
import logging
from typing import List, Dict, Optional, Callable
from .memory import ConversationMemory
from .intent import IntentManager
from .knowledge import KnowledgeBase

log = logging.getLogger(__name__)

class ResponseGenerator:
    """
    Orchestrates Memory, Intent, Knowledge, and LLM calls.
    Supports OpenAI and Anthropic (with streaming).
    """

    def __init__(self, model: str = "gpt-4o-mini", api_key: str = None):
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = None
        
        # Lazy load client
        if "gpt" in model or "o1" in model:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
                self.provider = "openai"
            except ImportError:
                log.warning("OpenAI library not found.")

    def generate(
        self, 
        user_input: str, 
        memory: ConversationMemory,
        intent_manager: Optional[IntentManager] = None,
        knowledge: Optional[KnowledgeBase] = None,
        stream: bool = False
    ):
        """
        Generate response.
        1. Detect Intent.
        2. Retrieve Context from KnowledgeBase.
        3. Call LLM.
        """
        # 1. Intent
        intent = "unknown"
        if intent_manager:
            intent, conf = intent_manager.predict(user_input)
        
        # 2. Context Retrieval
        context_str = ""
        if knowledge:
            hits = knowledge.search(user_input, top_k=1)
            if hits:
                doc, score = hits[0]
                context_str = f"Relevant Context:\n{doc['content']}\n\n"

        # 3. Construct Prompt
        # Inject context into user message (simple RAG approach)
        augmented_input = context_str + user_input if context_str else user_input
        
        # Add to memory
        memory.add("user", augmented_input)

        # 4. LLM Call
        if self.provider == "openai":
            return self._call_openai(memory.get_messages(), stream=stream)
        else:
            return "I am currently unable to connect to an AI provider."

    def _call_openai(self, messages: List[Dict], stream: bool = False):
        try:
            if stream:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    stream=True
                )
                # Generator for streaming
                def iter_chunks():
                    full_text = ""
                    for chunk in response:
                        if chunk.choices[0].delta.content:
                            content = chunk.choices[0].delta.content
                            full_text += content
                            yield content
                return iter_chunks()
            else:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages
                )
                return response.choices[0].message.content
        except Exception as e:
            log.error(f"OpenAI API Error: {e}")
            return "Sorry, I encountered an error."
