/**
 * YouRSS front-end behaviours (see docs/specs/ui-redesign.md).
 *
 * DOM conventions used by the templates:
 *  - a video is `.yourss-video#yourss-video-<id>` with `data-video-id` and optional `data-channel-id`;
 *    its media box is `.yourss-media` (thumbnail `img.yourss-thumbnail`; the player chrome is cloned in while it plays)
 *  - every command is a `[data-action]` element handled by the `actions` table below
 *  - a channel avatar is `img.yourss-avatar` (retried when it fails to load)
 *  - `template#yourss-empty-template` holds the empty state of a tab, `template#yourss-failed-template` the
 *    failure state shown when a channel or tab request fails
 *  - dialogs: `#yourss-settings`, `#yourss-shortcuts`, `#yourss-add`
 *  - an editable page lists its channels in `<body data-page-names>`; channels are added with a
 *    `form.yourss-add-form` (docs/specs/custom-pages.md)
 *
 * State classes: `is-playing`, `is-docked`, `is-watched`, `is-focused`, `is-filtered`,
 * `is-portrait` on a video; `listening`, `rail`, `menu-open`, `hide-watched`, `no-watched`, `watched-ready`, `listen-cover`,
 * `density-*` on body. Elements of the watched feature carry `data-watched-feature`.
 *
 * Everything is client side: theme, density, switches and watched videos live in localStorage
 * (`yourss-*` keys) and never reach the server.
 *
 * ES modules without a build step, resolved by the import map of the base template:
 * `yourss/core` (helpers, storage), `yourss/watched` (watched videos, counters), `yourss/player` (YouTube
 * player), `yourss/listen` (listen mode), and this entry point (settings, navigation, editable pages, commands,
 * htmx hooks).
 */
import { $, $$, flag, focusVideo, focusedVideo, listening, on, store, videoOf, visibleVideos } from "yourss/core"
import { applyWatched, captureFeed, feedIds, setWatched } from "yourss/watched"
import { enterListen, listenInUrl, listenNav, listenNavGo, listenNavUnfold, listenRefresh, withListen } from "yourss/listen"
import {
  closePlayer,
  dismissPlayer,
  leaveCard,
  placeStage,
  play,
  seekBy,
  step,
  togglePlayback,
  undock,
} from "yourss/player"

/* ---------- settings: theme, density and on/off flags ---------- */
const THEMES = ["neon", "dark", "light"]
const DENSITIES = ["compact", "normal", "large"]
const pick = (key, choices, fallback) => (choices.includes(store.get(key)) ? store.get(key) : fallback)

function setPressed(el, pressed) {
  el.classList.toggle("active", pressed)
  el.setAttribute("aria-pressed", String(pressed))
}

// Apply the stored settings to the page and mirror them in the settings dialog.
function applySettings() {
  const theme = pick("theme", THEMES, document.documentElement.dataset.theme)
  const density = pick("density", DENSITIES, "normal")
  document.documentElement.dataset.theme = theme
  DENSITIES.forEach((d) => document.body.classList.toggle(`density-${d}`, d === density))
  document.body.classList.toggle("rail", flag("rail"))
  document.body.classList.toggle("listen-cover", flag("listen-cover"))
  document.body.classList.toggle("no-watched", !flag("new-videos"))
  document.body.classList.toggle("hide-watched", flag("new-videos") && flag("hide-watched"))
  // Mini player turned off while in use: its card is out of the screen, so the player is closed
  if (!flag("dock") && $(".yourss-video.is-docked")) {
    closePlayer()
  }
  // The browser chrome follows the theme (top bar colour)
  const chrome = getComputedStyle(document.documentElement).getPropertyValue("--bg-side").trim()
  $('meta[name="theme-color"]')?.setAttribute("content", chrome)
  $$('[data-action="set-theme"]').forEach((el) => setPressed(el, el.dataset.value === theme))
  $$('[data-action="set-density"]').forEach((el) => setPressed(el, el.dataset.value === density))
  $$('[data-action="toggle"]').forEach((el) => el.setAttribute("aria-pressed", String(flag(el.dataset.flag))))
  $$('[data-action="set-flag"]').forEach((el) => setPressed(el, flag(el.dataset.flag) === (el.dataset.value === "1")))
}

function setSetting(key, value) {
  store.set(key, value)
  applySettings()
}

