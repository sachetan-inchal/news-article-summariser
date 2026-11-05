import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from app.database import init_db, get_db
from app.models import Article, Summary
from app.tasks import summarize_article
from app.celery_app import celery_app

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="News Summariser", lifespan=lifespan)

template_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=template_dir)

class ArticleIn(BaseModel):
    title: str | None = None
    text: str
    category: str | None = None
    risk_level: str = "normal"

@app.post("/articles/submit")
def submit(body: ArticleIn, db: Session = Depends(get_db)):
    a = Article(title=body.title, content=body.text,
                category=body.category, risk_level=body.risk_level)
    db.add(a); db.commit(); db.refresh(a)
    task = summarize_article.delay(a.id)
    return {"article_id": a.id, "task_id": task.id}

@app.get("/tasks/{task_id}")
def task_status(task_id: str):
    r = celery_app.AsyncResult(task_id)
    payload = {"state": r.state}
    if r.ready():
        payload["result"] = r.result
    return payload

@app.get("/summaries/{summary_id}")
def get_summary(summary_id: int, db: Session = Depends(get_db)):
    s = db.get(Summary, summary_id)
    if not s: raise HTTPException(404)
    return {"id": s.id, "article_id": s.article_id, "content": s.content,
            "status": s.status, "verification": s.verification}

@app.get("/summaries")
def list_summaries(status: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Summary)
    if status: q = q.filter(Summary.status == status)
    return [{"id": s.id, "article_id": s.article_id, "status": s.status}
            for s in q.order_by(Summary.id.desc()).limit(50).all()]

@app.get("/review", response_class=HTMLResponse)
def review_page(request: Request):
    return templates.TemplateResponse("review.html", {"request": request})

@app.get("/api/review/pending")
def pending(db: Session = Depends(get_db)):
    rows = (db.query(Summary, Article)
              .join(Article, Summary.article_id == Article.id)
              .filter(Summary.status == "pending_review")
              .order_by(Summary.id.asc()).limit(100).all())
    return [{"summary_id": s.id, "article_id": s.article_id,
             "article_title": a.title, "summary": s.content,
             "verification": s.verification} for s, a in rows]

@app.post("/api/review/{summary_id}/approve")
def approve(summary_id: int, db: Session = Depends(get_db)):
    s = db.get(Summary, summary_id)
    if not s: raise HTTPException(404)
    s.status = "approved"; s.reviewed_at = func.now(); db.commit()
    return {"ok": True}

@app.post("/api/review/{summary_id}/reject")
def reject(summary_id: int, db: Session = Depends(get_db)):
    s = db.get(Summary, summary_id)
    if not s: raise HTTPException(404)
    s.status = "rejected"; s.reviewed_at = func.now(); db.commit()
    return {"ok": True}

