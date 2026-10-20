# Privacy Policy: Odoo Mates WhatsApp Connector

Last updated: 20 October 2026

The Odoo Mates WhatsApp Connector is a browser extension for Chrome and Firefox. It connects WhatsApp Web,
open in a tab of your browser, to the Odoo database of your company, with the Odoo module WhatsApp Connector
Web (`om_whatsapp_web`). This policy says what it reads, where that goes, and what it keeps.

## In short

- The extension has **no server**. Its developer receives nothing: no messages, no numbers, no statistics.
- What it reads in WhatsApp Web goes **only to the Odoo addresses you allowed** in the extension, and to no one
  else.
- It sends no analytics, shows no ads, and sells or shares nothing.

## What it reads

While WhatsApp Web is open in your browser, the extension reads, from the page:

- the messages of your one-to-one chats: their text, files (pictures, documents, voice messages, audio,
  videos, up to 16 MB), time, sender and the message they answer;
- the phone number and the WhatsApp profile name of each contact, and their profile picture when Odoo asks
  for it;
- the delivery and read ticks of the messages, and the reactions;
- the number linked to WhatsApp Web, so that Odoo knows which of its accounts it is.

It does not read groups, statuses or channels.

On the Odoo pages you allowed, it receives from Odoo the messages you send: their text, files and the number
to send to.

## Where it goes

- **To your Odoo.** The messages, numbers, names, files and ticks are handed to the Odoo pages you allowed
  (in the backend of Odoo: `/odoo`, or `/web` up to Odoo 17). Odoo keeps those of its contacts and of the chats about its documents,
  and drops the others, which the extension then deletes. What Odoo keeps is governed by the company that runs
  that Odoo.
- **To WhatsApp.** The messages you send from Odoo are typed into WhatsApp Web and sent by it, as you would by
  hand. WhatsApp's own privacy policy applies to them.
- **Nowhere else.** The extension calls no other server. The only download it makes is a contact's profile
  picture, from WhatsApp itself, inside the WhatsApp Web tab.

## What it keeps

In the storage of your browser (`storage.local`), on your computer only:

- the Odoo addresses you allowed;
- the messages read but not yet taken by Odoo (at most 1000; each one is deleted once Odoo took or dropped it);
- the ids of the messages sent from Odoo (to not record them twice), and the time it last read;
- the state of WhatsApp Web (open, linked number), to show it in Odoo.

Nothing is kept anywhere else. Uninstalling the extension deletes all of it.

## Permissions

| Permission | Why |
| --- | --- |
| `web.whatsapp.com` | to send the messages of Odoo in WhatsApp Web, and read the replies |
| Your Odoo address (asked when you allow it) | to talk to the Odoo pages you allowed, and no other site |
| `storage` | to keep the allowed addresses and the messages not yet taken by Odoo |
| `scripting` | to run its script in the Odoo pages you allowed |
| `activeTab` | to see the address of the page when you click its icon, to offer to allow it |

## Your choices

- Remove an Odoo address in the options of the extension: it stops talking to it at once.
- Close WhatsApp Web: nothing is read while it is closed.
- Uninstall the extension: everything it kept is deleted.
- For the data in Odoo, ask the company that runs it.

## Children

The extension is a business tool, not meant for children under 13, and collects nothing about them.

## Changes

A change to this policy is published here, with its date, before the version of the extension that needs it.

## Contact

Niyas Raphy, developer of the extension: niyasraphyk@gmail.com
