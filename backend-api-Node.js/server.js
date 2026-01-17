import express from 'express';
import http from 'http';
import { Server } from 'socket.io';
import cors from 'cors';
import dotenv from 'dotenv';

dotenv.config();

const app = express();
app.use(cors());
app.use(express.json());

const server = http.createServer(app);
const io = new Server(server, {
  cors: { origin: "*", methods: ["GET", "POST"] }
});

// A porta deve ser dinâmica para o Render (process.env.PORT)
const PORT = process.env.PORT || 3000;

app.get('/', (req, res) => res.send('🚀 Sniper Pro V3 Bridge ONLINE'));

app.post('/api/update', (req, res) => {
  io.emit('update_data', req.body);
  res.status(200).send('OK');
});

io.on('connection', (socket) => {
  console.log(`✅ Dashboard Conectado! ID: ${socket.id}`);
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`🔥 Servidor Node.js a correr na porta: ${PORT}`);
});