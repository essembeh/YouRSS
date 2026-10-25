/**
 * Listen mode (docs/specs/listen-mode.md, mini-player.md): the player of the page stays in its mini player, with large
 * commands, and the cards are its queue. On top of the stage of yourss-player.js, this module adds the `listen` URL
 * parameter, the screen kept on and the Media Session.
 */
import { $, $$, listening } from "yourss/core"
import { hooks, seekBy, stagePlayer, step, toListen } from "yourss/player"

export const listenInUrl = () => new URLSearchParams(location.search).has("listen")

// `?listen` rather than `?listen=`: the address stays readable once bookmarked.
export function withListen(href, on = true) {
  const url = new URL(href, location.href)
  url.searchParams.delete("listen")
  if (on) {
    url.searchParams.set("listen", "")
  }
  return url.toString().replace(/([?&])listen=(&|$)/, "$1listen$2")
}

/* ---------- screen kept on while it plays: an embedded player stops with the screen ---------- */
let wakeLock = null

async function keepAwake(on) {
  if (!on) {
    wakeLock?.release()
    wakeLock = null
    return
  }
  // Absent on http:// (secure contexts only) and on older browsers
  if (wakeLock || !navigator.wakeLock) {
    return
  }
  try {
    wakeLock = await navigator.wakeLock.request("screen")
    wakeLock.addEventListener("release", () => (wakeLock = null))
  } catch {
    /* refused: low battery, page hidden */
  }
}

// The lock is released by the browser when the page is hidden; it is asked again when it comes back.
const playing = () => $("#yourss-stage")?.classList.contains("is-playing") ?? false
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible" && listening() && playing()) {
    keepAwake(true)
  }
})

/* ---------- lock screen and Bluetooth commands, when the browser routes them to the page ---------- */
const MEDIA_ACTIONS = {
  play: () => stagePlayer()?.playVideo(),
  pause: () => stagePlayer()?.pauseVideo(),
  previoustrack: () => step(-1),
  nexttrack: () => step(1),
  seekbackward: () => seekBy(-30),
  seekforward: () => seekBy(30),
}

function setMediaSession(on) {
  if (!("mediaSession" in navigator)) {
    return
  }
  for (const [action, handler] of Object.entries(MEDIA_ACTIONS)) {
    try {
      navigator.mediaSession.setActionHandler(action, on ? handler : null)
    } catch {
      /* action unknown to this browser */
    }
  }
  if (!on) {
    navigator.mediaSession.metadata = null
  }
}

/* ---------- hold −30 / +30: the jump adds up on the button, one seek on release (listen-mode.md) ---------- */
const HOLD_DELAY = 500
const HOLD_STEP = 500
// Past this, each step is a minute: a long podcast is crossed in a few seconds
const HOLD_FAST = 3000
let hold = null
let swallowClick = false

const jumpLabel = (seconds) => {
  const abs = Math.abs(seconds)
  return `${seconds < 0 ? "−" : "+"}${Math.floor(abs / 60)}:${String(abs % 60).padStart(2, "0")}`
}

const clock = (seconds) => {
  const s = Math.floor(seconds)
  const mm = String(Math.floor(s / 60) % 60).padStart(s >= 3600 ? 2 : 1, "0")
  return `${s >= 3600 ? `${Math.floor(s / 3600)}:` : ""}${mm}:${String(s % 60).padStart(2, "0")}`
}

// The finger hides the button: a bubble above it shows the jump and where it lands; a short buzz per step (Android).
function holdTick() {
  const { button, unit, started } = hold
  hold.total += Date.now() - started >= HOLD_FAST ? 2 * unit : unit
  button.textContent = jumpLabel(hold.total)
  button.dataset.jump = jumpLabel(hold.total)
  const player = stagePlayer()
  const duration = player?.getDuration?.() || 0
  if (duration) {
    const target = Math.min(duration, Math.max(0, player.getCurrentTime() + hold.total))
    button.dataset.target = `→ ${clock(target)} / ${clock(duration)}`
  }
  button.classList.add("is-holding")
  navigator.vibrate?.(10)
  hold.timer = setTimeout(holdTick, HOLD_STEP)
}

