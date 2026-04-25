<h1 align="center">🎮 Discord Deals Offers Bot</h1>

<p align="center">
  Bot automatizado para monitorar e notificar ofertas e jogos gratuitos diretamente no Discord 🚀
</p>
<div align="center">
   <img alt="Preview 1" src="https://i.imgur.com/xGyb3nW.jpeg" width="900px">
</div>

---

## 📌 Sobre o Projeto

Este projeto tem como objetivo automatizar a coleta e o envio de notificações sobre jogos gratuitos e promoções nas principais plataformas digitais, como:

* Steam
* Epic Games
* Nuuvem

Utilizando Python, Selenium e consumo de APIs, o sistema extrai informações relevantes como:

* 💰 Preço atual
* 🏷️ Status da oferta (gratuito/em promoção)
* 🎮 Plataforma do jogo

Os dados coletados podem ser:

* Enviados automaticamente para um servidor no Discord
* Armazenados em planilhas Excel para análise posterior

---

## ⚙️ Tecnologias Utilizadas

* **Python**
* **Selenium** → Automação de navegação e scraping de páginas dinâmicas
* **APIs externas** → Coleta de dados estruturados
* **Pandas** → Manipulação e exportação de dados
* **Regex (re)** → Extração de informações específicas
* **OS** → Manipulação de arquivos no sistema

---

## 🖼️ Demonstração

<div align="center">
   <img alt="Preview 1" src="https://imgur.com/vnfp7Il.jpeg" width="300px">
   <img alt="Preview 2" src="https://imgur.com/NleohOU.jpg" width="390px">
</div>

---

## 🚀 Funcionalidades

* 🔍 Monitoramento automático de ofertas
* 🎮 Identificação de jogos gratuitos
* 🤖 Integração com Discord para envio de notificações
* ⏱️ Execução automatizada (pode ser agendada)

---

## 📦 Como Utilizar

### 1. Clone o repositório

```bash
git clone https://github.com/codesaugusto/discord_deals_offerts
cd discord_deals_offerts
```

### 2. Crie um ambiente virtual (opcional, mas recomendado)

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Execute o projeto

```bash
python main.py
```

---

## 📁 Estrutura do Projeto (exemplo)

```
discord_deals_offerts/
│
├── src/
│   ├── scrapers/
│   ├── services/
│   ├── utils/
│
├── data/
│   └── ofertas.xlsx
│
├── main.py
├── requirements.txt
└── README.md
```

---

## 💡 Possíveis Melhorias

* Integração com mais plataformas
* Sistema de cache para evitar requisições repetidas
* Deploy em servidor (ex: VPS ou Docker)
* Dashboard web para visualização das ofertas

---


<p align="center">
  Feito com 💻 por Dev Codes Augusto
</p>
