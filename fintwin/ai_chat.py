"""Generic AI chat backend (ChatGPT-style) for FinTwin."""

from __future__ import annotations

import os
from typing import Any, List, Dict

def chat(messages: List[Dict[str, str]], model: str = "gpt-4o-mini") -> str:
    """Send messages to OpenAI and return assistant reply. Requires OPENAI_API_KEY."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return "OPENAI_API_KEY not set. Configure it to enable AI chat."
    try:
        import openai
        client = openai.OpenAI(api_key=api_key)
        resp = client.chat.completions.create(model=model, messages=messages)
        return resp.choices[0].message.content or ""
    except Exception as e:
        return f"AI chat error: {e}"

def simple_ask(question: str, context: str = "") -> str:
    msgs = []
    if context:
        msgs.append({"role": "system", "content": context})
    msgs.append({"role": "user", "content": question})
    return chat(msgs)