// Released (done) or left (cancelled): the button gets its label back; a hold that counted swallows the click.
function endHold(done) {
  if (!hold) {
    return
  }
  const { button, label, total, timer } = hold
  clearTimeout(timer)
  hold = null
  button.textContent = label
  button.classList.remove("is-holding")
  delete button.dataset.jump
  delete button.dataset.target
  if (total !== Number(button.dataset.seconds)) {
    swallowClick = true
    if (done) {
      seekBy(total)
    }
  }
}

document.addEventListener("pointerdown", (event) => {
  // A new gesture: a hold released out of its button left no click to swallow
  swallowClick = false
  const button = event.target.closest('.yourss-stage [data-action="seek"]')
  if (!button || event.button !== 0) {
    return
  }
  // A touch captures the pointer on its own: released, leaving the button cancels the hold
  button.releasePointerCapture?.(event.pointerId)
  const unit = Number(button.dataset.seconds)
  hold = { button, unit, total: unit, label: button.textContent, started: Date.now() }
  hold.timer = setTimeout(holdTick, HOLD_DELAY)
})
document.addEventListener("pointerup", () => endHold(true))
document.addEventListener("pointercancel", () => endHold(false))
document.addEventListener("pointerout", (event) => hold && event.target === hold.button && endHold(false))
// Before the handler of the commands (yourss.js): the click that ends a hold is not a +30 more
window.addEventListener(
  "click",
  (event) => {
    if (swallowClick) {
      swallowClick = false
      if (event.target.closest('[data-action="seek"]')) {
        event.stopPropagation()
      }
    }
  },
  true,
)
document.addEventListener("contextmenu", (event) => event.target.closest?.(".yourss-stage .is-seek") && event.preventDefault())

/* ---------- what to listen to: the page, its channels and their tabs (listen-mode.md) ---------- */
// Each row names its source in the page (the sidebar, the tabs): a choice clicks it, nothing is copied
const homeSource = () => $("details.yourss-folder[open] > summary") || $(".yourss-home-link")
const entriesList = () => $("details.yourss-folder[open] .yourss-channels") || $(".yourss-nav > .yourss-channels")
const shownSource = () => $(".yourss-hero[data-channel-page]")?.dataset.channelPage
const shownTabs = () => $$(".yourss-tabs .yourss-tab")
// The tabs of a channel not shown yet are not in the page: the usual ones, a missing one falls back to Recent
const TABS = ["Recent", "Videos", "Shorts", "Streams"]

function icon(name) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg")
  const use = document.createElementNS("http://www.w3.org/2000/svg", "use")
  use.setAttribute("href", `#i-${name}`)
  svg.append(use)
  return svg
}

function navButton(className, data, children) {
  const button = document.createElement("button")
  button.type = "button"
  button.className = className
  Object.assign(button.dataset, data)
  button.append(...children)
  return button
}

function label(text) {
  const span = document.createElement("span")
  span.textContent = text
  return span
}

function buildNav(list) {
  const shown = shownSource()
  const rows = []
  const home = homeSource()
  if (home) {
    const title = home.querySelector(".yourss-label")?.textContent.trim()
    const li = document.createElement("li")
    const row = navButton("yourss-listen-nav-item", { action: "listen-go", go: "home" }, [
      icon("home"),
      label(title && home.tagName === "SUMMARY" ? `All of ${title}` : "The whole page"),
    ])
    row.classList.toggle("is-current", !shown)
    li.append(row)
    rows.push(li)
  }
  const entries = entriesList()
  for (const entry of entries ? $$(":scope > li", entries) : []) {
    const id = entry.dataset.channelId || entry.dataset.playlistId
    const picture = $(".yourss-avatar, .yourss-nav-item > svg", entry)?.cloneNode(true) ?? icon("rss")
    const li = document.createElement("li")
    li.className = "yourss-listen-nav-entry"
    const name = label($(".yourss-label", entry)?.textContent.trim() || id)
    // A playlist has no tabs: it is chosen at once; a channel unfolds its tabs
    const row = entry.dataset.playlistId
      ? navButton("yourss-listen-nav-item", { action: "listen-go", go: "entry", id }, [picture, name])
      : navButton("yourss-listen-nav-item", { action: "listen-unfold" }, [picture, name, icon("chevron")])
    row.classList.toggle("is-current", id === shown)
    li.append(row)
    if (entry.dataset.channelId) {
      const tabs = document.createElement("div")
      tabs.className = "yourss-listen-nav-tabs"
      const found = id === shown ? shownTabs() : []
      const names = found.length ? found.map((tab) => tab.textContent.trim()) : TABS
      names.forEach((tab, index) => {
        const chip = navButton("yourss-listen-nav-tab", { action: "listen-go", go: "tab", id, tab }, [label(tab)])
        chip.classList.toggle("is-current", found[index]?.classList.contains("active") ?? false)
        tabs.append(chip)
      })
      li.append(tabs)
      li.classList.toggle("is-open", id === shown)
    }
    rows.push(li)
  }
  list.replaceChildren(...rows)
}

