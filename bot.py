import discord
from discord.ext import commands
import asyncio
from discord import FFmpegPCMAudio
from pathlib import Path
import os
from dotenv import load_dotenv
import platform
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# 🔄 Debug opcional: verifica se o arquivo principal existe
logger.info("Verificando arquivo de áudio principal: %s",
            Path("audios/ruliEntrance.mp3").exists())

# Carregar variáveis do .env
load_dotenv()

if platform.system() == "Windows":
    FFMPEG_PATH = r"D:\Usuarios\eliva\Documents\Meus_projetos\botSetName\folderDiversidade\ffmpeg\bin\ffmpeg.exe"
else:
    FFMPEG_PATH = "ffmpeg"

TOKEN = os.getenv("DISCORD_TOKEN")
VOICE_CHANNEL_ID = int(os.getenv("VOICE_CHANNEL_ID"))

intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    logger.info("🤖 Bot conectado como %s (ID: %s)", bot.user, bot.user.id)
    logger.info("🔍 Áudios configurados:")
    for key, value in os.environ.items():
        if key.startswith("USER_AUDIO_"):
            user_id = key.split("_")[-1]
            tipo = "entrada" if "EXIT" not in key else "saída"
            path = Path(value.strip())
            status = "✅ Existe" if path.exists() else "❌ NÃO encontrado"
            logger.info(" - %s %s: %s %s", tipo.title(), user_id, path, status)

@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return
    logger.info("[DEBUG] %s alterou estado de voz: %s → %s", member.name, before.channel, after.channel)
    joined = after.channel and after.channel.id == VOICE_CHANNEL_ID and before.channel != after.channel
    left = before.channel and before.channel.id == VOICE_CHANNEL_ID and (after.channel is None or after.channel.id != VOICE_CHANNEL_ID)

    if joined:
        logger.info("🎧 %s entrou no canal monitorado", member.name)
        await tocar_audio(member, entrada=True, canal=after.channel)
    elif left:
        logger.info("🚪 %s saiu do canal monitorado", member.name)
        await tocar_audio(member, entrada=False, canal=before.channel)

async def tocar_audio(member, entrada: bool, canal):
    tipo = "entrada" if entrada else "saída"
    key_prefix = "USER_AUDIO_" if entrada else "USER_AUDIO_EXIT_"
    user_audio = os.getenv(f"{key_prefix}{member.id}")

    if not user_audio:
        logger.info("ℹ️ Nenhum áudio de %s configurado para %s (ID: %s)", tipo, member.name, member.id)
        return

    audio_path = Path(user_audio.strip())
    if not audio_path.exists():
        logger.error("❌ Arquivo de áudio de %s não encontrado: %s", tipo, audio_path)
        return

    try:
        logger.info("🔄 Tentando conectar ao canal de voz para áudio de %s...", tipo)
        vc = discord.utils.get(bot.voice_clients, guild=canal.guild)

        if vc:
            if vc.is_connected():
                if vc.channel != canal:
                    logger.info("↪️ Bot conectado em outro canal. Movendo...")
                    await vc.move_to(canal)
                else:
                    logger.info("ℹ️ Bot já está conectado no canal correto. Reutilizando conexão.")
            else:
                logger.warning("⚠️ Conexão de voz inválida. Tentando reconectar...")
                await vc.disconnect(force=True)
                vc = await canal.connect()
                logger.info("✅ Reconectado ao canal de voz (%s)!", tipo)
        else:
            vc = await canal.connect()
            logger.info("✅ Conectado ao canal de voz (%s)!", tipo)

        def after_playing(error):
            if error:
                logger.error("❌ Erro durante reprodução do áudio de %s: %s", tipo, error)
            else:
                logger.info("✅ Áudio de %s finalizado", tipo)

        logger.info("▶️ Tocando áudio de %s: %s", tipo, audio_path)
        vc.play(FFmpegPCMAudio(str(audio_path), executable=FFMPEG_PATH), after=after_playing)

        while vc.is_playing():
            await asyncio.sleep(1)

        logger.info("🔇 Desconectando do canal de voz...")
        await vc.disconnect()
        vc = None
        logger.info("✅ Desconectado com sucesso")

    except Exception as e:
        logger.exception("❌ Erro inesperado ao tocar áudio de %s", tipo)

bot.run(TOKEN)