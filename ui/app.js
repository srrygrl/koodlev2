// ============================================================
// Estado local
// ============================================================
let isRunning = false;

// ============================================================
// Faz o Koddle parecer um app de mesa, não um site:
// - links sempre abrem no navegador padrão do Windows, nunca numa
//   janela nova dentro do próprio app
// - sem menu de botão direito estilo navegador (Voltar/Recarregar/Inspecionar)
// - sem seleção de texto solta pela tela (fora de campos de digitar)
// ============================================================
function openExternal(url) {
  if (!url || !window.pywebview) return;
  window.pywebview.api.open_external(url);
}

document.addEventListener("contextmenu", (e) => {
  const tag = e.target.tagName;
  if (tag !== "INPUT" && tag !== "TEXTAREA") {
    e.preventDefault();
  }
});

document.addEventListener("selectstart", (e) => {
  const tag = e.target.tagName;
  if (tag !== "INPUT" && tag !== "TEXTAREA") {
    e.preventDefault();
  }
});

document.addEventListener(
  "wheel",
  (e) => {
    if (e.ctrlKey) e.preventDefault();
  },
  { passive: false }
);

document.addEventListener("keydown", (e) => {
  if (e.ctrlKey && ["+", "-", "=", "0"].includes(e.key)) {
    e.preventDefault();
  }
});
const historySeen = new Set();

// ============================================================
// Navegação entre abas
// ============================================================
function switchTab(tab) {
  document.querySelectorAll(".nav-item").forEach((el) => {
    el.classList.toggle("is-active", el.dataset.tab === tab);
  });
  document.querySelectorAll(".panel").forEach((el) => {
    el.classList.toggle("hidden", el.id !== `tab-${tab}`);
  });
}

document.querySelectorAll(".nav-item").forEach((btn) => {
  btn.addEventListener("click", () => switchTab(btn.dataset.tab));
});

// ============================================================
// Botão iniciar/parar
// ============================================================
const toggleBtn = document.getElementById("toggleBtn");
const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");
const stateTag = document.getElementById("stateTag");
const profileState = document.getElementById("profileState");

toggleBtn.addEventListener("click", async () => {
  if (!window.pywebview) return;

  if (!isRunning) {
    const result = await window.pywebview.api.start();
    if (result && result.error) {
      setStatus("off", result.error);
      return;
    }
    isRunning = true;
    statusText.textContent = "Parar sincronização";
    setStatus("loading", "Procurando reprodução…");
  } else {
    await window.pywebview.api.stop();
    isRunning = false;
    statusText.textContent = "Iniciar sincronização";
    setStatus("off", "Parado");
  }
});

function setStatus(kind, label) {
  statusDot.classList.remove("is-loading", "is-live");
  if (kind === "loading") statusDot.classList.add("is-loading");
  if (kind === "live") statusDot.classList.add("is-live");
  stateTag.textContent = label;
  profileState.textContent = label;
}

// ============================================================
// Configurações (token do Discord)
// ============================================================
const tokenInput = document.getElementById("tokenInput");
const saveTokenBtn = document.getElementById("saveTokenBtn");
const saveHint = document.getElementById("saveHint");

saveTokenBtn.addEventListener("click", async () => {
  if (!window.pywebview) return;
  await window.pywebview.api.save_token(tokenInput.value.trim());
  saveHint.textContent = "Salvo.";
  setTimeout(() => (saveHint.textContent = ""), 2500);
  if (tokenInput.value.trim()) hideGate();
});

// ============================================================
// Elementos "tocando agora"
// ============================================================
const coverArt = document.getElementById("coverArt");
const coverPlaceholder = document.getElementById("coverPlaceholder");
const trackTitle = document.getElementById("trackTitle");
const trackArtist = document.getElementById("trackArtist");
const lyricLine = document.getElementById("lyricLine");
const timeTag = document.getElementById("timeTag");
const bgWash = document.getElementById("bgWash");
const historyList = document.getElementById("historyList");

