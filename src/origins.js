// Shared by the background, the popup and the options. An allowed Odoo is kept
// as its full origin, port included; its permission and its match pattern use
// the host alone, as Firefox refuses ports in them (Chrome ignores them).
// eslint-disable-next-line no-unused-vars
function patternOf(origin) {
    const url = new URL(origin);
    return `${url.protocol}//${url.hostname}/*`;
}

// Plain http only for an Odoo of this computer: on a network, anyone on the
// way could add a script to the page, and use WhatsApp through it.
// eslint-disable-next-line no-unused-vars
function isSafeOrigin(origin) {
    const url = new URL(origin);
    return url.protocol === "https:" || (url.protocol === "http:" && ["localhost", "127.0.0.1", "[::1]"].includes(url.hostname));
}

// The bridge only runs in the backend of Odoo, not in its website, shop or
// portal, where other scripts may run. Kept in step with odoo_bridge.js.
// eslint-disable-next-line no-unused-vars
function bridgeMatchesOf(origin) {
    const url = new URL(origin);
    return ["/odoo*", "/web", "/web?*", "/web/tests*"].map((path) => `${url.protocol}//${url.hostname}${path}`);
}

// eslint-disable-next-line no-unused-vars
function isBackendUrl(href) {
    const { pathname } = new URL(href);
    return pathname === "/odoo" || pathname.startsWith("/odoo/") || pathname === "/web" || pathname.startsWith("/web/tests");
}
