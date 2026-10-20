// Runs in the Odoo pages the user allowed in the options. Relays the requests
// of the om_whatsapp_web module (window.postMessage, JSON strings) to the
// background, and posts the answers back. See PROTOCOL.md.
//
// When the extension is reloaded or updated, the copy already in an open page
// is cut off from it while a new copy is injected: a cut-off copy stops
// answering, so that only the live one does.
(() => {
    if (globalThis.omWhatsappConnectorBridge) {
        return;
    }
    globalThis.omWhatsappConnectorBridge = true;

    const api = globalThis.browser ?? globalThis.chrome;
    const PAGE = "om-whatsapp-web";
    const EXTENSION = "om-whatsapp-extension";
    const PROTOCOL = 1;
    // cut off from the extension: "Receiving end does not exist", "Extension context invalidated"...
    const CUT_OFF = /receiving end does not exist|context invalidated|message manager disconnected|extension context/i;

    class CutOff extends Error {}

    async function toBackground(message) {
        if (!api.runtime?.id) {
            throw new CutOff();
        }
        try {
            return await api.runtime.sendMessage(message);
        } catch (error) {
            throw CUT_OFF.test(error.message) ? new CutOff() : error;
        }
    }

    // what the page may ask the background, and the fields of the request it passes on
    const RELAYED = {
        send: ["message"],
        inbox: [],
        "inbox-done": ["keys"],
        media: ["message_id"],
        react: ["reaction"],
        status: [],
        receipt: ["receipt"],
        picture: ["phone"],
        "open-tab": [],
    };

    async function answer(request) {
        if (request.protocol !== PROTOCOL) {
            return { ok: false, error: `Unsupported protocol ${request.protocol}, update the extension or Odoo.` };
        }
        if (request.type === "ping") {
            await toBackground({ type: "ping" });
            return { version: api.runtime.getManifest().version, features: ["send", "receive", "react", "status", "receipt", "picture"] };
        }
        const fields = RELAYED[request.type];
        if (!fields) {
            return null;
        }
        try {
            return await toBackground({
                type: request.type,
                ...Object.fromEntries(fields.map((field) => [field, request[field]])),
            });
        } catch (error) {
            if (error instanceof CutOff) {
                throw error;
            }
            return { ok: false, error: error.message };
        }
    }

    async function onMessage(event) {
        if (event.source !== window || event.origin !== location.origin || typeof event.data !== "string") {
            return;
        }
        // the backend only, as in origins.js: the website, shop and portal run other scripts
        const path = location.pathname;
        if (!(path === "/odoo" || path.startsWith("/odoo/") || path === "/web" || path.startsWith("/web/tests"))) {
            return;
        }
        let request;
        try {
            request = JSON.parse(event.data);
        } catch {
            return;
        }
        if (request?.source !== PAGE) {
            return;
        }
        let result;
        try {
            result = await answer(request);
        } catch (error) {
            if (error instanceof CutOff) {
                window.removeEventListener("message", onMessage);
                return;
            }
            result = { ok: false, error: error.message };
        }
        if (result) {
            // its own source and id last: an answer relayed from WhatsApp Web has a source of its own
            window.postMessage(
                JSON.stringify({ ...result, source: EXTENSION, protocol: PROTOCOL, id: request.id }),
                location.origin
            );
        }
    }

    window.addEventListener("message", onMessage);

    // the background has messages for Odoo, or the status of WhatsApp Web
    // changed: tell the page, which then asks
    const WAKES = new Set(["inbox-wake", "status-wake"]);
    function onWake(request, sender) {
        if (!api.runtime?.id) {
            api.runtime?.onMessage?.removeListener(onWake);
            return;
        }
        if (sender.id === api.runtime.id && WAKES.has(request?.type)) {
            window.postMessage(JSON.stringify({ source: EXTENSION, protocol: PROTOCOL, type: request.type }), location.origin);
        }
    }
    api.runtime.onMessage.addListener(onWake);
})();
