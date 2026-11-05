from app.verify_rules import rule_check
from app.verify_nli import nli_verify

def verify_summary(article: str, summary: str) -> dict:
    rule = rule_check(article, summary)
    if not rule["passed"]:
        return rule
    return nli_verify(article, summary)

