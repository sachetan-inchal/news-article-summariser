import re
from openai import OpenAI
from app.config import OLLAMA_BASE_URL, OLLAMA_MODEL
from app.prompts import SUMMARY_SYSTEM_PROMPT

client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

def _enforce_three_sentences(text: str) -> str:
    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(text.strip()) if s.strip()]
    return " ".join(sentences[:3])

def generate_summary(article: str, on_token=None) -> str:
    response = client.chat.completions.create(
        model=OLLAMA_MODEL,
        temperature=0.0,
        max_tokens=200,
        stream=True,
        messages=[{"role": "system",
                   "content": SUMMARY_SYSTEM_PROMPT.format(article=article)}],
    )
    parts = []
    for chunk in response:
        delta = chunk.choices[0].delta.content or ""
        if delta:
            parts.append(delta)
            if on_token:
                on_token(delta)
    return _enforce_three_sentences("".join(parts).strip())
