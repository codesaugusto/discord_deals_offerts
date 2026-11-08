import sqlite3
import datetime
import json
from typing import Dict, List

import os as _os

# Usa caminho absoluto baseado no diretório do próprio script,
# garantindo que o .db fique junto do código (onde o Discloud mantém os arquivos).
DB_FILE = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "jogos_disparados.db")

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    # WAL mode melhora concorrência e reduz risco de corrupção
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    print(f"[DB] Inicializando banco em: {DB_FILE}")
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS steam (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            preco_antigo REAL,
            preco REAL,
            desconto INTEGER,
            link TEXT UNIQUE NOT NULL,
            banner TEXT,
            data_fim TEXT,
            data_disparo INTEGER DEFAULT (strftime('%s', 'now')),
            UNIQUE(link)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS epic (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            link TEXT UNIQUE NOT NULL,
            banner TEXT,
            data_inicio TEXT,
            data_fim TEXT,
            data_disparo INTEGER DEFAULT (strftime('%s', 'now')),
            UNIQUE(link)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS promocoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            preco_antigo REAL,
            preco REAL,
            desconto INTEGER,
            link TEXT UNIQUE NOT NULL,
            banner TEXT,
            data_fim TEXT,
            data_disparo INTEGER DEFAULT (strftime('%s', 'now')),
            UNIQUE(link)
        )
    ''')
    conn.commit()
    conn.close()

def carregar_disparados() -> Dict[str, List[Dict]]:
    dados = {"steam": [], "epic": [], "promocoes": []}
    conn = get_connection()
    c = conn.cursor()
    
    for key, table in [("steam", "steam"), ("epic", "epic"), ("promocoes", "promocoes")]:
        try:
            c.execute("SELECT * FROM " + table)
            rows = c.fetchall()
            dados[key] = [dict(row) for row in rows]
        except Exception:
            pass
    conn.close()
    return dados

def _preparar_item(item, campos):
    """Garante que o dict tenha todos os campos esperados (com None para ausentes)."""
    return {campo: item.get(campo) for campo in campos}


def salvar_disparados(dados: Dict[str, List[Dict]]):
    conn = get_connection()
    c = conn.cursor()

    CAMPOS_STEAM = ["nome", "preco_antigo", "preco", "desconto", "link", "banner", "data_fim", "data_disparo"]
    CAMPOS_EPIC = ["nome", "link", "banner", "data_inicio", "data_fim", "data_disparo"]
    CAMPOS_PROMO = ["nome", "preco_antigo", "preco", "desconto", "link", "banner", "data_fim", "data_disparo"]

    try:
        for key, items in dados.items():
            if not items:
                continue

            if key == "steam":
                c.executemany('''
                    INSERT OR IGNORE INTO steam (nome, preco_antigo, preco, desconto, link, banner, data_fim, data_disparo)
                    VALUES (:nome, :preco_antigo, :preco, :desconto, :link, :banner, :data_fim, :data_disparo)
                ''', [_preparar_item(item, CAMPOS_STEAM) for item in items])

            elif key == "epic":
                c.executemany('''
                    INSERT OR IGNORE INTO epic (nome, link, banner, data_inicio, data_fim, data_disparo)
                    VALUES (:nome, :link, :banner, :data_inicio, :data_fim, :data_disparo)
                ''', [_preparar_item(item, CAMPOS_EPIC) for item in items])

            elif key == "promocoes":
                c.executemany('''
                    INSERT OR IGNORE INTO promocoes (nome, preco_antigo, preco, desconto, link, banner, data_fim, data_disparo)
                    VALUES (:nome, :preco_antigo, :preco, :desconto, :link, :banner, :data_fim, :data_disparo)
                ''', [_preparar_item(item, CAMPOS_PROMO) for item in items])

        conn.commit()
        print("[INFO] Dados salvos no SQLite.")
    except Exception as e:
        conn.rollback()
        print(f"[ERRO] Falha ao salvar no SQLite: {e}")
    finally:
        conn.close()

def limpar_expirados():
    conn = get_connection()
    c = conn.cursor()
    c.execute("BEGIN TRANSACTION")
    
    data_atual = datetime.datetime.now()
    
    try:
        for key, table in [("steam", "steam"), ("epic", "epic"), ("promocoes", "promocoes")]:
            # 1. Remove itens expirados (data_fim < hoje)
            c.execute(f'''
                DELETE FROM {table}
                WHERE data_fim IS NOT NULL 
                AND strftime('%s', 'now') > strftime('%s', COALESCE(data_fim, 0))
            ''')
            
            # 2. Remove itens "mortos" (já disparados há mais de 1 semana)
            # Isso evita acumulação de históricos muito antigos que ocupam espaço.
            c.execute(f'''
                DELETE FROM {table}
                WHERE data_disparo IS NOT NULL
                AND (strftime('%s', 'now') - data_disparo) > 7 * 24 * 60 * 60
            ''')
        
        conn.commit()
        print("[INFO] Dados expirados e antigos limpos do SQLite.")
    except Exception as e:
        c.execute("ROLLBACK")
        print(f"[ERRO] Falha ao limpar dados: {e}")
    finally:
        conn.close()

# Função auxiliar para backup do JSON (mantém compatibilidade temporária)
def backup_para_json():
    dados = carregar_disparados()
    with open("jogos_disparados.json", "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    print("[INFO] Backup JSON criado.")

if __name__ == "__main__":
    init_db()
    # Teste rápido
    print(carregar_disparados())