/* ---------- search: filters the cards of the page by title and channel name ---------- */
function applySearch() {
  const query = ($("#yourss-search")?.value || "").trim().toLowerCase()
  const clear = $(".yourss-search-clear")
  if (clear) {
    clear.hidden = query === ""
  }
  $$(".yourss-video").forEach((el) => {
    el.classList.toggle("is-filtered", query !== "" && !el.textContent.toLowerCase().includes(query))
  })
}

/* ---------- keyboard navigation in the grid ---------- */
// Move the selection in the grid: left / right follow the reading order, up / down go to the
// card of the row above / below which is the closest horizontally.
function moveFocus(direction) {
  const videos = visibleVideos()
  const current = focusedVideo() || $(".yourss-video.is-playing")
  const index = videos.indexOf(current)
  if (index < 0) {
    // Nothing selected yet: start from the first card on screen
    focusVideo(videos.find((el) => el.getBoundingClientRect().bottom > 0) || videos[0])
  } else if (direction === "left" || direction === "right") {
    focusVideo(videos[index + (direction === "right" ? 1 : -1)] || current)
  } else {
    focusVideo(cardInNextRow(videos, current, direction === "down") || current)
  }
}

function cardInNextRow(videos, current, down) {
  const box = current.getBoundingClientRect()
  const center = (b) => b.left + b.width / 2
  const beyond = videos
    .map((el) => ({ el, box: el.getBoundingClientRect() }))
    .filter((item) => (down ? item.box.top >= box.bottom - 1 : item.box.bottom <= box.top + 1))
  if (beyond.length === 0) {
    return null
  }
  const tops = beyond.map((item) => item.box.top)
  const rowTop = down ? Math.min(...tops) : Math.max(...tops)
  const row = beyond.filter((item) => Math.abs(item.box.top - rowTop) < 2)
  row.sort((x, y) => Math.abs(center(x.box) - center(box)) - Math.abs(center(y.box) - center(box)))
  return row[0].el
}

/* ---------- channel or playlist opened inside a page: the URL is `<page>?c=<channel id>` or `<page>?p=<playlist id>` ---------- */
const SELECTION_PARAMS = { c: "channel", p: "playlist" }

function selectionFromUrl() {
  const params = new URLSearchParams(location.search)
  for (const [param, kind] of Object.entries(SELECTION_PARAMS)) {
    const id = params.get(param)
    if (id !== null && /^[\w@.-]+$/.test(id)) {
      return { kind, id }
    }
  }
  return null
}

function markActiveChannel() {
  const wanted = selectionFromUrl()
  $$(".yourss-channel, .yourss-playlist").forEach((row) => {
    const id = row.dataset.channelId || row.dataset.playlistId
    $(".yourss-nav-item", row)?.classList.toggle("active", id === wanted?.id)
  })
  // The Home of a user page, or the row of the open folder
  $$(".yourss-home-link, details.yourss-folder > summary").forEach((el) => {
    const folder = el.closest(".yourss-folder")
    el.classList.toggle("active", wanted === null && (folder === null || folder.open))
  })
}

// Go to the entry after (step 1) or before (step -1) the active one: Home, then each channel and playlist.
function moveChannel(step) {
  const entries = $$(
    ".yourss-home-link, details.yourss-folder > summary, .yourss-channel .yourss-nav-item, .yourss-playlist .yourss-nav-item",
  ).filter((el) => el.offsetParent !== null)
  const target = entries[entries.findIndex((el) => el.classList.contains("active")) + step]
  if (target) {
    target.click()
    target.scrollIntoView({ block: "nearest" })
  }
}

// Open what the URL names when the page shows something else (fresh load, pasted URL).
// `?c=<channel>&p=<playlist>` is a playlist of the channel, opened from its Playlists tab.
function syncChannelFromUrl() {
  const wanted = selectionFromUrl()
  const shown = $("#yourss-content [data-channel-page]")?.dataset.channelPage
  const listed = wanted && $(`.yourss-${wanted.kind}[data-${wanted.kind}-id="${CSS.escape(wanted.id)}"]`)
  const nested = wanted?.kind === "channel" ? new URLSearchParams(location.search).get("p") : null
  const shownNested = $("#yourss-content [data-channel-playlist]")?.dataset.channelPlaylist ?? null
  if (listed && (wanted.id !== shown || nested !== shownNested)) {
    const id = encodeURIComponent(wanted.id)
    const url = nested ? `/htmx/playlist/${encodeURIComponent(nested)}?tab=all&channel=${id}` : `/htmx/${wanted.kind}/${id}`
    htmx.ajax("GET", url, { target: "#yourss-content" })
  }
  markActiveChannel()
}

