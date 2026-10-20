// Runs in the page of WhatsApp Web itself (MAIN world), injected by the
// background. WhatsApp Web makes the input of Document when it is clicked and
// opens the file picker at once: when the extension expects it, the picker is
// skipped and the input is kept in the page, for the extension to give it the
// file.
(() => {
    const root = document.documentElement;
    if (root.dataset.omHook) {
        return;
    }
    root.dataset.omHook = "1";

    // keep the input instead of opening the picker; true when it was expected
    const keep = (input) => {
        if (input?.type !== "file" || !root.dataset.omExpectFile) {
            return false;
        }
        delete root.dataset.omExpectFile;
        input.setAttribute("data-om-picked", "1");
        if (!input.isConnected) {
            input.style.display = "none";
            document.body.append(input);
        }
        return true;
    };

    const click = HTMLInputElement.prototype.click;
    HTMLInputElement.prototype.click = function () {
        return keep(this) ? undefined : click.call(this);
    };
    const showPicker = HTMLInputElement.prototype.showPicker;
    if (showPicker) {
        HTMLInputElement.prototype.showPicker = function () {
            return keep(this) ? undefined : showPicker.call(this);
        };
    }
    // a click on its label, or a click event sent to it
    document.addEventListener(
        "click",
        (event) => {
            if (keep(event.target)) {
                event.preventDefault();
            }
        },
        true
    );
})();
