import asyncio
import aiohttp
import datetime
import os
import re
from typing import Dict, List, Optional


class IsThereAnyDealScraper:
    """Promoções via API v2 da IsThereAnyDeal (https://docs.isthereanydeal.com/)."""

    BASE_URL = "https://api.isthereanydeal.com/deals/v2"
    SHOP_STEAM = 61        # id da Steam na ITAD
    LIMITE_MAXIMO = 200    # limite por requisição da API v2

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        # Lido no runtime: o .env é carregado depois dos imports iniciais.
        self.key = (os.getenv("ITAD_KEY") or "").strip()

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers={"Accept": "application/json"})
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    @staticmethod
    def _para_epoch(valor) -> str:
        """Converte a data ISO 8601 da ITAD no timestamp usado pelo banco/filtro."""
        if not valor:
            return ""
        try:
            data = datetime.datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
        except ValueError:
            return ""
        if data.tzinfo is None:
            data = data.replace(tzinfo=datetime.timezone.utc)
        return str(int(data.timestamp()))

    def _extrair_promocao(self, item: Dict) -> Optional[Dict]:
        # DLCs e pacotes podem abrir páginas de conteúdo adicional, não do jogo.
        if item.get("type") != "game":
            return None

        deal = item.get("deal") or {}
        link = deal.get("url") or ""
        if not link:
            return None

        preco = (deal.get("price") or {}).get("amount")
        if preco is None:
            return None
        preco_antigo = (deal.get("regular") or {}).get("amount") or 0

        desconto = deal.get("cut")
        if desconto is None:
            if preco_antigo > preco:
                desconto = round(((preco_antigo - preco) / preco_antigo) * 100)
            else:
                desconto = 0

        assets = item.get("assets") or {}
        banner = ""
        for chave in ("banner600", "banner400", "banner300", "banner145", "boxart"):
            if assets.get(chave):
                banner = assets[chave]
                break

        return {
            "nome": item.get("title") or "Promoção",
            "preco_antigo": float(preco_antigo),
            "preco": float(preco),
            "desconto": int(desconto),
            "link": link,
            "banner": banner,
            "data_fim": self._para_epoch(deal.get("expiry")),
        }

    async def fetch_featured(self, limit: int = 20, offset: int = 0) -> List[Dict]:
        """Busca ofertas ativas da Steam priorizando jogos em alta."""
        if not self.key:
            print("[IsThereAnyDeal] ITAD_KEY não configurada no .env; nenhuma promoção coletada.")
            return []

        limit = max(1, min(int(limit), self.LIMITE_MAXIMO))
        params = {
            "key": self.key,
            "country": "BR",
            "shops": str(self.SHOP_STEAM),
            "sort": "-trending",
            "nondeals": "false",
            "limit": str(limit),
            "offset": str(max(0, offset)),
        }

        try:
            async with self.session.get(
                self.BASE_URL, params=params, timeout=aiohttp.ClientTimeout(total=20)
            ) as resp:
                if resp.status in (401, 403):
                    print(f"[IsThereAnyDeal] Chave inválida ou sem permissão (HTTP {resp.status}). Confira ITAD_KEY.")
                    return []
                if resp.status == 429:
                    print("[IsThereAnyDeal] Limite de requisições atingido (HTTP 429).")
                    return []
                if resp.status != 200:
                    print(f"[IsThereAnyDeal] Resposta inesperada (HTTP {resp.status}).")
                    return []
                if "application/json" not in resp.headers.get("Content-Type", "").lower():
                    print("[IsThereAnyDeal] Resposta não-JSON; ignorando.")
                    return []

                data = await resp.json(content_type=None)
        except Exception as e:
            print(f"[IsThereAnyDeal] Erro ao buscar promoções: {e}")
            return []

        if not isinstance(data, dict):
            print("[IsThereAnyDeal] Formato de resposta inesperado; ignorando.")
            return []

        promos = []
        vistos = set()
        for item in data.get("list") or []:
            promo = self._extrair_promocao(item)
            if not promo or promo["link"] in vistos:
                continue
            vistos.add(promo["link"])
            promos.append(promo)

        return promos[:limit]


