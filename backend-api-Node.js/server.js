import express from 'express';
import http from 'http';
import { Server } from 'socket.io';
import cors from 'cors';

/**
 * SERVIDOR PONTE API - SNIPER PRO V3 (MODO IA & SMC)
 * Este servidor funciona como o sistema nervoso central, ligando
 * o motor de trading em Python ao Dashboard React no navegador.
 */

const app = express();

// Configurações de Middleware
app.use(cors()); // Permite que o Dashboard se ligue de qualquer porta (ex: 5173)
app.use(express.json()); // Processa os dados JSON enviados pelo Python

const server = http.createServer(app);

// Configuração do Socket.io para baixa latência
const io = new Server(server, {
  cors: {
    origin: "*",
    methods: ["GET", "POST"]
  }
});

// Rota de Teste: Verificar se a ponte está online via navegador
app.get('/', (req, res) => {
  res.send('🚀 Sniper Pro V3 Bridge API is Online (ESM Mode)!');
});

/**
 * ENDPOINT: /api/update
 * Recebe a telemetria do Python (Saldo, PNL, Sinais da IA e Logs)
 */
app.post('/api/update', (req, res) => {
  const incomingData = req.body;

  if (!incomingData) {
    return res.status(400).json({ error: 'Nenhum dado recebido pelo robô.' });
  }

  // Retransmite para o Dashboard em tempo real
  io.emit('update_data', incomingData);

  // Log no terminal para monitorizar a atividade da ponte
  if (incomingData.log && incomingData.log.type === 'SUCCESS') {
    console.log(`[ORDEM] ${incomingData.log.message}`);
  }

  res.status(200).json({ status: 'success', message: 'Dados transmitidos ao Dashboard' });
});

// Eventos de Conexão do Dashboard
io.on('connection', (socket) => {
  console.log(`\n✅ Dashboard Conectado! ID: ${socket.id}`);
  
  socket.on('disconnect', () => {
    console.log(`❌ Dashboard Desconectado. ID: ${socket.id}`);
  });
});

// Definição da Porta (Deve ser a mesma configurada no main.py)
const PORT = 3000;

server.listen(PORT, '0.0.0.0', () => {
  console.log(`
  ======================================================
  🔥 SNIPER PRO V3 - PONTE DE DADOS IA ATIVA (ESM)
  ======================================================
  📡 Servidor Node.js a correr na porta: ${PORT}
  🔗 Endpoint Python: http://127.0.0.1:${PORT}/api/update
  💻 Dashboard: http://localhost:5173
  
  A aguardar decisões do Agente Gemini...
  ======================================================
  `);
});