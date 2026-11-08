import asyncio
import json
from typing import List, Dict

import coleta

class PollerState:
    last_id = 0
    last_timestamp = 0

    @classmethod
    async def load_state(cls):
        try:
            with open("smartpoller_state.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                cls.last_id = int(data.get("last_id", 0))
                cls.last_timestamp = int(data.get("last_timestamp", 0))
        except Exception:
            pass

    @classmethod
    async def save_state(cls):
        try:
            with open("smartpoller_state.json", "w", encoding="utf-8") as f:
                json.dump({"last_id": cls.last_id, "last_timestamp": cls.last_timestamp}, f)
        except Exception:
            pass

async def coletar_novas_promocoes() -> List[Dict]:
    await PollerState.load_state()
    try:
        ofertas = await coleta.coletar_promocoes_steam()
        if not ofertas:
            return []

        # Mantém uma deduplicação leve sem depender do Steam antigo.
        novos = []
        for item in ofertas:
            link = item.get("link", "")
            if not link:
                continue
            if link not in [m.get("link") for m in novos]:
                novos.append(item)
        return novos
    except Exception as e:
        print(f"[SmartPoller] Erro ao coletar promoções via IsThereAnyDeal: {e}")
        return []

async def coletar_novas_gratis(qtd: int = 5) -> List[Dict]:
    await PollerState.load_state()
    try:
        epic_games = await coleta.coletar_jogos_gratis_epic(max(1, qtd))

        vistos = set()
        novos = []
        for item in epic_games:
            link = item.get("link", "")
            if not link or link in vistos:
                continue
            item_com_loja = dict(item)
            item_com_loja["loja"] = "Epic Games"
            vistos.add(link)
            novos.append(item_com_loja)
            if len(novos) >= qtd:
                break

        return novos[:qtd]
    except Exception as e:
        print(f"[SmartPoller] Erro ao coletar jogos grátis: {e}")
        return []