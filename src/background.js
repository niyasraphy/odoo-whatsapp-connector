// Background of the extension: keeps the bridge registered in the Odoo
// addresses the user allowed, sends the messages of Odoo one after the
// other through the WhatsApp Web tab, a short pause between them, and
// keeps the messages read in WhatsApp Web until an Odoo page takes them.
const api = globalThis.browser ?? globalThis.chrome;

/* global patternOf, bridgeMatchesOf, isBackendUrl, isSafeOrigin */
if (typeof importScripts === "function") {
    importScripts("origins.js"); // Chrome; Firefox lists it in the manifest
}

const WHATSAPP = "https://web.whatsapp.com/";
const BRIDGE_ID = "odoo-bridge";
const LOAD_TIMEOUT = 60000;
const MAX_FILES = 10;
// between two sends, a pause of this many ms, at random: not the rhythm of a machine
const GAP_MIN = 1500;
const GAP_MAX = 4000;
// chats opened in the page with numbers WhatsApp Web never had, in an hour
const NEW_CHATS_PER_HOUR = 30;
const HOUR = 3600000;

// ------------------------------------------------------------
// Odoo addresses
// ------------------------------------------------------------

async function getOrigins() {
    const { origins = [] } = await api.storage.local.get("origins");
    return origins;
}

async function allowedOrigins() {
    const allowed = [];
    for (const origin of await getOrigins()) {
        if (isSafeOrigin(origin) && (await api.permissions.contains({ origins: [patternOf(origin)] }))) {
            allowed.push(origin);
        }
    }
    return allowed;
}

let syncing = Promise.resolve();

/** Register the bridge in the allowed Odoo addresses, one sync at a time: the
 * events that call it come in bursts (permission granted, address saved). */
function syncBridge() {
    syncing = syncing.then(registerBridge, registerBridge);
    syncing.catch((error) => console.error("Odoo bridge not registered:", error));
    return syncing;
}

/** Register the bridge in the allowed Odoo addresses, and inject it in their open tabs. */
async function registerBridge() {
    const registered = await api.scripting.getRegisteredContentScripts({ ids: [BRIDGE_ID] });
    if (registered.length) {
        await api.scripting.unregisterContentScripts({ ids: [BRIDGE_ID] });
    }
    const origins = await allowedOrigins();
    if (!origins.length) {
        return;
    }
    const matches = [...new Set(origins.flatMap(bridgeMatchesOf))];
    await api.scripting.registerContentScripts([
        { id: BRIDGE_ID, matches, js: ["odoo_bridge.js"], runAt: "document_start", persistAcrossSessions: true },
    ]);
    for (const tab of await api.tabs.query({ url: matches })) {
        api.scripting.executeScript({ target: { tabId: tab.id }, files: ["odoo_bridge.js"] }).catch(() => {});
    }
}

// ------------------------------------------------------------
// Sending
// ------------------------------------------------------------

let queue = Promise.resolve();

function enqueue(job) {
    const run = queue.then(job, job);
    queue = run.catch(() => {});
    return run;
}

function checkMessage(message) {
    if (!/^\d{6,15}$/.test(message?.phone || "")) {
        throw new Error("The number is not valid.");
    }
    if (typeof message.body !== "string") {
        throw new Error("The message has no text.");
    }
    const attachments = message.attachments || [];
    if (!Array.isArray(attachments) || attachments.length > MAX_FILES) {
        throw new Error(`At most ${MAX_FILES} files can be sent with a message.`);
    }
    if (attachments.some((a) => typeof a?.name !== "string" || typeof a.data !== "string")) {
        throw new Error("A file of the message is not valid.");
    }
    if (message.quoted && typeof message.quoted.id !== "string") {
        throw new Error("The message it answers is not valid.");
    }
}

/** Resolves when the WhatsApp Web script of the tab announces itself. */
function waitForLoad(tabId) {
    let stop;
    const loaded = new Promise((resolve, reject) => {
        const onMessage = (request, sender) => {
            if (request?.type === "whatsapp-loaded" && sender.tab?.id === tabId) {
                stop();
                resolve();
            }
        };
        const timer = setTimeout(() => {
            stop();
            reject(new Error("WhatsApp Web did not load in time."));
        }, LOAD_TIMEOUT);
        stop = () => {
            clearTimeout(timer);
            api.runtime.onMessage.removeListener(onMessage);
        };
        api.runtime.onMessage.addListener(onMessage);
    });
    loaded.catch(() => {});
    return { loaded, stop: () => stop() };
}

