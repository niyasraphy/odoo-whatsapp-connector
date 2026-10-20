# Odoo Mates WhatsApp Connector

A browser extension for **Chrome** and **Firefox** that connects **WhatsApp Web** to your **Odoo** (versions 15 to 20). Send
WhatsApp messages and PDFs from Odoo while you stay on your Odoo page, and get the replies of your customers
back in Odoo.

It works with the free Odoo module **WhatsApp Connector Web** (`om_whatsapp_web`) by Odoo Mates, built on
**WhatsApp Connector Base** (`om_whatsapp_base`).

**Odoo versions:** 15, 16, 17, 18, 19 and 20, Community and Enterprise, with the module of the same version.

- **Send from Odoo:** a quotation, an invoice, any document with its PDF. The message goes out from WhatsApp
  Web, open in another tab of the same browser.
- **Replies in Odoo:** the answers of your customers, with their pictures, documents and voice messages, come
  to the document they answer and to their conversation in Discuss. Delivered and read ticks, reactions and
  profile pictures too.
- **No Meta API, no sign-up:** it uses your own WhatsApp, as WhatsApp Web does.
- **Only where you allow it:** it talks to the Odoo addresses you allow, and to no other site.
- **One message at a time**, each one started by a user in Odoo. No bulk sending: WhatsApp bans the numbers
  that do it from WhatsApp Web.

> Not affiliated with WhatsApp or Meta. WhatsApp is a trademark of WhatsApp LLC.

## Install

- **Chrome, Edge and other Chromium browsers:** Chrome Web Store (link coming soon).
- **Firefox 140 or later:** Firefox Add-ons (link coming soon).

Then, in your Odoo, install **WhatsApp Connector Web** (`om_whatsapp_web`) from the Odoo Apps store, in the version of your Odoo.

## Set up

1. In Odoo, go to **WhatsApp > Configuration > Accounts**, open an account (or create one), set its
   **Provider** to **WhatsApp Web**, and add the users who send from it.
2. Open **https://web.whatsapp.com** in a tab and link it to your phone, as usual.
3. On a page of your Odoo, click the icon of the extension, then **Allow this Odoo**. The browser asks you to
   confirm the address. (Or add it in the options of the extension.)
4. In Odoo, send a WhatsApp from a contact or a document: it goes out from the WhatsApp Web tab.

Keep WhatsApp Web open in a tab while you work: the replies come to Odoo while it is open, and those that came
while it was closed come when you open it again. The dot in the top bar of Odoo shows whether WhatsApp Web is
connected.

Plain `http://` addresses are only accepted for `localhost`: use the `https://` address of your Odoo.

## Privacy

The extension has no server, and its developer receives nothing. What it reads in WhatsApp Web goes only to the
Odoo addresses you allowed. Groups, statuses and channels are not read. See [PRIVACY.md](PRIVACY.md).

| Permission | Why |
| --- | --- |
| `web.whatsapp.com` | send the messages of Odoo in WhatsApp Web, and read the replies |
| Your Odoo address (asked when you allow it) | talk to the backend pages of that Odoo (`/odoo`, or `/web` up to Odoo 17), and no other site |
| `storage` | keep the allowed addresses, and the messages until Odoo takes them |
| `scripting` | run its script in the Odoo pages you allowed |
| `activeTab` | see the address of the page when you click the icon, to offer to allow it |

## Troubleshooting

- **Send says the address is not allowed:** click the icon of the extension on that Odoo page, then Allow this
  Odoo, and Send again.
- **Not linked:** WhatsApp Web shows its QR code; scan it with your phone.
- **The popup says "Messages not read":** WhatsApp changed its page; update the extension. Sending still works.
- **No replies in Odoo:** the number linked to WhatsApp Web must be the number of the account in Odoo, and the
  user must be one of its users.

---

## For developers

### Build

```
python3 build.py            # dist/chrome, dist/firefox and their .zip
python3 build.py firefox
```

Chrome: `chrome://extensions`, Developer mode, Load unpacked, `dist/chrome`.
Firefox: `about:debugging#/runtime/this-firefox`, Load Temporary Add-on, `dist/firefox/manifest.json`.