function formatTime(seconds) {
  const s = Math.max(0, Math.floor(seconds || 0));
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${String(m).padStart(2, "0")}:${String(r).padStart(2, "0")}`;
}

function setAccentColor(rgb) {
  if (!rgb) return;
  const root = document.documentElement.style;
  root.setProperty("--accent-r", rgb[0]);
  root.setProperty("--accent-g", rgb[1]);
  root.setProperty("--accent-b", rgb[2]);
}

function setCoverImage(dataUri) {
  if (dataUri) {
    coverArt.src = dataUri;
    coverArt.classList.add("is-visible");
    coverPlaceholder.classList.add("is-hidden");
    bgWash.style.setProperty("--cover-url", `url(${dataUri})`);
  } else {
    coverArt.classList.remove("is-visible");
    coverPlaceholder.classList.remove("is-hidden");
    bgWash.style.removeProperty("--cover-url");
  }
}

function addToHistory(title, artist, art) {
  const key = `${title}::${artist}`;
  if (historySeen.has(key)) return;
  historySeen.add(key);

  const emptyMsg = historyList.querySelector(".empty-state");
  if (emptyMsg) emptyMsg.remove();

  const li = document.createElement("li");
  li.className = "track-row";
  li.innerHTML = `
    <img src="${art || ""}" alt="" onerror="this.style.visibility='hidden'" />
    <div class="track-row-info">
      <div class="track-row-title"></div>
      <div class="track-row-artist"></div>
    </div>
  `;
  li.querySelector(".track-row-title").textContent = title;
  li.querySelector(".track-row-artist").textContent = artist;
  historyList.prepend(li);
}

// ============================================================
// Ponte: Python chama window.updateState(payload)
// ============================================================
window.updateState = function (payload) {
  switch (payload.type) {
    case "state":
      setStatus(payload.live ? "live" : "loading", payload.label);
      break;

    case "song":
      trackTitle.textContent = payload.title || "Nada tocando ainda";
      trackArtist.textContent = payload.artist || "";
      setCoverImage(payload.art || null);
      setAccentColor(payload.color || null);
      if (payload.title) addToHistory(payload.title, payload.artist, payload.art);
      break;

    case "lyric":
      lyricLine.textContent = payload.text || "…";
      timeTag.textContent = formatTime(payload.position);
      break;

    case "error":
      setStatus("off", "Erro: " + payload.message);
      isRunning = false;
      statusText.textContent = "Iniciar sincronização";
      break;
  }
};

// ============================================================
// Gate inicial — pede o token do Discord antes de usar
// ============================================================
const gateOverlay = document.getElementById("gateOverlay");
const gateClose = document.getElementById("gateClose");
const gateGoSettings = document.getElementById("gateGoSettings");

function showGate() {
  gateOverlay.classList.remove("hidden");
}
function hideGate() {
  gateOverlay.classList.add("hidden");
}

gateClose.addEventListener("click", hideGate);
gateGoSettings.addEventListener("click", () => {
  switchTab("settings");
  hideGate();
});

// ============================================================
// Perfil — estado salvo + elementos de exibição
// ============================================================
const profileCoverDisplay = document.getElementById("profileCoverDisplay");
const profileAvatarDisplay = document.getElementById("profileAvatarDisplay");
const avatarDisplayPlaceholder = document.getElementById("avatarDisplayPlaceholder");
const profileNameDisplay = document.getElementById("profileNameDisplay");
const profileHandleDisplay = document.getElementById("profileHandleDisplay");
const profileBioDisplay = document.getElementById("profileBioDisplay");
const openEditProfileBtn = document.getElementById("openEditProfileBtn");

let profileData = { avatar: "", cover: "", name: "", handle: "", bio: "" };

function renderProfileDisplay() {
  profileCoverDisplay.style.backgroundImage = profileData.cover
    ? `url(${profileData.cover})`
    : "none";

  if (profileData.avatar) {
    profileAvatarDisplay.innerHTML = `<img src="${profileData.avatar}" alt="" />`;
  } else {
    profileAvatarDisplay.innerHTML = `<span class="avatar-placeholder">+</span>`;
  }

  profileNameDisplay.textContent = profileData.name || "Seu nome";
  profileHandleDisplay.textContent = `@${profileData.handle || "usuario"}`;
  profileBioDisplay.textContent =
    profileData.bio || 'Adicione uma bio em "Editar perfil".';
}

async function loadProfile() {
  if (!window.pywebview) return;
  const profile = await window.pywebview.api.get_profile();
  profileData = {
    avatar: profile.avatar || "",
    cover: profile.cover || "",
    name: profile.name || "",
    handle: profile.handle || "",
    bio: profile.bio || "",
  };
  renderProfileDisplay();
}

// ============================================================
// Modal: Editar perfil (foto/capa com arrastar + zoom, nome, bio)
// ============================================================
const editProfileOverlay = document.getElementById("editProfileOverlay");
const editProfileClose = document.getElementById("editProfileClose");
const saveProfileBtn = document.getElementById("saveProfileBtn");

const coverFileInput = document.getElementById("coverFileInput");
const coverViewport = document.getElementById("coverViewport");
const editCoverImg = document.getElementById("editCoverImg");
const coverEmptyState = document.getElementById("coverEmptyState");

const avatarFileInput = document.getElementById("avatarFileInput");
const avatarViewport = document.getElementById("avatarViewport");
const editAvatarImg = document.getElementById("editAvatarImg");
const editAvatarPlaceholder = document.getElementById("editAvatarPlaceholder");

const nameInput = document.getElementById("nameInput");
const handleInput = document.getElementById("handleInput");
const bioInput = document.getElementById("bioInput");
const bioCounter = document.getElementById("bioCounter");

function readFileAsDataUri(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function loadImageElement(dataUri) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = dataUri;
  });
}

// Controlador genérico: arrastar pra reposicionar + slider pra zoom, dentro de um viewport recortado
function createCropController(viewportEl, imgEl, emptyStateEl, fileInputEl, plusHintEl) {
  let sourceImg = null;
  let baseScale = 1;
  let zoom = 1;
  let offsetX = 0;
  let offsetY = 0;
  let vpWidth = 0;
  let vpHeight = 0;
  let dragging = false;
  let startX = 0, startY = 0, startOffsetX = 0, startOffsetY = 0;
  let pointerDownPos = null;
  const CLICK_THRESHOLD = 5;

  function applyTransform() {
    imgEl.style.transform = `translate(${offsetX}px, ${offsetY}px) scale(${baseScale * zoom})`;
  }

  function clampOffset() {
    const scale = baseScale * zoom;
    const scaledW = sourceImg.naturalWidth * scale;
    const scaledH = sourceImg.naturalHeight * scale;
    offsetX = Math.min(0, Math.max(vpWidth - scaledW, offsetX));
    offsetY = Math.min(0, Math.max(vpHeight - scaledH, offsetY));
  }

  const MIN_ZOOM = 1;
  const MAX_ZOOM = 2.5;

  function clear() {
    sourceImg = null;
    imgEl.classList.add("hidden");
    imgEl.removeAttribute("src");
    if (emptyStateEl) emptyStateEl.classList.remove("hidden");
    if (plusHintEl) plusHintEl.classList.add("hidden");
    zoom = 1;
  }

  async function load(dataUri) {
    if (!dataUri) {
      clear();
      return;
    }
    const rect = viewportEl.getBoundingClientRect();
    vpWidth = rect.width;
    vpHeight = rect.height;

    sourceImg = await loadImageElement(dataUri);
    imgEl.src = dataUri;
    imgEl.classList.remove("hidden");
    if (emptyStateEl) emptyStateEl.classList.add("hidden");
    if (plusHintEl) plusHintEl.classList.remove("hidden");

    const srcRatio = sourceImg.naturalWidth / sourceImg.naturalHeight;
    const dstRatio = vpWidth / vpHeight;
    baseScale =
      srcRatio > dstRatio ? vpHeight / sourceImg.naturalHeight : vpWidth / sourceImg.naturalWidth;
    zoom = 1;

    offsetX = (vpWidth - sourceImg.naturalWidth * baseScale) / 2;
    offsetY = (vpHeight - sourceImg.naturalHeight * baseScale) / 2;
    applyTransform();
  }

  viewportEl.addEventListener(
    "wheel",
    (e) => {
      if (!sourceImg) return;
      e.preventDefault();

      const rect = viewportEl.getBoundingClientRect();
      const cx = e.clientX - rect.left;
      const cy = e.clientY - rect.top;

      const oldScale = baseScale * zoom;
      const direction = e.deltaY < 0 ? 1 : -1; // scroll pra cima = zoom in
      zoom = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, zoom + direction * 0.12));

      const imgCx = (cx - offsetX) / oldScale;
      const imgCy = (cy - offsetY) / oldScale;
      const newScale = baseScale * zoom;
      offsetX = cx - imgCx * newScale;
      offsetY = cy - imgCy * newScale;

      clampOffset();
      applyTransform();
    },
    { passive: false }
  );

  viewportEl.addEventListener("pointerdown", (e) => {
    pointerDownPos = { x: e.clientX, y: e.clientY };
    if (sourceImg) {
      dragging = true;
      startX = e.clientX;
      startY = e.clientY;
      startOffsetX = offsetX;
      startOffsetY = offsetY;
      viewportEl.classList.add("is-dragging");
    }
    viewportEl.setPointerCapture(e.pointerId);
  });
  viewportEl.addEventListener("pointermove", (e) => {
    if (!dragging) return;
    offsetX = startOffsetX + (e.clientX - startX);
    offsetY = startOffsetY + (e.clientY - startY);
    clampOffset();
    applyTransform();
  });
  viewportEl.addEventListener("pointerup", (e) => {
    dragging = false;
    viewportEl.classList.remove("is-dragging");

    if (pointerDownPos) {
      const dx = e.clientX - pointerDownPos.x;
      const dy = e.clientY - pointerDownPos.y;
      if (Math.sqrt(dx * dx + dy * dy) < CLICK_THRESHOLD) {
        fileInputEl.click();
      }
    }
    pointerDownPos = null;
  });
  viewportEl.addEventListener("pointerleave", () => {
    dragging = false;
    viewportEl.classList.remove("is-dragging");
    pointerDownPos = null;
  });

  function bake(outWidth) {
    if (!sourceImg) return "";
    const outHeight = Math.round((outWidth * vpHeight) / vpWidth);
    const canvas = document.createElement("canvas");
    canvas.width = outWidth;
    canvas.height = outHeight;
    const ctx = canvas.getContext("2d");

    const factor = outWidth / vpWidth;
    const scale = baseScale * zoom * factor;
    const dx = offsetX * factor;
    const dy = offsetY * factor;

    ctx.drawImage(
      sourceImg,
      dx,
      dy,
      sourceImg.naturalWidth * scale,
      sourceImg.naturalHeight * scale
    );
    return canvas.toDataURL("image/jpeg", 0.88);
  }

  return { load, clear, bake, hasImage: () => !!sourceImg };
}

const coverPlusHint = document.getElementById("coverPlusHint");
const avatarPlusHint = document.getElementById("avatarPlusHint");

const coverCrop = createCropController(coverViewport, editCoverImg, coverEmptyState, coverFileInput, coverPlusHint);
const avatarCrop = createCropController(avatarViewport, editAvatarImg, editAvatarPlaceholder, avatarFileInput, avatarPlusHint);

openEditProfileBtn.addEventListener("click", async () => {
  nameInput.value = profileData.name || "";
  handleInput.value = profileData.handle || "";
  bioInput.value = profileData.bio || "";
  bioCounter.textContent = `${bioInput.value.length}/160`;

  editProfileOverlay.classList.remove("hidden");

  // Carrega depois do overlay virar visível, pra medir o viewport com o tamanho real
  await coverCrop.load(profileData.cover || null);
  await avatarCrop.load(profileData.avatar || null);
});

editProfileClose.addEventListener("click", () => {
  editProfileOverlay.classList.add("hidden");
});

coverFileInput.addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  await coverCrop.load(await readFileAsDataUri(file));
  coverFileInput.value = "";
});

avatarFileInput.addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  await avatarCrop.load(await readFileAsDataUri(file));
  avatarFileInput.value = "";
});

handleInput.addEventListener("input", () => {
  const clean = handleInput.value
    .toLowerCase()
    .replace(/[^a-z0-9_.]/g, "")
    .slice(0, 30);
  if (clean !== handleInput.value) handleInput.value = clean;
});

bioInput.addEventListener("input", () => {
  bioCounter.textContent = `${bioInput.value.length}/160`;
});

saveProfileBtn.addEventListener("click", async () => {
  if (!window.pywebview) return;

  saveProfileBtn.disabled = true;
  saveProfileBtn.textContent = "Salvando…";

  const payload = {
    cover: coverCrop.hasImage() ? coverCrop.bake(1200) : "",
    avatar: avatarCrop.hasImage() ? avatarCrop.bake(500) : "",
    name: nameInput.value.trim(),
    handle: handleInput.value.trim(),
    bio: bioInput.value,
  };

  await window.pywebview.api.save_profile(payload);

  profileData = payload;
  renderProfileDisplay();

  saveProfileBtn.disabled = false;
  saveProfileBtn.textContent = "Salvar";
  editProfileOverlay.classList.add("hidden");
});

// ============================================================
// Amigos — servidor próprio (login, lista, pedidos, chat, ouvir junto)
// ============================================================
const FRIENDS_API_BASE = "https://valiant-youth-env.up.railway.app";
const FRIENDS_WS_BASE = "wss://valiant-youth-env.up.railway.app/ws";

const friendsAuthView = document.getElementById("friendsAuthView");
const friendsMainView = document.getElementById("friendsMainView");
const friendsUsernameInput = document.getElementById("friendsUsernameInput");
const friendsPasswordInput = document.getElementById("friendsPasswordInput");
const friendsLoginBtn = document.getElementById("friendsLoginBtn");
const friendsRegisterBtn = document.getElementById("friendsRegisterBtn");
const friendsAuthError = document.getElementById("friendsAuthError");
const friendsMyUsername = document.getElementById("friendsMyUsername");
const friendsLogoutBtn = document.getElementById("friendsLogoutBtn");

const addFriendInput = document.getElementById("addFriendInput");
const addFriendBtn = document.getElementById("addFriendBtn");
const addFriendHint = document.getElementById("addFriendHint");
const friendRequestsBlock = document.getElementById("friendRequestsBlock");
const incomingRequestsList = document.getElementById("incomingRequestsList");
const friendsListEl = document.getElementById("friendsList");

const chatEmptyState = document.getElementById("chatEmptyState");
const chatActiveView = document.getElementById("chatActiveView");
const chatFriendDot = document.getElementById("chatFriendDot");
const chatFriendName = document.getElementById("chatFriendName");
const chatMessages = document.getElementById("chatMessages");
const chatInput = document.getElementById("chatInput");
const chatSendBtn = document.getElementById("chatSendBtn");
const shareNowPlayingBtn = document.getElementById("shareNowPlayingBtn");
const friendNowPlayingCard = document.getElementById("friendNowPlayingCard");
const friendNowPlayingImg = document.getElementById("friendNowPlayingImg");
const friendNowPlayingTitle = document.getElementById("friendNowPlayingTitle");
const friendNowPlayingArtist = document.getElementById("friendNowPlayingArtist");

let friendsToken = "";
let friendsUsernameValue = "";
let friendsSocket = null;
let friendsOnlineSet = new Set();
let currentChatFriend = null;
let friendsReconnectTimer = null;

function friendsAuthHeaders() {
  return { Authorization: `Bearer ${friendsToken}`, "Content-Type": "application/json" };
}

async function initFriends() {
  if (!window.pywebview) return;
  const session = await window.pywebview.api.get_friends_session();
  if (session.token) {
    friendsToken = session.token;
    friendsUsernameValue = session.username;
    const ok = await friendsVerifySession();
    if (ok) {
      enterFriendsMainView();
      return;
    }
  }
  showFriendsAuthView();
}

async function friendsVerifySession() {
  try {
    const resp = await fetch(`${FRIENDS_API_BASE}/me`, { headers: friendsAuthHeaders() });
    return resp.ok;
  } catch {
    return false;
  }
}

function showFriendsAuthView() {
  friendsAuthView.classList.remove("hidden");
  friendsMainView.classList.add("hidden");
}

function enterFriendsMainView() {
  friendsAuthView.classList.add("hidden");
  friendsMainView.classList.remove("hidden");
  friendsMyUsername.textContent = friendsUsernameValue;
  connectFriendsSocket();
  loadFriendsList();
  loadFriendRequests();
}

async function friendsAuth(kind) {
  const username = friendsUsernameInput.value.trim();
  const password = friendsPasswordInput.value;
  friendsAuthError.textContent = "";

  if (!username || !password) {
    friendsAuthError.textContent = "Preenche usuário e senha.";
    return;
  }

  try {
    const resp = await fetch(`${FRIENDS_API_BASE}/${kind}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const data = await resp.json();

    if (!resp.ok) {
      friendsAuthError.textContent = data.detail || "Erro ao entrar.";
      return;
    }

    friendsToken = data.access_token;
    friendsUsernameValue = data.username;
    await window.pywebview.api.save_friends_session(friendsToken, friendsUsernameValue);
    friendsPasswordInput.value = "";
    enterFriendsMainView();
  } catch {
    friendsAuthError.textContent = "Não consegui falar com o servidor. Ele está no ar?";
  }
}

