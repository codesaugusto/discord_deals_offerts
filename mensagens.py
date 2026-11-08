import persistencia
import coleta
import discord
import time
import datetime
from dotenv import load_dotenv
import os
import asyncio

load_dotenv()

CANAL_PROMOCOES_ID = int(os.getenv("CANAL_PROMOCOES_ID"))
CANAL_JOGOS_GRATIS_ID = int(os.getenv("CANAL_JOGOS_GRATIS_ID"))
GUILD_ID = int(os.getenv("GUILD_ID"))

class LinkButton(discord.ui.View):
    def __init__(self, url: str = ""):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="🔗 Link do Jogo", url=url))

STEAM_LOGO = "https://store.cloudflare.steamstatic.com/public/shared/images/header/globalheader_logo.png"
EPIC_LOGO = "https://brandlogos.net/wp-content/uploads/2021/10/epic-games-logo-512x512.png"

def formatar_data(timestamp):
    if not timestamp:
        return ""
    try:
        ts = int(timestamp)
        if ts > 9999999999: ts //= 1000
        return discord.utils.format_dt(datetime.datetime.fromtimestamp(ts), style="d T")
    except Exception:
        return str(timestamp)


def _embed_de_promocao(item):
    nome = item.get("nome") or item.get("title") or "Promoção"
    link = item.get("link") or ""
    preco_antigo = float(item.get("preco_antigo", 0) or 0)
    preco = float(item.get("preco", 0) or 0)
    desconto = item.get("desconto", 0)
    banner = item.get("banner")
    descricao = item.get("descricao", "")

    embed = discord.Embed(
        title=nome,
        url=link,
        description=(
            f"{descricao}\n\n"
            f"💸 **De:** ~~R${preco_antigo:.2f}~~\n"
            f"💰 **Por:** R${preco:.2f}\n"
            f"🔻 **Desconto:** {desconto}%"
        ),
        color=0x1b2838
    )
    embed.set_author(name="Steam")
    embed.set_thumbnail(url=STEAM_LOGO)
    if banner:
        embed.set_image(url=banner)
    return embed, LinkButton(link)


def _embed_de_jogo_gratis(item):
    nome = item.get("nome") or item.get("title") or "Jogo grátis"
    link = item.get("link") or ""
    banner = item.get("banner")
    descricao = item.get("descricao", "**GRÁTIS**")
    loja = item.get("loja") or "Steam"
    logo = item.get("logo") or (EPIC_LOGO if loja == "Epic Games" else STEAM_LOGO)

    embed = discord.Embed(
        title=nome,
        url=link,
        description=descricao,
        color=0x313131 if loja == "Epic Games" else 0x1b2838
    )
    embed.set_author(name=loja)
    embed.set_thumbnail(url=logo)
    if banner:
        embed.set_image(url=banner)
    return embed, LinkButton(link)


async def enviar_jogos_gratis_steam_epic(canal, qtd=3, persistir=True):
    disparados = persistencia.carregar_disparados()
    chave = "epic"
    disparados.setdefault(chave, [])

    mensagens = []
    if persistir:
        jogos = await coleta.coletar_jogos_gratis_epic(qtd * 2)
        novos = []
        for jogo in jogos:
            if not any(j.get("link") == jogo.get("link") for j in disparados[chave]):
                jogo["data_disparo"] = int(time.time())
                jogo["loja"] = "Epic Games"
                novos.append(jogo)
                disparados[chave].append(jogo)
        persistencia.salvar_disparados(disparados)
    else:
        novos = disparados.get(chave, [])[:qtd]

    for jogo in novos:
        embed = discord.Embed(
            title=jogo.get("nome", "Jogo"),
            url=jogo.get("link", ""),
            description=f"{jogo.get('descricao', '')}\n\n**GRÁTIS**",
            color=0x313131
        )
        embed.set_author(name="Epic Games")
        embed.set_thumbnail(url=EPIC_LOGO)
        if jogo.get("banner"):
            embed.set_image(url=jogo["banner"])
        view = LinkButton(jogo.get("link", ""))
        mensagens.append((embed, view))

    return mensagens

async def enviar_promocoes_steam(canal, qtd=None, persistir=True):
    chave = "steam"
    disparados = persistencia.carregar_disparados()
    disparados.setdefault(chave, [])
    mensagens = []
    novos = []

    if not persistir:
        qtd = qtd or 5
        novos = disparados[chave][:qtd]
    else:
        promocoes = await coleta.coletar_promocoes_steam()
        for promo in promocoes:
            if not any(p.get("link") == promo.get("link") for p in disparados[chave]):
                print(f"[DEBUG] Nova promoção: {promo.get('nome')}")
                promo["data_disparo"] = int(time.time())
                novos.append(promo)
                disparados[chave].append(promo)
            if qtd is not None and len(novos) == qtd:
                break
        persistencia.salvar_disparados(disparados)

    for promo in novos:
        mensagens.append(_embed_de_promocao(promo))

    return mensagens

def limpar_expirados():
    data_atual = datetime.datetime.now()
    dados = persistencia.carregar_disparados()
    alterado = False

    for chave, lista in dados.items():
        if not isinstance(lista, list): continue
        lista_filtrada = []
        for item in lista:
            ts = item.get("data_disparo")
            if ts:
                try:
                    t = int(ts)
                    if t > 9999999999: t //= 1000
                    if data_atual - datetime.datetime.fromtimestamp(t) > datetime.timedelta(days=7):
                        continue
                except: pass
            lista_filtrada.append(item)

        if len(lista_filtrada) != len(lista):
            dados[chave] = lista_filtrada
            alterado = True

    if alterado:
        persistencia.salvar_disparados(dados)
        print("[INFO] Dados expirados limpos.")
        
async def tratar_mensagens(mensagens_list, destino, tipo="promocao"):
    async def enviar_msg(conteudo=None, embed=None, view=None):
        kwargs = {"allowed_mentions": discord.AllowedMentions.none()}
        if conteudo is not None:
            kwargs["content"] = conteudo
        if embed is not None:
            kwargs["embed"] = embed
        if view is not None:
            kwargs["view"] = view

        if hasattr(destino, 'followup'):
            return await destino.followup.send(**kwargs)
        else:
            return await destino.send(**kwargs)

    if not mensagens_list:
        embed = discord.Embed(title="Nenhuma oferta encontrada", description="Atualmente, não há novas promoções disponíveis.", color=0x1b2838)
        await enviar_msg(embed=embed)
        return

    for i, mensagem in enumerate(mensagens_list):
        if isinstance(mensagem, dict):
            if tipo == "promocao":
                mensagem = _embed_de_promocao(mensagem)
            else:
                mensagem = _embed_de_jogo_gratis(mensagem)

        if isinstance(mensagem, tuple):
            embed, view = mensagem
            await enviar_msg(embed=embed, view=view)
        else:
            await enviar_msg(conteudo=str(mensagem))

        if i < len(mensagens_list) - 1:
            await asyncio.sleep(3)