/* global patternOf, isSafeOrigin */
const api = globalThis.browser ?? globalThis.chrome;

const list = document.getElementById("origins");
const empty = document.getElementById("empty");
const error = document.getElementById("error");

async function getOrigins() {
    const { origins = [] } = await api.storage.local.get("origins");
    return origins;
}

async function save(origins) {
    // the background registers the bridge in these addresses when they change
    await api.storage.local.set({ origins });
    await render();
}

function showError(message) {
    error.textContent = message;
    error.hidden = !message;
}

async function render() {
    const origins = await getOrigins();
    list.replaceChildren(
        ...origins.map((origin) => {
            const item = document.createElement("li");
            item.className = "origin";
            const label = document.createElement("span");
            label.textContent = origin;
            const remove = document.createElement("button");
            remove.className = "remove";
            remove.textContent = "Remove";
            remove.addEventListener("click", async () => {
                const rest = origins.filter((o) => o !== origin);
                // another allowed Odoo on the same host, another port, keeps the permission
                if (!rest.some((o) => patternOf(o) === patternOf(origin))) {
                    await api.permissions.remove({ origins: [patternOf(origin)] });
                }
                await save(rest);
            });
            item.append(label, remove);
            return item;
        })
    );
    empty.hidden = origins.length > 0;
}

document.getElementById("add").addEventListener("submit", async (event) => {
    event.preventDefault();
    showError("");
    let origin;
    try {
        origin = new URL(document.getElementById("address").value.trim()).origin;
    } catch {
        showError("Enter the full address, for example https://mycompany.odoo.com");
        return;
    }
    if (!/^https?:/.test(origin)) {
        showError("Only http and https addresses can be allowed.");
        return;
    }
    if (!isSafeOrigin(origin)) {
        showError("Use the https address of your Odoo: plain http is only allowed for localhost.");
        return;
    }
    // must stay the first await: the browser asks only during the click
    api.storage.local.set({ pending: origin }); // not awaited: see the popup
    const granted = await api.permissions.request({ origins: [patternOf(origin)] });
    if (!granted) {
        showError("The browser did not allow this address.");
        return;
    }
    // the background keeps the address once the permission is granted; saved
    // here too for the browsers that are slower to tell it
    const origins = await getOrigins();
    if (!origins.includes(origin)) {
        await save([...new Set([...origins, origin])]);
    } else {
        await render();
    }
    document.getElementById("address").value = "";
});

render();
