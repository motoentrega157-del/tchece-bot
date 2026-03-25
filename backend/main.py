from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import asyncio
import json
import os
import secrets
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

from . import database as db
try:
    from . import agent as ag
except Exception:
    ag = None
from .image_creator import criar_story_async
from .instagram import publicar_post

app = FastAPI(title="Tchê Celulares - Instagram Bot", version="1.0.0")
security = HTTPBasic()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Frontend estático ─────────────────────────────────────────────────
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
STORIES_DIR = os.path.join(os.path.dirname(__file__), "stories")
os.makedirs(STORIES_DIR, exist_ok=True)

app.mount("/stories", StaticFiles(directory=STORIES_DIR), name="stories")
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

scheduler = AsyncIOScheduler(timezone="America/Sao_Paulo")

# WebSocket manager
class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, mensagem: dict):
        mortos = []
        for ws in self.active:
            try:
                await ws.send_json(mensagem)
            except:
                mortos.append(ws)
        for ws in mortos:
            self.disconnect(ws)

manager = ConnectionManager()
gerando = False  # Lock simples - evita gerar 2 ao mesmo tempo


def verificar_senha(credentials: HTTPBasicCredentials = Depends(security)):
    senha_correta = os.getenv("DASHBOARD_PASSWORD", "tchece123")
    ok = secrets.compare_digest(credentials.password.encode(), senha_correta.encode())
    if not ok:
        raise HTTPException(status_code=401, detail="Senha incorreta",
                            headers={"WWW-Authenticate": "Basic"})
    return credentials.username


# ── Ciclo do Agente ────────────────────────────────────────────────────
async def ciclo_agente(tema: str = None):
    global gerando
    if gerando:
        await manager.broadcast({"tipo": "log", "dados": "⚠️ Agente já está trabalhando! Aguarde..."})
        return
    gerando = True
    post_id = None
    try:
        await manager.broadcast({"tipo": "status", "dados": "working"})
        await manager.broadcast({"tipo": "log", "dados": "🚀 Agente iniciado! Preparando conteúdo..."})

        conteudo = None
        async for evento in ag.gerar_conteudo(tema):
            await manager.broadcast(evento)
            if evento["tipo"] == "conteudo":
                conteudo = evento["dados"]
            elif evento["tipo"] == "erro":
                await manager.broadcast({"tipo": "status", "dados": "idle"})
                return

        if not conteudo:
            return

        # Salvar no banco (status: generating)
        post_id = await db.criar_post(
            titulo=conteudo["titulo"],
            legenda=conteudo["legenda"],
            tema=conteudo["tema"],
        )
        await db.atualizar_post(post_id, status="generating")

        await manager.broadcast({"tipo": "log", "dados": "🎨 Criando imagem Story..."})

        caminho = await criar_story_async(
            titulo=conteudo["titulo"],
            legenda=conteudo["legenda"],
            hashtags=conteudo["hashtags"],
            tema=conteudo["tema"],
            emoji=conteudo["emoji"],
            post_id=post_id,
        )

        await db.atualizar_post(post_id, imagem_local=caminho, status="pending")

        await manager.broadcast({"tipo": "log", "dados": "✅ Imagem criada! Aguardando aprovação..."})
        await manager.broadcast({
            "tipo": "novo_post",
            "dados": {
                "id": post_id,
                "titulo": conteudo["titulo"],
                "legenda": conteudo["legenda"],
                "hashtags": conteudo["hashtags"],
                "tema": conteudo["tema"],
                "imagem_url": f"/stories/story_{post_id}.png",
                "status": "pending",
            }
        })
        await manager.broadcast({"tipo": "status", "dados": "idle"})

    except Exception as e:
        await manager.broadcast({"tipo": "log", "dados": f"❌ Erro no agente: {str(e)}"})
        await manager.broadcast({"tipo": "status", "dados": "idle"})
        if post_id:
            await db.atualizar_post(post_id, status="error")
    finally:
        gerando = False


# ── Endpoints REST ─────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    await db.init_db()
    hora_manha = await db.get_config("hora_manha") or "08:30"
    hora_noite = await db.get_config("hora_noite") or "13:00"
    _agendar_horarios(hora_manha, hora_noite)
    scheduler.start()
    print(f"✅ Bot iniciado! Agendamentos: {hora_manha} e {hora_noite}")

def _agendar_horarios(hora_manha: str, hora_noite: str):
    scheduler.remove_all_jobs()
    h1, m1 = hora_manha.split(":")
    h2, m2 = hora_noite.split(":")
    
    # Horários de Geração (1 hora ANTES da publicação)
    hg1 = (int(h1) - 1) % 24
    hg2 = (int(h2) - 1) % 24

    # Agendar a CRIAÇÃO da arte (fica pending)
    scheduler.add_job(ciclo_agente, "cron", hour=hg1, minute=int(m1), id="prep_manha")
    scheduler.add_job(ciclo_agente, "cron", hour=hg2, minute=int(m2), id="prep_noite")

    # Agendar a PUBLICAÇÃO de fato (colhe o aproved)
    scheduler.add_job(rotina_publicar_agendado, "cron", hour=int(h1), minute=int(m1), id="pub_manha")
    scheduler.add_job(rotina_publicar_agendado, "cron", hour=int(h2), minute=int(m2), id="pub_noite")


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()  # manter vivo
    except WebSocketDisconnect:
        manager.disconnect(ws)


