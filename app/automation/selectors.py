EMAIL_SELECTORS = (
    "#eposta_adres",
    "#email",
    "input#email",
    "input[type='email']",
    "[data-email]",
    ".emailbox-input",
    ".mail-address",
)

COPY_EMAIL_SELECTORS = (
    "button:has-text('копія')",
    "button:has-text('Copy')",
    "[data-clipboard-target]",
)

REFRESH_SELECTORS = (
    ".yoket-link",
    "a:has-text('Видалити')",
    "button:has-text('новий')",
    "button:has-text('New')",
    "button:has-text('Refresh')",
    "a:has-text('новий')",
    "button:has-text('оновлення')",
    "a:has-text('оновлення')",
    ".refresh",
)

INBOX_ROW_SELECTORS = (
    "table tbody tr",
    ".inbox-dataList li",
    ".mail-list li",
    ".inbox-list li",
    "[data-email-id]",
)

EMPTY_INBOX_TEXTS = (
    "чекає листів",
    "waiting for emails",
    "no emails",
)

EMAIL_BODY_SELECTORS = (
    ".mail-content",
    ".email-content",
    ".message-body",
    "article",
    "iframe",
)
