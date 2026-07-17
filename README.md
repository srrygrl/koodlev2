# Koddle Server

Servidor de contas, amigos, chat em tempo real e sincronização de "ouvindo junto" pro Koddle.




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