friendsLoginBtn.addEventListener("click", () => friendsAuth("login"));
friendsRegisterBtn.addEventListener("click", () => friendsAuth("register"));
friendsPasswordInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") friendsAuth("login");
});

friendsLogoutBtn.addEventListener("click", async () => {
  if (friendsSocket) friendsSocket.close();
  friendsToken = "";
  friendsUsernameValue = "";
  currentChatFriend = null;
  if (window.pywebview) await window.pywebview.api.clear_friends_session();
  showFriendsAuthView();
});

// ---------------- WebSocket (chat + presença + ouvir junto) ----------------

function connectFriendsSocket() {
  if (friendsSocket) friendsSocket.close();
  clearTimeout(friendsReconnectTimer);

  friendsSocket = new WebSocket(`${FRIENDS_WS_BASE}?token=${encodeURIComponent(friendsToken)}`);

  friendsSocket.addEventListener("message", (event) => {
    let data;
    try {
      data = JSON.parse(event.data);
    } catch {
      return;
    }
    handleFriendsSocketMessage(data);
  });

  friendsSocket.addEventListener("close", () => {
    if (friendsToken) {
      friendsReconnectTimer = setTimeout(connectFriendsSocket, 4000);
    }
  });
}

function handleFriendsSocketMessage(data) {
  if (data.type === "presence") {
    if (data.online) friendsOnlineSet.add(data.username);
    else friendsOnlineSet.delete(data.username);
    renderFriendOnlineDots();
  } else if (data.type === "chat") {
    const otherParty = data.from === friendsUsernameValue ? currentChatFriend : data.from;
    if (otherParty === currentChatFriend) {
      appendChatBubble(data.from === friendsUsernameValue, data.text);
    }
  } else if (data.type === "now_playing") {
    if (data.from === currentChatFriend) {
      showFriendNowPlaying(data);
    }
  }
}

