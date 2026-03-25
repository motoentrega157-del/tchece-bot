import google.generativeai as genai
import os
import random
import asyncio
from typing import AsyncGenerator
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY", ""))

TEMAS = [
    {
        "nome": "Bateria",
        "emoji": "🔋",
        "exemplos": ["bateria que dura pouco", "carregamento lento", "bateria inchada", "como economizar bateria"]
    },
    {
        "nome": "Tela",
        "emoji": "📱",
        "exemplos": ["tela trincada", "tela piscando", "touch não funciona", "linha na tela"]
    },
    {
        "nome": "Câmera",
        "emoji": "📷",
        "exemplos": ["câmera embaçada", "fotos com manchas", "câmera trava", "flash não funciona"]
    },
    {
        "nome": "Carregador",
        "emoji": "⚡",
        "exemplos": ["porta USB solta", "carregamento interrompido", "carregador original vs pirata", "carregamento sem fio"]
    },
    {
        "nome": "Software",
        "emoji": "🔧",
        "exemplos": ["celular travando", "app que fecha sozinho", "memória cheia", "atualização de sistema"]
    },
    {
        "nome": "Água",
        "emoji": "💧",
        "exemplos": ["celular molhado", "o que fazer se cair na água", "resistente à água", "arroz para celular"]
    },
    {
        "nome": "Manutenção Preventiva",
        "emoji": "🛡️",
        "exemplos": ["quando levar para revisão", "sinais de problema", "como cuidar do celular", "proteção e capinha"]
    },
    {
        "nome": "Curiosidade Tech",
        "emoji": "💡",
        "exemplos": ["como funciona o touch screen", "por que o celular esquenta", "processador do celular", "5G explicado"]
    },
]

async def gerar_conteudo(tema_forcado: str = None) -> AsyncGenerator[dict, None]:
    """
    Gerador assíncrono que faz stream do progresso da geração de conteúdo.
    Yields dicts: {"tipo": "log"|"conteudo"|"erro", "dados": ...}
    """
    tema = random.choice(TEMAS)
    if tema_forcado:
        for t in TEMAS:
            if tema_forcado.lower() in t["nome"].lower():
                tema = t
                break

    assunto = random.choice(tema["exemplos"])

    yield {"tipo": "log", "dados": f"🤔 Escolhendo tema: {tema['emoji']} {tema['nome']}..."}
    await asyncio.sleep(0.5)

    yield {"tipo": "log", "dados": f"💡 Assunto selecionado: {assunto}"}
    await asyncio.sleep(0.5)

    yield {"tipo": "log", "dados": "✍️ Conectando com IA Gemini para gerar conteúdo..."}
    await asyncio.sleep(0.3)

    prompt = f"""
Você é um especialista em marketing digital para a empresa "Tchê Celulares", uma assistência técnica especializada em reparo de celulares.

Crie um conteúdo para um Story do Instagram sobre o seguinte assunto: **{assunto}** (categoria: {tema['nome']}).

Retorne EXATAMENTE neste formato JSON (sem markdown, sem explicações):
{{
    "titulo": "Título chamativo com no máximo 6 palavras, pode ter emoji",
    "legenda": "Texto informativo de 3-4 frases curtas e diretas sobre o assunto. Use linguagem casual e amigável. Pode ter emojis. Termine com um call-to-action como 'Precisa de ajuda? Fala com a gente! 📲'",
    "hashtags": "#tchêcelulares #assistenciatecnica #celular #dica #reparo"
}}

Regras:
- Linguagem: português brasileiro, informal e amigável  
- NÃO use jargão técnico demais
- O título deve ser impactante para parar o dedo do usuário
- A legenda deve entregar valor real (dica, alerta, informação útil)
"""

    try:
        model = genai.GenerativeModel("gemini-2.0-flash")

        yield {"tipo": "log", "dados": "🧠 IA analisando e criando conteúdo..."}

        response = await asyncio.to_thread(
            model.generate_content, prompt
        )

        texto = response.text.strip()
        # Limpar possíveis blocos de código markdown
        if texto.startswith("```"):
            texto = texto.split("```")[1]
            if texto.startswith("json"):
                texto = texto[4:]
        texto = texto.strip()

        import json
        dados = json.loads(texto)

        yield {"tipo": "log", "dados": "✅ Conteúdo gerado com sucesso!"}
        await asyncio.sleep(0.3)

        yield {
            "tipo": "conteudo",
            "dados": {
                "titulo": dados["titulo"],
                "legenda": dados["legenda"],
                "hashtags": dados.get("hashtags", "#tchêcelulares"),
                "tema": tema["nome"],
                "emoji": tema["emoji"],
                "assunto": assunto,
            }
        }

    except Exception as e:
        yield {"tipo": "erro", "dados": f"Erro ao gerar conteúdo: {str(e)}"}
