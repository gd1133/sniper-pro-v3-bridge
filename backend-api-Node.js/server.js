import express from 'express';
import http from 'http';
import { Server } from 'socket.io';
import cors from 'cors';
import dotenv from 'dotenv';

// Carrega as variáveis de ambiente do ficheiro .env
dotenv.config();

const app = express();
const server = http.createServer(app);

/**
 * CONFIGURAÇÃO DO SOCKET.IO
 * Permite conexões de qualquer origem (CORS) para o Dashboard.
 */
const io = new Server(server, {
  cors: {
    origin: "*",
    methods: ["GET", "POST"]
  }
});

app.use(cors());
app.use(express.json());

// Memória temporária: evita que o Dashboard fique em branco ao ser atualizado
let lastMarketData = null;

/**
 * ROTA PRINCIPAL: Verificação de status
 */
app.get('/', (req, res) => {
  res.send('🚀 Sniper Pro V3 Bridge ONLINE (ESM Mode)');
});

/**
 * ROTA DE ATUALIZAÇÃO: O Robô Python chama este endpoint
 */
app.post('/api/update', (req, res) => {
  const data = req.body;
  
  if (data.market_data) {
    lastMarketData = data.market_data;
  }

  // IMPORTANTE: O nome do evento deve ser 'update' para coincidir com o Dashboard
  io.emit('update', data);
  
  const symbol = data.market_data?.symbol || 'Sinal de Sistema';
  console.log(`📡 Dados recebidos: ${symbol}`);
  
  res.status(200).send({ status: 'success' });
});

/**
 * GESTÃO DE CONEXÕES: Dashboard React
 */
io.on('connection', (socket) => {
  console.log(`✅ Dashboard Conectado! ID: ${socket.id}`);
  
  // Se já houver um trade em curso, envia os dados imediatamente ao conectar
  if (lastMarketData) {
    socket.emit('update', { 
      market_data: lastMarketData, 
      log: { 
        message: "Sincronizado com operação ativa.", 
        type: "info", 
        time: new Date().toLocaleTimeString() 
      } 
    });
  }

  socket.on('disconnect', () => {
    console.log('❌ Dashboard Desconectado.');
  });
});

// A porta deve ser dinâmica (process.env.PORT) para funcionar no Render/Nuvem
const PORT = process.env.PORT || 3000;

server.listen(PORT, '0.0.0.0', () => {
  console.log(`🔥 Servidor Ponte Master rodando na porta: ${PORT}`);
});