/** The WhatsApp Web tab, when it shows the chat of ``phone`` with an empty message box. */
async function tabOnChat(tab, phone) {
    if (!tab || tab.status !== "complete") {
        return false;
    }
    try {
        return (await api.tabs.sendMessage(tab.id, { type: "open-chat" }))?.phone === phone;
    } catch {
        return false;
    }
}

async function newChatsThisHour() {
    const { newChats = [] } = await api.storage.local.get("newChats");
    return newChats.filter((at) => at > Date.now() - HOUR);
}

async function countNewChat() {
    await api.storage.local.set({ newChats: [...(await newChatsThisHour()), Date.now()] });
}

/** Open the chat of ``phone`` in the open WhatsApp Web, without loading it
 * again: true once it shows. False when it cannot, to load /send?phone=. */
async function switchInTab(tab, phone) {
    if (!tab || tab.status !== "complete") {
        return false;
    }
    const allowNew = (await newChatsThisHour()).length < NEW_CHATS_PER_HOUR;
    let answer;
    try {
        answer = await api.tabs.sendMessage(tab.id, { type: "switch-chat", phone, allowNew });
    } catch {
        return false;
    }
    if (answer?.missing) {
        throw new Error("This number is not on WhatsApp.");
    }
    if (answer?.limit) {
        throw new Error(
            `${NEW_CHATS_PER_HOUR} new chats were started in the last hour: to keep your number safe, ` +
                "wait a while before writing to numbers that never wrote to you."
        );
    }
    if (answer?.phone !== phone) {
        return false;
    }
    if (answer.isNew) {
        await countNewChat();
    }
    return true;
}

async function openChat(message) {
    let [tab] = await api.tabs.query({ url: `${WHATSAPP}*` });
    // messages to the same chat, one after the other, or another chat opened
    // in the page: no need to load the page again
    if ((await tabOnChat(tab, message.phone)) || (await switchInTab(tab, message.phone))) {
        await api.scripting.executeScript({ target: { tabId: tab.id }, world: "MAIN", files: ["page_hook.js"] }).catch(() => {});
        return tab.id;
    }
    return loadChat(tab, message);
}

/** Open the chat with /send?phone=..&text=..: the page loads again, and WhatsApp Web fills the text in. */
async function loadChat(tab, message) {
    // with files, the text goes as their caption: the message box stays empty
    const text = message.attachments?.length ? "" : message.body;
    const url = `${WHATSAPP}send?phone=${message.phone}&text=${encodeURIComponent(text)}`;
    tab ??= await api.tabs.create({ url: "about:blank", pinned: true, active: false });
    // listen before navigating: the page may announce itself before update() returns
    const wait = waitForLoad(tab.id);
    try {
        await api.tabs.update(tab.id, { url });
    } catch (error) {
        wait.stop();
        throw error;
    }
    await wait.loaded;
    // in the page itself, to receive the input WhatsApp Web makes for Document
    await api.scripting.executeScript({ target: { tabId: tab.id }, world: "MAIN", files: ["page_hook.js"] }).catch(() => {});
    return tab.id;
}

let lastSentAt = 0;

async function pause() {
    const wait = lastSentAt + GAP_MIN + Math.random() * (GAP_MAX - GAP_MIN) - Date.now();
    if (wait > 0) {
        await new Promise((resolve) => setTimeout(resolve, wait));
    }
}

async function deliver(message) {
    try {
        checkMessage(message);
        await pause();
        let tabId = await openChat(message);
        // the ids of the messages sent before are not those of this one
        const { sent = [] } = await api.storage.local.get("sent");
        let answer = await api.tabs.sendMessage(tabId, { type: "deliver", message, exclude: sent });
        if (answer?.code === "no-text") {
            // the text could not be typed in the chat opened in the page, and nothing went: WhatsApp
            // Web fills it in when it loads the chat from the link
            const [tab] = await api.tabs.query({ url: `${WHATSAPP}*` });
            tabId = await loadChat(tab, message);
            answer = await api.tabs.sendMessage(tabId, { type: "deliver", message, exclude: sent });
        }
        if (answer?.ok) {
            await rememberSent(answer.whatsapp_ids || []);
        }
        return answer;
    } catch (error) {
        return { ok: false, error: error.message };
    } finally {
        lastSentAt = Date.now();
    }
}