/* ---------- user page: a tree of pages, one open at a time, loaded on demand (docs/specs/pages-users.md) ---------- */
const folderEls = () => $$("details.yourss-folder")
const folderEl = (name) => folderEls().find((el) => el.dataset.folder === name) || null
const folderLoaded = (name) => ($(`ul[data-folder-list="${CSS.escape(name)}"]`)?.children.length || 0) > 0

// The address of a folder is `/u/<user>/<page>`; the address of the user is its first segment
const userPath = () => location.pathname.replace(/^(\/u\/[^/]+).*$/, "$1")

function folderFromUrl() {
  const match = location.pathname.match(/^\/u\/[^/]+\/([^/]+)$/)
  const name = match && decodeURIComponent(match[1])
  return name && folderEl(name) ? name : null
}

// One folder open at a time, whatever the browser does with the `name` attribute of <details>
function unfold(el) {
  folderEls().forEach((other) => (other.open = other === el))
  syncFolderNav()
}

// The top bar of a phone names the open folder; its chevrons and the sidebar's are disabled at both ends
function syncFolderNav() {
  const name = $("#yourss-folder-name")
  if (!name) {
    return
  }
  const open = folderEls().findIndex((el) => el.open)
  name.textContent = open < 0 ? "" : $(".yourss-label", folderEls()[open]).textContent
  $$('[data-action="folder-step"]').forEach((btn) => {
    const target = open + Number(btn.dataset.step)
    btn.disabled = open < 0 || target < 0 || target >= folderEls().length
  })
}

// Open the previous or the next folder, like a tap on its row: nothing happens at both ends.
// The direction is kept on <html> until the swap settles: the CSS slides the content that way.
function stepFolder(step) {
  const els = folderEls()
  const target = els.findIndex((el) => el.open) + step
  if (els.length > 0 && target >= 0 && target < els.length) {
    document.documentElement.dataset.slide = step > 0 ? "next" : "prev"
    showFolder(els[target].dataset.folder, { push: true })
  }
}
const clearSlide = () => delete document.documentElement.dataset.slide
// The swap settles when the animation starts: the direction stays until the view transition ends
// A transition cut short by the next swap rejects its promise: the direction is cleared either way
on("htmx:afterSettle", () => (document.activeViewTransition?.finished ?? Promise.resolve()).then(clearSlide, clearSlide))
on("htmx:responseError", clearSlide)
on("htmx:sendError", clearSlide)

// A horizontal swipe on the content (phones) moves to the next or the previous folder. The content follows
// the finger, resists when there is no folder on that side, then leaves while the next one loads.
const SWIPE = { lock: 12, minDistance: 60, maxDuration: 800, edge: 25, follow: 0.6, resist: 0.2 }
let swipe = null
const content = () => $("#yourss-content")
function canStep(step) {
  const target = folderEls().findIndex((el) => el.open) + step
  return target >= 0 && target < folderEls().length
}
// Back in place at once, with no transition: the new content must not slide after a swap
function resetContent() {
  const el = content()
  if (el) {
    el.classList.remove("is-swiping", "is-leaving")
    el.style.transition = "none"
    el.style.transform = ""
    void el.offsetWidth
    el.style.transition = ""
  }
}
on("touchstart", (event) => {
  const touch = event.touches[0]
  // While a view transition plays, the touch lands on <html>: it is the content unless the drawer is open
  const onContent =
    event.touches.length === 1 &&
    (event.target.closest(".yourss-main") ||
      (event.target === document.documentElement && !document.body.classList.contains("menu-open")))
  const fromEdge = touch.clientX < SWIPE.edge || touch.clientX > window.innerWidth - SWIPE.edge
  swipe = onContent && !fromEdge && content() ? { x: touch.clientX, y: touch.clientY, time: event.timeStamp, axis: null } : null
}, { passive: true })
on("touchmove", (event) => {
  if (!swipe) {
    return
  }
  const dx = event.touches[0].clientX - swipe.x
  const dy = event.touches[0].clientY - swipe.y
  // The first clear move locks the axis: a vertical one is a scroll, left to the browser
  if (swipe.axis === null && Math.max(Math.abs(dx), Math.abs(dy)) >= SWIPE.lock) {
    swipe.axis = Math.abs(dx) > Math.abs(dy) * 1.5 ? "x" : "y"
  }
  // Moving the content while a view transition captures it aborts that transition: no follow until it ends
  if (swipe.axis === "x" && !document.activeViewTransition) {
    content().classList.add("is-swiping")
    content().style.transform = `translateX(${dx * (canStep(dx < 0 ? 1 : -1) ? SWIPE.follow : SWIPE.resist)}px)`
  }
}, { passive: true })
function endSwipe(event) {
  const start = swipe
  swipe = null
  if (!start || !content()) {
    return
  }
  const dx = event.type === "touchend" ? event.changedTouches[0].clientX - start.x : 0
  const step = dx < 0 ? 1 : -1
  const done = start.axis === "x" && Math.abs(dx) >= SWIPE.minDistance && event.timeStamp - start.time <= SWIPE.maxDuration
  content().classList.remove("is-swiping")
  if (done && canStep(step)) {
    content().classList.add("is-leaving")
    content().style.transform = `translateX(${-step * 30}%)`
    stepFolder(step)
  } else {
    content().style.transform = ""
  }
}
on("touchend", endSwipe, { passive: true })
on("touchcancel", endSwipe, { passive: true })
on("htmx:afterSwap", (event) => event.detail.target?.id === "yourss-content" && resetContent())
on("htmx:responseError", resetContent)
on("htmx:sendError", resetContent)

