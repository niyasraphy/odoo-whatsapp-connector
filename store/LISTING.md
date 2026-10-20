# Store listing: Odoo Mates WhatsApp Connector

What to fill in on the Chrome Web Store and on Firefox Add-ons, for version 1.8.0. Publisher: Niyas Raphy's
own developer accounts. Repository: under `niyasraphy` on GitHub.

Privacy policy URL: the `PRIVACY.md` of the repository once it is pushed, e.g.
`https://github.com/niyasraphy/<repository>/blob/main/PRIVACY.md`.

## Texts

**Name:** Odoo Mates WhatsApp Connector

**Summary (132 characters at most):**
Send WhatsApp messages and PDFs from Odoo through WhatsApp Web, and get the replies of your customers back in Odoo.

**Description:**

Connects WhatsApp Web to your Odoo 20, with the free Odoo module WhatsApp Connector Web (om_whatsapp_web) by
Odoo Mates.

- Send from Odoo: a quotation, an invoice, any document with its PDF, from the WhatsApp button of Odoo. The
  message goes out from WhatsApp Web, open in another tab, while you stay on your Odoo page.
- Replies in Odoo: the answers of your customers, their files and voice messages come to the document they
  answer and to their conversation in Discuss. Delivered and read ticks too.
- No Meta API, no sign-up: it uses your own WhatsApp, as WhatsApp Web does.
- Works only on the Odoo addresses you allow: open your Odoo, click the icon, Allow this Odoo.
- One message at a time, each one sent by a user. No bulk sending.

Needs: Odoo 20 with the module WhatsApp Connector Web (om_whatsapp_web), and WhatsApp Web open in the browser.

Not affiliated with WhatsApp or Meta. WhatsApp is a trademark of WhatsApp LLC.

**Category:** Chrome: Workflow & Planning (or Productivity). Firefox: Productivity.

**Support:** the Odoo Apps page of WhatsApp Connector Web, or the issues of the GitHub repository.

## Chrome Web Store: Privacy practices

**Single purpose:**
Connect WhatsApp Web to the user's own Odoo database: send the messages the user starts in Odoo through
WhatsApp Web, and bring the replies back to that Odoo.

**Permission justifications:**

- `storage`: keeps the Odoo addresses the user allowed, and the messages read in WhatsApp Web until the user's
  Odoo takes them.
- `scripting`: registers the script that talks to Odoo, only in the Odoo addresses the user allowed.
- `activeTab`: reads the address of the current tab when the user clicks the icon, to offer to allow that Odoo.
- Host `https://web.whatsapp.com/*`: sends the messages in WhatsApp Web and reads the replies.
- Optional hosts (`https://*/*`, `http://*/*`): asked one address at a time, only for the Odoo the user allows;
  the extension cannot know the address of the user's Odoo in advance. Plain http is accepted for localhost
  only.

**Remote code:** No. All the code is in the package.

**Data usage, check:**

- Personally identifiable information (phone numbers and names of the contacts)
- Personal communications (the messages and their files)
- Website content (what is read from WhatsApp Web)

**Certify:**

- I do not sell or transfer user data to third parties, outside of the approved use cases. (The data goes to
  the user's own Odoo, which the user chose.)
- I do not use or transfer user data for purposes unrelated to the item's single purpose.
- I do not use or transfer user data to determine creditworthiness or for lending purposes.

## Firefox Add-ons

- **Source code:** not needed, the files are not minified or bundled.
- **Data collection:** declare personal communications. Since 2025 Mozilla asks new add-ons to declare it in
  the manifest too (`browser_specific_settings.gecko.data_collection_permissions`); `build.py` adds it.
- **Add-on id:** `whatsapp-connector@odoomates.com`. It is permanent once published: change it before the first
  upload if it should not carry odoomates.com.
- **Notes for reviewers:** "Works with an Odoo 20 database running the module om_whatsapp_web. Open web.whatsapp.com
  and an Odoo page, click the icon, Allow this Odoo, then send a WhatsApp from a contact in Odoo."

## Screenshots (1280x800)

To capture once om_whatsapp_web has its new screenshots: the popup Allowed on an Odoo page, the options page,
a quotation sent from Odoo with its PDF, and the replies in Discuss.
