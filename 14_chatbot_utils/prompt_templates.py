from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any
from jinja2 import Environment, FileSystemLoader, Template

class PromptEngine:
    """
    Advanced prompt management using Jinja2.
    Supports template inheritance, loops, and conditions.
    """

    def __init__(self, template_dir: str = None):
        if template_dir:
            self.env = Environment(loader=FileSystemLoader(template_dir))
        else:
            self.env = Environment() # Use empty env for raw strings

    def from_string(self, template_str: str) -> Template:
        return self.env.from_string(template_str)

    def from_file(self, filename: str) -> Template:
        return self.env.get_template(filename)

    def render(self, template: str, variables: Dict[str, Any]) -> str:
        """Render a template string with variables."""
        tmpl = self.env.from_string(template)
        return tmpl.render(**variables)

# Pre-defined templates using Jinja syntax
TEMPLATES = {
    "system": "You are a helpful AI assistant. Be concise and accurate.",
    "few_shot": """
Examples:
{% for ex in examples %}
User: {{ ex.user }}
Assistant: {{ ex.assistant }}
{% endfor %}

Current User: {{ query }}
Assistant:""",
    "cot": """Think step by step to answer the following question.
Question: {{ query }}
Answer:"""
}

def get_prompt(name: str, **kwargs) -> str:
    engine = PromptEngine()
    if name not in TEMPLATES:
        raise ValueError(f"Template {name} not found")
    return engine.render(TEMPLATES[name], kwargs)