@app.post("/api/gerar")
async def gerar_post(tema: Optional[str] = None):
    """Dispara o agente manualmente."""
    asyncio.create_task(ciclo_agente(tema))
    return {"ok": True, "mensagem": "Agente iniciado!"}


@app.get("/api/pendentes")
async def listar_pendentes():
    posts = await db.listar_posts(status="pending")
    for p in posts:
        p["imagem_url"] = f"/stories/story_{p['id']}.png"
    return posts


@app.get("/api/historico")
async def historico():
    posts = await db.listar_posts(limit=30)
    for p in posts:
        if p.get("imagem_local"):
            p["imagem_url"] = f"/stories/story_{p['id']}.png"
    return posts


class AprovarRequest(BaseModel):
    legenda: Optional[str] = None  # legenda editada (opcional)

@app.post("/api/aprovar/{post_id}")
async def aprovar_post(post_id: int, body: AprovarRequest = AprovarRequest()):
    post = await db.buscar_post(post_id)
    if not post:
        raise HTTPException(404, "Post não encontrado")
    if post["status"] != "pending":
        raise HTTPException(400, f"Post não está pendente (status: {post['status']})")

    # Atualiza a legenda e muda o status para aprovado (pronto para ser colhido no horário certo)
    await db.atualizar_post(post_id, legenda=body.legenda if body.legenda else post["legenda"], status="approved")
    
    await manager.broadcast({"tipo": "log", "dados": f"✅ Story #{post_id} aprovado! Ficará na fila de espera para o próximo horário programado."})
    await manager.broadcast({"tipo": "post_atualizado", "dados": {"id": post_id, "status": "approved"}})
    return {"ok": True, "mensagem": "Post aprovado e na fila!"}

# ── Rotina de Publicação no Horário Marcado ────────────────────────────
async def rotina_publicar_agendado():
    """Roda nos horários agendados para colher um post aprovado e mandar pro Insta"""
    posts_aprovados = await db.listar_posts(status="approved")
    if not posts_aprovados:
        await manager.broadcast({"tipo": "log", "dados": "⚠️ Horário de postagem chegou, mas não há posts aprovados na fila!"})
        return
    
    post = posts_aprovados[0]  # Pega o mais antigo aprovado
    post_id = post["id"]
    
    await db.atualizar_post(post_id, status="publishing")
    await manager.broadcast({"tipo": "status", "dados": "working"})
    await manager.broadcast({"tipo": "log", "dados": f"⏰ O Relógio tocou! Publicando Story aprovado #{post_id} no Instagram..."})

    try:
        resultado = await publicar_post(post["imagem_local"])
        await db.atualizar_post(
            post_id,
            status="published",
            instagram_media_id=resultado["media_id"],
            imagem_url=resultado["imagem_url"],
            publicado_em=datetime.now().isoformat()
        )
        await manager.broadcast({"tipo": "log", "dados": f"✅ Story #{post_id} publicado 100% automático no Instagram!"})
        await manager.broadcast({"tipo": "post_atualizado", "dados": {"id": post_id, "status": "published"}})
    except Exception as e:
        await db.atualizar_post(post_id, status="error")
        await manager.broadcast({"tipo": "log", "dados": f"❌ Erro ao publicar: {str(e)}"})
    finally:
        await manager.broadcast({"tipo": "status", "dados": "idle"})


@app.post("/api/rejeitar/{post_id}")
async def rejeitar_post(post_id: int):
    post = await db.buscar_post(post_id)
    if not post:
        raise HTTPException(404, "Post não encontrado")
    await db.atualizar_post(post_id, status="rejected")
    await manager.broadcast({"tipo": "post_atualizado", "dados": {"id": post_id, "status": "rejected"}})
    return {"ok": True}


class HorariosRequest(BaseModel):
    hora_manha: str
    hora_noite: str

@app.post("/api/horarios")
async def atualizar_horarios(body: HorariosRequest):
    await db.set_config("hora_manha", body.hora_manha)
    await db.set_config("hora_noite", body.hora_noite)
    _agendar_horarios(body.hora_manha, body.hora_noite)
    return {"ok": True, "hora_manha": body.hora_manha, "hora_noite": body.hora_noite}


@app.get("/api/horarios")
async def obter_horarios():
    return {
        "hora_manha": await db.get_config("hora_manha") or "09:00",
        "hora_noite": await db.get_config("hora_noite") or "18:00",
    }


@app.get("/api/status")
async def status_bot():
    pendentes = await db.listar_posts(status="pending")
    publicados_hoje = [
        p for p in await db.listar_posts(status="published")
        if p.get("publicado_em", "").startswith(datetime.now().strftime("%Y-%m-%d"))
    ]
    return {
        "gerando": gerando,
        "pendentes": len(pendentes),
        "publicados_hoje": len(publicados_hoje),
        "hora_manha": await db.get_config("hora_manha"),
        "hora_noite": await db.get_config("hora_noite"),
    }
