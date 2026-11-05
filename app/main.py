import os
import json
import asyncio
import redis.asyncio as aredis
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from app.database import init_db, get_db
from app.models import Article, Summary
from app.tasks import summarize_article
from app.celery_app import celery_app
from app.config import CELERY_BROKER_URL as _BROKER

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="News Summariser", lifespan=lifespan)

template_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=template_dir)

static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

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

@app.get("/factory")
def factory_page():
    return FileResponse(os.path.join(static_dir, "factory.html"))

@app.get("/api/articles/samples")
def get_sample_articles(limit: int = 20, offset: int = 0):
    candidates = [
        os.path.join(static_dir, "genuine_articles_300.json"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "genuine_articles_300.json"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "genuine_articles_300.json"),
        "genuine_articles_300.json"
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data[offset:offset+limit]
            except Exception:
                pass
    return []

@app.get("/api/reload-check")
def reload_check():
    stamp_path = "frontend/.reload-stamp"
    if os.path.exists(stamp_path):
        return {"mtime": os.path.getmtime(stamp_path)}
    alt_stamp = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", ".reload-stamp")
    if os.path.exists(alt_stamp):
        return {"mtime": os.path.getmtime(alt_stamp)}
    return {"mtime": 0}

@app.websocket("/ws/factory")
async def factory_ws(ws: WebSocket):
    await ws.accept()
    r = aredis.from_url(_BROKER, decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe("factory_events")
    try:
        while True:
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.5)
            if msg:
                await ws.send_text(msg["data"])
            else:
                await asyncio.sleep(0.02)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        try:
            await pubsub.unsubscribe("factory_events")
            await r.close()
        except Exception:
            pass
