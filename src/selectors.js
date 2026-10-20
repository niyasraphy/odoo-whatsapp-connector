// Elements of WhatsApp Web, most stable first. WhatsApp changes its page
// without notice: when sending breaks, this is the file to fix. Icons
// (data-icon) are preferred to labels, which are translated.
// eslint-disable-next-line no-unused-vars
const OM_SELECTORS = {
    // the message box of the open chat
    composer: [
        'footer div[contenteditable="true"][role="textbox"]',
        'footer div[contenteditable="true"]',
        '#main div[contenteditable="true"]',
    ],
    sendButton: [
        'footer span[data-icon="wds-ic-send-filled"]',
        'footer span[data-icon="send"]',
        'footer button[aria-label="Send"]',
        'footer [data-icon*="send"]',
        // the message box may no longer be in a footer: the send button of the open chat
        '#main [data-icon="wds-ic-send-filled"]',
        '#main button[aria-label="Send"]',
        '#main [data-icon*="send"]',
    ],
    // the send button of the preview of a file; only one that shows up after the
    // file was given counts, so loose selectors are fine here
    mediaSendButton: [
        'div[role="dialog"] [data-icon*="send"]',
        '[data-icon="wds-ic-send-filled"]:not(footer *)',
        '[data-icon*="send"]:not(footer *)',
        '[aria-label="Send"]:not(footer *)',
    ],
    // the caption box of that preview (the one focused is used first)
    captionBox: [
        'div[role="dialog"] div[contenteditable="true"]',
        'div[contenteditable="true"][aria-label*="caption" i]',
        'div[contenteditable="true"]:not(footer *)',
    ],
    // the + of the message box, which opens the menu with Document
    attachButton: [
        'footer button[aria-label="Attach"]',
        'footer [data-icon="plus-rounded"]',
        'footer [data-icon="plus"]',
        'footer [data-icon*="plus"]',
        'footer [data-icon*="attach"]',
        'footer [data-icon*="clip"]',
        'footer button[title="Attach"]',
    ],
    // Document, in that menu
    // (looked for only in the menu the + brings, by icon here, else by its label)
    documentMenuItem: ['[data-icon*="document"]', '[data-icon*="doc"]'],
    // the hidden input of Document, when WhatsApp Web keeps one in the page
    documentInput: ['input[type="file"][accept="*"]', 'input[type="file"]:not([accept^="image"]):not([accept^="video"])'],
    // where a file can be dropped
    dropZone: ['#main', '#app'],
    // the popup shown for a number that is not on WhatsApp
    popup: ['div[data-animate-modal-popup="true"]', 'div[role="dialog"]'],
    popupButton: ['div[data-animate-modal-popup="true"] button', 'div[role="dialog"] button'],
    // the QR code of a browser not linked to a phone
    qrCode: ['[data-testid="link-device-qr-code"]', 'div[data-ref] canvas', 'canvas[aria-label*="QR"]'],
    // the header of the open chat: its text changes with the chat
    chatHeader: ['#main header'],
    // the list of chats, there once WhatsApp Web is loaded
    chatList: ['#pane-side', '#side'],
};
