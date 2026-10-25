/**
 * Listen mode (docs/specs/listen-mode.md, mini-player.md): the player of the page stays in its mini player, with large
 * commands, and the cards are its queue. On top of the stage of yourss-player.js, this module adds the `listen` URL
 * parameter, the screen kept on and the Media Session.
 */
import { $, listening } from "yourss/core"
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
export const listenRefresh = () => listening() && toListen()
