import asyncio
import time
from typing import List, Dict

import coleta
import persistencia


async def coletar_novas_promocoes() -> List[Dict]:
    """Coleta promoções e filtra as que já foram disparadas (consultando o banco)."""
    try:
        ofertas = await coleta.coletar_promocoes_steam()
        if not ofertas:
            return []

        # Carrega links já disparados do banco
        disparados = persistencia.carregar_disparados()
        links_disparados = {p.get("link") for p in disparados.get("steam", []) if p.get("link")}

        novos = []
        for item in ofertas:
            link = item.get("link", "")
            if not link:
                continue
            # Só inclui se ainda não foi disparado
            if link in links_disparados:
                continue
            if link in {m.get("link") for m in novos}:
                continue
            item["data_disparo"] = int(time.time())
            novos.append(item)

        # Salva os novos no banco para não repetir
        if novos:
            disparados.setdefault("steam", []).extend(novos)
            persistencia.salvar_disparados(disparados)
            print(f"[SmartPoller] {len(novos)} promoções novas registradas no banco.")

        return novos
    except Exception as e:
        print(f"[SmartPoller] Erro ao coletar promoções: {e}")
        return []


async def coletar_novas_gratis(qtd: int = 5) -> List[Dict]:
    """Coleta jogos grátis e filtra os que já foram disparados (consultando o banco)."""
    try:
        epic_games = await coleta.coletar_jogos_gratis_epic(max(1, qtd))

        # Carrega links já disparados do banco
        disparados = persistencia.carregar_disparados()
        links_disparados = {j.get("link") for j in disparados.get("epic", []) if j.get("link")}

        novos = []
        vistos = set()
        for item in epic_games:
            link = item.get("link", "")
            if not link or link in vistos:
                continue
            # Só inclui se ainda não foi disparado
            if link in links_disparados:
                continue
            item_com_loja = dict(item)
            item_com_loja["loja"] = "Epic Games"
            item_com_loja["data_disparo"] = int(time.time())
            vistos.add(link)
            novos.append(item_com_loja)
            if len(novos) >= qtd:
                break

        # Salva os novos no banco para não repetir
        if novos:
            disparados.setdefault("epic", []).extend(novos)
            persistencia.salvar_disparados(disparados)
            print(f"[SmartPoller] {len(novos)} jogos grátis novos registrados no banco.")

        return novos[:qtd]
    except Exception as e:
        print(f"[SmartPoller] Erro ao coletar jogos grátis: {e}")
        return []