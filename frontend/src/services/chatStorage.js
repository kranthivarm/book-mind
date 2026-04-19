

const CHATS_KEY = "bm_chats";
const msgKey = (chatId) => `bm_msgs_${chatId}`;

function uid() {
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

//   Chat list

export function getAllChats() {
  try {
    return JSON.parse(localStorage.getItem(CHATS_KEY) || "[]");
  } catch {
    return [];
  }
}

export function createChat({ bookId, bookName, totalPages, totalChunks }) {
  const chat = {
    chatId: uid(),
    bookId,
    bookName,
    totalPages,
    totalChunks,
    createdAt:   Date.now(),
    lastMessage: "",
    lastAt:      Date.now(),
  };
  const chats = getAllChats();
  chats.unshift(chat); // newest first
  localStorage.setItem(CHATS_KEY, JSON.stringify(chats));
  return chat;
}

export function updateChatPreview(chatId, lastMessage) {
  const chats = getAllChats().map((c) =>
    c.chatId === chatId
      ? { ...c, lastMessage: lastMessage.slice(0, 60), lastAt: Date.now() }
      : c
  );
  localStorage.setItem(CHATS_KEY, JSON.stringify(chats));
}

export function deleteChat(chatId) {
  const chats = getAllChats().filter((c) => c.chatId !== chatId);
  localStorage.setItem(CHATS_KEY, JSON.stringify(chats));
  localStorage.removeItem(msgKey(chatId));
}

//   Messages

export function getMessages(chatId) {
  try {
    return JSON.parse(localStorage.getItem(msgKey(chatId)) || "[]");
  } catch {
    return [];
  }
}

export function saveMessage(chatId, { role, text, sources = null }) {
  const messages = getMessages(chatId);
  const msg = { id: uid(), role, text, sources, timestamp: Date.now() };
  messages.push(msg);
  localStorage.setItem(msgKey(chatId), JSON.stringify(messages));
  return msg;
}

// Update the last AI message in place (used after streaming completes)
export function updateLastAiMessage(chatId, { text, sources }) {
  const messages = getMessages(chatId);
  // Find last AI message and update it
  for (let i = messages.length - 1; i >= 0; i--) {
    if (messages[i].role === "ai") {
      messages[i].text    = text;
      messages[i].sources = sources;
      break;
    }
  }
  localStorage.setItem(msgKey(chatId), JSON.stringify(messages));
}