// Open a folder and load its Home: through a click on its row (htmx pushes the URL) or silently, for the URL of a load.
function showFolder(name, { push }) {
  const el = folderEl(name)
  unfold(el)
  const row = $("summary", el)
  if (push) {
    row.click()
  } else {
    htmx.ajax("GET", row.getAttribute("hx-get"), { target: "#yourss-content" })
  }
}

// Open the folder of the URL. Without one, the page goes to the last folder shown of this user, else to its first one.
function syncFolderFromUrl() {
  if (folderEls().length === 0) {
    return
  }
  const name = folderFromUrl()
  if (name === null) {
    const user = userPath()
    const remembered = store.get("user-page") || ""
    const known = remembered.startsWith(`${user}/`) && folderEl(decodeURIComponent(remembered.slice(user.length + 1)))
    const target = known ? remembered : `${user}/${encodeURIComponent(folderEls()[0].dataset.folder)}`
    location.replace(listenInUrl() ? withListen(target) : target)
  } else if (folderLoaded(name)) {
    unfold(folderEl(name))
    store.set("user-page", location.pathname)
  } else {
    showFolder(name, { push: false })
  }
}

// A folder Home just settled: it is the folder to remember, its cards are the feed, then the URL may name a channel inside it.
on("htmx:afterSettle", (event) => {
  const shown = $("#yourss-content [data-folder-page]")
  if (event.detail.target?.id === "yourss-content" && shown) {
    store.set("user-page", location.pathname)
    captureFeed()
    syncChannelFromUrl()
  }
})

/* ---------- editable page: its channels live in its address (docs/specs/custom-pages.md) ---------- */
const editable = "pageNames" in document.body.dataset
const pageNames = () => (document.body.dataset.pageNames || "").split(",").filter(Boolean)
const EDITED_FLAG = "yourss-edited"
const PAGE_PATH = /^\/(?:UC[\w-]{22}|PL[\w-]{32})(?:,(?:UC[\w-]{22}|PL[\w-]{32}))*$/

// Navigate to the page made of `names`. The next page asks for a new bookmark, or, when it is the
// first one built from the home page, shows how to add more subscriptions.
function goToPage(names) {
  flagEdited(pageNames().length === 0 ? "first" : "1")
  location.assign(names.length > 0 ? `/${names.join(",")}` : "/")
}

function flagEdited(value) {
  try {
    sessionStorage.setItem(EDITED_FLAG, value)
  } catch {
    /* private mode */
  }
}

function removeChannel(el) {
  if (confirm(`Remove ${el.dataset.name} from this page?`)) {
    goToPage(pageNames().filter((name) => name !== el.dataset.id))
  }
}

function showAddError(form, message) {
  const error = $(".yourss-add-error", form)
  error.textContent = message
  error.hidden = message === ""
}

