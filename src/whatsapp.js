// Runs in web.whatsapp.com. The background asks this script to open the chat
// in the page (switch-chat), else opens it with /send?phone=...&text=..., which
// loads the page again; this script then tells the background it is there, and
// sends the text and files it is given. It also relays the messages read by
// page_reader.js to the background.
/* global OM_SELECTORS */
(() => {
    const api = globalThis.browser ?? globalThis.chrome;
    const S = OM_SELECTORS;

    const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

    function find(selectors, root = document) {
        for (const selector of selectors) {
            const element = root.querySelector(selector);
            if (element) {
                return element;
            }
        }
        return null;
    }

    function press(element) {
        (element.closest('button, [role="button"]') || element).click();
    }

    async function waitFor(check, timeout, interval = 250) {
        const end = Date.now() + timeout;
        while (Date.now() < end) {
            const value = check();
            if (value) {
                return value;
            }
            await sleep(interval);
        }
        return null;
    }

    // While it looks the number up, WhatsApp shows a "Starting chat" popup,
    // which may have a button and stay a while when WhatsApp is slow. The
    // "invalid number" popup comes after it, with another text: a popup whose
    // text changed and stays this long is that one.
    const INVALID_AFTER = 2000;
    // a popup that never changes: the lookup did not end
    const STUCK_AFTER = 20000;

    function popupText() {
        return find(S.popup)?.innerText.trim().split("\n")[0] || "";
    }

    async function waitForChat() {
        let firstText = null;
        let popupSince = 0;
        let shownSince = 0;
        let text = "";
        const state = await waitFor(() => {
            if (find(S.composer)) {
                return "chat";
            }
            if (find(S.qrCode)) {
                return "login";
            }
            if (find(S.chatList) && find(S.popupButton)) {
                text = popupText();
                firstText ??= text;
                shownSince ||= Date.now();
                if (text !== firstText) {
                    popupSince ||= Date.now();
                    if (Date.now() - popupSince >= INVALID_AFTER) {
                        return "invalid";
                    }
                }
                if (Date.now() - shownSince >= STUCK_AFTER) {
                    return "stuck";
                }
            } else {
                popupSince = 0;
                shownSince = 0;
            }
            return null;
        }, 45000);
        if (state === "login") {
            throw new Error("WhatsApp Web is not linked: open web.whatsapp.com and scan the QR code with your phone.");
        }
        if (state === "invalid") {
            // the text of WhatsApp, in the language of the user, says what is wrong
            press(find(S.popupButton));
            throw new Error(text ? `WhatsApp Web says: ${text}` : "This number is not on WhatsApp.");
        }
        if (state === "stuck") {
            press(find(S.popupButton));
            throw new Error(`WhatsApp Web could not open the chat${text ? ` (it says: ${text})` : ""}: try again in a moment.`);
        }
        if (!state) {
            throw new Error("WhatsApp Web did not open the chat in time: check its tab in this browser.");
        }
    }

    /** Put ``body`` in the message box: typed, else pasted, as a tab in the background may not take the focus. */
    async function fillComposer(body) {
        if (find(S.composer).textContent.trim()) {
            return true; // filled in by /send?text=
        }
        find(S.composer).focus();
        document.execCommand("insertText", false, body);
        if (await waitFor(() => find(S.composer)?.textContent.trim(), 800)) {
            return true;
        }
        const transfer = new DataTransfer();
        transfer.setData("text/plain", body);
        find(S.composer).dispatchEvent(new ClipboardEvent("paste", { clipboardData: transfer, bubbles: true, cancelable: true }));
        return Boolean(await waitFor(() => find(S.composer)?.textContent.trim(), 1500));
    }

    /** The text could not be put in the message box, and nothing went: the background loads the chat with it. */
    class NoText extends Error {
        code = "no-text";
    }

    async function sendText(body, nothingSent) {
        if (!(await fillComposer(body))) {
            if (nothingSent) {
                throw new NoText("The text could not be typed in WhatsApp Web.");
            }
            throw new Error("The files were sent, but the text could not be typed in WhatsApp Web: send it again as a message.");
        }
        const button = await waitFor(() => find(S.sendButton), 5000);
        if (button) {
            press(button);
        } else {
            // the button changed: Enter in the message box sends, as when typing
            const enter = { key: "Enter", code: "Enter", keyCode: 13, which: 13, bubbles: true, cancelable: true };
            find(S.composer).dispatchEvent(new KeyboardEvent("keydown", enter));
        }
        if (!(await waitFor(() => !find(S.composer)?.textContent.trim(), 5000))) {
            if (!button) {
                console.warn("[Odoo Mates WhatsApp Connector] send button not found", describePage());
                throw new Error("The send button of WhatsApp Web was not found.");
            }
            throw new Error("WhatsApp Web did not send the text.");
        }
    }

    function toFile(attachment) {
        const binary = atob(attachment.data);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) {
            bytes[i] = binary.charCodeAt(i);
        }
        return new File([bytes], attachment.name, { type: attachment.mimetype || "application/octet-stream" });
    }

    function transferOf(files) {
        const transfer = new DataTransfer();
        for (const file of files) {
            transfer.items.add(file);
        }
        return transfer;
    }

    function findAll(selectors) {
        return new Set(selectors.flatMap((selector) => [...document.querySelectorAll(selector)]));
    }

    /** The send button of the file preview, once one shows up that was not there before. */
    function waitForPreview(before, timeout) {
        return waitFor(() => [...findAll(S.mediaSendButton)].find((element) => !before.has(element)), timeout);
    }

    function closeMenus() {
        document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", code: "Escape", keyCode: 27, bubbles: true }));
    }

    // Ways to hand the files to WhatsApp Web, all at once, so they share one
    // preview. Each returns [preview send button or null, what happened].
    const fileWays = {
        async paste(files, before) {
            const composer = find(S.composer);
            composer.focus();
            composer.dispatchEvent(
                new ClipboardEvent("paste", { clipboardData: transferOf(files), bubbles: true, cancelable: true })
            );
            const button = await waitForPreview(before, 4000);
            return [button, button ? "preview" : "no preview"];
        },
        async drop(files, before) {
            const zone = find(S.dropZone);
            if (!zone) {
                return [null, "no chat to drop on"];
            }
            const transfer = transferOf(files);
            const box = zone.getBoundingClientRect();
            const point = { clientX: box.left + box.width / 2, clientY: box.top + box.height / 2 };
            const fire = (target, type) =>
                target.dispatchEvent(new DragEvent(type, { dataTransfer: transfer, bubbles: true, cancelable: true, ...point }));
            fire(zone, "dragenter");
            fire(zone, "dragover");
            await sleep(300);
            // WhatsApp shows a drop area over the chat on dragenter: drop on what is now under the point
            const target = document.elementFromPoint(point.clientX, point.clientY) || zone;
            fire(target, "dragover");
            fire(target, "drop");
            const button = await waitForPreview(before, 4000);
            return [button, button ? "preview" : "no preview"];
        },
        async attach(files, before) {
            const plus = find(S.attachButton);
            if (!plus) {
                return [null, "+ button not found"];
            }
            const inputsBefore = findAll(S.documentInput);
            const menu = await openMenu(plus);
            let input = [...findAll(S.documentInput)].find((e) => !inputsBefore.has(e));
            if (!input) {
                if (!menu.length) {
                    return [null, `the + menu did not open (clicked: ${plus.dataset.icon || plus.tagName})`];
                }
                // the input is made when Document is clicked: page_hook.js keeps it
                const item = documentItem(menu);
                if (!item) {
                    const seen = describeMenu(menu);
                    console.warn("[Odoo Mates WhatsApp Connector] Document not in the menu", seen, menu);
                    closeMenus();
                    return [null, `Document not found in the menu (${seen})`];
                }
                const root = document.documentElement;
                root.dataset.omExpectFile = "1";
                press(item);
                input = await waitFor(() => document.querySelector("input[data-om-picked]"), 3000);
                delete root.dataset.omExpectFile;
                if (!input) {
                    const hook = root.dataset.omHook ? "on" : "off";
                    closeMenus();
                    return [null, `document input not found (hook: ${hook}, clicked: ${item.dataset.icon || item.innerText?.trim().slice(0, 20) || item.tagName})`];
                }
                input.removeAttribute("data-om-picked");
            }
            input.files = transferOf(files).files;
            input.dispatchEvent(new Event("change", { bubbles: true }));
            const button = await waitForPreview(before, 10000);
            if (!button) {
                closeMenus();
            }
            return [button, button ? "preview" : "no preview"];
        },
    };

    /** Click the + and return the elements it brought: its menu. Tries a
     * plain click, then a full pointer sequence, as some buttons open on press. */
    async function openMenu(plus) {
        const added = [];
        const observer = new MutationObserver((records) => {
            for (const record of records) {
                added.push(...[...record.addedNodes].filter((node) => node.nodeType === Node.ELEMENT_NODE));
            }
        });
        observer.observe(document.body, { childList: true, subtree: true });
        try {
            press(plus);
            await waitFor(() => added.length, 1200);
            if (!added.length) {
                const target = plus.closest('button, [role="button"]') || plus;
                const box = target.getBoundingClientRect();
                const at = { bubbles: true, cancelable: true, clientX: box.x + box.width / 2, clientY: box.y + box.height / 2 };
                for (const type of ["pointerdown", "mousedown", "pointerup", "mouseup", "click"]) {
                    const Kind = type.startsWith("pointer") ? PointerEvent : MouseEvent;
                    target.dispatchEvent(new Kind(type, { ...at, button: 0, pointerType: "mouse" }));
                }
                await waitFor(() => added.length, 1200);
            }
            await sleep(300); // let the menu finish
        } finally {
            observer.disconnect();
        }
        return added.filter((node) => node.isConnected);
    }

    // the label of Document, in the languages WhatsApp Web shows most
    const DOCUMENT_LABEL = /^(document|documento|dokument|documents?|документ|المستند|مستند|दस्तावेज़|文档|文件|ドキュメント|문서|belge|dokumen|tài liệu)$/i;

    /** Document in the menu brought by the +: by its icon, else by its label. */
    function documentItem(menu) {
        const inMenu = (selector) => menu.flatMap((node) => [...(node.matches(selector) ? [node] : []), ...node.querySelectorAll(selector)]);
        const byIcon = S.documentMenuItem.map((selector) => inMenu(selector)[0]).find(Boolean);
        if (byIcon) {
            return byIcon;
        }
        const items = inMenu('[role="menuitem"], li, [role="button"], button');
        const byLabel = items.find((element) =>
            [element.getAttribute("aria-label"), element.innerText?.trim().split("\n")[0]].some((label) =>
                DOCUMENT_LABEL.test(label || "")
            )
        );
        // in any language: Document is the first item of the menu of the +
        return byLabel || inMenu('[role="menu"] [role="menuitem"]')[0];
    }

    /** What the + menu shows, to tell in the error. */
    function describeMenu(menu) {
        const all = (selector) => menu.flatMap((node) => [...(node.matches(selector) ? [node] : []), ...node.querySelectorAll(selector)]);
        const icons = [...new Set(all("[data-icon]").map((e) => e.dataset.icon))].slice(0, 10);
        const labels = [...new Set(all('li, [role="menuitem"], [role="button"], button').map((e) => e.innerText?.trim().split("\n")[0]).filter(Boolean))].slice(0, 8);
        return `icons: ${icons.join(", ") || "none"}; labels: ${labels.join(", ") || "none"}`;
    }

    /** Type the text in the caption box of the preview; false when there is none. */
    async function writeCaption(text) {
        const box = await waitFor(() => {
            const focused = document.activeElement;
            if (focused?.isContentEditable && !focused.closest("footer")) {
                return focused;
            }
            return find(S.captionBox);
        }, 3000);
        if (!box) {
            return false;
        }
        box.focus();
        document.execCommand("insertText", false, text);
        const start = text.trim().split("\n")[0].slice(0, 30);
        return Boolean(await waitFor(() => box.textContent.includes(start), 1500));
    }

    /**
     * Send the files in one go, with ``caption`` as the caption of the first:
     * text and PDF then come as one message. Returns whether the caption went
     * with them.
     */
    async function sendFiles(attachments, caption) {
        const files = attachments.map(toFile);
        const names = attachments.map((a) => a.name).join(", ");
        const steps = [];
        let button = null;
        for (const [way, run] of Object.entries(fileWays)) {
            const [found, what] = await run(files, findAll(S.mediaSendButton));
            steps.push(`${way}: ${what}`);
            if (found) {
                button = found;
                break;
            }
        }
        if (!button) {
            console.warn("[Odoo Mates WhatsApp Connector] file not taken", steps, describePage());
            throw new Error(`WhatsApp Web did not take the file ${names} (${steps.join("; ")}).`);
        }
        const captioned = caption ? await writeCaption(caption) : false;
        press(button);
        if (!(await waitFor(() => !button.isConnected, 30000))) {
            throw new Error(`WhatsApp Web did not send the file ${names}.`);
        }
        return captioned;
    }

    /** What the page shows, to fix selectors.js when WhatsApp Web changed. */
    function describePage() {
        const icons = (root) => [...(root?.querySelectorAll("[data-icon]") || [])].map((e) => e.dataset.icon);
        return {
            footerIcons: icons(document.querySelector("footer")),
            fileInputs: [...document.querySelectorAll('input[type="file"]')].map((e) => e.accept),
            dialogs: document.querySelectorAll('[role="dialog"]').length,
            sendIcons: [...document.querySelectorAll('[data-icon*="send"]')].map((e) => e.dataset.icon),
        };
    }

    async function deliver(message, exclude = []) {
        // seconds, with room for a clock behind the one of WhatsApp
        const since = Math.floor(Date.now() / 1000) - 10;
        await waitForChat();
        if (message.quoted) {
            // a reply in Odoo: the message box quotes the message it answers, as Reply does
            const quote = await toReader("quote", { phone: message.phone, id: message.quoted.id }, 5000).catch(() => ({}));
            if (!quote.quoted) {
                console.warn("[Odoo Mates WhatsApp Connector] reply sent without its quote:", quote.error || "no way to quote");
            }
        }
        const attachments = message.attachments || [];
        // with files, the text is their caption; without caption box, it follows them
        const captioned = attachments.length ? await sendFiles(attachments, message.body) : false;
        if (message.body && !captioned) {
            await sendText(message.body, !attachments.length);
        }
        const ids = await sentIds(message, since, new Set(exclude));
        await waitTransmitted(ids);
        lastChat = { phone: message.phone, header: chatHeader() };
        return { ok: true, whatsapp_ids: ids };
    }

    // the chat this tab sent to last, while the page is not loaded again
    let lastChat = null;

    /** The name of the open chat: the first line of its header, without "online", "typing"... */
    function chatHeader() {
        return find(S.chatHeader)?.innerText.trim().split("\n")[0] || null;
    }

    /**
     * WhatsApp Web shows a message at once and sends it a moment later (the
     * clock): loading the page again before that loses it. Wait for its tick;
     * without the reader, give it a few seconds.
     */
    async function waitTransmitted(ids) {
        if (!ids.length) {
            await sleep(3000);
            return;
        }
        for (let i = 0; i < 60; i++) {
            try {
                if ((await toReader("transmitted", { ids }, 2000)).transmitted) {
                    return;
                }
            } catch {
                await sleep(3000);
                return;
            }
            await sleep(500);
        }
        throw new Error("WhatsApp Web did not send the message in time: check the connection of WhatsApp Web.");
    }

    /**
     * The number of the chat open in this tab, when its message box is empty:
     * the extension then sends there without loading the page again. It is
     * the chat sent to last when its header is still on the screen, else the
     * one the reader sees open.
     */
    async function openChatReady() {
        const composer = find(S.composer);
        if (!composer || composer.textContent.trim() || find(S.popupButton)) {
            return null;
        }
        const header = chatHeader();
        if (lastChat && header && header === lastChat.header) {
            return lastChat.phone;
        }
        try {
            return (await toReader("active", {}, 2000)).phone || null;
        } catch {
            return null;
        }
    }

    /**
     * Open the chat of ``phone`` in this page, without loading it again.
     * Answers ``{phone}`` once it shows with an empty message box, ``{missing}``
     * (not on WhatsApp), ``{limit}`` (a new chat, not allowed), or nothing
     * sure: the background then loads /send?phone= as before.
     */
    async function switchChat(phone, allowNew) {
        if (!find(S.chatList) || find(S.popupButton)) {
            return {};
        }
        const composerBefore = find(S.composer);
        const headerBefore = chatHeader();
        let answer;
        try {
            answer = await toReader("open", { phone, allowNew }, 20000);
        } catch {
            return {};
        }
        if (answer.missing || answer.limit) {
            return { missing: answer.missing, limit: answer.limit };
        }
        if (!answer.opened) {
            return {};
        }
        // the screen follows a moment later: until the chat shown is another,
        // the message box is still the one of the chat before
        const composer = await waitFor(() => {
            const found = find(S.composer);
            const changed = !composerBefore || found !== composerBefore || chatHeader() !== headerBefore;
            return changed && found;
        }, 5000);
        // a text the user typed in that chat is not sent in place of the message
        if (!composer || composer.textContent.trim()) {
            return {};
        }
        const check = await toReader("active", {}, 2000).catch(() => ({}));
        if (check.phone !== phone) {
            return {};
        }
        return { phone, isNew: Boolean(answer.isNew) };
    }

    // ------------------------------------------------------------
    // Reading: page_reader.js reads the messages in the page, this script
    // hands them to the background
    // ------------------------------------------------------------

    // the last state the reader told: {ok, me, error}
    let readerState = null;

    /** What this page shows: still loading, the QR code of a browser not linked, or the chats. */
    function pageStatus() {
        if (find(S.qrCode)) {
            return { state: "qr" };
        }
        if (!find(S.chatList)) {
            return { state: "loading" };
        }
        return {
            state: "ready",
            me: readerState?.me || null,
            reader: readerState ? readerState.ok : null,
            error: readerState?.ok === false ? readerState.error : null,
        };
    }

    const READER = "om-whatsapp-reader";
    const CONTENT = "om-whatsapp-content";
    const waiting = new Map();
    let lastRid = 0;

    function toReader(type, data, timeout = 60000) {
        const rid = ++lastRid;
        return new Promise((resolve, reject) => {
            const timer = setTimeout(() => {
                waiting.delete(rid);
                reject(new Error("WhatsApp Web did not answer in time."));
            }, timeout);
            waiting.set(rid, (answer) => {
                clearTimeout(timer);
                waiting.delete(rid);
                resolve(answer);
            });
            window.postMessage({ source: CONTENT, type, rid, ...data }, location.origin);
        });
    }

    /**
     * Ids WhatsApp gave the messages just sent, to tell Odoo; none when the
     * reader does not work. The ids of earlier sends (``exclude``) are not
     * theirs; the one with the text of the message comes first.
     */
    async function sentIds(message, since, exclude) {
        const text = (message.body || "").trim();
        for (let i = 0; i < 6; i++) {
            try {
                const answer = await toReader("sent", { phone: message.phone, since }, 2000);
                const fresh = (answer.messages || []).filter((sent) => !exclude.has(sent.id));
                if (fresh.length) {
                    const own = fresh.filter((sent) => sent.text.trim() === text);
                    return [...own, ...fresh.filter((sent) => !own.includes(sent))].map((sent) => sent.id);
                }
            } catch {
                return [];
            }
            await sleep(500);
        }
        return [];
    }

    async function initReader() {
        const answer = await api.runtime.sendMessage({ type: "inbox-since" }).catch(() => null);
        const since = answer?.since ?? Math.floor(Date.now() / 1000);
        window.postMessage({ source: CONTENT, type: "init", since }, location.origin);
    }

    window.addEventListener("message", (event) => {
        const data = event.data;
        if (event.source !== window || event.origin !== location.origin || data?.source !== READER) {
            return;
        }
        if (data.type === "loaded") {
            initReader();
        } else if (data.type === "answer") {
            const { source, type, rid, ...answer } = data;
            waiting.get(rid)?.(answer);
        } else if (data.type === "messages") {
            api.runtime.sendMessage({ type: "inbox-add", items: data.items }).catch(() => {});
        } else if (data.type === "state") {
            const state = { ok: data.ok, me: data.me || null, error: data.error || null };
            readerState = state;
            api.runtime.sendMessage({ type: "reader-state", state }).catch(() => {});
        }
    });

    api.runtime.onMessage.addListener((request, sender, sendResponse) => {
        if (sender.id !== api.runtime.id) {
            return false;
        }
        if (request?.type === "deliver") {
            deliver(request.message, request.exclude).then(sendResponse, (error) =>
                sendResponse({ ok: false, error: error.message, code: error.code })
            );
            return true;
        }
        if (request?.type === "status") {
            sendResponse(pageStatus());
            return false;
        }
        if (request?.type === "switch-chat") {
            switchChat(request.phone, request.allowNew).then(sendResponse, () => sendResponse({}));
            return true;
        }
        if (request?.type === "open-chat") {
            openChatReady().then((phone) => sendResponse({ phone }));
            return true;
        }
        if (request?.type === "picture") {
            toReader("picture", { phone: request.phone }, 20000).then(sendResponse, (error) =>
                sendResponse({ ok: false, error: error.message })
            );
            return true;
        }
        if (request?.type === "receipt") {
            const { phone, ids, kind } = request.receipt;
            toReader("receipt", { phone, ids, kind }, 20000).then(sendResponse, (error) =>
                sendResponse({ ok: false, error: error.message })
            );
            return true;
        }
        if (request?.type === "react") {
            const { phone, whatsapp_id: id, emoji } = request.reaction;
            toReader("react", { phone, id, emoji }, 20000).then(sendResponse, (error) =>
                sendResponse({ ok: false, error: error.message })
            );
            return true;
        }
        if (request?.type === "media") {
            toReader("media", { id: request.id }, 50000).then(sendResponse, (error) => sendResponse({ ok: false, error: error.message }));
            return true;
        }
        return false;
    });

    let lastState = null;
    setInterval(() => {
        const state = pageStatus().state;
        if (state !== lastState) {
            lastState = state;
            api.runtime.sendMessage({ type: "page-state", state }).catch(() => {});
        }
    }, 2000);

    initReader();
    api.runtime.sendMessage({ type: "whatsapp-loaded" }).catch(() => {});
})();
