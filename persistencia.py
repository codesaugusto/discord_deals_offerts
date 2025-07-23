import json
import os
import datetime

DISPARADOS_FILE = "jogos_disparados.json"

def carregar_disparados():
    if not os.path.exists(DISPARADOS_FILE):
        return {"steam": [], "epic": []}
    with open(DISPARADOS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def salvar_disparados(data):
    with open(DISPARADOS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
def limpar_expirados():
    data_atual = datetime.datetime.now()
    dados = carregar_disparados()
    alterado = False
    uma_semana = datetime.timedelta(days=7)

    for chave, lista in dados.items():
        if not isinstance(lista, list):
            continue

        lista_filtrada = []
        for item in lista:
            timestamp = item.get("data_disparo")  # <-- usa o campo de disparo

            if timestamp:
                try:
                    ts = int(timestamp)
                    if ts > 9999999999:  # milissegundos
                        ts = ts // 1000
                    data_disparo = datetime.datetime.fromtimestamp(ts)
                    if data_atual - data_disparo > uma_semana:
                        continue  # já tem mais de uma semana, descarta
                except Exception:
                    pass  # erro na data, mantém por segurança

            lista_filtrada.append(item)

        if len(lista_filtrada) != len(lista):
            dados[chave] = lista_filtrada
            alterado = True

    if alterado:
        salvar_disparados(dados)
        print("[INFO] Dados antigos foram limpos (mais de 1 semana).")
    else:
        print("[INFO] Nenhum dado antigo para limpar.")
