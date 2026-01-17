🤖 Sniper IA V3 - Binance Trading Master

O Sniper IA V3 é um sistema avançado de trading quantitativo automatizado, desenhado para operar no mercado de Futuros da Binance (USDT-M). O sistema utiliza uma combinação de indicadores técnicos clássicos e o poder de processamento do Agente Gemini (Google AI) para identificar reversões de tendência com alta probabilidade de lucro.

🚀 Principais Funcionalidades

Scanner Matrix IA: Monitorização em tempo real de 52 ativos simultâneos.

Estratégia de Reversão: Algoritmo focado em identificar exaustão de preço e pontos de viragem.

Cérebro Gemini IA: Integração com a API do Google GenAI para validação de sinais e gestão de saída.

Dashboard Profissional: Interface em React 19 com telemetria em tempo real (P&L, Balanço, Logs).

Execução Master: Sistema de "Retry" automático e tolerância a falhas de rede (Timeout Protection).

Gestão de Banca: Otimizado para contas pequenas (ex: $35) com cálculo dinâmico de lote.

🛠️ Stack Tecnológica

Backend (Core)

Python 3.10+: Motor principal de execução.

CCXT: Biblioteca para comunicação de baixa latência com a Binance API.

Python-Dotenv: Gestão segura de chaves e segredos.

API & Middleware

Node.js & Express: Servidor de ponte para comunicação entre o robô e o dashboard.

Socket.io: Transmissão de dados em tempo real.

Frontend (Dashboard)

React 19 + TypeScript: Interface moderna e tipada.

Tailwind CSS: Estilização premium com tema escuro (Binance Style).

Lucide React: Ícones de alta definição para monitorização técnica.

📦 Estrutura do Projecto

meu-bot/
├── backend-core-Python/    # Motor de Trading (Python)
│   ├── main.py             # Script principal com lógica de conexão
│   ├── bot_logic.py        # Estratégia de Reversão e IA
│   └── scanner.py          # Scanner de volatilidade
├── backend-api-Node.js/    # API de comunicação (Server)
├── frontend/               # Dashboard React (Interface)
└── .gitignore              # Proteção de chaves API


⚙️ Instalação e Configuração

1. Requisitos Prévios

Node.js instalado.

Python 3.10+ instalado.

Chaves API da Binance (com permissão de Futuros habilitada).

Chave API do Google Gemini.

2. Configuração do Backend (Python)

cd backend-core-Python
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
pip install ccxt python-dotenv requests


3. Configuração do Frontend (React)

cd frontend
npm install --legacy-peer-deps


4. Variáveis de Ambiente (.env)

Crie um ficheiro .env na raiz das pastas backend e frontend:

BINANCE_API_KEY=tua_chave_aqui
BINANCE_SECRET_KEY=teu_segredo_aqui
GEMINI_API_KEY=tua_chave_gemini


🚦 Como Rodar

Inicie o Servidor Node.js:

node backend-api-Node.js/server.js


Inicie o Dashboard:

npm run dev


Ligue o Motor Python:

python backend-core-Python/main.py


⚠️ Aviso de Risco (Disclaimer)

O trading de criptomoedas envolve um risco substancial de perda e não é adequado para todos os investidores. O uso de alavancagem pode trabalhar tanto contra si como a seu favor.

Este software é para fins educacionais e de automação pessoal.

Rentabilidade passada não garante lucros futuros.

Não somos responsáveis por perdas financeiras decorrentes do uso deste robô.

📄 Licença

Este projecto está sob a licença MIT. Consulte o ficheiro LICENSE para mais detalhes.

Desenvolvido com ❤️ para a comunidade Trading Master.