// The server resolves what was typed to a channel or playlist id, the browser builds the new address.
async function addChannel(form) {
  const query = form.elements.q.value.trim()
  if (query === "" || form.classList.contains("is-busy")) {
    return
  }
  form.classList.add("is-busy")
  showAddError(form, "")
  try {
    const response = await fetch(`/api/resolve?q=${encodeURIComponent(query)}`)
    // An unexpected failure of the server has no JSON body
    const body = await response.json().catch(() => ({}))
    if (!response.ok) {
      showAddError(form, typeof body.detail === "string" ? body.detail : `The server failed (error ${response.status}), try again`)
    } else if (pageNames().includes(body.id)) {
      showAddError(form, `${body.name} is already on this page`)
    } else if (pageNames().length >= Number(document.body.dataset.pageMax)) {
      showAddError(form, `A page holds at most ${document.body.dataset.pageMax} channels and playlists: remove one first`)
    } else {
      goToPage([...pageNames(), body.id])
      return
    }
  } catch {
    showAddError(form, "The server cannot be reached")
  }
  form.classList.remove("is-busy")
}

function openAddDialog() {
  const dialog = $("#yourss-add")
  if (dialog && $(".yourss-channels")) {
    $$(".is-highlighted").forEach((el) => el.classList.remove("is-highlighted"))
    dialog.showModal()
    $("input", dialog).focus()
  }
}

async function copyLink(el) {
  const url = location.origin + location.pathname
  try {
    await navigator.clipboard.writeText(url)
    el.textContent = "Address copied"
  } catch {
    // No clipboard access (plain http): let the visitor copy it by hand
    prompt("Address of this page", url)
  }
}

// Remember the page, offer it on the home page and ask for a bookmark after an edit.
function initEditablePage() {
  if (editable && pageNames().length > 0) {
    store.set("page", location.pathname)
  }
  // Offered only when this browser remembers a page, and one an address can still name (ids only)
  const resume = $("#yourss-my-page")
  const page = store.get("page")
  if (resume && page && PAGE_PATH.test(page)) {
    const count = page.split(",").length
    resume.href = page
    $("#yourss-my-page-count").textContent = `${count} subscription${count > 1 ? "s" : ""}`
    $("#yourss-my-page-path").textContent = page
    resume.hidden = false
  }
  try {
    const edited = sessionStorage.getItem(EDITED_FLAG)
    sessionStorage.removeItem(EDITED_FLAG)
    if (edited === "first" && $("#yourss-welcome") && $(".yourss-channels")) {
      welcome()
    } else if (edited && $("#yourss-bookmark")) {
      $("#yourss-bookmark").hidden = false
    }
  } catch {
    /* private mode */
  }
}

// First page built from the home page: show where subscriptions are added, and keep the command
// highlighted (with the menu which holds it on phones) until it is used.
function welcome() {
  $("#yourss-welcome").showModal()
  $$('[data-action="add-channel"], .yourss-topbar [data-action="menu"]').forEach((el) => el.classList.add("is-highlighted"))
}

/* ---------- images ---------- */
// Portrait thumbnails (shorts) are flagged so that CSS can switch the aspect ratio.
function flagPortrait(img) {
  if (img.naturalHeight > img.naturalWidth) {
    img.closest(".yourss-media")?.classList.add("is-portrait")
  }
}

function watchThumbnails() {
  $$("img.yourss-thumbnail").forEach((img) => {
    if (img.complete) {
      flagPortrait(img)
    } else {
      img.addEventListener("load", () => flagPortrait(img), { once: true })
    }
  })
}

// Google rate limits the avatars (HTTP 429): a failed one is retried a few times.
const AVATAR_RETRY_DELAYS = [2000, 6000, 15000]

function retryAvatar(event) {
  const img = event.target
  if (!(img instanceof HTMLImageElement) || !img.classList.contains("yourss-avatar")) {
    return
  }
  const attempt = Number(img.dataset.retry || 0)
  if (attempt < AVATAR_RETRY_DELAYS.length) {
    img.dataset.retry = attempt + 1
    const src = img.getAttribute("src")
    setTimeout(() => img.isConnected && (img.src = src), AVATAR_RETRY_DELAYS[attempt])
  }
}