/** React in WhatsApp Web to a message: {phone, whatsapp_id, emoji}, an empty emoji takes it back. */
async function react(reaction) {
    if (!/^\d{6,15}$/.test(reaction?.phone || "") || typeof reaction.whatsapp_id !== "string" || !reaction.whatsapp_id) {
        return { ok: false, error: "The reaction is not valid." };
    }
    if (typeof reaction.emoji !== "string" || reaction.emoji.length > 32) {
        return { ok: false, error: "The emoji is not valid." };
    }
    const [tab] = await api.tabs.query({ url: `${WHATSAPP}*` });
    if (!tab) {
        return { ok: false, error: "WhatsApp Web is not open in this browser." };
    }
    try {
        return await api.tabs.sendMessage(tab.id, { type: "react", reaction });
    } catch (error) {
        return { ok: false, error: error.message };
    }
}

// ------------------------------------------------------------
// Status: whether WhatsApp Web is open and linked in this browser
// ------------------------------------------------------------

const STATUS_TIMEOUT = 2500;

/** {tab, state: loading | qr | ready, me, reader, error}: the WhatsApp Web of this browser, as its tab tells. */
async function status() {
    const [tab] = await api.tabs.query({ url: `${WHATSAPP}*` });
    if (!tab) {
        return { ok: true, tab: false };
    }
    let timer;
    const late = new Promise((resolve) => (timer = setTimeout(() => resolve(null), STATUS_TIMEOUT)));
    const page = await Promise.race([api.tabs.sendMessage(tab.id, { type: "status" }).catch(() => null), late]);
    clearTimeout(timer);
    // a tab still loading, asleep or stuck does not answer
    return { ok: true, tab: true, ...(page || { state: "loading" }) };
}

/** Mark messages read or played in WhatsApp Web: {phone, ids, kind: read | played}. */
async function receipt(request) {
    const { phone, ids, kind } = request || {};
    if (!/^\d{6,15}$/.test(phone || "") || !Array.isArray(ids) || !ids.length || !["read", "played"].includes(kind)) {
        return { ok: false, error: "The receipt is not valid." };
    }
    const [tab] = await api.tabs.query({ url: `${WHATSAPP}*` });
    if (!tab) {
        return { ok: false, error: "WhatsApp Web is not open in this browser." };
    }
    try {
        return await api.tabs.sendMessage(tab.id, { type: "receipt", receipt: { phone, ids: ids.map(String), kind } });
    } catch (error) {
        return { ok: false, error: error.message };
    }
}

/** The profile picture of ``phone``, read in WhatsApp Web. */
async function picture(phone) {
    if (!/^\d{6,15}$/.test(phone || "")) {
        return { ok: false, error: "The number is not valid." };
    }
    const [tab] = await api.tabs.query({ url: `${WHATSAPP}*` });
    if (!tab) {
        return { ok: false, error: "WhatsApp Web is not open in this browser." };
    }
    try {
        return await api.tabs.sendMessage(tab.id, { type: "picture", phone });
    } catch (error) {
        return { ok: false, error: error.message };
    }
}

/** Show the WhatsApp Web tab, opened pinned when there is none: to scan its QR code. */
async function openTab() {
    const [tab] = await api.tabs.query({ url: `${WHATSAPP}*` });
    if (tab) {
        await api.tabs.update(tab.id, { active: true });
        await api.windows.update(tab.windowId, { focused: true }).catch(() => {});
    } else {
        await api.tabs.create({ url: WHATSAPP, pinned: true, active: true });
    }
    return { ok: true };
}

let statusTimer = null;

/** Tell the open Odoo pages the status changed, once for a burst of events. */
function wakeStatus() {
    clearTimeout(statusTimer);
    statusTimer = setTimeout(async () => {
        const origins = await allowedOrigins();
        if (!origins.length) {
            return;
        }
        for (const tab of await api.tabs.query({ url: [...new Set(origins.flatMap(bridgeMatchesOf))] })) {
            api.tabs.sendMessage(tab.id, { type: "status-wake" }).catch(() => {});
        }
    }, 400);
}

// ------------------------------------------------------------
// Receiving
// ------------------------------------------------------------

