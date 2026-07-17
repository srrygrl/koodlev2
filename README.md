# Koddle

App de mesa (Windows) com visual inspirado no Spotify: detecta sozinho a música tocando no momento
(via qualquer player que exponha controle de mídia do Windows, como o app do Spotify) e:

- Atualiza seu status personalizado do Discord em tempo real com a letra sincronizada.
- Mostra a capa do álbum na tela.
- Deixa o fundo do app com a cor da capa, borrado/fosco (estilo "now playing" do Spotify).
- Tem navegação lateral: Início, Buscar, Sua Biblioteca, Recomendações, Amigos e Perfil.

Tudo isso funciona **sem precisar de nenhuma credencial da API do Spotify** — a detecção da música
usa o controle de mídia nativo do Windows, o mesmo que aparece na barra de tarefas.

## O que já funciona de verdade

- **Início**: capa, música, artista e letra sincronizada, tudo em tempo real, assim que você dá play
  em qualquer coisa no Spotify (ou outro player compatível).
- **Sua Biblioteca**: histórico das músicas tocadas na sessão atual.
- **Perfil**: capa, foto de perfil (com zoom), nome e bio, no estilo de uma rede social — tudo editável
  pelo botão "Editar perfil".
- **Configurações**: token do Discord, salvo em `config.json`, fora do código.
- **Amigos**: contas de verdade (cadastro/login), lista de amigos com status online, pedidos de
  amizade, chat em tempo real e "ouvir junto" (compartilha a música que está tocando com o amigo
  que você está conversando). Depende de um servidor próprio rodando à parte — veja `koddle-server/`.

## O que ainda falta

- **Buscar** e **Recomendações**: dependiam da API do Spotify, removida do Koddle. Ficam reservadas
  pra uma eventual nova fonte de dados no futuro.

## Amigos — servidor próprio

A aba Amigos se conecta a um servidor separado (pasta `koddle-server/`, FastAPI + MongoDB, hospedado
no Railway). O endereço do servidor já vem configurado no `app.js` (constante `FRIENDS_API_BASE`).

Cada pessoa que for usar o Koddle com você precisa criar a própria conta (usuário + senha) na aba
Amigos — é separado da conta do Discord ou do Spotify.

Se você precisar trocar o servidor de lugar no futuro, o único ajuste necessário é atualizar as
constantes `FRIENDS_API_BASE` e `FRIENDS_WS_BASE` no topo do bloco "Amigos" em `ui/app.js`.

## Como rodar

1. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```
   > No Windows, o pywebview usa o **Microsoft Edge WebView2** por baixo dos panos.
   > Ele já vem instalado por padrão no Windows 10/11 atualizados; se faltar, o Windows
   > baixa automaticamente na primeira execução (ou pegue em https://developer.microsoft.com/microsoft-edge/webview2/).

2. Rode o app:
   ```
   python app.py
   ```

3. Clique em **Configurações** na barra lateral, cole seu token do Discord e clique em **Salvar**.
   Se você abrir o app sem token configurado, uma tela vai te lembrar disso automaticamente.

4. Clique em **Iniciar sincronização**. Dê play em uma música no Spotify — a capa, a letra e o fundo
   dinâmico começam a atualizar sozinhos.

## Observação importante

Este app usa o token da sua própria conta do Discord pra editar o status automaticamente.
Isso tecnicamente vai contra os Termos de Serviço do Discord (que proíbem automação de contas de
usuário, os chamados "self-bots"). É um uso comum em projetos pessoais, mas fique ciente do risco.

## Estrutura de arquivos

```
koddle/
├── app.py              # backend Python (mídia, letras, Discord, cor da capa)
├── requirements.txt
├── koddle.spec          # configuração do PyInstaller pra gerar o .exe
├── build.bat            # gera o .exe com um clique (Windows)
├── icon.ico             # opcional — seu ícone customizado, se quiser
├── config.json          # criado automaticamente, guarda o token (não compartilhe)
└── ui/
    ├── index.html
    ├── style.css        # tema visual (glass escuro + cor dinâmica da capa)
    └── app.js           # troca de abas + ponte com o Python
```

## Gerando o executável (.exe)

Isso só funciona rodando no **Windows** (o Koddle depende de APIs do Windows, então o `.exe`
também só roda lá).

### Jeito fácil: um clique

1. Confirme que a pasta tem `app.py`, `requirements.txt`, `koddle.spec`, `build.bat` e a pasta `ui/`
   todos juntos.
2. Dê duplo clique em **`build.bat`** (ou rode `build.bat` num terminal dentro da pasta).
3. Espere terminar — pode demorar alguns minutos na primeira vez.
4. O executável aparece em **`dist\Koddle.exe`**.

O script instala as dependências, instala o PyInstaller e gera o `.exe` sozinho.

### Jeito manual

```
pip install -r requirements.txt
pip install pyinstaller
pyinstaller koddle.spec
```

### Ícone personalizado (opcional)

Se quiser um ícone customizado, coloque um arquivo **`icon.ico`** na mesma pasta do `app.py` antes
de gerar o executável — o `koddle.spec` já detecta e usa automaticamente se ele existir.

### Coisas importantes sobre o .exe gerado

- **Primeira execução**: o Windows SmartScreen provavelmente vai avisar "Windows protegeu seu PC",
  porque o executável não é assinado digitalmente. Clique em "Mais informações" → "Executar assim
  mesmo". Isso é normal para `.exe` gerados localmente com PyInstaller, não é um vírus.
- **WebView2**: o `.exe` ainda depende do Microsoft Edge WebView2 estar instalado no Windows (já vem
  por padrão no Windows 10/11 atualizados).
- **config.json**: o `.exe` cria/lê o `config.json` na mesma pasta onde ele está — leve os dois
  juntos se for mover o programa de lugar.
- **Antivírus**: alguns antivírus reclamam de executáveis `--onefile` do PyInstaller por serem
  "desconhecidos" (falso positivo comum, não é um problema real do código).
