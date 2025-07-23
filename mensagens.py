import persistencia
import coleta
import discord
import datetime
import time
import os
from dotenv import load_dotenv

load_dotenv()

GUILD_ID = int(os.getenv("GUILD_ID"))
CANAL_PROMOCOES_ID = int(os.getenv("CANAL_PROMOCOES_ID"))
CANAL_JOGOS_GRATIS_ID = int(os.getenv("CANAL_JOGOS_GRATIS_ID"))

class LinkButton(discord.ui.View):
    def __init__(self, url):
        super().__init__()
        self.add_item(discord.ui.Button(label="🔗 Link do Jogo", url=url))

# Logo da Steam
STEAM_LOGO = "https://store.cloudflare.steamstatic.com/public/shared/images/header/globalheader_logo.png"
# Logo da Epic Games
EPIC_LOGO = "https://brandlogos.net/wp-content/uploads/2021/10/epic-games-logo-512x512.png"

def formatar_data(timestamp):
    if not timestamp:
        return ""
    try:
        ts = int(timestamp)
        # Se for milissegundos, converte para segundos
        if ts > 9999999999:
            ts = ts // 1000
        return datetime.datetime.fromtimestamp(ts).strftime('%d/%m/%Y %H:%M')
    except Exception:
        return str(timestamp)

async def enviar_jogos_gratis_steam_epic(canal, qtd=3, persistir=True):
    disparados = persistencia.carregar_disparados()
    lojas = [
        {
            "nome": "Steam",
            "coletar": coleta.buscar_jogos_gratis_steam,  # Use a função persistente!
            "chave_json": "steam_gratis",
            "logo": STEAM_LOGO,
            "cor": 0x1b2838,
            "descricao": lambda jogo: "**GRÁTIS**",
            "data_inicio": None,
            "data_fim": lambda jogo: jogo.get("data_fim")
        },
        {
            "nome": "Epic Games",
            "coletar": coleta.coletar_jogos_gratis_epic,
            "chave_json": "epic",
            "logo": EPIC_LOGO,
            "cor": 0x313131,
            "descricao": lambda jogo: f"{jogo.get('descricao', '')}\n\n**GRÁTIS**",
            "data_inicio": lambda jogo: jogo.get("data_inicio"),
            "data_fim": lambda jogo: jogo.get("data_fim")
        }
    ]

    mensagens = []
    total_novos = 0
    for loja in lojas:
        chave = loja["chave_json"]
        if chave not in disparados:
            disparados[chave] = []

        if persistir:
            jogos = loja["coletar"](qtd * 2)
            print(f"[DEBUG] Jogos coletados da {loja['nome']}: {jogos}")
            novos = []
            for jogo in jogos:
                id_unico = jogo["link"]
                print(f"[DEBUG] Verificando jogo: {id_unico}")
                if not any(j.get("link") == id_unico for j in disparados[chave]):
                    print(f"[DEBUG] Novo jogo encontrado: {jogo['nome']}")
                    jogo["data_disparo"] = int(time.time())  # Adiciona timestamp aqui
                    novos.append(jogo)
                    disparados[chave].append(jogo)
                if len(novos) == qtd:
                    break
            # Sempre salva, mesmo se não houver novos, para garantir a existência da chave
            persistencia.salvar_disparados(disparados)
        else:
            novos = disparados.get(chave, [])[:qtd]
            if not novos:
                jogos = loja["coletar"](qtd * 2)
                novos = []
                for jogo in jogos:
                    id_unico = jogo["link"]
                    if id_unico not in [j.get("link") for j in disparados[chave]]:
                        novos.append(jogo)
                        disparados[chave].append(jogo)
                    if len(novos) == qtd:
                        break
                persistencia.salvar_disparados(disparados)


        total_novos += len(novos)
        for jogo in novos:
            embed = discord.Embed(
                title=jogo.get("nome", "Jogo"),
                url=jogo.get("link", ""),
                description=loja["descricao"](jogo),
                color=loja["cor"]
            )
            embed.set_author(name=loja["nome"])
            embed.set_thumbnail(url=loja["logo"])
            if jogo.get("banner"):
                embed.set_image(url=jogo["banner"])
            if loja["data_inicio"] and loja["data_inicio"](jogo):
                embed.add_field(name="📅 De", value=formatar_data(loja["data_inicio"](jogo)), inline=True)
            if loja["data_fim"] and loja["data_fim"](jogo):
                embed.add_field(name="⏰ Até", value=formatar_data(loja["data_fim"](jogo)), inline=True)
            view = LinkButton(jogo.get("link", ""))
            mensagens.append((embed, view))


    return mensagens
        

async def enviar_promocoes_steam(canal, qtd=None, persistir=True):
    guild = canal.guild
    chave = "steam"
    disparados = persistencia.carregar_disparados()
    disparados.setdefault(chave, [])

    mensagens = []
    novos = []

    # Se persistir for False, usamos os já salvos (reaproveitamento)
    if not persistir:
        novos = disparados[chave][:qtd]
    else:
        promocoes = coleta.coletar_promocoes_steam()
        for promo in promocoes:
            id_unico = promo["link"]
            if not any(p.get("link") == id_unico for p in disparados[chave]):
                print(f"[DEBUG] Nova promoção encontrada: {promo['nome']}")
                promo["data_disparo"] = int(time.time())  # Adiciona timestamp aqui
                novos.append(promo)
                disparados[chave].append(promo)
            if len(novos) == qtd:
                break
        persistencia.salvar_disparados(disparados)

    for promo in novos:
        embed = discord.Embed(
            title=promo["nome"],
            url=promo["link"],
            description=(
                f"{promo.get('descricao', '')}\n\n"
                f"💸 **De:** ~~R${promo['preco_antigo']:.2f}~~\n"
                f"💰 **Por:** R${promo['preco']:.2f}\n"
                f"🔻 **Desconto:** {promo['desconto']}%"
            ),
            color=0x1b2838
        )
        embed.set_author(name="Steam")
        embed.set_thumbnail(url=STEAM_LOGO)
        if promo.get("banner"):
            embed.set_image(url=promo["banner"])
        if promo.get("data_fim"):
            embed.add_field(name="🗓️ Até", value=formatar_data(promo["data_fim"]), inline=True)
        view = LinkButton(promo["link"])
        mensagens.append((embed, view))

    return mensagens



def limpar_expirados():
    data_atual = datetime.datetime.now()
    dados = persistencia.carregar_disparados()
    alterado = False

    for chave, lista in dados.items():
        if not isinstance(lista, list):
            continue

        lista_filtrada = []
        for item in lista:
            timestamp = item.get("data_fim")

            if timestamp:
                # Converte timestamp string/int para datetime
                try:
                    ts = int(timestamp)
                    if ts > 9999999999:  # milissegundos
                        ts = ts // 1000
                    data_fim = datetime.datetime.fromtimestamp(ts)
                    if data_fim < data_atual:
                        continue  # expirado
                except Exception:
                    pass  # erro na data, manter por segurança

            lista_filtrada.append(item)

        if len(lista_filtrada) != len(lista):
            dados[chave] = lista_filtrada
            alterado = True

    if alterado:
        persistencia.salvar_disparados(dados)
        print("[INFO] Dados expirados foram limpos.")
    else:
        print("[INFO] Nenhum dado expirado para limpar.")
