from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import requests

from app.config import settings

router = APIRouter()


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    answer: str
    source_documents: list[dict] = []


def _get_database_url() -> str:
    # Prefer settings.database_url (from env/.env) but allow DATABASE_URL env var.
    return os.environ.get("DATABASE_URL") or settings.database_url


def _fetch_relevant_rows(db_url: str, question: str) -> list[dict]:
    """Simple keyword search across trees and species to build grounding context.
    Returns list of rows with table and fields for inclusion in prompt.
    """
    rows = []
    if not db_url:
        return rows
    conn = None
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        kw = f"%{question}%"
        # Search trees by common_name or scientific_name
        cur.execute(
            "SELECT 'trees' as table_name, com_id, common_name, scientific_name, family, display_category, latitude, longitude FROM trees WHERE common_name ILIKE %s OR scientific_name ILIKE %s LIMIT 10",
            (kw, kw),
        )
        rows.extend(cur.fetchall())
        # Search species by scientific_name or common_name
        cur.execute(
            "SELECT 'species' as table_name, scientific_name, common_name, family, display_category, total_count FROM species WHERE scientific_name ILIKE %s OR common_name ILIKE %s LIMIT 10",
            (kw, kw),
        )
        rows.extend(cur.fetchall())
    except Exception:
        # swallow DB errors here and return empty list; endpoint will still work but without grounding
        return []
    finally:
        if conn:
            conn.close()
    return rows


def _call_gemini(prompt: str) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set in environment")

    # NOTE: Adjust endpoint/model as your organization requires. This is a commonly used
    # Generative Language API pattern; you may need to change URL and payload to match
    # the exact Gemini/Generative API version you are using.
    url = "https://generativelanguage.googleapis.com/v1beta2/models/text-bison-001:generate"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"prompt": {"text": prompt}, "maxOutputTokens": 512}
    resp = requests.post(url, headers=headers, json=payload, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    # Response shape may vary by API version; try to extract text in common places.
    if "candidates" in data and isinstance(data["candidates"], list):
        return data["candidates"][0].get("content", "").strip()
    if "output" in data and isinstance(data["output"], dict):
        # some versions return output.generated_text
        return data["output"].get("generated_text", "").strip()
    # Fallback: stringify whole response
    return str(data)


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is required")

    db_url = _get_database_url()
    rows = _fetch_relevant_rows(db_url, question)

    # Build a short grounding context from rows
    grounding_lines = []
    for r in rows:
        if r.get("table_name") == "trees":
            grounding_lines.append(f"Tree: {r.get('common_name')} ({r.get('scientific_name')}) at {r.get('latitude')},{r.get('longitude')} in category {r.get('display_category')}")
        else:
            # species
            grounding_lines.append(f"Species: {r.get('common_name')} ({r.get('scientific_name')}), count={r.get('total_count')}")

    prompt = "You are an assistant answering questions about the TouchGrass tree dataset. Use the grounding data and the database rows to answer concisely.\n\n"
    if grounding_lines:
        prompt += "Grounding data:\n" + "\n".join(grounding_lines) + "\n\n"
    prompt += f"Question: {question}\nAnswer:" 

    try:
        answer = _call_gemini(prompt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI model call failed: {e}")

    return ChatResponse(answer=answer, source_documents=[dict(r) for r in rows])