// ---------------- Lista de amigos ----------------

async function loadFriendsList() {
  try {
    const resp = await fetch(`${FRIENDS_API_BASE}/friends`, { headers: friendsAuthHeaders() });
    const data = await resp.json();
    renderFriendsList(data.friends || []);
  } catch {
    friendsListEl.innerHTML = '<li class="muted small">Não consegui carregar seus amigos.</li>';
  }
}

let lastFriendsData = [];

function renderFriendsList(friends) {
  lastFriendsData = friends;
  if (!friends.length) {
    friendsListEl.innerHTML = '<li class="empty-state">Nenhum amigo ainda.</li>';
    return;
  }
  friendsListEl.innerHTML = friends
    .map((f) => {
      const online = friendsOnlineSet.has(f.username) || f.online;
      return `
        <li class="friend-row ${f.username === currentChatFriend ? "is-active" : ""}" data-friend="${f.username}">
          <span class="dot ${online ? "is-live" : ""}"></span>
          <span class="friend-row-name">${escapeHtmlFriends(f.username)}</span>
        </li>
      `;
    })
    .join("");
}

function renderFriendOnlineDots() {
  renderFriendsList(lastFriendsData);
}

friendsListEl.addEventListener("click", (e) => {
  const row = e.target.closest(".friend-row[data-friend]");
  if (row) openChatWith(row.dataset.friend);
});

