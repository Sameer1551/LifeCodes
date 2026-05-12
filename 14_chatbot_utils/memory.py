from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import Deque, List, Dict, Optional

# Optional: tiktoken for accurate token counting
try:
    import tiktoken
    _TOKENIZER = tiktoken.get_encoding("cl100k_base") # GPT-3.5/GPT-4 encoding
except ImportError:
    _TOKENIZER = None

class ConversationMemory:
    """
    Token-aware conversation memory.
    Maintains a sliding window of history that fits within a token budget.
    """

    def __init__(self, max_tokens: int = 3000, system_prompt: str = ""):
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt
        self._history: Deque[Dict[str, str]] = deque() # {"role": "...", "content": "..."}

    def _count_tokens(self, text: str) -> int:
        if _TOKENIZER:
            return len(_TOKENIZER.encode(text))
        # Fallback: 1 token ~= 4 chars
        return len(text) // 4

    def add(self, role: str, content: str):
        """Add a message and ensure it fits within max_tokens."""
        self._history.append({"role": role, "content": content})
        self._prune()

    def _prune(self):
        """Remove oldest messages until under token limit."""
        # Calculate current total tokens
        total = self._count_tokens(self.system_prompt) if self.system_prompt else 0
        for msg in self._history:
            total += self._count_tokens(msg["content"])
        
        while total > self.max_tokens and len(self._history) > 1:
            removed = self._history.popleft()
            total -= self._count_tokens(removed["content"])

    def get_messages(self) -> List[Dict[str, str]]:
        """Return messages formatted for OpenAI API (including system prompt)."""
        msgs = []
        if self.system_prompt:
            msgs.append({"role": "system", "content": self.system_prompt})
        msgs.extend(list(self._history))
        return msgs

    def save(self, path: Path):
        Path(path).write_text(json.dumps(list(self._history), indent=2))

    def load(self, path: Path):
        if path.exists():
            data = json.loads(path.read_text())
            for msg in data:
                self._history.append(msg)

    def clear(self):
        self._history.clear()
