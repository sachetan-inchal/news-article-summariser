from app.celery_app import celery_app
from app.llm import generate_summary
from app.verify import verify_summary
from app.database import SessionLocal
from app.models import Article, Summary

@celery_app.task(bind=True, max_retries=3, default_retry_delay=20)
def summarize_article(self, article_id: int):
    db = SessionLocal()
    try:
        article = db.get(Article, article_id)
        if not article:
            return {"error": "article not found"}

        try:
            summary_text = generate_summary(article.content)
        except Exception as exc:
            raise self.retry(exc=exc)

        verification = verify_summary(article.content, summary_text)
        status = ("auto_published"
                  if verification["passed"] and article.risk_level != "high"
                  else "pending_review")

        summary = Summary(article_id=article.id,
                          content=summary_text,
                          status=status,
                          verification=verification)
        db.add(summary)
        db.commit()
        db.refresh(summary)
        return {"summary_id": summary.id, "status": status}
    finally:
        db.close()