const INBOX_MAX = 1000;
const BATCH = 20;
// an Odoo page has this long to record what it took, else another one gets it
const LEASE = 90000;
// a status or a reaction waits this long, for Odoo to know the id of the message it just sent
const STATUS_DELAY = 10000;
const SENT_MAX = 300;

let inboxQueue = Promise.resolve();

/** Run ``change`` on the stored inbox, one change at a time: the events come
 * from several tabs at once. */
function withInbox(change) {
    const run = inboxQueue.then(async () => {
        const stored = await api.storage.local.get(["inbox", "since", "sent"]);
        const state = { inbox: stored.inbox || [], since: stored.since ?? null, sent: stored.sent || [] };
        const result = await change(state);
        await api.storage.local.set(state);
        return result;
    });
    inboxQueue = run.catch(() => {});
    return run;
}

/** Keep what the reader saw; a message Odoo sent itself is already in Odoo. */
async function addToInbox(items) {
    const added = await withInbox((state) => {
        const sent = new Set(state.sent);
        const byKey = new Map(state.inbox.map((item) => [item.key, item]));
        let count = 0;
        for (const item of items) {
            if (!item?.id || !["message", "status", "reaction"].includes(item.kind)) {
                continue;
            }
            const key = `${item.kind}:${item.id}`;
            const known = byKey.get(key);
            if (item.kind === "message" && (known || (item.from_me && sent.has(item.id)))) {
                continue;
            }
            if (item.kind === "status" && known && known.ack >= item.ack) {
                continue;
            }
            // a reaction changed or taken back replaces the one before
            byKey.set(key, { ...item, key, lease: 0, added: Date.now() });
            count++;
            if (item.t) {
                state.since = Math.max(state.since || 0, item.t);
            }
        }
        state.inbox = [...byKey.values()].slice(-INBOX_MAX);
        return count;
    });
    if (added) {
        wakeOdoo();
    }
}

async function rememberSent(ids) {
    if (!ids.length) {
        return;
    }
    await withInbox((state) => {
        const sent = new Set(ids);
        state.sent = [...state.sent, ...ids].slice(-SENT_MAX);
        state.inbox = state.inbox.filter((item) => !(item.kind === "message" && item.from_me && sent.has(item.id)));
    });
}

/** Up to BATCH items for one Odoo page, kept from the others for a while. */
function takeInbox() {
    return withInbox((state) => {
        const now = Date.now();
        const items = state.inbox
            .filter((item) => !item.lease || item.lease < now)
            .filter((item) => item.kind === "message" || now - item.added >= STATUS_DELAY)
            .slice(0, BATCH);
        for (const item of items) {
            item.lease = now + LEASE;
        }
        return items.map(({ lease, added, ...item }) => item);
    });
}

function removeFromInbox(keys) {
    const done = new Set(keys);
    return withInbox((state) => {
        state.inbox = state.inbox.filter((item) => !done.has(item.key));
    });
}

/** The time the reader starts from, in seconds: now on the first run, so the past is not read. */
function inboxSince() {
    return withInbox((state) => {
        state.since ??= Math.floor(Date.now() / 1000);
        return state.since;
    });
}

/** Tell the open Odoo pages there is something to take. */
async function wakeOdoo() {
    const origins = await allowedOrigins();
    if (!origins.length) {
        return;
    }
    for (const tab of await api.tabs.query({ url: [...new Set(origins.flatMap(bridgeMatchesOf))] })) {
        api.tabs.sendMessage(tab.id, { type: "inbox-wake" }).catch(() => {});
    }
}

/** The file of a message; ``retry`` when WhatsApp Web cannot give it now (closed, loading): Odoo waits for it. */
async function fetchMedia(id) {
    const [tab] = await api.tabs.query({ url: `${WHATSAPP}*` });
    if (!tab) {
        return { ok: false, retry: true, error: "WhatsApp Web is not open in this browser." };
    }
    try {
        return await api.tabs.sendMessage(tab.id, { type: "media", id });
    } catch (error) {
        // a tab loading, or asleep, has no script to answer yet
        return { ok: false, retry: true, error: error.message };
    }
}

/** What Odoo may take: nothing while WhatsApp Web is closed or not synced, so that the messages come
 * in together, in order, with their files, once it is open again. */
