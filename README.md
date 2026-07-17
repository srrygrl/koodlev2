# Koddle Server

Servidor de contas, amigos, chat em tempo real e sincronização de "ouvindo junto" pro Koddle.

Stack: **FastAPI** (Python) + **WebSocket** (chat em tempo real) + **MongoDB** (contas, amizades,
histórico de mensagens) + **JWT** (login).

## 1. Criar o banco de dados (MongoDB Atlas — grátis)

1. Acesse **https://www.mongodb.com/cloud/atlas/register** e crie uma conta.
2. Crie um cluster gratuito (**M0**, tier Free).
3. Em **"Database Access"**, crie um usuário de banco (usuário + senha — anota isso).
4. Em **"Network Access"**, clique em **"Add IP Address"** → **"Allow access from anywhere"**
   (`0.0.0.0/0`). Isso é necessário porque o Railway não tem um IP fixo previsível.
5. No cluster, clique em **"Connect"** → **"Drivers"** → copia a **connection string** (algo tipo
   `mongodb+srv://usuario:<password>@cluster0.xxxxx.mongodb.net/`).
6. Troca `<password>` pela senha que você criou no passo 3.

Essa string é o valor de `MONGODB_URI`.

## 2. Rodar local (pra testar antes de subir pro Railway)

1. Copia `.env.example` pra um arquivo chamado `.env` e preenche com seus valores reais
   (`MONGODB_URI` do passo 1, e qualquer texto aleatório longo pro `JWT_SECRET`).
2. Instala as dependências:
   ```
   pip install -r requirements.txt
   ```
3. Roda o servidor:
   ```
   uvicorn main:app --reload
   ```
4. Abre **http://127.0.0.1:8000/docs** no navegador — isso mostra uma interface interativa com
   todas as rotas (`/register`, `/login`, `/friends`, etc.) pra você testar direto no navegador,
   sem precisar escrever código nenhum ainda.

## 3. Deploy no Railway

1. Sobe essa pasta pra um repositório no GitHub (crie um repo novo, sobe esses arquivos).
2. Acesse **https://railway.app**, faça login com GitHub.
3. **"New Project"** → **"Deploy from GitHub repo"** → escolhe o repositório que você acabou de criar.
4. O Railway vai detectar o `Procfile` e o `requirements.txt` sozinho e começar a build.
5. Vai em **"Variables"** (dentro do projeto no Railway) e adiciona as mesmas três variáveis do
   `.env`: `MONGODB_URI`, `DB_NAME`, `JWT_SECRET`.
6. Depois do deploy terminar, vai em **"Settings" → "Networking" → "Generate Domain"** — isso te dá
   uma URL pública tipo `https://koddle-server-production.up.railway.app`.

Essa URL é o endereço que o Koddle vai usar pra se conectar ao servidor (tanto pra chamadas normais
`https://...` quanto pro WebSocket, trocando `https` por `wss`).

## 4. Testar se está no ar

```
curl https://sua-url.up.railway.app/
```
Deve responder `{"status":"ok","service":"koddle-server"}`.

## Como a API funciona (resumo)

- `POST /register` — `{"username": "...", "password": "..."}` → cria conta, devolve um token
- `POST /login` — mesma coisa, devolve token de quem já tem conta
- `GET /me` — dados da conta logada (precisa do token no header `Authorization: Bearer <token>`)
- `POST /friends/request` — `{"username": "amigo"}` → envia pedido de amizade
- `POST /friends/accept` / `POST /friends/decline` — aceita/recusa um pedido recebido
- `GET /friends` — lista de amigos (com quem está online agora)
- `GET /friends/requests` — pedidos pendentes (enviados e recebidos)
- `GET /messages/{usuario}` — histórico de conversa com esse amigo
- `WS /ws?token=...` — conexão em tempo real: manda `{"type":"chat","to":"amigo","text":"oi"}` pra
  conversar, ou `{"type":"now_playing","to":"amigo","title":"...","artist":"...","is_playing":true}`
  pra compartilhar o que está tocando

## Próximo passo

Esse servidor ainda não está conectado ao Koddle — ele funciona sozinho, testável pelo `/docs` ou
por `curl`. O próximo passo é adicionar a tela de login/cadastro e a aba de Amigos no Koddle,
fazendo ele se conectar nesse servidor.
