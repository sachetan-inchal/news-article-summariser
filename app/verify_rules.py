import re

MONTHS = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*"

def rule_check(article: str, summary: str) -> dict:
    errors = []

    article_nums = set(re.findall(r"\b\d[\d,.]*\b", article))
    summary_nums = set(re.findall(r"\b\d[\d,.]*\b", summary))
    missing_nums = summary_nums - article_nums
    if missing_nums:
        errors.append({"type": "numbers", "detail": sorted(missing_nums)})

    date_pat = rf"\b{MONTHS}\s+\d{{1,2}},?\s+\d{{4}}\b"
    article_dates = set(re.findall(date_pat, article, flags=re.IGNORECASE))
    summary_dates = set(re.findall(date_pat, summary, flags=re.IGNORECASE))
    missing_dates = summary_dates - article_dates
    if missing_dates:
        errors.append({"type": "dates", "detail": sorted(missing_dates)})

    return {"passed": len(errors) == 0, "errors": errors}

