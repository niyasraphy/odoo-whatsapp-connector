// Runs in the page of WhatsApp Web itself (MAIN world). Reads the messages
// from the store of WhatsApp Web, not from the screen: every chat, without
// opening it, and without marking anything as read. Talks to whatsapp.js
// with window.postMessage. See PROTOCOL.md.
//
// WhatsApp renames its modules without notice: when reading breaks, the popup
// says so, and MODULES below is the list to fix.
(() => {
    if (window.omWhatsappReader) {
        return;
    }
    window.omWhatsappReader = true;

    const READER = "om-whatsapp-reader";
    const CONTENT = "om-whatsapp-content";

    // names of the modules of WhatsApp Web, newest first
    const MODULES = {
        collections: ["WAWebCollections"],
        me: ["WAWebUserPrefsMeUser"],
        contacts: ["WAWebApiContact"],
        download: ["WAWebDownloadManager"],
        // to open a chat in the page, without loading it again
        wids: ["WAWebWidFactory"],
        findChat: ["WAWebFindChatAction"],
        cmd: ["WAWebCmd"],
        exists: ["WAWebQueryExistsJob"],
        reaction: ["WAWebSendReactionMsgAction"],
        seen: ["WAWebUpdateUnreadChatAction"],
        pictures: ["WAWebContactProfilePicThumbBridge"],
        // not sure of these names: the reader falls back on read, and says so in the console
        played: ["WAWebPttPlayedAction", "WAWebSendPlayedReceiptAction", "WAWebMsgPlayedAction"],
    };
    // kinds of messages that come with their file
    const MEDIA = new Set(["image", "document", "sticker", "ptt", "audio", "video"]);
    // kinds of messages that come as a note, without their content
    const NOTES = {
        location: "Location",
        vcard: "Contact card",
        multi_vcard: "Contact cards",
        poll_creation: "Poll",
    };
    const MAX_MEDIA_SIZE = 16 * 1024 * 1024;
    const MAX_PICTURE_SIZE = 2 * 1024 * 1024;
    // each of the two ways to download a file has this long (ms): Odoo waits 60 s for the file
    const DOWNLOAD_TIMEOUT = 20000;
    const MAX_CATCH_UP = 200;
    // the reader looks this far (seconds) before the last message it saw: what came while it was cut
    // off is caught up when WhatsApp Web loads it (Odoo skips what it already has)
    const CATCH_UP_MARGIN = 3600;

    const reported = new Set();
    let collections = null;

    function load(names) {
        for (const name of names) {
            try {
                const module = window.require?.(name);
                if (module) {
                    return module;
                }
            } catch {
                // not this name
            }
        }
        return null;
    }

    function post(data) {
        window.postMessage({ source: READER, ...data }, location.origin);
    }

    function allMessages() {
        const Msg = collections.Msg;
        return Msg.getModelsArray?.() || Msg.models || Msg._models || [];
    }

    /** Digits of the phone number of a chat with one person, else null:
     * groups, status, channels. Chats addressed by a hidden id (@lid) are
     * looked up in the contacts. */
    function phoneOf(wid) {
        if (typeof wid === "string") {
            const [user, server] = wid.split("@");
            wid = { user, server, _serialized: wid };
        }
        if (!wid) {
            return null;
        }
        if (wid.server === "c.us" || wid.server === "s.whatsapp.net") {
            return wid.user || null;
        }
        if (wid.server !== "lid") {
            return null;
        }
        const contacts = load(MODULES.contacts);
        for (const lookup of [
            () => contacts?.getPhoneNumber?.(wid),
            () => collections.Contact?.get?.(wid)?.phoneNumber,
            () => collections.Contact?.get?.(wid)?.attributes?.phoneNumber,
        ]) {
            try {
                const found = lookup();
                if (found?.user) {
                    return found.user;
                }
            } catch {
                // next way
            }
        }
        return null;
    }

    function profileName(msg) {
        try {
            return msg.notifyName || collections.Contact?.get?.(msg.id.remote)?.pushname || null;
        } catch {
            return null;
        }
    }

    /** A reaction to a message of a chat with one person: its emoji, empty when taken back. */
    function reactionItem(parentKey, senderWid, emoji, t) {
        const phone = phoneOf(parentKey?.remote);
        if (!phone || !parentKey?.id) {
            return null;
        }
        const fromMe = senderWid ? phoneOf(senderWid) !== phone : false;
        return {
            kind: "reaction",
            id: `${parentKey.id}:${fromMe ? "me" : phone}`,
            message_id: parentKey.id,
            phone,
            from_me: fromMe,
            emoji: emoji || "",
            t: t || 0,
        };
    }

    function reportReactions(items) {
        items = items.filter(Boolean);
        if (items.length) {
            post({ type: "messages", items });
        }
    }

    function itemOf(msg) {
        const key = msg.id;
        if (!key?.id || msg.isNotification) {
            return null;
        }
        const phone = phoneOf(key.remote);
        if (!phone) {
            return null;
        }
        const item = {
            kind: "message",
            id: key.id,
            phone,
            from_me: Boolean(key.fromMe),
            type: msg.type,
            t: msg.t || 0,
            body: "",
            quoted_id: msg.quotedStanzaID || null,
            // the name the contact gave themselves in WhatsApp
            name: (!key.fromMe && profileName(msg)) || null,
        };
        if (msg.type === "reaction") {
            return null; // see watchReactions
        }
        if (msg.type === "chat") {
            item.body = msg.body || "";
        } else if (MEDIA.has(msg.type)) {
            // the body of a picture is its thumbnail: the text is the caption
            item.body = msg.caption || "";
            item.has_media = true;
            item.filename = msg.filename || null;
            item.mimetype = msg.mimetype || null;
            item.size = msg.size || 0;
        } else if (NOTES[msg.type]) {
            item.note = NOTES[msg.type];
            item.body = msg.caption || "";
        } else {
            return null; // waiting for the message, call, system message...
        }
        return item;
    }

    function report(messages) {
        const items = [];
        for (const msg of messages) {
            const item = itemOf(msg);
            if (item && !reported.has(item.id)) {
                reported.add(item.id);
                items.push(item);
            }
        }
        if (items.length) {
            post({ type: "messages", items });
        }
    }

    function reportAck(msg) {
        if (msg.id?.fromMe && msg.ack >= 2 && phoneOf(msg.id.remote)) {
            post({ type: "messages", items: [{ kind: "status", id: msg.id.id, ack: msg.ack }] });
        }
    }

    function findMessage(id) {
        return allMessages().find((msg) => msg.id?.id === id);
    }

    function toBase64(blob) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result.split(",", 2)[1]);
            reader.onerror = () => reject(reader.error);
            reader.readAsDataURL(blob);
        });
    }

    /** ``promise``, or an error after ``ms``. */
    function within(promise, ms, error) {
        let timer;
        const late = new Promise((_resolve, reject) => (timer = setTimeout(() => reject(new Error(error)), ms)));
        return Promise.race([promise, late]).finally(() => clearTimeout(timer));
    }

    // stands in for the performance logger WhatsApp Web wants with a download: its methods are only called
    const NOOP = new Proxy(function () {}, { get: (_target, key) => (key === "then" ? undefined : NOOP), apply: () => NOOP });

    /** The file of a message, downloaded and decrypted by WhatsApp Web; it does not keep it in memory. */
    async function download(msg) {
        const manager = load(MODULES.download)?.downloadManager;
        if (manager) {
            try {
                const buffer = await within(manager.downloadAndMaybeDecrypt({
                    directPath: msg.directPath,
                    encFilehash: msg.encFilehash,
                    filehash: msg.filehash,
                    mediaKey: msg.mediaKey,
                    mediaKeyTimestamp: msg.mediaKeyTimestamp,
                    type: msg.type,
                    mimetype: msg.mimetype,
                    signal: new AbortController().signal,
                    downloadQpl: NOOP,
                }), DOWNLOAD_TIMEOUT, "WhatsApp Web did not download the file in time.");
                if (buffer?.byteLength) {
                    return new Blob([buffer], { type: msg.mimetype || "application/octet-stream" });
                }
            } catch (error) {
                console.warn("[Odoo Mates WhatsApp Connector] download manager:", error.message);
            }
        }
        // older WhatsApp Web: the file in memory, once the message downloaded it
        if (msg.mediaData?.mediaStage !== "RESOLVED") {
            await within(
                Promise.resolve(msg.downloadMedia?.({ downloadEvenIfExpensive: true, rmrReason: 1, isUserInitiated: true })),
                DOWNLOAD_TIMEOUT,
                "WhatsApp Web did not download the file in time."
            );
        }
        let blob = msg.mediaData?.mediaBlob;
        blob = blob?.forceToBlob ? blob.forceToBlob() : blob;
        if (blob instanceof Blob) {
            return blob;
        }
        throw new Error("WhatsApp Web did not give the file: the extension needs an update.");
    }

    const EXTENSIONS = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
        "application/pdf": "pdf",
        "audio/ogg": "ogg",
        "audio/mpeg": "mp3",
        "audio/mp4": "m4a",
        "video/mp4": "mp4",
    };
    const NAMES = { sticker: "sticker", ptt: "voice-message", audio: "audio", video: "video", image: "photo" };

    async function media(id) {
        const msg = findMessage(id);
        if (!msg || !MEDIA.has(msg.type)) {
            throw new Error("The message is no longer in WhatsApp Web.");
        }
        if ((msg.size || 0) > MAX_MEDIA_SIZE) {
            throw new Error("The file is too big.");
        }
        const blob = await download(msg);
        const mimetype = msg.mimetype || blob.type || "application/octet-stream";
        const extension = EXTENSIONS[mimetype.split(";")[0]] || "bin";
        const name = msg.filename || `${NAMES[msg.type] || "whatsapp"}-${id}.${extension}`;
        return { name, mimetype: mimetype.split(";")[0], data: await toBase64(blob) };
    }

    /** The messages sent to ``phone`` since ``since`` (seconds), oldest first: {id, text}. */
    function sentMessages(phone, since) {
        return allMessages()
            .filter((msg) => msg.id?.fromMe && (msg.t || 0) >= since && phoneOf(msg.id.remote) === phone)
            .sort((a, b) => a.t - b.t)
            .map((msg) => ({ id: msg.id.id, text: (msg.type === "chat" ? msg.body : msg.caption) || "" }));
    }

    /** Whether WhatsApp sent the messages to its server: one tick, no more clock. */
    function transmitted(ids) {
        const wanted = new Set(ids);
        const found = allMessages().filter((msg) => wanted.has(msg.id?.id));
        return found.length === wanted.size && found.every((msg) => (msg.ack || 0) >= 1);
    }

    /** Digits of the number of the chat open on the screen, or null. */
    function activePhone() {
        const Chat = collections.Chat;
        for (const lookup of [
            () => Chat?.getActive?.(),
            () => (Chat?.getModelsArray?.() || Chat?.models || []).find((chat) => chat.active),
        ]) {
            try {
                const chat = lookup();
                if (chat?.id) {
                    return phoneOf(chat.id);
                }
            } catch {
                // next way
            }
        }
        return null;
    }

    /** The chat of a number WhatsApp Web already has, or null. */
    function knownChat(phone) {
        return (collections.Chat?.getModelsArray?.() || collections.Chat?.models || []).find(
            (chat) => !chat.isGroup && phoneOf(chat.id) === phone
        ) || null;
    }

    /**
     * Open the chat of ``phone`` as a click in the list of chats does, without
     * loading the page again. ``allowNew`` false: only a chat WhatsApp Web
     * already has. Answers ``opened``; else ``missing`` (not on WhatsApp),
     * ``limit`` (a new chat, not allowed) or neither (this WhatsApp Web cannot:
     * the extension loads /send?phone= instead).
     */
    async function openChat(phone, allowNew) {
        const wids = load(MODULES.wids);
        const findChat = load(MODULES.findChat);
        const cmd = load(MODULES.cmd)?.Cmd;
        if (!wids?.createWid || !findChat?.findOrCreateLatestChat || !cmd?.openChatBottom) {
            return { opened: false };
        }
        let chat = knownChat(phone);
        const isNew = !chat;
        if (isNew) {
            if (!allowNew) {
                return { opened: false, limit: true };
            }
            let wid = wids.createWid(`${phone}@c.us`);
            const exists = load(MODULES.exists);
            if (exists?.queryWidExists) {
                const found = await exists.queryWidExists(wid);
                if (!found) {
                    return { opened: false, missing: true };
                }
                wid = found.wid || wid;
            }
            const result = await findChat.findOrCreateLatestChat(wid);
            chat = result?.chat || result;
        }
        if (!chat?.id) {
            return { opened: false };
        }
        // the argument changed between versions of WhatsApp Web
        for (const open of [() => cmd.openChatBottom({ chat }), () => cmd.openChatBottom(chat)]) {
            try {
                await open();
            } catch {
                // the other way
            }
            if (activePhone() === phone) {
                return { opened: true, isNew };
            }
        }
        return { opened: false };
    }

    /** A message of the chat of ``phone`` by its id, from the store, loading it when it is not there. */
    async function findChatMessage(phone, id) {
        const loaded = allMessages().find((msg) => msg.id?.id === id && phoneOf(msg.id.remote) === phone);
        if (loaded) {
            return loaded;
        }
        const keys = [true, false].map((fromMe) => `${fromMe}_${phone}@c.us_${id}`);
        try {
            const found = await collections.Msg.getMessagesById?.(keys);
            return found?.messages?.[0] || null;
        } catch {
            return null;
        }
    }

    /** React to a message as a click on an emoji does; an empty emoji takes the reaction back. */
    async function react(phone, id, emoji) {
        const action = load(MODULES.reaction);
        if (!action?.sendReactionToMsg) {
            throw new Error("WhatsApp Web changed: the extension needs an update to send reactions.");
        }
        const msg = await findChatMessage(phone, id);
        if (!msg) {
            throw new Error("WhatsApp Web does not have this message: open its chat there, then react again.");
        }
        await action.sendReactionToMsg(msg, emoji);
        return {};
    }

    /** The address of the profile picture of ``phone``, as the list of chats shows it; null when none. */
    async function pictureUrl(phone) {
        const wid = knownChat(phone)?.id || load(MODULES.wids)?.createWid?.(`${phone}@c.us`);
        if (!wid) {
            return null;
        }
        const bridge = load(MODULES.pictures);
        for (const lookup of [
            () => collections.ProfilePicThumb?.get?.(wid)?.imgFull,
            () => collections.ProfilePicThumb?.get?.(wid)?.eurl,
            async () => (await bridge?.profilePicFind?.(wid))?.eurl,
            async () => (await bridge?.requestProfilePicFromServer?.(wid))?.eurl,
        ]) {
            try {
                const url = await lookup();
                if (url) {
                    return url;
                }
            } catch {
                // next way
            }
        }
        return null;
    }

    /** The profile picture of ``phone``: its data, else its address for Odoo to download, else none. */
    async function picture(phone) {
        const url = await pictureUrl(phone);
        if (!url) {
            return { none: true };
        }
        try {
            const response = await within(fetch(url), 10000, "timeout");
            if (response.ok) {
                const blob = await response.blob();
                if (blob.size && blob.size <= MAX_PICTURE_SIZE) {
                    return { data: await toBase64(blob), mimetype: blob.type || "image/jpeg" };
                }
            }
        } catch {
            // the address goes to Odoo
        }
        return { url };
    }

    /**
     * Quote the message ``id`` in the message box of the open chat, as Reply
     * does: what is sent next answers it. Not sure of the names of WhatsApp
     * Web: each way is tried, and the reply goes without its quote otherwise.
     */
    async function quote(phone, id) {
        const msg = allMessages().find((m) => m.id?.id === id && phoneOf(m.id.remote) === phone);
        const chat = knownChat(phone);
        if (!msg || !chat) {
            return { quoted: false, error: "WhatsApp Web does not have the message it answers." };
        }
        const cmd = load(MODULES.cmd)?.Cmd;
        for (const way of [
            () => cmd?.quoteMsg?.(chat, msg),
            () => cmd?.replyToMsg?.(chat, msg),
            () => cmd?.setQuotedMsg?.(chat, msg),
            () => chat.composeQuotedMsg !== undefined && (chat.composeQuotedMsg = msg),
        ]) {
            try {
                const done = await way();
                if (done !== undefined && done !== false) {
                    return { quoted: true };
                }
            } catch {
                // next way
            }
        }
        return { quoted: false, error: "WhatsApp Web changed: the extension needs an update to quote." };
    }

    /** Mark the chat of ``phone`` read (blue ticks), as opening it does. */
    async function markSeen(phone) {
        const chat = knownChat(phone);
        const seen = load(MODULES.seen);
        if (!chat || !seen?.sendSeen) {
            throw new Error(chat ? "WhatsApp Web changed: the extension needs an update to mark messages read." : "WhatsApp Web does not have this chat.");
        }
        try {
            await seen.sendSeen({ chat, threadId: undefined });
        } catch {
            await seen.sendSeen(chat, false); // older WhatsApp Web
        }
    }

    /** Mark voice messages played (the blue microphone); else at least read. */
    async function markPlayed(phone, ids) {
        const wanted = new Set(ids);
        const msgs = allMessages().filter((msg) => wanted.has(msg.id?.id) && phoneOf(msg.id.remote) === phone);
        const action = load(MODULES.played);
        const play = action && ["markPlayed", "sendPlayedReceipt", "markMessagesPlayed"].map((name) => action[name]).find(Boolean);
        if (play && msgs.length) {
            for (const msg of msgs) {
                await play(msg);
            }
            return { played: true };
        }
        console.warn("[Odoo Mates WhatsApp Connector] no played receipt in this WhatsApp Web: marked read");
        await markSeen(phone);
        return { played: false };
    }

    async function receipt(phone, ids, kind) {
        if (kind === "played") {
            return await markPlayed(phone, ids);
        }
        await markSeen(phone);
        return {};
    }

    function me() {
        const prefs = load(MODULES.me);
        for (const lookup of [() => prefs?.getMaybeMePnUser?.(), () => prefs?.getMaybeMeUser?.()]) {
            try {
                const wid = lookup();
                if (wid?.user) {
                    return wid.user;
                }
            } catch {
                // next way
            }
        }
        return null;
    }

    /**
     * Reactions: WhatsApp Web keeps them as messages of type reaction, or in a
     * collection of their own, by version. Both are watched.
     */
    function watchReactions() {
        collections.Msg.on("add", (msg) => {
            if (msg.type === "reaction" && msg.isNewMsg) {
                reportReactions([reactionItem(msg.reactionParentKey, msg.author || msg.from, msg.reactionText, msg.t)]);
            }
        });
        const Reactions = collections.Reactions;
        if (!Reactions?.on) {
            return;
        }
        const read = (model) => {
            const items = [];
            const groups = model.reactions?.getModelsArray?.() || model.reactions?.models || model.reactions || [];
            for (const group of groups) {
                for (const sender of group.senders?.getModelsArray?.() || group.senders?.models || group.senders || []) {
                    items.push(reactionItem(model.id, sender.senderUserJid || sender.sender, sender.reactionText, sender.timestamp));
                }
            }
            reportReactions(items);
        };
        Reactions.on("add", read);
        Reactions.on("change", read);
    }

    function start(since) {
        const Msg = collections.Msg;
        try {
            watchReactions();
        } catch {
            // reading the messages goes on without the reactions
        }
        const from = since - CATCH_UP_MARGIN;
        // new, or loaded later (a chat opened): what came while the reader was cut off
        const recent = (msg) => msg.isNewMsg || (msg.t || 0) >= from;
        Msg.on("add", (msg) => recent(msg) && report([msg]));
        // a message still being decrypted gets its type later
        Msg.on("change:type", (msg) => recent(msg) && report([msg]));
        Msg.on("change:ack", reportAck);
        // what came while the extension was not reading, as far as the page has
        // it; the extension drops what it already had
        const missed = allMessages()
            .filter((msg) => (msg.t || 0) >= from)
            .sort((a, b) => a.t - b.t)
            .slice(-MAX_CATCH_UP);
        report(missed);
    }

    async function answer(request) {
        if (request.type === "media") {
            return await media(request.id);
        }
        if (request.type === "sent") {
            return { messages: sentMessages(request.phone, request.since) };
        }
        if (request.type === "transmitted") {
            return { transmitted: transmitted(request.ids) };
        }
        if (request.type === "active") {
            return { phone: activePhone() };
        }
        if (request.type === "quote") {
            return await quote(request.phone, request.id);
        }
        if (request.type === "picture") {
            return await picture(request.phone);
        }
        if (request.type === "receipt") {
            return await receipt(request.phone, request.ids, request.kind);
        }
        if (request.type === "react") {
            return await react(request.phone, request.id, request.emoji);
        }
        if (request.type === "open") {
            return await openChat(request.phone, request.allowNew);
        }
        return null;
    }

    let since = null;

    window.addEventListener("message", async (event) => {
        const request = event.data;
        if (event.source !== window || request?.source !== CONTENT) {
            return;
        }
        if (request.type === "init") {
            since = request.since || 0;
            return;
        }
        if (!collections) {
            post({ type: "answer", rid: request.rid, ok: false, retry: true, error: "WhatsApp Web is not ready." });
            return;
        }
        try {
            post({ type: "answer", rid: request.rid, ok: true, ...(await answer(request)) });
        } catch (error) {
            post({ type: "answer", rid: request.rid, ok: false, error: error.message });
        }
    });

    // wait for WhatsApp Web to be linked and loaded, and for the start time
    const startedAt = Date.now();
    let told = "";
    const tell = (state) => {
        const key = JSON.stringify(state);
        if (key !== told) {
            told = key;
            post({ type: "state", ...state });
        }
    };
    const wait = setInterval(() => {
        const found = load(MODULES.collections);
        if (!found?.Msg) {
            if (Date.now() - startedAt > 120000) {
                tell({ ok: false, error: "The modules of WhatsApp Web were not found: the extension needs an update." });
            }
            return;
        }
        const number = me();
        if (!number) {
            tell({ ok: false, error: "WhatsApp Web is not linked." });
            return;
        }
        if (since === null) {
            return;
        }
        clearInterval(wait);
        collections = found;
        try {
            start(since);
            tell({ ok: true, me: number });
        } catch (error) {
            tell({ ok: false, error: `Messages cannot be read: ${error.message}` });
        }
    }, 2000);
    post({ type: "loaded" });
})();
