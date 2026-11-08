import asyncio
import aiohttp
import os
import re
from typing import Dict, List, Optional

class IsThereAnyDealScraper:
    BASE_URL = "https://api.isthereanydeal.com/v01/deals"

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.key = os.getenv("ITAD_KEY")

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers={"Accept": "application/json"})
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def _normalizar_payload(self, payload):
        if isinstance(payload, list):
            return payload
        if not isinstance(payload, dict):
            return []

        for key in ("list", "deals", "items", "games", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
        if "data" in payload and isinstance(payload["data"], dict):
            return self._normalizar_payload(payload["data"])
        if "data" in payload and isinstance(payload["data"], list):
            return payload["data"]
        return []

    def _extrair_texto(self, item, *keys):
        for key in keys:
            value = item.get(key)
            if value not in (None, ""):
                return value
        return ""

    def _extrair_preco(self, item):
        for key in ("price_new", "new_price", "price", "current_price", "amount"):
            value = item.get(key)
            if isinstance(value, (int, float)):
                return float(value)
        return 0.0

    def _extrair_preco_antigo(self, item):
        for key in ("price_old", "old_price", "normal_price", "list_price"):
            value = item.get(key)
            if isinstance(value, (int, float)):
                return float(value)
        return 0.0

    def _extrair_desconto(self, item):
        for key in ("cut", "discount", "sale", "save"):
            value = item.get(key)
            if value not in (None, ""):
                return int(value)
        old = self._extrair_preco_antigo(item)
        new = self._extrair_preco(item)
        if old and new and old > new:
            return int(round(((old - new) / old) * 100))
        return 0

    def _extrair_link(self, item):
        for key in ("url", "deal_url", "store_url", "link"):
            value = item.get(key)
            if value:
                return value
        game = item.get("game")
        if isinstance(game, dict):
            for key in ("url", "deal_url", "store_url", "link"):
                value = game.get(key)
                if value:
                    return value
        app_id = item.get("steam_id") or item.get("app_id") or item.get("steamAppId")
        if app_id:
            return f"https://store.steampowered.com/app/{app_id}"
        return ""

    def _extrair_banner(self, item):
        for key in ("image", "image_url", "thumb", "banner", "icon"):
            value = item.get(key)
            if value:
                return value
        game = item.get("game")
        if isinstance(game, dict):
            for key in ("image", "image_url", "thumb", "banner"):
                value = game.get(key)
                if value:
                    return value
        return ""

    async def fetch_featured(self, limit: int = 15) -> List[Dict]:
        params = {
            "country": "BR",
            "limit": str(limit),
            "sort": "price",
            "shop": "steam",
        }
        if self.key:
            params["key"] = self.key
        try:
            async with self.session.get(f"{self.BASE_URL}/list/", params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                items = self._normalizar_payload(data)
                promos = []
                for item in items:
                    link = self._extrair_link(item)
                    if not link:
                        continue
                    preco = self._extrair_preco(item)
                    preco_antigo = self._extrair_preco_antigo(item)
                    desconto = self._extrair_desconto(item)
                    if preco_antigo and preco_antigo > preco and desconto > 0:
                        promos.append({
                            "nome": self._extrair_texto(item, "title", "name", "game", "shop"),
                            "preco_antigo": float(preco_antigo),
                            "preco": float(preco),
                            "desconto": desconto,
                            "link": link,
                            "banner": self._extrair_banner(item),
                            "data_fim": self._extrair_texto(item, "expiry", "end", "expiration", "date")
                        })
                return promos[:limit]
        except Exception as e:
            print(f"[IsThereAnyDeal] Erro ao buscar promoções: {e}")
            return []

    async def fetch_free(self, limit: int = 5) -> List[Dict]:
        params = {
            "country": "BR",
            "limit": str(limit * 3),
            "shop": "steam",
            "sort": "price",
        }
        if self.key:
            params["key"] = self.key
        try:
            async with self.session.get(f"{self.BASE_URL}/list/", params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                items = self._normalizar_payload(data)
                jogos = []
                for item in items:
                    if len(jogos) >= limit:
                        break
                    preco = self._extrair_preco(item)
                    if preco != 0:
                        continue
                    link = self._extrair_link(item)
                    if not link:
                        continue
                    jogos.append({
                        "nome": self._extrair_texto(item, "title", "name", "game", "shop"),
                        "link": link,
                        "banner": self._extrair_banner(item),
                        "data_fim": self._extrair_texto(item, "expiry", "end", "expiration", "date"),
                    })
                return jogos
        except Exception as e:
            print(f"[IsThereAnyDeal] Erro ao buscar grátis: {e}")
            return []

class SteamScraper:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers={"Accept": "application/json"})
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def fetch_featured(self) -> Optional[List[Dict]]:
        try:
            async with self.session.get(
                "https://store.steampowered.com/api/featuredcategories?cc=BR&l=portuguese",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                content_type = resp.headers.get("Content-Type", "")
                if resp.status != 200:
                    return None
                if "application/json" not in content_type.lower():
                    print("[SteamScraper] Resposta HTML/anti-bot em featured; ignorando.")
                    return None
                data = await resp.json()
                specials = data.get("specials", {})
                items = specials.get("items", [])
                promos = []
                for item in items:
                    discount = item.get("discount_percent", 0)
                    if discount > 0:
                        promos.append({
                            "nome": item.get("name"),
                            "preco_antigo": float(item.get("original_price", 0) / 100) if item.get("original_price") else 0,
                            "preco": float(item.get("final_price", 0) / 100) if item.get("final_price") else 0,
                            "desconto": discount,
                            "link": f"https://store.steampowered.com/app/{item.get('id')}",
                            "banner": item.get("header_image"),
                            "data_fim": item.get("discount_expiration", "")
                        })
                return promos[:15]
        except (aiohttp.ContentTypeError, ValueError, TypeError) as e:
            print(f"[SteamScraper] Resposta inválida do Steam em featured: {e}")
            return None
        except Exception as e:
            print(f"[SteamScraper] Erro ao buscar promoções: {e}")
            return None

    async def fetch_free(self, limit: int) -> List[Dict]:
        try:
            async with self.session.get(
                "https://store.steampowered.com/search/results/?query&maxprice=free&specials=1&supportedlang=brazilian&ndl=1&count=50&cc=BR&l=portuguese",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                content_type = resp.headers.get("Content-Type", "")
                if resp.status != 200:
                    return []
                if "application/json" not in content_type.lower():
                    print("[SteamScraper] Resposta bloqueada/inválida do Steam; ignorando fallback.")
                    return []
                data = await resp.json()
                results = data.get("items", [])
                jogos = []
                for item in results:
                    if len(jogos) >= limit:
                        break
                    try:
                        preco_str = str(item.get("final_price", 0) / 100)
                        preco = float(preco_str) if preco_str.replace(".", "", 1).isdigit() else 0
                        if preco == 0:
                            app_match = re.search(r'/app/(\d+)', item.get('url', ''))
                            app_id = app_match.group(1) if app_match else "0"
                            jogos.append({
                                "nome": item.get("name"),
                                "link": item.get("url"),
                                "banner": f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app_id}/header.jpg",
                                "data_fim": ""
                            })
                    except Exception:
                        continue
                return jogos
        except (aiohttp.ContentTypeError, ValueError, TypeError) as e:
            print(f"[SteamScraper] Resposta inválida do Steam em free search: {e}")
            return []
        except Exception as e:
            print(f"[SteamScraper] Erro ao buscar grátis: {e}")
            return []

class EpicScraper:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None

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

                        slug = elem.get("productSlug") or elem.get("urlSlug")
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
async def coletar_promocoes_steam() -> Optional[List[Dict]]:
    async with IsThereAnyDealScraper() as scraper:
        deals = await scraper.fetch_featured(15)
        if deals:
            return deals

    async with SteamScraper() as scraper:
        return await scraper.fetch_featured()

async def coletar_jogos_gratis_steam(limit: int = 5) -> List[Dict]:
    print("[INFO] Steam free-games endpoint desativado: fonte bloqueada pelo anti-bot.")
    return []

async def coletar_jogos_gratis_epic(limit: int = 5) -> List[Dict]:
    async with EpicScraper() as scraper:
        return await scraper.fetch_free(limit)

if __name__ == "__main__":
    # Teste rápido
    asyncio.run(coletar_promocoes_steam())
    asyncio.run(coletar_jogos_gratis_steam(3))
    asyncio.run(coletar_jogos_gratis_epic(3))