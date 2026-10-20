// The popup of the toolbar icon: on an Odoo page not allowed yet, allow it in
// one click. activeTab gives the address of the page and a look at it, only
// when the user clicks the icon.
/* global patternOf, isSafeOrigin */
const api = globalThis.browser ?? globalThis.chrome;

const state = document.getElementById("state");
const error = document.getElementById("error");

function show(...nodes) {
    state.replaceChildren(...nodes);
}

function text(tag, content, className) {
    const element = document.createElement(tag);
    element.textContent = content;
    if (className) {
        element.className = className;
    }
    return element;
}

async function isOdoo(tabId) {
    try {
        const [result] = await api.scripting.executeScript({
            target: { tabId },
            world: "MAIN",
            func: () => Boolean(window.odoo && (window.odoo.info || window.odoo.loader)),
        });
        return Boolean(result?.result);
    } catch {
        return false;
    }
}

async function allowedOrigins() {
    const { origins = [] } = await api.storage.local.get("origins");
    return origins.filter(isSafeOrigin);
}

async function render() {
    const [tab] = await api.tabs.query({ active: true, currentWindow: true });
    let origin = null;
    try {
        origin = tab?.url && new URL(tab.url).origin;
    } catch {
        origin = null;
    }
    if (!origin || !/^https?:/.test(origin) || origin === "https://web.whatsapp.com") {
        show(text("p", "Open your Odoo, then click this icon to allow it."));
        return;
    }
    if (!isSafeOrigin(origin)) {
        show(text("p", "Open your Odoo with https to allow it:"), text("p", origin, "origin"),
            text("p", "Plain http is only allowed for localhost.", "muted"));
        return;
    }
    const allowed =
        (await allowedOrigins()).includes(origin) &&
        (await api.permissions.contains({ origins: [patternOf(origin)] }));
    if (allowed) {
        show(text("p", "WhatsApp messages can be sent from", ""), text("p", origin, "origin"), text("p", "Allowed", "ok"));
        return;
    }
    if (!(await isOdoo(tab.id))) {
        show(text("p", "This page does not look like Odoo:"), text("p", origin, "origin"),
            text("p", "Open your Odoo, then click this icon to allow it.", "muted"));
        return;
    }
    const button = text("button", "Allow this Odoo");
    button.addEventListener("click", async () => {
        error.hidden = true;
        // not awaited: the browser asks only during the click
        api.storage.local.set({ pending: origin });
        const granted = await api.permissions.request({ origins: [patternOf(origin)] });
        if (!granted) {
            error.textContent = "The browser did not allow this address.";
            error.hidden = false;
            return;
        }
        // the background keeps the address and starts the bridge in its tabs
        for (let i = 0; i < 20 && !(await allowedOrigins()).includes(origin); i++) {
            await new Promise((resolve) => setTimeout(resolve, 100));
        }
        render();
renderReader();
    });
    show(text("p", "Send WhatsApp messages from this Odoo:"), text("p", origin, "origin"), button,
        text("p", "Then click Send again in Odoo.", "muted"));
}

/** Whether page_reader.js reads the messages of WhatsApp Web, as it last said. */
async function renderReader() {
    const line = document.getElementById("reader");
    const { reader } = await api.storage.local.get("reader");
    if (!reader) {
        return;
    }
    line.className = `reader ${reader.ok ? "ok" : "error"}`;
    line.textContent = reader.ok
        ? `Reading the messages of +${reader.me} for Odoo`
        : `Messages not read: ${reader.error}`;
    line.hidden = false;
}

document.getElementById("options").addEventListener("click", (event) => {
    event.preventDefault();
    api.runtime.openOptionsPage();
});

render();
renderReader();
