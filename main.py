import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import db, create_document, get_documents
from schemas import Message, Post, Reply, Report, MoodEntry, CounselorRequest
from datetime import datetime, timezone

app = FastAPI(title="Unmutte API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Unmutte backend running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set",
        "database_name": "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set",
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                response["collections"] = db.list_collection_names()[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"
    return response

# Utility
class ChatRequest(BaseModel):
    session_id: str
    text: str
    lang: Optional[str] = "en"

class ChatResponse(BaseModel):
    reply: str
    intensity: float
    lang: str
    suggest_break: bool

# Simple multilingual, non-judgmental responder with intensity estimation
# Note: In production, plug into a hosted LLM. Here we simulate safely.

SOFT_RESPONSES_EN = [
    "I’m here, yaar. Say whatever you need. No judgement, only warmth.",
    "That sounded really heavy. Take your time, I’m listening.",
    "You’re not alone. Main hoon na — I’m right here with you.",
]
SOFT_RESPONSES_HI = [
    "Main yahin hoon, yaar. Jo mann mein hai bol do. Koi faisla nahi.",
    "Ye sab kaafi bhaari lag raha hai. Araam se, main sun raha/rahi hoon.",
    "Tum akelay nahi ho. Main saath hoon, bilkul paas.",
]

TRIGGER_WORDS = [
    "hate", "useless", "worthless", "kill", "die", "abuse", "stupid", "idiot",
    "nobody", "broken", "angry", "rage"
]


def estimate_intensity(text: str) -> float:
    t = text.lower()
    score = sum(1 for w in TRIGGER_WORDS if w in t)
    score += min(5, max(0, (len(text) // 120)))
    return max(0.0, min(1.0, score / 8.0))


def generate_reply(text: str, lang: str) -> str:
    base = SOFT_RESPONSES_HI if (lang or "").lower().startswith("hi") else SOFT_RESPONSES_EN
    add = " Thoda sa saans lein — 4 count in, 4 hold, 4 out. Main yahin hoon." if estimate_intensity(text) > 0.7 else " Bolo aur, jo dil mein hai."
    return base[len(text) % len(base)] + add

@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    intensity = estimate_intensity(req.text)
    reply = generate_reply(req.text, req.lang or "en")
    suggest_break = intensity >= 0.8

    # Store encrypted placeholder (simulate at-rest encryption)
    try:
        create_document("message", {
            "session_id": req.session_id,
            "role": "user",
            "text": "",  # do not store plaintext
            "ciphertext": "enc::" + req.text[::-1],  # reversible demo; replace with real crypto
            "intensity": intensity,
            "lang": req.lang,
        })
        create_document("message", {
            "session_id": req.session_id,
            "role": "assistant",
            "text": "",
            "ciphertext": "enc::" + reply[::-1],
            "intensity": intensity,
            "lang": req.lang,
        })
    except Exception as e:
        # If DB not available, proceed without failing chat
        pass

    return ChatResponse(reply=reply, intensity=intensity, lang=req.lang or "en", suggest_break=suggest_break)

# Community Endpoints
class NewPost(BaseModel):
    content: str

class NewReply(BaseModel):
    post_id: str
    content: str

from random import randint

def make_alias() -> str:
    return f"Ally-{randint(100,999)}"

@app.post("/api/community/post")
def create_post(data: NewPost):
    doc_id = create_document("post", {
        "alias": make_alias(),
        "avatar_seed": str(randint(1, 9999)),
        "content": data.content,
        "status": "pending",  # goes through moderation first
        "reports": 0,
    })
    return {"id": doc_id, "status": "pending"}

@app.get("/api/community/feed")
def feed():
    posts = get_documents("post", {"status": "published"}, limit=50)
    return {"items": posts}

@app.post("/api/community/reply")
def add_reply(data: NewReply):
    doc_id = create_document("reply", {
        "post_id": data.post_id,
        "alias": make_alias(),
        "content": data.content,
        "status": "pending",
    })
    return {"id": doc_id, "status": "pending"}

class ReportReq(BaseModel):
    target_type: str
    target_id: str
    reason: Optional[str] = None

@app.post("/api/community/report")
def report_item(r: ReportReq):
    doc_id = create_document("report", r.model_dump())
    return {"id": doc_id, "queued": True}

# Wellness: Mood Tracker
class MoodReq(BaseModel):
    session_id: str
    mood: int
    note: Optional[str] = None

@app.post("/api/wellness/mood")
def add_mood(m: MoodReq):
    doc_id = create_document("moodentry", m.model_dump())
    return {"id": doc_id}

@app.get("/api/wellness/mood/{session_id}")
def get_mood(session_id: str):
    items = get_documents("moodentry", {"session_id": session_id}, limit=100)
    return {"items": items}

# Premium: Counselor requests + disclaimer text
DISCLAIMER = (
    "Unmutte's human listeners are trained emotional support peers, not licensed clinical therapists "
    "unless explicitly stated. They offer compassionate listening, not medical advice. In an emergency, "
    "contact local services immediately."
)

class CounselorReq(BaseModel):
    session_id: str
    topic: Optional[str] = None

@app.get("/api/premium/disclaimer")
def premium_disclaimer():
    return {"disclaimer": DISCLAIMER}

@app.post("/api/premium/request")
def request_listener(req: CounselorReq):
    doc_id = create_document("counselorrequest", req.model_dump())
    return {"id": doc_id, "status": "queued"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