// ---------------- Pedidos de amizade ----------------

addFriendBtn.addEventListener("click", async () => {
  const username = addFriendInput.value.trim();
  if (!username) return;

  try {
    const resp = await fetch(`${FRIENDS_API_BASE}/friends/request`, {
      method: "POST",
      headers: friendsAuthHeaders(),
      body: JSON.stringify({ username }),
    });
    const data = await resp.json();
    if (!resp.ok) {
      addFriendHint.textContent = data.detail || "Erro ao enviar pedido.";
      return;
    }
    addFriendHint.textContent = "Pedido enviado!";
    addFriendInput.value = "";
    setTimeout(() => (addFriendHint.textContent = ""), 2500);
  } catch {
    addFriendHint.textContent = "Não consegui falar com o servidor.";
  }
});

async function loadFriendRequests() {
  try {
    const resp = await fetch(`${FRIENDS_API_BASE}/friends/requests`, { headers: friendsAuthHeaders() });
    const data = await resp.json();
    renderIncomingRequests(data.incoming || []);
  } catch {
    /* silencioso — não é crítico */
  }
}

function renderIncomingRequests(incoming) {
  if (!incoming.length) {
    friendRequestsBlock.classList.add("hidden");
    return;
  }
  friendRequestsBlock.classList.remove("hidden");
  incomingRequestsList.innerHTML = incoming
    .map(
      (username) => `
        <li class="friend-request-row">
          <span class="friend-request-name">${escapeHtmlFriends(username)}</span>
          <div class="friend-request-actions">
            <button class="icon-btn-sm accept" data-accept="${username}" title="Aceitar">&#10003;</button>
            <button class="icon-btn-sm decline" data-decline="${username}" title="Recusar">&times;</button>
          </div>
        </li>
      `
    )
    .join("");
}

