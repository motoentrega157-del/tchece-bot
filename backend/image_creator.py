from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os
import textwrap
import math
import asyncio

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "stories")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Cores Tchê Celulares
COR_AZUL = (52, 153, 200)          # #3499C8
COR_AZUL_ESCURO = (30, 100, 145)   # #1E6491
COR_CINZA = (61, 69, 83)           # #3D4553
COR_BRANCO = (255, 255, 255)
COR_PRETO = (20, 20, 20)
COR_AMARELO = (255, 200, 0)

W, H = 1080, 1920

def _carregar_fonte(tamanho: int, negrito: bool = False) -> ImageFont.ImageFont:
    """Tenta carregar fonte do sistema, fallback para padrão."""
    fontes_windows = [
        "C:/Windows/Fonts/arialbd.ttf" if negrito else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibrib.ttf" if negrito else "C:/Windows/Fonts/calibri.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
    ]
    for caminho in fontes_windows:
        if os.path.exists(caminho):
            try:
                return ImageFont.truetype(caminho, tamanho)
            except:
                continue
    return ImageFont.load_default()

def _gradiente(img: Image.Image, cor1: tuple, cor2: tuple):
    """Preenche a imagem com gradiente vertical."""
    draw = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        r = int(cor1[0] * (1 - t) + cor2[0] * t)
        g = int(cor1[1] * (1 - t) + cor2[1] * t)
        b = int(cor1[2] * (1 - t) + cor2[2] * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

def _texto_centralizado(draw, texto: str, y: int, fonte, cor, largura_max: int = 900, espacamento: int = 10):
    """Escreve texto centralizado com quebra automática de linha."""
    linhas = []
    palavras = texto.split()
    linha_atual = ""
    for palavra in palavras:
        teste = f"{linha_atual} {palavra}".strip()
        bbox = draw.textbbox((0, 0), teste, font=fonte)
        if bbox[2] > largura_max:
            if linha_atual:
                linhas.append(linha_atual)
            linha_atual = palavra
        else:
            linha_atual = teste
    if linha_atual:
        linhas.append(linha_atual)

    altura_total = 0
    for linha in linhas:
        bbox = draw.textbbox((0, 0), linha, font=fonte)
        altura_total += (bbox[3] - bbox[1]) + espacamento

    y_atual = y
    for linha in linhas:
        bbox = draw.textbbox((0, 0), linha, font=fonte)
        largura = bbox[2] - bbox[0]
        x = (W - largura) // 2
        # Sombra
        draw.text((x + 2, y_atual + 2), linha, font=fonte, fill=(0, 0, 0, 80))
        draw.text((x, y_atual), linha, font=fonte, fill=cor)
        y_atual += (bbox[3] - bbox[1]) + espacamento

    return y_atual

def criar_story(titulo: str, legenda: str, hashtags: str, tema: str, emoji: str, post_id: int) -> str:
    """
    Cria imagem Story 1080x1920 com identidade visual Tchê Celulares.
    Retorna o caminho do arquivo salvo.
    """
    img = Image.new("RGB", (W, H))
    _gradiente(img, COR_AZUL_ESCURO, (15, 60, 100))
    draw = ImageDraw.Draw(img)

    # ── Faixa superior com padrão decorativo ──────────────────────────
    for i in range(0, W + 100, 60):
        draw.line([(i - 50, 0), (i, 180)], fill=(*COR_AZUL, 120), width=2)

    # ── Header Brand ──────────────────────────────────────────────────
    fonte_brand = _carregar_fonte(52, negrito=True)
    fonte_slogan = _carregar_fonte(32)

    # Logo texto se não houver imagem
    logo_path = os.path.join(ASSETS_DIR, "logo.png")
    if os.path.exists(logo_path):
        try:
            logo = Image.open(logo_path).convert("RGBA")
            logo_w = 500
            ratio = logo_w / logo.width
            logo_h = int(logo.height * ratio)
            logo = logo.resize((logo_w, logo_h), Image.LANCZOS)
            x_logo = (W - logo_w) // 2
            img.paste(logo, (x_logo, 60), logo)
            y_pos = 60 + logo_h + 20
        except:
            _texto_centralizado(draw, "TCHÊ CELULARES", 70, fonte_brand, COR_BRANCO)
            y_pos = 160
    else:
        _texto_centralizado(draw, "TCHÊ CELULARES", 70, fonte_brand, COR_BRANCO)
        y_pos = 160

    # ── Linha separadora ──────────────────────────────────────────────
    draw.rectangle([(80, y_pos + 5), (W - 80, y_pos + 8)], fill=COR_AZUL)
    y_pos += 30

    # ── Badge do tema ─────────────────────────────────────────────────
    fonte_tema = _carregar_fonte(36, negrito=True)
    texto_tema = f"{emoji}  {tema.upper()}"
    bbox_tema = draw.textbbox((0, 0), texto_tema, font=fonte_tema)
    larg_badge = (bbox_tema[2] - bbox_tema[0]) + 60
    alt_badge = (bbox_tema[3] - bbox_tema[1]) + 24
    x_badge = (W - larg_badge) // 2
    draw.rounded_rectangle(
        [x_badge, y_pos, x_badge + larg_badge, y_pos + alt_badge],
        radius=20, fill=COR_AZUL
    )
    draw.text((x_badge + 30, y_pos + 12), texto_tema, font=fonte_tema, fill=COR_BRANCO)
    y_pos += alt_badge + 50

    # ── Título principal ──────────────────────────────────────────────
    fonte_titulo = _carregar_fonte(88, negrito=True)
    y_pos = _texto_centralizado(draw, titulo, y_pos, fonte_titulo, COR_BRANCO, largura_max=950)
    y_pos += 30

    # ── Linha decorativa ─────────────────────────────────────────────
    draw.rectangle([(200, y_pos), (W - 200, y_pos + 4)], fill=(*COR_AMARELO, 200))
    y_pos += 40

    # ── Corpo do texto ────────────────────────────────────────────────
    fonte_corpo = _carregar_fonte(46)
    y_pos = _texto_centralizado(draw, legenda, y_pos, fonte_corpo, (220, 235, 245), largura_max=920, espacamento=14)
    y_pos += 40

    # ── Avatar / Mascote ──────────────────────────────────────────────
    avatar_path = os.path.join(ASSETS_DIR, "avatar.png")
    if os.path.exists(avatar_path):
        try:
            avatar = Image.open(avatar_path).convert("RGBA")
            av_h = 380
            ratio = av_h / avatar.height
            av_w = int(avatar.width * ratio)
            avatar = avatar.resize((av_w, av_h), Image.LANCZOS)
            x_av = W - av_w - 40
            y_av = H - av_h - 220
            img.paste(avatar, (x_av, y_av), avatar)
        except:
            pass

    # ── Caixa CTA ─────────────────────────────────────────────────────
    cta_y = H - 200
    draw.rounded_rectangle(
        [(60, cta_y), (W - 60, cta_y + 110)],
        radius=30, fill=COR_AZUL
    )
    fonte_cta = _carregar_fonte(44, negrito=True)
    _texto_centralizado(draw, "📲  DM para orçamento gratuito!", cta_y + 28, fonte_cta, COR_BRANCO)

    # ── Hashtags ─────────────────────────────────────────────────────
    fonte_hash = _carregar_fonte(28)
    _texto_centralizado(draw, hashtags, H - 80, fonte_hash, (150, 190, 220))

    # ── Salvar ────────────────────────────────────────────────────────
    nome_arquivo = f"story_{post_id}.png"
    caminho = os.path.join(OUTPUT_DIR, nome_arquivo)
    img.save(caminho, "PNG", quality=95)
    return caminho

async def criar_story_async(titulo: str, legenda: str, hashtags: str, tema: str, emoji: str, post_id: int) -> str:
    return await asyncio.to_thread(criar_story, titulo, legenda, hashtags, tema, emoji, post_id)
