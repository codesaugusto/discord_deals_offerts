import discord
import mensagens
import persistencia
import asyncio
from discord.ext import commands
from discord.ext import tasks
from mensagens import CANAL_PROMOCOES_ID, CANAL_JOGOS_GRATIS_ID, GUILD_ID
import os
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot {bot.user.name} está online!")
    for guild in bot.guilds:
        print(f"- {guild.name} (ID: {guild.id})")

    try:
        guild = discord.Object(id=GUILD_ID)
        synced = await bot.tree.sync(guild=guild)
        print(f"{len(synced)} comandos sincronizados no guild {GUILD_ID}.")
    except Exception as e:
        print(f"Erro ao sincronizar comandos: {e}")

    disparo_promocoes.start()
    disparo_free_games.start()
    limpar_expirados_diariamente.start()

@bot.tree.command(name="steam_ofertas", guild=discord.Object(id=GUILD_ID))
async def steam_ofertas(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        mensagens_list = await mensagens.enviar_promocoes_steam(interaction.channel, persistir=False)
        await mensagens.tratar_mensagens(mensagens_list, interaction)
    except Exception as e:
        print(f"[ERRO] steam_ofertas: {e}")

@bot.tree.command(name="free_games", guild=discord.Object(id=GUILD_ID))
async def free_games(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        mensagens_list = await mensagens.enviar_jogos_gratis_steam_epic(interaction.channel, persistir=False)
        await mensagens.tratar_mensagens(mensagens_list, interaction)
    except Exception as e:
        print(f"[ERRO] free_games: {e}")

@tasks.loop(minutes=5)
async def disparo_promocoes():
    canal = bot.get_channel(CANAL_PROMOCOES_ID)
    if not canal:
        print(f"Canal {CANAL_PROMOCOES_ID} não encontrado.")
        return
    try:
        import smartpoller
        mensagens_list = await smartpoller.coletar_novas_promocoes()
        if mensagens_list:
            import datetime
            hoje = datetime.datetime.now()
            validas = [m for m in mensagens_list if not (m.get("data_fim") and datetime.datetime.fromtimestamp(int(m["data_fim"])) < hoje)]
            if validas:
                await mensagens.tratar_mensagens(validas, canal, tipo="promocao")
                print(f"[INFO] {len(validas)} novas promoções enviadas.")
            else:
                print("[INFO] Todas as promoções filtradas como expiradas.")
    except Exception as e:
        print(f"[ERRO] Disparo Promoções: {e}")

@tasks.loop(minutes=5)
async def disparo_free_games():
    canal = bot.get_channel(CANAL_JOGOS_GRATIS_ID)
    if not canal:
        print(f"Canal {CANAL_JOGOS_GRATIS_ID} não encontrado.")
        return
    try:
        import smartpoller
        mensagens_list = await smartpoller.coletar_novas_gratis(3)
        if mensagens_list:
            await mensagens.tratar_mensagens(mensagens_list, canal, tipo="gratis")
            print(f"[INFO] {len(mensagens_list)} novos jogos grátis enviados.")
    except Exception as e:
        print(f"[ERRO] Disparo Free Games: {e}")

@tasks.loop(hours=24)
async def limpar_expirados_diariamente():
    try:
        persistencia.limpar_expirados()
    except Exception as e:
        print(f"[ERRO] Limpeza: {e}")

async def tratar_mensagens(mensagens_list, destino, tipo="promocao"):
    async def enviar_msg(conteudo=None, embed=None, view=None):
        if hasattr(destino, 'followup'):
            return await destino.followup.send(conteudo or embed or view, allowed_mentions=discord.AllowedMentions.none())
        else:
            return await destino.send(conteudo or embed or view, allowed_mentions=discord.AllowedMentions.none())

    if not mensagens_list:
        embed = discord.Embed(
            title="Nenhuma oferta encontrada",
            description="Atualmente, não há novas promoções disponíveis.",
            color=0x1b2838
        )
        await enviar_msg(embed=embed)
        return

    for i, mensagem in enumerate(mensagens_list):
        if i == len(mensagens_list) - 1:
            if isinstance(mensagem, tuple):
                embed, view = mensagem
                await enviar_msg(embed=embed, view=view)
            else:
                await enviar_msg(conteudo=mensagem)
        else:
            if isinstance(mensagem, tuple):
                embed, view = mensagem
                await enviar_msg(embed=embed, view=view)
            else:
                await enviar_msg(conteudo=mensagem)
            await asyncio.sleep(3)

if __name__ == "__main__":
    id_bot = os.getenv("ID_BOT")
    if not id_bot:
        print("[ERRO] Variável ID_BOT não definida no .env!")
        exit(1)

    persistencia.init_db()
    bot.run(id_bot)