incomingRequestsList.addEventListener("click", async (e) => {
  const acceptBtn = e.target.closest("[data-accept]");
  const declineBtn = e.target.closest("[data-decline]");
  if (!acceptBtn && !declineBtn) return;

  const username = acceptBtn ? acceptBtn.dataset.accept : declineBtn.dataset.decline;
  const endpoint = acceptBtn ? "accept" : "decline";

  await fetch(`${FRIENDS_API_BASE}/friends/${endpoint}`, {
    method: "POST",
    headers: friendsAuthHeaders(),
    body: JSON.stringify({ username }),
  });

  loadFriendRequests();
  if (acceptBtn) loadFriendsList();
});

// ---------------- Chat ----------------

async function openChatWith(username) {
  currentChatFriend = username;
  renderFriendsList(lastFriendsData);

  chatEmptyState.classList.add("hidden");
  chatActiveView.classList.remove("hidden");
  chatFriendName.textContent = username;
  chatFriendDot.classList.toggle("is-live", friendsOnlineSet.has(username));
  friendNowPlayingCard.classList.add("hidden");
  chatMessages.innerHTML = `<p class="muted small">Carregando…</p>`;

  try {
    const resp = await fetch(`${FRIENDS_API_BASE}/messages/${encodeURIComponent(username)}`, {
      headers: friendsAuthHeaders(),
    });
    const data = await resp.json();
    chatMessages.innerHTML = "";
    (data.messages || []).forEach((m) => appendChatBubble(m.from === friendsUsernameValue, m.text));
  } catch {
    chatMessages.innerHTML = `<p class="muted small">Não consegui carregar as mensagens.</p>`;
  }
}

