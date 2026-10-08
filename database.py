from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from config import DB_PATH

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    echo=False,
    connect_args={"check_same_thread": False, "timeout": 30},
)
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Template(Base):
    __tablename__ = "templates"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), unique=True)
    filename = Column(String(300))
    category = Column(String(100), default="general")
    text_boxes = Column(Text)  # JSON: [{"x":..,"y":..,"w":..,"h":..,"align":"center"}]
    usage_count = Column(Integer, default=0)
    avg_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)


class Meme(Base):
    __tablename__ = "memes"
    id = Column(Integer, primary_key=True)
    template_id = Column(Integer, ForeignKey("templates.id"))
    top_text = Column(String(500))
    bottom_text = Column(String(500))
    caption = Column(Text)
    filename = Column(String(300))
    style = Column(String(50))
    funny_score = Column(Float, default=0.0)
    relatable_score = Column(Float, default=0.0)
    trending_score = Column(Float, default=0.0)
    original_score = Column(Float, default=0.0)
    viral_score = Column(Float, default=0.0)
    total_score = Column(Float, default=0.0)
    is_duplicate = Column(Boolean, default=False)
    is_nsfw = Column(Boolean, default=False)
    is_published = Column(Boolean, default=False)
    published_at = Column(DateTime, nullable=True)
    phash = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    template = relationship("Template")


class Performance(Base):
    __tablename__ = "performance"
    id = Column(Integer, primary_key=True)
    meme_id = Column(Integer, ForeignKey("memes.id"))
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    saves = Column(Integer, default=0)
    reach = Column(Integer, default=0)
    recorded_at = Column(DateTime, default=datetime.utcnow)


class LearningStat(Base):
    __tablename__ = "learning_stats"
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True)  # e.g. "style:dark", "template:drake"
    value = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(engine)


def get_session():
    return SessionLocal()
