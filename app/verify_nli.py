from sentence_transformers import CrossEncoder
import spacy

_nli_model = None
_nlp = None

def _get_nli():
    global _nli_model
    if _nli_model is None:
        _nli_model = CrossEncoder("cross-encoder/nli-deberta-v3-base")
    return _nli_model

def _get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp

# Exact id2label mapping: {0: 'contradiction', 1: 'entailment', 2: 'neutral'}
LABELS = ["contradiction", "entailment", "neutral"]

def _extract_claims(summary: str) -> list[str]:
    doc = _get_nlp()(summary)
    return [s.text.strip() for s in doc.sents if s.text.strip()]

def nli_verify(article: str, summary: str) -> dict:
    claims = _extract_claims(summary)
    if not claims:
        return {"passed": False,
                "errors": [{"type": "nli", "detail": "no claims extracted"}]}

    model = _get_nli()
    failures = []
    for claim in claims:
        scores = model.predict([(article, claim)])[0]
        idx = int(scores.argmax())
        label = LABELS[idx]
        confidence = float(scores.max())
        if label == "contradiction" and confidence > 0.7:
            failures.append({"claim": claim, "label": label,
                             "confidence": round(confidence, 3)})
        elif label == "neutral" and confidence > 0.8:
            failures.append({"claim": claim, "label": "unsupported",
                             "confidence": round(confidence, 3)})

    return {"passed": len(failures) == 0,
            "errors": [{"type": "nli", "detail": failures}] if failures else []}

