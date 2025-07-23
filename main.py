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

# permissoes do bot
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Bot {bot.user.name} esta online!")

    print("Servidores conectados:")
    for guild in bot.guilds:
        print(f"- {guild.name} (ID: {guild.id})")

    try:
        guild = discord.Object(id=GUILD_ID)
        synced = await bot.tree.sync(guild=guild)  # sincroniza comandos só nesse servidor
        print(f" {len(synced)} comandos de barra sincronizados no guild {GUILD_ID}.")
    except Exception as e:
        print(f"Erro ao sincronizar comandos: {e}")

    # limpar_expirados_diariamente.start()
    disparo_automatico_steam.start()
    # disparo_automatico_free.start()
    
@bot.tree.command(
    name="steam_ofertas",
    description="Mostra promoções de jogos da Steam", 
    guild=discord.Object(id=GUILD_ID))
async def steam_ofertas(interaction: discord.Interaction):
    await interaction.response.defer()
    mensagens_list = await mensagens.enviar_promocoes_steam(interaction.channel, persistir=False)
    await tratar_mensagens(mensagens_list, interaction)


@bot.tree.command(
    name="free_games",
    description="Mostra jogos grátis da Steam e Epic Games",
    guild=discord.Object(id=GUILD_ID)
)
async def free_games(interaction: discord.Interaction):
    await interaction.response.defer()
    mensagens_list = await mensagens.enviar_jogos_gratis_steam_epic(interaction.channel, persistir=False)
    await tratar_mensagens(mensagens_list, interaction)


@tasks.loop(hours=12)
async def disparo_automatico_steam():
    canal = bot.get_channel(CANAL_PROMOCOES_ID)
    if canal is None:
        print(f"Canal {CANAL_PROMOCOES_ID} não encontrado.")
        return
    mensagens_list = await mensagens.enviar_promocoes_steam(canal, persistir=True)
    await tratar_mensagens(mensagens_list, canal, tipo="promocao")



@tasks.loop(hours=12)  # Ajuste o intervalo depois
async def disparo_automatico_free():
    canal = bot.get_channel(CANAL_JOGOS_GRATIS_ID)
    if canal is None:
        print(f"Canal {CANAL_JOGOS_GRATIS_ID} não encontrado.")
        return
    mensagens_list = await mensagens.enviar_jogos_gratis_steam_epic(canal, persistir=True)
    await tratar_mensagens(mensagens_list, canal, tipo="gratis")

@tasks.loop(hours=24)
async def limpar_expirados_diariamente():
    persistencia.limpar_expirados()
    
async def tratar_mensagens(mensagens_list, destino, tipo="promocao"):
    # destino pode ser interaction ou canal (TextChannel)

    # Função auxiliar para enviar mensagens de forma genérica
    async def enviar_msg(conteudo=None, embed=None, view=None):
        if hasattr(destino, 'followup'):  # é interaction
            if conteudo:
                return await destino.followup.send(conteudo, allowed_mentions=discord.AllowedMentions.none())
            else:
                return await destino.followup.send(embed=embed, view=view)
        else:  # assume que é canal
            if conteudo:
                return await destino.send(conteudo, allowed_mentions=discord.AllowedMentions.none())
            else:
                return await destino.send(embed=embed, view=view)

    # 🔧 Aqui está a correção importante: passar o tipo corretamente
    if await tratar_mensagem_vazia(mensagens_list, destino, enviar_msg, tipo=tipo):
        return

    if len(mensagens_list) == 1 and isinstance(mensagens_list[0], str):
        await enviar_msg(conteudo=mensagens_list[0])
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


async def tratar_mensagem_vazia(mensagens_list, destino, enviar_msg, tipo="oferta"):
    if not mensagens_list:
        if tipo == "gratis":
            embed = discord.Embed(
                title="🎮 Nenhum jogo gratuito encontrado",
                description="No momento, não encontramos jogos grátis disponíveis na Steam ou Epic Games.\n\nTente novamente mais tarde!",
                color=0x1b2838
            )
        else:
            embed = discord.Embed(
                title="💸 Nenhuma oferta encontrada",
                description="Atualmente, não há novas promoções disponíveis.\n\nVolte mais tarde para conferir novamente!",
                color=0x1b2838
            )

        await enviar_msg(embed=embed)
        return True
    return False


if __name__ == "__main__":
    id_bot = os.getenv("ID_BOT")
    bot.run(id_bot)