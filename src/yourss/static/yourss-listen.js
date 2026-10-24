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
