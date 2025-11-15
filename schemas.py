"""
Database Schemas for Unmutte

Each Pydantic model corresponds to a MongoDB collection (collection name is the lowercase of class name).
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class Message(BaseModel):
    session_id: str = Field(..., description="Anonymous session identifier")
    role: str = Field(..., description="'user' | 'assistant'")
    text: str = Field(..., description="Plaintext content (not stored at rest)")
    ciphertext: Optional[str] = Field(None, description="Encrypted content stored at rest")
    intensity: Optional[float] = Field(None, ge=0, le=1, description="Emotional intensity score")
    lang: Optional[str] = Field("en", description="Language code e.g., 'en' or 'hi'")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class Post(BaseModel):
    alias: str = Field(..., description="Auto-generated anonymous handle, e.g., Ally-901")
    avatar_seed: Optional[str] = Field(None, description="Seed for rendering generic avatar")
    content: str = Field(..., description="Post text")
    status: str = Field("published", description="published | pending | removed")
    reports: int = Field(0, ge=0)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class Reply(BaseModel):
    post_id: str = Field(..., description="ID of the parent post")
    alias: str
    content: str
    status: str = Field("published")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class Report(BaseModel):
    target_type: str = Field(..., description="post | reply")
    target_id: str
    reason: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class MoodEntry(BaseModel):
    session_id: str
    mood: int = Field(..., ge=1, le=5)
    note: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class CounselorRequest(BaseModel):
    session_id: str
    topic: Optional[str] = None
    status: str = Field("queued", description="queued | connected | closed")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