// One channel unfolded at a time.
export function listenNavUnfold(el) {
  const entry = el.closest(".yourss-listen-nav-entry")
  const open = !entry.classList.contains("is-open")
  $$(".yourss-listen-nav-entry.is-open").forEach((other) => other.classList.remove("is-open"))
  entry.classList.toggle("is-open", open)
}

// Opens or closes the panel (`open` forces it); true when it was open, so that Esc closes it first.
export function listenNav(open) {
  const panel = $("[data-listen-nav]")
  if (!panel) {
    return false
  }
  const wasOpen = !panel.hidden
  const show = open ?? !wasOpen
  if (show) {
    buildNav($("[data-listen-nav-list]", panel))
  }
  panel.hidden = !show
  return wasOpen
}

// A tap around the sheet closes it.
document.addEventListener("click", (event) => event.target.matches?.("[data-listen-nav]") && listenNav(false))

const entryLink = (id) =>
  $(`li[data-channel-id="${CSS.escape(id)}"] > a, li[data-playlist-id="${CSS.escape(id)}"] > a`, entriesList())

// A choice loads its content as the page would (htmx); the first new card then starts (leaveCard, listenRefresh).
// The tab of a channel not shown yet waits on the body until the channel is in (`data-listen-tab`).
export function listenNavGo(el) {
  listenNav(false)
  const { go, id, tab } = el.dataset
  if (go === "home") {
    const home = homeSource()
    // The Home of a page is a plain link, a reload: the mode goes with the address
    if (home?.tagName === "A") {
      location.href = withListen(home.href)
    } else {
      home?.click()
    }
  } else if (go === "entry") {
    entryLink(id)?.click()
  } else if (id === shownSource()) {
    shownTabs()
      .find((button) => button.textContent.trim() === tab)
      ?.click()
  } else {
    const link = entryLink(id)
    if (link && tab !== TABS[0]) {
      document.body.dataset.listenTab = tab
    }
    link?.click()
  }
}

/* ---------- the hooks of the stage ---------- */
hooks.onState = (on, state) => {
  if (listening() && state !== window.YT.PlayerState.BUFFERING) {
    keepAwake(on)
  }
}

hooks.onVideo = (video, { title, channel }) => {
  if (listening() && "mediaSession" in navigator) {
    const artwork = $(".yourss-thumbnail", video)?.src
    navigator.mediaSession.metadata = new MediaMetadata({ title, artist: channel, artwork: artwork ? [{ src: artwork }] : [] })
  }
}

// The player closed (✕, Esc, new content): the listen mode ends with it.
hooks.onClose = () => {
  if (!listening()) {
    return
  }
  keepAwake(false)
  setMediaSession(false)
  document.body.classList.remove("listening")
  history.replaceState(history.state, "", withListen(location.href, false))
}

/* ---------- entering: the URL carries the mode ---------- */
export function enterListen() {
  if (!listening()) {
    document.body.classList.add("listening")
    setMediaSession(true)
    history.replaceState(history.state, "", withListen(location.href))
  }
  toListen()
}

// New cards (a folder loaded at start, infinite scroll): the queue grows, nothing started yet starts.
export function listenRefresh() {
  if (!listening()) {
    return
  }
  // The channel chosen with a tab is in: that tab is opened, its cards start, not the ones of Recent
  const pending = document.body.dataset.listenTab
  if (pending && $(".yourss-tabs")) {
    delete document.body.dataset.listenTab
    const tab = shownTabs().find((button) => button.textContent.trim() === pending)
    if (tab) {
      tab.click()
      return
    }
  }
  toListen()
}
