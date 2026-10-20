# Protocol between Odoo and the extension

Version 1. The Odoo module is `om_whatsapp_web` (`static/src/extension_bridge.js`).

## Page and bridge

The Odoo page and the bridge (`odoo_bridge.js`, a content script of the Odoo addresses allowed in the
options) talk with `window.postMessage(JSON.stringify(data), location.origin)`. Both sides ignore
messages from other windows, from other origins, and that are not JSON strings.

Request, from the page:

```json
{"source": "om-whatsapp-web", "protocol": 1, "id": "<unique>", "type": "ping"}
{"source": "om-whatsapp-web", "protocol": 1, "id": "<unique>", "type": "send",
 "message": {"phone": "32470123456", "body": "Hello",
             "attachments": [{"name": "INV-001.pdf", "mimetype": "application/pdf", "data": "<base64>"}]}}
{"source": "om-whatsapp-web", "protocol": 1, "id": "<unique>", "type": "inbox"}
{"source": "om-whatsapp-web", "protocol": 1, "id": "<unique>", "type": "inbox-done", "keys": ["message:3EB0..."]}
{"source": "om-whatsapp-web", "protocol": 1, "id": "<unique>", "type": "media", "message_id": "3EB0..."}
{"source": "om-whatsapp-web", "protocol": 1, "id": "<unique>", "type": "react", "reaction": {"phone": "32470123456", "whatsapp_id": "3EB0...", "emoji": "👍"}}
```

Answer, from the bridge, with the `id` of the request:

```json
{"source": "om-whatsapp-extension", "protocol": 1, "id": "<same>", "version": "1.1.0", "features": ["send", "receive"]}
{"source": "om-whatsapp-extension", "protocol": 1, "id": "<same>", "ok": true, "whatsapp_ids": ["3EB0..."]}
{"source": "om-whatsapp-extension", "protocol": 1, "id": "<same>", "ok": false, "error": "This number is not on WhatsApp."}
```

`phone` holds digits only, with the country code. The page waits 0.5 s for a ping and 120 s for a
send. A request with another `protocol` gets `ok: false`. Before 1.1.0 the ping has no `features`:
the extension only sends. From 1.4.0 it has `react`: the reader reacts to the message (its WhatsApp
id, in the chat of `phone`) with `WAWebSendReactionMsgAction.sendReactionToMsg`, an empty `emoji`
taking the reaction back; the answer is `{ok, error}`, within 30 s. A message the store of WhatsApp
Web does not have fails with the reason.

From 1.5.0 it has `status`: `{"type": "status"}` is answered with `{ok, tab, state, me, reader, error}`:
`tab` false when no WhatsApp Web tab is open in this browser; else `state` is `loading` (or a tab that
does not answer within 2.5 s), `qr` (not linked to a phone) or `ready`, with `me` the number linked,
`reader` whether the messages are read (`error` when not). `{"type": "open-tab"}` shows the WhatsApp
Web tab, opened pinned when there is none. The bridge posts `{"type": "status-wake"}` when the status
may have changed (a WhatsApp Web tab closed, opened or loaded, linked or unlinked): the page then asks
`status` again.

From 1.7.0, `picture` (`{phone}`) answers the profile picture of the number, as the list of chats of
WhatsApp Web has it: `{ok, data, mimetype}`, or `{ok, url}` when the page could not download it (Odoo
downloads it, from `*.whatsapp.net` only), or `{ok, none: true}`; `features` has `picture`. Odoo asks
only for the customers without a photo in Odoo, when the account shows the pictures.

From 1.6.0, `receipt` (`{receipt: {phone, ids, kind: "read" | "played"}}`) marks the chat read
(`WAWebUpdateUnreadChatAction.sendSeen`), or voice messages played, else read; `features` has `receipt`.

From 1.5.7, the text is typed in the message box, else pasted (a tab in the background may not take
the focus); when it still cannot be put there and nothing went yet, `deliver` answers `code: "no-text"`
and the background opens the chat with `/send?phone=..&text=..` and delivers again.

From 1.5.6, the bridge sets its own `source`, `protocol` and `id` after the fields of the answer, and
the content script drops the envelope (`source`, `type`, `rid`) of the answers of the reader: before,
the `source` of the reader replaced the one of the extension in the answers of `media` and `react`,
and the page never took them (a timeout).

From 1.5.5, files come from `WAWebDownloadManager.downloadManager.downloadAndMaybeDecrypt`, which now
wants `mimetype` and a `downloadQpl` (a performance logger: a stand-in whose methods do nothing), first;
WhatsApp Web no longer keeps the file of a message in memory (`mediaData.mediaBlob` is empty).

From 1.5.4, each way to download a file has 20 s, and the page waits 60 s for it (1.4.0 to 1.5.3
could not read any file: a helper of the reactions replaced the one that finds the message).

From 1.5.3, an install, update or reload of the extension loads the open WhatsApp Web tab again (its
scripts would be cut off), and the reader reports the messages up to an hour before the last one it
saw, also when WhatsApp Web loads them later (a chat opened): what came while it was cut off is caught
up, and Odoo skips what it already has.

