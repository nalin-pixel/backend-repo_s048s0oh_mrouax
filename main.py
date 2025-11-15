import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests

app = FastAPI(title="Anime Streamer Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

JIKAN_BASE = "https://api.jikan.moe/v4"

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

@app.get("/api/anime/popular")
def popular_anime(limit: int = 12):
    try:
        r = requests.get(f"{JIKAN_BASE}/top/anime", params={"limit": limit, "filter": "bypopularity"}, timeout=20)
        r.raise_for_status()
        data = r.json().get("data", [])
        return {"results": data}
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=str(e))

@app.get("/api/anime/trending")
def trending_anime(limit: int = 12):
    try:
        # Treat trending as currently airing top
        r = requests.get(f"{JIKAN_BASE}/top/anime", params={"limit": limit, "filter": "airing"}, timeout=20)
        r.raise_for_status()
        data = r.json().get("data", [])
        return {"results": data}
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=str(e))

@app.get("/api/anime/{anime_id}")
def anime_detail(anime_id: int):
    try:
        r = requests.get(f"{JIKAN_BASE}/anime/{anime_id}/full", timeout=20)
        r.raise_for_status()
        data = r.json().get("data")
        if not data:
            raise HTTPException(status_code=404, detail="Anime not found")
        return data
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=str(e))

@app.get("/api/anime/{anime_id}/recommendations")
def anime_recommendations(anime_id: int, limit: int = 12):
    try:
        r = requests.get(f"{JIKAN_BASE}/anime/{anime_id}/recommendations", params={"limit": limit}, timeout=20)
        r.raise_for_status()
        data = r.json().get("data", [])
        # Jikan wraps recommendations; flatten to anime items where available
        results = []
        for item in data:
            entry = item.get("entry")
            if isinstance(entry, dict):
                results.append(entry)
            elif isinstance(entry, list) and entry:
                results.append(entry[0])
        return {"results": results[:limit]}
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=str(e))

@app.get("/api/anime/search")
def search_anime(q: str, limit: int = 24):
    if not q:
        return {"results": []}
    try:
        r = requests.get(f"{JIKAN_BASE}/anime", params={"q": q, "limit": limit, "order_by": "score", "sort": "desc"}, timeout=20)
        r.raise_for_status()
        data = r.json().get("data", [])
        return {"results": data}
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=str(e))

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    
    try:
        # Try to import database module
        from database import db
        
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            
            # Try to list collections to verify connectivity
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]  # Show first 10 collections
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
            
    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    
    # Check environment variables
    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
