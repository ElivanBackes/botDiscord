import discord
from discord.ext import commands
import asyncio
from discord import FFmpegPCMAudio
from pathlib import Path
import os
from dotenv import load_dotenv

# 🔄 Debug opcional: verifica se o arquivo principal existe
print(Path("D:/Usuarios/eliva/Documents/Meus_projetos/botSetName/audios/ruliEntrance.mp3").exists())

# 📦 Carregar variáveis do .env
load_dotenv()

FFMPEG_PATH = r"D:\Usuarios\eliva\Documents\Meus_projetos\botSetName\folderDiversidade\ffmpeg\bin\ffmpeg.exe"
TOKEN = os.getenv("DISCORD_TOKEN")
VOICE_CHANNEL_ID = int(os.getenv("VOICE_CHANNEL_ID"))

intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# 🔊 Exibe os áudios mapeados ao iniciar o bot
@bot.event
async def on_ready():
    print(f"🤖 Bot conectado como {bot.user} (ID: {bot.user.id})")
    print("🔍 Áudios configurados:")
    
    for key, value in os.environ.items():
        if key.startswith("USER_AUDIO_"):
            user_id = key.split("_")[-1]
            tipo = "entrada" if "EXIT" not in key else "saída"
            path = Path(value.strip())
            status = "✅ Existe" if path.exists() else "❌ NÃO encontrado"
            print(f" - {tipo.title()} {user_id}: {path} {status}")

# 🎧 Evento de mudança de estado de voz
@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return

    print(f"[DEBUG] {member.name} alterou estado de voz: {before.channel} → {after.channel}")

    joined = after.channel and after.channel.id == VOICE_CHANNEL_ID and before.channel != after.channel
    left = before.channel and before.channel.id == VOICE_CHANNEL_ID and (after.channel is None or after.channel.id != VOICE_CHANNEL_ID)

    if joined:
        print(f"🎧 {member.name} entrou no canal monitorado")
        await tocar_audio(member, entrada=True, canal=after.channel)

    elif left:
        print(f"🚪 {member.name} saiu do canal monitorado")
        await tocar_audio(member, entrada=False, canal=before.channel)

# 🔈 Função para tocar o áudio (entrada ou saída)
async def tocar_audio(member, entrada: bool, canal):
    tipo = "entrada" if entrada else "saída"
    key_prefix = "USER_AUDIO_" if entrada else "USER_AUDIO_EXIT_"
    user_audio = os.getenv(f"{key_prefix}{member.id}")

    if not user_audio:
        print(f"ℹ️ Nenhum áudio de {tipo} configurado para {member.name} (ID: {member.id})")
        return

    audio_path = Path(user_audio.strip())
    if not audio_path.exists():
        print(f"❌ Arquivo de áudio de {tipo} não encontrado: {audio_path}")
        return

    try:
        print(f"🔄 Tentando conectar ao canal de voz para áudio de {tipo}...")
        vc = discord.utils.get(bot.voice_clients, guild=canal.guild)
        
        if vc:
            if vc.is_connected():
                if vc.channel != canal:
                    print("↪️ Bot conectado em outro canal. Movendo...")
                    await vc.move_to(canal)
                else:
                    print("ℹ️ Bot já está conectado no canal correto. Reutilizando conexão.")
            else:
                print("⚠️ Conexão de voz inválida. Tentando reconectar...")
                await vc.disconnect(force=True)
                vc = await canal.connect()
                print(f"✅ Reconectado ao canal de voz ({tipo})!")
        else:
            vc = await canal.connect()
            print(f"✅ Conectado ao canal de voz ({tipo})!")

        def after_playing(error):
            if error:
                print(f"❌ Erro durante reprodução do áudio de {tipo}: {error}")
            else:
                print(f"✅ Áudio de {tipo} finalizado")

        print(f"▶️ Tocando áudio de {tipo}: {audio_path}")
        vc.play(FFmpegPCMAudio(str(audio_path), executable=FFMPEG_PATH), after=after_playing)

        while vc.is_playing():
            await asyncio.sleep(1)

        print("🔇 Desconectando do canal de voz...")
        await vc.disconnect()
        vc = None # Forçar limpeza
        print("✅ Desconectado com sucesso")

    except Exception as e:
        print(f"❌ Erro inesperado ao tocar áudio de {tipo}: {e}")

# 🚀 Iniciar o bot
bot.run(TOKEN)
