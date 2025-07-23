import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import sys
import persistencia
import re

sys.stdout.reconfigure(encoding='utf-8')

def coletar_promocoes_steam():
    steam_url = "https://store.steampowered.com/api/featuredcategories/?cc=BR&l=portuguese"
    steam_resp = requests.get(steam_url)
    if steam_resp.status_code == 200:
        steam_data = steam_resp.json()
        steam_promos = [jogo for jogo in steam_data['specials']['items'] if jogo['discount_percent'] > 0]
        resultado = []
        for jogo in steam_promos:
            resultado.append({
                "nome": jogo.get('name'),
                "preco_antigo": jogo.get('original_price', 0) / 100,
                "preco": jogo.get('final_price', 0) / 100,
                "desconto": jogo.get('discount_percent', 0),
                "link": f"https://store.steampowered.com/app/{jogo.get('id')}",
                "banner": jogo.get('header_image'),
                "data_fim": jogo.get('discount_expiration', '')
            })
        return resultado
    else:
        return None

def coletar_jogos_gratis_steam(qtd=5):
    url = "https://store.steampowered.com/search/results/?query&maxprice=free&specials=1&supportedlang=brazilian&ndl=1&count=50&cc=BR&l=portuguese"
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    time.sleep(3)  # Aguarda o carregamento da página

    resultado = []
    # Cada jogo está em um <a class="search_result_row">
    jogos = driver.find_elements(By.XPATH, '//a[contains(@class, "search_result_row")]')
    for jogo in jogos:
        try:
            nome = jogo.find_element(By.XPATH, './/span[contains(@class, "title")]').text.strip()
            preco_antigo = jogo.find_element(By.XPATH, '//*[@class="discount_original_price"]').text.strip()
            preco = jogo.find_element(By.XPATH, '//*[@class="discount_final_price"]').text.strip()
            desconto = jogo.find_element(By.XPATH, '//*[@class="discount_pct"]').text.strip()
            # Pega o desconto, se existir
            try:
                desconto = jogo.find_element(By.XPATH, './/div[contains(@class, "search_discount")]').text.strip()
            except:
                desconto = ""
            # Pega o preço antigo e o preço atual
            try:
                preco_antigo = jogo.find_element(By.XPATH, './/strike').text.strip().replace("R$", "").replace(",", ".")
                preco_antigo = float(preco_antigo)
            except:
                preco_antigo = 0.0
            try:
                preco = jogo.find_element(By.XPATH, '//*[@class="discount_final_price"]').text.strip()
                if "Grátis" in preco or "R$0,00" in preco:
                    preco = 0.0
                else:
                    preco = preco.replace("R$", "").replace(",", ".")
                    preco = float(preco)
            except:
                preco = 0.0
            # Só pega jogos com desconto de 100% (promoção grátis)
            if "-100%" in desconto or preco == 0.0:
                link = jogo.get_attribute("href")

                # Usa regex para extrair o App ID da URL
                match = re.search(r'/app/(\d+)', link)
                if match:
                    app_id = match.group(1)
                    banner = f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app_id}/header.jpg"
                else:
                    banner = ""

                resultado.append({
                    "nome": nome,
                    "preco_antigo": preco_antigo,
                    "preco": preco,
                    "desconto": desconto,
                    "link": link,
                    "banner": banner,
                    "data_fim": ""
                })
            if len(resultado) >= qtd:
                break
        except Exception as e:
            print(f"[DEBUG] Erro ao coletar jogo: {e}")
            continue
    driver.quit()
    return resultado

def coletar_jogos_gratis_epic(qtd=5):
    epic_url = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions?locale=pt-BR&country=BR&allowCountries=BR"
    epic_resp = requests.get(epic_url)
    jogos_gratis = []
    if epic_resp.status_code == 200:
        epic_data = epic_resp.json()
        elementos = epic_data['data']['Catalog']['searchStore']['elements']
        for jogo in elementos:
            try:
                preco = jogo['price']['totalPrice']['discountPrice']
                if preco == 0:
                    imagens = jogo.get('keyImages', [])
                    banner = None
                    for img in imagens:
                        if img.get('type') == 'OfferImageWide':
                            banner = img.get('url')
                            break
                    if not banner and imagens:
                        banner = imagens[0].get('url')
                    # Busca datas de início e fim da promoção
                    data_inicio = ""
                    data_fim = ""
                    if jogo.get('promotions') and jogo['promotions'].get('promotionalOffers'):
                        ofertas = jogo['promotions']['promotionalOffers']
                        if ofertas and ofertas[0].get('offers'):
                            offer = ofertas[0]['offers'][0]
                            data_inicio = offer.get('startDate', '')
                            data_fim = offer.get('endDate', '')
                    jogos_gratis.append({
                        "nome": jogo.get('title', 'Título desconhecido'),
                        "link": f"https://store.epicgames.com/pt-BR/p/{jogo.get('productSlug') or jogo.get('urlSlug') or ''}",
                        "banner": banner,
                        "data_inicio": data_inicio,
                        "data_fim": data_fim
                    })
            except (KeyError, TypeError):
                continue
            if len(jogos_gratis) == qtd:
                break
    return jogos_gratis

def buscar_jogos_gratis_steam(qtd=5):
    dados = persistencia.carregar_disparados()
    jogos = dados.get("steam_gratis", [])
    if jogos:
        print("[DEBUG] Carregando jogos grátis do arquivo.")
        return jogos[:qtd]
    print("[DEBUG] Nenhum jogo grátis salvo, fazendo scraping...")
    jogos = coletar_jogos_gratis_steam(qtd)
    if jogos:
        dados["steam_gratis"] = jogos
        persistencia.salvar_disparados(dados)
    return jogos[:qtd]
