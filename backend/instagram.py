import requests
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

IMGBB_API_KEY = os.getenv("IMGBB_API_KEY", "")
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID", "")

GRAPH_API = "https://graph.facebook.com/v19.0"


def upload_imgbb(caminho_imagem: str) -> str:
    """Faz upload da imagem para imgbb e retorna a URL pública."""
    with open(caminho_imagem, "rb") as f:
        img_bytes = f.read()

    import base64
    img_b64 = base64.b64encode(img_bytes).decode("utf-8")

    resp = requests.post(
        "https://api.imgbb.com/1/upload",
        data={"key": IMGBB_API_KEY, "image": img_b64},
        timeout=30
    )
    resp.raise_for_status()
    data = resp.json()
    return data["data"]["url"]


def postar_story_instagram(imagem_url: str) -> str:
    """
    Posta um Story no Instagram via Graph API.
    Retorna o media_id publicado.
    """
    # 1. Criar container de mídia
    resp_container = requests.post(
        f"{GRAPH_API}/{INSTAGRAM_ACCOUNT_ID}/media",
        params={
            "image_url": imagem_url,
            "media_type": "IMAGE",
            "is_stories_item": "true",
            "access_token": INSTAGRAM_ACCESS_TOKEN,
        },
        timeout=30
    )
    resp_container.raise_for_status()
    container_id = resp_container.json()["id"]

    # 2. Publicar
    resp_pub = requests.post(
        f"{GRAPH_API}/{INSTAGRAM_ACCOUNT_ID}/media_publish",
        params={
            "creation_id": container_id,
            "access_token": INSTAGRAM_ACCESS_TOKEN,
        },
        timeout=30
    )
    resp_pub.raise_for_status()
    media_id = resp_pub.json()["id"]
    return media_id


async def publicar_post(caminho_imagem: str) -> dict:
    """
    Workflow completo: upload → story.
    Retorna {"imagem_url": str, "media_id": str}
    """
    imagem_url = await asyncio.to_thread(upload_imgbb, caminho_imagem)
    media_id = await asyncio.to_thread(postar_story_instagram, imagem_url)
    return {"imagem_url": imagem_url, "media_id": media_id}
