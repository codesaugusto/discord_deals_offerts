import sqlite3
import datetime
import json
from typing import Dict, List

DB_FILE = "jogos_disparados.db"

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
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

def salvar_disparados(dados: Dict[str, List[Dict]]):
    conn = get_connection()
    c = conn.cursor()
    c.execute("BEGIN TRANSACTION")
    
    try:
        for key, items in dados.items():
            if not items:
                continue
            
            if key == "steam":
                c.execute('''
                    INSERT OR REPLACE INTO steam (nome, preco_antigo, preco, desconto, link, banner, data_fim, data_disparo)
                    VALUES (:nome, :preco_antigo, :preco, :desconto, :link, :banner, :data_fim, :data_disparo)
                ''')
                c.executemany('''
                    INSERT OR REPLACE INTO steam (nome, preco_antigo, preco, desconto, link, banner, data_fim, data_disparo)
                    VALUES (:nome, :preco_antigo, :preco, :desconto, :link, :banner, :data_fim, :data_disparo)
                ''', [{k: v for k, v in item.items()} for item in items])

            elif key == "epic":
                c.execute('''
                    INSERT OR REPLACE INTO epic (nome, link, banner, data_inicio, data_fim, data_disparo)
                    VALUES (:nome, :link, :banner, :data_inicio, :data_fim, :data_disparo)
                ''')
                c.executemany('''
                    INSERT OR REPLACE INTO epic (nome, link, banner, data_inicio, data_fim, data_disparo)
                    VALUES (:nome, :link, :banner, :data_inicio, :data_fim, :data_disparo)
                ''', [{k: v for k, v in item.items()} for item in items])

            elif key == "promocoes":
                c.execute('''
                    INSERT OR REPLACE INTO promocoes (nome, preco_antigo, preco, desconto, link, banner, data_fim, data_disparo)
                    VALUES (:nome, :preco_antigo, :preco, :desconto, :link, :banner, :data_fim, :data_disparo)
                ''')
                c.executemany('''
                    INSERT OR REPLACE INTO promocoes (nome, preco_antigo, preco, desconto, link, banner, data_fim, data_disparo)
                    VALUES (:nome, :preco_antigo, :preco, :desconto, :link, :banner, :data_fim, :data_disparo)
                ''', [{k: v for k, v in item.items()} for item in items])
        
        c.execute("COMMIT")
        print("[INFO] Dados salvos no SQLite.")
    except Exception as e:
        c.execute("ROLLBACK")
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