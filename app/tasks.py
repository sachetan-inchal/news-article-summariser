import time
from app.celery_app import celery_app
from app.llm import generate_summary
from app.verify_rules import rule_check
from app.verify_nli import nli_verify
from app.database import SessionLocal
from app.models import Article, Summary
from app.events import publish

STAGE_DELAY_SEC = 0.125

@celery_app.task(bind=True, max_retries=3, default_retry_delay=20)
def summarize_article(self, article_id: int):
    publish("task_started", article_id=article_id)
    time.sleep(STAGE_DELAY_SEC)
    db = SessionLocal()
    try:
        article = db.get(Article, article_id)
        if not article:
            publish("task_failed", article_id=article_id, reason="article not found")
            return {"error": "article not found"}

        publish("stage_change", article_id=article_id, stage="llm")

        def on_token(tok):
            publish("token", article_id=article_id, token=tok)

        try:
            summary_text = generate_summary(article.content, on_token=on_token)
        except Exception as exc:
            publish("task_failed", article_id=article_id, reason=str(exc))
            raise self.retry(exc=exc)

        time.sleep(STAGE_DELAY_SEC)
        publish("stage_change", article_id=article_id, stage="verify_rules")
        rule = rule_check(article.content, summary_text)

        if not rule["passed"]:
            verification = rule
        else:
            time.sleep(STAGE_DELAY_SEC)
            publish("stage_change", article_id=article_id, stage="verify_nli")
            verification = nli_verify(article.content, summary_text)

        time.sleep(STAGE_DELAY_SEC)
        publish("stage_change", article_id=article_id, stage="store")
        status = ("auto_published"
                  if verification["passed"] and article.risk_level != "high"
                  else "pending_review")

        summary = Summary(article_id=article.id, content=summary_text,
                          status=status, verification=verification)
        db.add(summary); db.commit(); db.refresh(summary)

        time.sleep(STAGE_DELAY_SEC)
        publish("task_completed",
                article_id=article_id,
                summary_id=summary.id,
                status=status,
                summary=summary_text,
                verification=verification)
        return {"summary_id": summary.id, "status": status}
    finally:
        db.close()