`build.py` writes one manifest a browser: a service worker for Chrome; background scripts, the add-on id and the
data collection declaration for Firefox. The store texts and the answers to the store forms are in
[store/LISTING.md](store/LISTING.md); `store/assets.py` draws the icons.

### Files

| File | Runs in | Role |
| --- | --- | --- |
| `src/odoo_bridge.js` | allowed Odoo pages (backend) | relays the requests of Odoo to the background |
| `src/background.js` | background | allowed addresses, inbox, queue, opens the chat in the WhatsApp Web tab |
| `src/origins.js` | background, popup, options | match patterns, safe addresses, backend paths |
| `src/whatsapp.js` | web.whatsapp.com | sends the text and the files in the open chat |
| `src/selectors.js` | web.whatsapp.com | the elements of WhatsApp Web it uses |
| `src/page_hook.js` | web.whatsapp.com page | keeps the file input of Document instead of opening the file picker |
| `src/page_reader.js` | web.whatsapp.com page | reads the messages from the store of WhatsApp Web |
| `src/popup.*` | toolbar icon | on an Odoo page, Allow this Odoo in one click |
| `src/options.*` | options page | allow and remove Odoo addresses |

The protocol with Odoo is in [PROTOCOL.md](PROTOCOL.md).

### How reading works

While WhatsApp Web is open, `page_reader.js` reads the messages from its store, not from the screen: every
one-to-one chat, without opening it or marking it read. Text, pictures, documents, stickers, voice messages,
audio and videos with their files (16 MB at most); locations, contact cards and polls as a note. The messages
sent from the phone, the ticks of the messages sent and the reactions come too.

Odoo decides what it keeps: its contacts, the chats about its documents, and the other numbers when its account
keeps unknown numbers (the default), from the time the account first connected. What it does not keep is
dropped in the browser.

### When WhatsApp Web changes

WhatsApp changes its page without notice. When sending breaks, fix `src/selectors.js`: open WhatsApp Web,
inspect the element (message box, send button, preview of a file) and put its new selector first in its list.
Icons (`data-icon`) and `data-testid` survive longer than labels, which are translated.

When reading breaks (the popup says "Messages not read"), WhatsApp renamed its modules: fix `MODULES` at the
top of `src/page_reader.js`. In the console of WhatsApp Web, `require("WAWebCollections").Msg` must give the
collection of the messages.

### Manual test, with a linked phone

1. Text only, to a number on WhatsApp: sent, and Sent in Odoo and on the chatter.
2. With a PDF (a template with a report): one message, the PDF with the text as its caption. With several
   files: one send, the text on the first file.
3. A number not on WhatsApp: failed in Odoo with the text of the WhatsApp popup. A number on WhatsApp never
   fails this way, even when WhatsApp is slow to look it up.
4. WhatsApp Web tab closed: opened pinned in the background, then sent.
5. Browser not linked (log out in WhatsApp Web): failed with "not linked".
6. Odoo not allowed yet: Send opens the dialog in Odoo; click the icon, Allow this Odoo, then Send in the
   dialog: the message goes, with its files, without reloading the page.
7. Six quick answers in a conversation: all six arrive, in order.
8. The popup says "Reading the messages of +<number> for Odoo" once WhatsApp Web is loaded.
9. Reply from the phone of a contact to a message sent from a sales order: the reply is on the chatter of the
   order within 20 s, and in the conversation in Discuss. Quote an older message of another order: the reply
   goes to that order.
10. A picture, a PDF and a voice message from the contact: in Odoo with their files.
11. A message from an unknown number: a conversation with a Create Contact button (when the account keeps
    unknown numbers). A group message: nothing in Odoo.
12. A message typed on the phone to a contact: in Odoo, sent by the user; a message sent from Odoo is there
    once, and its ticks go to delivered and read.
13. Close the WhatsApp Web tab, get a message, open it again: the message comes to Odoo.
14. A website, shop or portal page of the allowed Odoo: the extension does not answer there.
15. All of it again in Firefox.
