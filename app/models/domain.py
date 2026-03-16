import datetime
import uuid
from sqlalchemy import Column, Integer, String, Text, DateTime, Date, JSON, ForeignKey, Float
from sqlalchemy.orm import relationship
from app.core.database import Base

class Faq(Base):
    __tablename__ = "faqs"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(String(255), nullable=False)
    answer = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    source_path = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    metadata_json = Column(JSON, nullable=True) # Renamed to metadata_json to avoid conflict if needed, or just metadata
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class DocumentTracking(Base):
    __tablename__ = "document_trackings"

    id = Column(Integer, primary_key=True, index=True)
    tracking_number = Column(String(30), unique=True, index=True, nullable=False)
    document_type = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)
    note = Column(String(100), nullable=True)
    estimated_completion_date = Column(Date, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class ChatHistory(Base):
    __tablename__ = "chat_histories"

    id = Column(Integer, primary_key=True, index=True)
    message = Column(Text, nullable=False)
    response = Column(Text, nullable=True)
    category = Column(String(255), nullable=True)
    ip_address = Column(String(255), nullable=True)
    user_agent = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    asal_desa = Column(String(255), nullable=True)
    role = Column(String(50), default="user") # admin / user
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan", lazy="selectin")

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    user = relationship("User", back_populates="sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan", lazy="selectin")

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), ForeignKey("chat_sessions.id"), nullable=False)
    role = Column(String(50), nullable=False) # user / assistant
    content = Column(Text, nullable=False)
    retrieved_docs = Column(JSON, nullable=True)
    response_time = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    session = relationship("ChatSession", back_populates="messages")