/* ---------- commands: one entry per `data-action` value ---------- */
const actions = {
  play: (el) => play(videoOf(el).dataset.videoId),
  "folder-step": (el) => stepFolder(Number(el.dataset.step)),
  "close-player": dismissPlayer,
  undock,
  listen: () => (listening() ? closePlayer() : enterListen()),
  "listen-nav": () => listenNav(),
  "listen-go": listenNavGo,
  "listen-unfold": listenNavUnfold,
  step: (el) => step(Number(el.dataset.step)),
  seek: (el) => seekBy(Number(el.dataset.seconds)),
  "toggle-playback": togglePlayback,
  "toggle-watched": (el) => {
    const video = videoOf(el)
    setWatched([video.dataset.videoId], !video.classList.contains("is-watched"))
  },
  "mark-feed-watched": () => setWatched(feedIds()),
  // The videos listed on the channel page, plus the ones the feed knows for this channel.
  "mark-channel-watched": (el) => {
    const onPage = $$("#tab-content .yourss-video[data-video-id]").map((video) => video.dataset.videoId)
    setWatched([...onPage, ...feedIds(el.dataset.channelId)])
    el.classList.add("is-done")
  },
  tab: (el) => $$(".yourss-tab", el.closest('[role="tablist"]')).forEach((tab) => setPressed(tab, tab === el)),
  menu: () => document.body.classList.toggle("menu-open"),
  rail: () => setSetting("rail", flag("rail") ? "0" : "1"),
  settings: () => $("#yourss-settings").showModal(),
  shortcuts: () => $("#yourss-shortcuts").showModal(),
  "close-dialog": (el) => el.closest("dialog").close(),
  "set-theme": (el) => setSetting("theme", el.dataset.value),
  "set-density": (el) => setSetting("density", el.dataset.value),
  toggle: (el) => setSetting(el.dataset.flag, flag(el.dataset.flag) ? "0" : "1"),
  "set-flag": (el) => setSetting(el.dataset.flag, el.dataset.value),
  "reset-storage": () => {
    if (confirm("Reset every setting and forget the watched videos?")) {
      store.clear()
      location.reload()
    }
  },
  dismiss: (el) => el.parentElement.remove(),
  "clear-search": () => {
    $("#yourss-search").value = ""
    applySearch()
    $("#yourss-search").focus()
  },
  "add-channel": openAddDialog,
  // The demo page is welcomed like a first page built from the home page; the link then navigates
  "open-demo": () => flagEdited("first"),
  "welcome-add": (el) => {
    el.closest("dialog").close()
    openAddDialog()
  },
  // An example of the add form goes in its field, ready to be submitted
  "add-example": (el) => {
    const form = el.closest("form")
    form.elements.q.value = el.textContent.trim()
    form.elements.q.focus()
    showAddError(form, "")
  },
  "remove-channel": removeChannel,
  "copy-link": copyLink,
  "scroll-top": () => window.scrollTo({ top: 0, behavior: "smooth" }),
}

on("click", (event) => {
  // A click on the backdrop lands on the dialog element itself.
  if (event.target instanceof HTMLDialogElement) {
    event.target.close()
    return
  }
  // The row of a folder is its Home (htmx loads it), only its caret folds it: never the native toggle
  const summary = event.target.closest("details.yourss-folder > summary")
  if (summary) {
    event.preventDefault()
    const details = summary.parentElement
    if (event.target.closest(".yourss-caret")) {
      // Unfolding a folder never loaded in this page is opening it: its entries come with its Home
      if (details.open) {
        details.open = false
      } else if (folderLoaded(details.dataset.folder)) {
        unfold(details)
      } else {
        showFolder(details.dataset.folder, { push: true })
      }
      return
    }
    if (!event.target.closest("[data-action]")) {
      unfold(details)
      // Choosing a folder leaves the drawer (phones) like choosing a channel does; the caret (a synthetic click) keeps it
      if (event.isTrusted) {
        document.body.classList.remove("menu-open")
      }
      return
    }
  }
  const trigger = event.target.closest("[data-action]")
  if (trigger) {
    actions[trigger.dataset.action]?.(trigger)
  }
  // A click on a card, outside its image and its commands, selects it without playing
  const card = videoOf(event.target)
  if (card && !event.target.closest("[data-action], a, button")) {
    focusVideo(card, false)
  }
  // Leaving the drawer by a link or by the settings entry closes it (phones).
  if (event.target.closest('.yourss-sidebar a, .yourss-sidebar [data-action="settings"]')) {
    document.body.classList.remove("menu-open")
  }
})

on("input", (event) => {
  if (event.target.id === "yourss-search") {
    applySearch()
  }
  // Typing again clears the error of the previous attempt
  const form = event.target.closest(".yourss-add-form")
  if (form) {
    showAddError(form, "")
  }
})