async function inboxFor() {
    const { reader } = await api.storage.local.get("reader");
    if (!reader?.me) {
        return { ok: true, items: [], me: null };
    }
    const now = await status();
    if (!now.tab || now.state !== "ready") {
        return { ok: true, items: [], me: reader.me, waiting: true };
    }
    return { ok: true, items: await takeInbox(), me: reader.me };
}

function fromWhatsapp(sender) {
    return sender.id === api.runtime.id && sender.tab && sender.url?.startsWith(WHATSAPP);
}

async function fromAllowedOdoo(sender) {
    if (sender.id !== api.runtime.id || !sender.tab || !sender.url) {
        return false;
    }
    return isBackendUrl(sender.url) && (await allowedOrigins()).includes(new URL(sender.url).origin);
}

// ------------------------------------------------------------
// Events
// ------------------------------------------------------------

// from the WhatsApp Web tab
const FROM_WHATSAPP = {
    "inbox-add": (request) => addToInbox(request.items || []).then(() => ({ ok: true })),
    "inbox-since": () => inboxSince().then((since) => ({ since })),
    "reader-state": async (request) => {
        await api.storage.local.set({ reader: { ...request.state, at: Date.now() } });
        wakeStatus();
        return { ok: true };
    },
    "page-state": async () => {
        wakeStatus();
        return { ok: true };
    },
};

// from the pages of an allowed Odoo
const FROM_ODOO = {
    send: (request) => enqueue(() => deliver(request.message)),
    inbox: () => inboxFor(),
    "inbox-done": (request) => removeFromInbox(request.keys || []).then(() => ({ ok: true })),
    media: (request) => fetchMedia(request.message_id),
    // in the line of the sends: a reaction does not go in the middle of a message
    react: (request) => enqueue(() => react(request.reaction)),
    status: () => status(),
    receipt: (request) => receipt(request.receipt),
    picture: (request) => picture(request.phone),
    "open-tab": () => openTab(),
};

api.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request?.type === "ping") {
        sendResponse({ ok: true });
        return false;
    }
    const fromTab = FROM_WHATSAPP[request?.type];
    if (fromTab) {
        if (!fromWhatsapp(sender)) {
            return false;
        }
        fromTab(request).then(sendResponse, (error) => sendResponse({ ok: false, error: error.message }));
        return true;
    }
    const fromPage = FROM_ODOO[request?.type];
    if (fromPage) {
        fromAllowedOdoo(sender).then((allowed) =>
            allowed
                ? fromPage(request).then(sendResponse, (error) => sendResponse({ ok: false, error: error.message }))
                : sendResponse({ ok: false, error: "This Odoo address is not allowed in the extension." })
        );
        return true;
    }
    return false;
});

// a WhatsApp Web tab closed, opened or loaded again: the status may have changed
api.tabs.onRemoved.addListener(() => wakeStatus());
api.tabs.onUpdated.addListener((_tabId, change, tab) => {
    if ((change.status || change.url) && (tab.url || "").startsWith(WHATSAPP)) {
        wakeStatus();
    }
});

/** The extension installed, updated or reloaded: the scripts in an open WhatsApp Web tab are cut off
 * from it, and it would miss what comes until the tab loads again. Load it again now. */
async function reloadWhatsapp() {
    for (const tab of await api.tabs.query({ url: `${WHATSAPP}*` })) {
        api.tabs.reload(tab.id).catch(() => {});
    }
}

api.runtime.onInstalled.addListener(() => {
    syncBridge();
    reloadWhatsapp();
});
api.runtime.onStartup.addListener(() => syncBridge());
api.permissions.onAdded.addListener(async ({ origins = [] }) => {
    // the popup marks the address it allows before the prompt: keep it even if
    // the popup closed with the prompt, as Firefox does
    const { pending } = await api.storage.local.get("pending");
    const known = await getOrigins();
    if (pending && isSafeOrigin(pending) && origins.includes(patternOf(pending)) && !known.includes(pending)) {
        await api.storage.local.set({ origins: [...known, pending] }); // syncs the bridge
    } else {
        syncBridge();
    }
    if (pending) {
        await api.storage.local.remove("pending");
    }
});
api.permissions.onRemoved.addListener(() => syncBridge());
api.storage.onChanged.addListener((changes, area) => {
    if (area === "local" && changes.origins) {
        syncBridge();
    }
});
