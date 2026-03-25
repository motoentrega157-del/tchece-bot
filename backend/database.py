import aiosqlite
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "tchece_bot.db")

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                legenda TEXT NOT NULL,
                tema TEXT NOT NULL,
                imagem_local TEXT,
                imagem_url TEXT,
                status TEXT DEFAULT 'pending',
                instagram_media_id TEXT,
                criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
                publicado_em TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS config (
                chave TEXT PRIMARY KEY,
                valor TEXT NOT NULL
            )
        """)
        # Defaults
        defaults = [
            ("hora_1", "08:30"),
            ("hora_2", "13:00"),
            ("ativo", "true"),
        ]
        for chave, valor in defaults:
            await db.execute(
                "INSERT OR IGNORE INTO config (chave, valor) VALUES (?, ?)",
                (chave, valor)
            )
        await db.commit()

async def criar_post(titulo: str, legenda: str, tema: str, imagem_local: str = None) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO posts (titulo, legenda, tema, imagem_local) VALUES (?, ?, ?, ?)",
            (titulo, legenda, tema, imagem_local)
        )
        await db.commit()
        return cursor.lastrowid

async def atualizar_post(post_id: int, **kwargs):
    if not kwargs:
        return
    campos = ", ".join(f"{k} = ?" for k in kwargs)
    valores = list(kwargs.values()) + [post_id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE posts SET {campos} WHERE id = ?", valores)
        await db.commit()

async def buscar_post(post_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM posts WHERE id = ?", (post_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def listar_posts(status: str = None, limit: int = 20) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if status:
            async with db.execute(
                "SELECT * FROM posts WHERE status = ? ORDER BY criado_em DESC LIMIT ?",
                (status, limit)
            ) as cursor:
                rows = await cursor.fetchall()
        else:
            async with db.execute(
                "SELECT * FROM posts ORDER BY criado_em DESC LIMIT ?", (limit,)
            ) as cursor:
                rows = await cursor.fetchall()
        return [dict(r) for r in rows]

async def get_config(chave: str) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT valor FROM config WHERE chave = ?", (chave,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def set_config(chave: str, valor: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO config (chave, valor) VALUES (?, ?)", (chave, valor)
        )
        await db.commit()