on("submit", (event) => {
  if (event.target.matches(".yourss-add-form")) {
    event.preventDefault()
    addChannel(event.target)
  }
})

on("keydown", (event) => {
  const typing = event.target.matches("input, textarea, [contenteditable]")
  if (event.key === "Escape") {
    document.body.classList.remove("menu-open")
    if (listenNav(false)) {
      return
    }
    if (typing) {
      event.target.value = ""
      event.target.blur()
      applySearch()
    } else if (!$("dialog[open]") && !document.fullscreenElement) {
      dismissPlayer()
    }
    return
  }
  if (typing || event.ctrlKey || event.metaKey || event.altKey) {
    return
  }
  // No other page shortcut while a dialog is open.
  if ($("dialog[open]")) {
    return
  }
  const video = focusedVideo()
  const shift = event.shiftKey
  const folders = folderEls().length > 0
  const shortcuts = {
    "/": () => $("#yourss-search")?.focus(),
    "?": () => $("#yourss-shortcuts").showModal(),
    // In listen mode, Shift + left / right go back / forward 30 seconds in the mini player
    // Otherwise, on a user, Shift + left / right open the previous / next folder
    ArrowRight: () => (shift && listening() ? seekBy(30) : shift && folders ? stepFolder(1) : moveFocus("right")),
    ArrowLeft: () => (shift && listening() ? seekBy(-30) : shift && folders ? stepFolder(-1) : moveFocus("left")),
    // With Shift, up / down walk the sidebar (Home, then each channel) instead of the grid
    ArrowDown: () => (shift ? moveChannel(1) : moveFocus("down")),
    ArrowUp: () => (shift ? moveChannel(-1) : moveFocus("up")),
    n: () => step(1),
    p: () => step(-1),
    // Space plays the selected card (in listen mode: play / pause); without a selection, it scrolls the page
    " ": () => (listening() ? togglePlayback() : video ? play(video.dataset.videoId) : false),
    l: () => (listening() ? closePlayer() : enterListen()),
    w: () => video && setWatched([video.dataset.videoId], !video.classList.contains("is-watched")),
    h: () => flag("new-videos") && setSetting("hide-watched", flag("hide-watched") ? "0" : "1"),
    a: openAddDialog,
    x: dismissPlayer,
  }
  if (event.key in shortcuts && shortcuts[event.key]() !== false) {
    event.preventDefault()
  }
})

/* ---------- htmx: content swaps (channel page, tabs, infinite scroll, history) ---------- */
// Everything that depends on the cards currently in the page.
function refresh() {
  watchThumbnails()
  applyWatched()
  applySearch()
  listenRefresh()
  placeStage()
}

on("htmx:afterSettle", refresh)
on("htmx:pushedIntoHistory", () => {
  markActiveChannel()
  // The links of the page do not carry the mode: the address keeps it while it lasts
  if (listening()) {
    history.replaceState(history.state, "", withListen(location.href))
  }
})
on("htmx:historyRestore", () => {
  closePlayer()
  captureFeed()
  syncFolderFromUrl()
  syncChannelFromUrl()
  refresh()
})

// New content closes the player, appending (infinite scroll) must not; in listen mode the new cards become the queue.
on("htmx:beforeSwap", (event) => {
  const swap = event.detail.elt.getAttribute("hx-swap") || "innerHTML"
  if (!swap.startsWith("afterend") && !swap.startsWith("beforeend")) {
    if (listening()) {
      leaveCard()
    } else {
      closePlayer()
    }
  }
})

// A failed channel or tab request must not leave the previous content on screen: show the failure state.
function showFailure(event) {
  const target = event.detail.target
  if (target?.id === "tab-content" || target?.id === "yourss-content") {
    closePlayer()
    target.replaceChildren($("#yourss-failed-template").content.cloneNode(true))
  }
}
on("htmx:responseError", showFailure)
on("htmx:sendError", showFailure)

/* ---------- boot: a module runs once the document is parsed ---------- */
document.addEventListener("error", retryAvatar, true)
window.addEventListener("scroll", () => $("#scroll-to-top").classList.toggle("visible", window.scrollY > 300), {
  passive: true,
})
applySettings()
initEditablePage()
captureFeed()
syncFolderFromUrl()
syncChannelFromUrl()
refresh()
if (listenInUrl()) {
  enterListen()
}

// Handy from the browser console and from tests.
window.yourss = { play, closePlayer, enterListen, setSetting, setWatched, store }