From 1.5.2, `inbox` gives nothing (`waiting: true`) while WhatsApp Web is closed or not ready: the
messages wait in the extension and come together, in order, once it is open and synced; the status
wake then tells the page to take them. From 1.5.1, a `media` answer has `retry: true` when WhatsApp Web cannot give the file now (no tab, a
tab loading or asleep, a reader not ready): the page leaves the message in the inbox, without counting
a try, and asks again once WhatsApp Web is open (for 24 hours at most). `whatsapp_ids` are the ids WhatsApp gave the messages sent (several with
several files), when the reader works.

## Receiving

The reader takes the messages of WhatsApp Web; the Odoo page takes them from the extension and has Odoo
record those of the numbers it knows.

- `inbox` answers `{ok, me, items}`: `me` is the number linked in WhatsApp Web (digits), `items` up to 20
  items, kept for this page for 90 s (another Odoo page gets them after that). An item is
  `{key, kind: "message", id, phone, from_me, type, t, body, quoted_id, has_media, filename, mimetype, size, note}`
  or `{key, kind: "status", id, ack}` (2 delivered, 3 read, 4 played) for a message sent, or
  `{key, kind: "reaction", id, message_id, phone, from_me, emoji}` (no emoji: taken back). A message has `name`,
  the WhatsApp name of the contact, and `has_media` for pictures, documents, stickers, voice messages
  (`type` ptt), audio and videos.
  `id` is the id of the message in WhatsApp (the stanza id), `quoted_id` the one of the message it
  answers. `note` names a kind sent without its content (voice message, video, sticker...).
- `inbox-done` removes the items the page dealt with, recorded or dropped.
- `media` answers `{ok, name, mimetype, data}` (base64) or `{ok: false, error}`: the file of a message, downloaded
  by WhatsApp Web.
- The bridge posts `{"source": "om-whatsapp-extension", "protocol": 1, "type": "inbox-wake"}` (no `id`) when
  there is something new; the page also looks every 20 s.
- Odoo first gets the numbers only (`om_whatsapp_web_accept`), and the text and files of the accepted
  messages after (`om_whatsapp_web_receive`): what comes from other numbers never leaves the browser.

## Inside the extension

- bridge -> background: `{type: "ping"}`, so that a bridge cut off by a reload of the extension does not
  answer the page; `{type: "send", message}`, accepted only from the tabs of an allowed address.
- background: one message at a time. It opens `https://web.whatsapp.com/send?phone=..&text=..` (no text when
  the message has files: the text becomes the caption of the first file, in one send) in
  the WhatsApp Web tab (opened pinned in the background when there is none), and waits for
  `{type: "whatsapp-loaded"}` from that tab.
- background -> WhatsApp Web tab: `{type: "open-chat"}`, answered with `{phone}` when the tab shows the chat of
  that number with an empty message box: the background then sends there without loading the page
  again. Else it asks the tab to switch to the chat.
- background -> WhatsApp Web tab: `{type: "switch-chat", phone, allowNew}`: the reader opens the chat in the page
  (`WAWebCmd.openChatBottom`, the chat found with `WAWebFindChatAction`, the number checked with
  `WAWebQueryExistsJob`), and the tab answers `{phone, isNew}` once it shows that chat with an empty
  message box, `{missing}` for a number not on WhatsApp, `{limit}` for a chat WhatsApp Web never had
  when `allowNew` is false. Any other answer: the background loads `/send?phone=..`, as before.
- background: a pause of 1.5 to 4 s, at random, between two sends; at most 30 new chats opened in the page
  in an hour (`newChats` in `storage.local`).
- background -> WhatsApp Web tab: `{type: "deliver", message, exclude}`, answered with `{ok, error, whatsapp_ids}`
  once WhatsApp sent the messages to its server (their tick): loading the page again before that
  loses them. `exclude` are the ids of earlier sends, which are not those of this one.
- reader (`page_reader.js`, in the page of WhatsApp Web) <-> `whatsapp.js`: `window.postMessage` of objects,
  `source` `om-whatsapp-reader` or `om-whatsapp-content`. The content script gives the start time
  (`init`, seconds); the reader answers `state` (`{ok, me, error}`), `messages` (items), and the
  `media`, `sent` (`{phone, since}` -> `messages`: `{id, text}`), `transmitted` (`{ids}` -> `transmitted`),
  `active` (-> `phone` of the open chat) and `open` (`{phone, allowNew}` -> `opened`, `isNew`, `missing`,
  `limit`) requests with `answer` and their `rid`.
- WhatsApp Web tab -> background: `inbox-add` (items), `inbox-since`, `reader-state`. The background keeps the
  items in `storage.local` (`inbox`, at most 1000), without the messages Odoo sent itself (`sent`), and
  wakes the bridges. A status waits 10 s before an Odoo page gets it. The start time (`since`) is the
  time of the last message seen, the time of the first run before: the past is not read.
- popup: shows `reader` from `storage.local`, the last state of the reader.
- The options save the allowed addresses in `storage.local` (`origins`); the background registers the
  bridge in them when they or the granted permissions change.
