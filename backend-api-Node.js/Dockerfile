# Imagem base de Node.js
FROM node:18-slim

WORKDIR /app

# Copia e instala as dependências do servidor
COPY package*.json ./
RUN npm install --production

# Copia o resto dos ficheiros da API
COPY . .

EXPOSE 3000

# Inicia o servidor Node
CMD ["node", "server.js"]