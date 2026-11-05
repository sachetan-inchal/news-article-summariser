import re
from openai import OpenAI
from app.config import OLLAMA_BASE_URL, OLLAMA_MODEL
from app.prompts import SUMMARY_SYSTEM_PROMPT

client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

def _enforce_three_sentences(text: str) -> str:
    """qwen2.5:3b sometimes ignores the length rule. Enforce it deterministically."""
    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(text.strip()) if s.strip()]
    sentences = sentences[:3]
    while len(sentences) > 1 and len(" ".join(sentences).split('.')) - 1 > 3:
        sentences.pop()
    # If under-length, leave as-is; a shorter-than-3 summary is still faithful.
    return " ".join(sentences)

def generate_summary(article: str) -> str:
    response = client.chat.completions.create(
        model=OLLAMA_MODEL,
        temperature=0.0,
        max_tokens=200,
        messages=[{"role": "system",
                   "content": SUMMARY_SYSTEM_PROMPT.format(article=article)}],
    )
    raw = response.choices[0].message.content.strip()
    return _enforce_three_sentences(raw)
