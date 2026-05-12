# cli.py
import argparse
from pathlib import Path
from .memory import ConversationMemory
from .intent import IntentManager
from .knowledge import KnowledgeBase
from .response import ResponseGenerator

def main():
    parser = argparse.ArgumentParser(description="AI Chatbot CLI")
    parser.add_argument("--model", default="gpt-4o-mini", help="OpenAI model name")
    args = parser.parse_args()

    # 1. Init Components
    memory = ConversationMemory(max_tokens=2000, system_prompt="You are a helpful assistant.")
    
    # Define simple rules
    rules = {
        "greeting": ["hello", "hi", "hey"],
        "farewell": ["bye", "goodbye"],
        "query": ["what", "how", "why"]
    }
    intent_mgr = IntentManager(rules=rules)
    
    # 2. Init LLM
    bot = ResponseGenerator(model=args.model)
    
    print("Chatbot ready. Type 'exit' to quit.")
    while True:
        try:
            user_input = input("You: ")
            if user_input.lower() == "exit": break
            
            # Generate Response (Non-streaming for simplicity in CLI)
            response = bot.generate(user_input, memory, intent_manager=intent_mgr)
            
            print(f"Bot: {response}")
            
            # Save to memory loop
            memory.add("assistant", response)
            
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    main()
