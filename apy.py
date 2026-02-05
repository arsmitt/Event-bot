from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
from typing import List, Optional
import uvicorn

app = FastAPI(title="3-In-A-Row Leaderboard API")

# Настройки CORS для доступа с вашего GitHub Pages
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://arsmitt.github.io"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class GameScore(BaseModel):
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    score: int
    game_time: Optional[int] = None

class LeaderboardEntry(BaseModel):
    user_id: int
    username: Optional[str]
    first_name: Optional[str]
    score: int
    rank: int

@app.get("/")
async def root():
    return {"message": "3-In-A-Row Leaderboard API", "status": "active"}

@app.post("/api/save_score")
async def save_score(score_data: GameScore):
    """Сохраняет результат игры"""
    try:
        conn = sqlite3.connect('game_leaderboard.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO user_scores (user_id, username, first_name, score, game_time)
            VALUES (?, ?, ?, ?, ?)
        ''', (score_data.user_id, score_data.username, 
              score_data.first_name, score_data.score, score_data.game_time))
        
        conn.commit()
        conn.close()
        return {"status": "success", "message": "Score saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/top_scores", response_model=List[LeaderboardEntry])
async def get_top_scores(limit: int = 10):
    """Возвращает таблицу лидеров"""
    try:
        conn = sqlite3.connect('game_leaderboard.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT DISTINCT 
                user_id, 
                username, 
                first_name, 
                MAX(score) as best_score
            FROM user_scores 
            GROUP BY user_id
            ORDER BY best_score DESC 
            LIMIT ?
        ''', (limit,))
        
        results = []
        rows = cursor.fetchall()
        conn.close()
        
        for i, (user_id, username, first_name, score) in enumerate(rows, 1):
            results.append(LeaderboardEntry(
                user_id=user_id,
                username=username,
                first_name=first_name,
                score=score,
                rank=i
            ))
        
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/user_stats/{user_id}")
async def get_user_stats(user_id: int):
    """Возвращает статистику пользователя"""
    try:
        conn = sqlite3.connect('game_leaderboard.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                MAX(score) as best_score,
                COUNT(*) as total_games,
                AVG(score) as avg_score
            FROM user_scores 
            WHERE user_id = ?
        ''', (user_id,))
        
        stats = cursor.fetchone()
        conn.close()
        
        if stats and stats[0]:
            return {
                "user_id": user_id,
                "best_score": stats[0],
                "total_games": stats[1],
                "average_score": round(stats[2], 1) if stats[2] else 0
            }
        return {"user_id": user_id, "best_score": 0, "total_games": 0, "average_score": 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