function appendChatBubble(isMine, text) {
  const bubble = document.createElement("div");
  bubble.className = `chat-bubble ${isMine ? "is-mine" : "is-theirs"}`;
  bubble.textContent = text;
  chatMessages.appendChild(bubble);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function sendChatMessage() {
  const text = chatInput.value.trim();
  if (!text || !currentChatFriend || !friendsSocket || friendsSocket.readyState !== WebSocket.OPEN) return;

  friendsSocket.send(JSON.stringify({ type: "chat", to: currentChatFriend, text }));
  chatInput.value = "";
}

chatSendBtn.addEventListener("click", sendChatMessage);
chatInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendChatMessage();
});

// ---------------- Ouvir junto ----------------

shareNowPlayingBtn.addEventListener("click", () => {
  if (!currentChatFriend || !friendsSocket || friendsSocket.readyState !== WebSocket.OPEN) return;

  friendsSocket.send(
    JSON.stringify({
      type: "now_playing",
      to: currentChatFriend,
      title: trackTitle.textContent.trim(),
      artist: trackArtist.textContent.trim(),
      is_playing: true,
    })
  );
});

function showFriendNowPlaying(data) {
  friendNowPlayingCard.classList.remove("hidden");
  friendNowPlayingTitle.textContent = data.title || "";
  friendNowPlayingArtist.textContent = data.artist || "";
  friendNowPlayingImg.src = coverArt.classList.contains("is-visible") ? coverArt.src : "";
}

function escapeHtmlFriends(str) {
  const div = document.createElement("div");
  div.textContent = str || "";
  return div.innerHTML;
}

// ============================================================
// Boot
// ============================================================
window.addEventListener("pywebviewready", async () => {
  loadProfile();
  initFriends();
  const token = await (window.pywebview ? window.pywebview.api.get_token() : Promise.resolve(""));
  if (token) {
    tokenInput.value = token;
  } else {
    showGate();
  }
});