class EpicScraper:
    HASH_SLUG = re.compile(r"^[0-9a-f]{32}$")

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None

    @classmethod
    def _slug_pagina(cls, elem: Dict) -> str:
        """Descobre o slug real da página do produto na Epic Games Store.

        O campo `urlSlug` costuma vir como hash (ex.: "7ca01ab906ad4eff92d4ed1efa5fbfcb"),
        que gera link 404. O slug usado pela loja está em offerMappings/catalogNs.
        """
        def extrair(mappings) -> str:
            if not isinstance(mappings, list):
                return ""
            for mapping in mappings:
                if isinstance(mapping, dict) and mapping.get("pageType") == "productHome" and mapping.get("pageSlug"):
                    return mapping["pageSlug"]
            for mapping in mappings:
                if isinstance(mapping, dict) and mapping.get("pageSlug"):
                    return mapping["pageSlug"]
            return ""

        product_slug = elem.get("productSlug") or ""
        if product_slug:
            product_slug = product_slug.split("/")[0]

        candidatos = [
            extrair(elem.get("offerMappings")),
            extrair((elem.get("catalogNs") or {}).get("mappings")),
            product_slug,
            elem.get("urlSlug") or "",
        ]

        for slug in candidatos:
            slug = str(slug or "").strip()
            if slug and not cls.HASH_SLUG.match(slug):
                return slug
        return ""

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers={"Accept": "application/json"})
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def fetch_free(self, limit: int) -> List[Dict]:
        session = self.session or aiohttp.ClientSession(headers={"Accept": "application/json"})
        should_close = self.session is None
        try:
            async with session.get(
                "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions?locale=pt-BR&country=BR&allowCountries=BR",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status != 200:
                    return []

                data = await resp.json()
                elementos = data.get("data", {}).get("Catalog", {}).get("searchStore", {}).get("elements", [])
                jogos = []
                for elem in elementos:
                    if len(jogos) >= limit:
                        break
                    try:
                        price_block = (elem.get("price") or {}).get("totalPrice") or {}
                        preco = price_block.get("discountPrice")
                        if preco not in (0, "0"):
                            continue

                        slug = self._slug_pagina(elem)
                        if not slug:
                            continue

                        imagens = elem.get("keyImages") or []
                        banner = next(
                            (img.get("url") for img in imagens if img.get("type") == "OfferImageWide"),
                            imagens[0].get("url") if imagens else None,
                        )

                        promocoes = elem.get("promotions") or {}
                        promo_offers = promocoes.get("promotionalOffers") or []
                        data_inicio = ""
                        data_fim = ""
                        if promo_offers:
                            offers = promo_offers[0].get("promotionalOffers") or []
                            if offers:
                                data_inicio = offers[0].get("startDate", "")
                                data_fim = offers[0].get("endDate", "")

                        jogos.append({
                            "nome": elem.get("title"),
                            "link": f"https://store.epicgames.com/pt-BR/p/{slug}",
                            "banner": banner,
                            "data_inicio": data_inicio,
                            "data_fim": data_fim,
                        })
                    except Exception:
                        continue
                return jogos[:limit]
        except Exception as e:
            print(f"[EpicScraper] Erro ao buscar grátis: {e}")
            return []
        finally:
            if should_close:
                await session.close()


# Funções de coleta assíncronas (compatíveis com smartpoller.py)
async def coletar_promocoes_steam() -> List[Dict]:
    try:
        limite = int(os.getenv("ITAD_LIMIT", "20"))
    except ValueError:
        limite = 20

    async with IsThereAnyDealScraper() as scraper:
        return await scraper.fetch_featured(limite)


async def coletar_jogos_gratis_epic(limit: int = 5) -> List[Dict]:
    async with EpicScraper() as scraper:
        return await scraper.fetch_free(limit)


if __name__ == "__main__":
    # Teste rápido
    print(asyncio.run(coletar_promocoes_steam())[:3])
    print(asyncio.run(coletar_jogos_gratis_epic(3)))
