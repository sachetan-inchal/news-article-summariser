from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, JSON, ForeignKey
from sqlalchemy.sql import func
from app.database import Base

class Article(Base):
    __tablename__ = "articles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=True)
    content = Column(Text, nullable=False)
    category = Column(String(80), nullable=True)
    risk_level = Column(String(20), default="normal")
    created_at = Column(TIMESTAMP, server_default=func.now())

class Summary(Base):
    __tablename__ = "summaries"
    id = Column(Integer, primary_key=True, autoincrement=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    status = Column(String(30), default="pending_review", index=True)
    verification = Column(JSON, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    reviewed_at = Column(TIMESTAMP, nullable=True)

