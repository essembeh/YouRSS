/**
 * The YouTube player (docs/specs/mini-player.md): one for the page, the stage, laid over the playing card or kept in the
 * mini player, moved by CSS only (an iframe moved in the DOM reloads).
 */
import { $, $$, flag, focusVideo, focusedVideo, listening, videoById, visibleVideos } from "yourss/core"
import { setWatched } from "yourss/watched"

/* ---------- YouTube IFrame API, loaded on the first play ---------- */
let ytApi = null

export function loadYouTubeApi() {
  ytApi ??= new Promise((resolve) => {
    window.onYouTubeIframeAPIReady = () => resolve(window.YT)
    const script = document.createElement("script")
    script.src = "https://www.youtube.com/iframe_api"
    document.head.appendChild(script)
  })
  return ytApi
}

// A video counts as watched after a few seconds of actual playback (pauses do not count).
const WATCHED_AFTER_SECONDS = 5
const playback = { timer: null, seconds: 0, videoId: null }

function stopPlaybackTracking() {
  clearInterval(playback.timer)
  playback.timer = null
  playback.videoId = null
}

function trackPlayback(playing, videoId) {
  if (playback.videoId !== videoId) {
    playback.videoId = videoId
    playback.seconds = 0
  }
  clearInterval(playback.timer)
  playback.timer = null
  if (!playing || playback.seconds >= WATCHED_AFTER_SECONDS) {
    return
  }
  playback.timer = setInterval(() => {
    playback.seconds += 1
    if (playback.seconds >= WATCHED_AFTER_SECONDS) {
      clearInterval(playback.timer)
      playback.timer = null
      setWatched([videoId])
    }
  }, 1000)
}

// The player always runs on the no-cookie domain.
const PLAYER_HOST = "https://www.youtube-nocookie.com"

// YT.Player replaces its target node, so it is mounted on a disposable child of `host`.
export function createPlayer(YT, host, videoId, { onReady, onEnded, onState, onError } = {}) {
  const mount = document.createElement("div")
  host.replaceChildren(mount)
  return new YT.Player(mount, {
    videoId,
    host: PLAYER_HOST,
    width: "100%",
    height: "100%",
    playerVars: { autoplay: 1 },
    events: {
      onReady: (event) => onReady?.(event.target),
      // The id is read from the player: `loadVideoById` changes it under the same player
      onStateChange: (event) => {
        trackPlayback(event.data === YT.PlayerState.PLAYING, event.target.getVideoData?.().video_id ?? videoId)
        onState?.(event.data)
        if (event.data === YT.PlayerState.ENDED) {
          onEnded?.()
        }
      },
      onError: (event) => onError?.(event.data),
    },
  })
}

// The play / pause and -30 / +30 commands of the mini player (listen mode): false while there is no player yet.
export const stagePlayer = () => stage.player

export function togglePlayback() {
  const player = stage.player
  const state = player?.getPlayerState?.()
  if (state === undefined) {
    return false
  }
  if (state === window.YT.PlayerState.PLAYING || state === window.YT.PlayerState.BUFFERING) {
    player.pauseVideo()
  } else {
    player.playVideo()
  }
  return true
}

export function seekBy(seconds) {
  const player = stage.player
  if (!player?.getCurrentTime) {
    return false
  }
  player.seekTo(Math.max(0, player.getCurrentTime() + seconds), true)
  return true
}

/* ---------- the stage: over the playing card while it is on screen, else in the mini player ---------- */
// What the listen mode (yourss-listen.js) adds on top of the stage
export const hooks = { onState: null, onVideo: null, onClose: null }

const stage = { player: null, ready: false, videoId: null, observer: null, seen: false, resize: null }
const stageEl = () => $("#yourss-stage")
const playingCard = () => $(".yourss-video.is-playing")

// The stage covers the card (absolute, in page coordinates: it follows the scroll by itself) or sits in the corner.
export function placeStage() {
  const el = stageEl()
  const video = playingCard()
  if (!el || !video) {
    return
  }
  const media = $(".yourss-media", video)
  const docked = listening() || video.classList.contains("is-docked")
  el.classList.toggle("is-docked", docked)
  el.classList.toggle("is-anchored", !docked)
  el.classList.toggle("is-portrait", media.classList.contains("is-portrait"))
  if (docked) {
    el.style.cssText = ""
    // The page keeps room under its last cards for the mini player
    document.body.style.setProperty("--stage-h", `${el.offsetHeight}px`)
    return
  }
  const box = media.getBoundingClientRect()
  el.style.cssText = `top: ${box.top + scrollY}px; left: ${box.left + scrollX}px; width: ${box.width}px; height: ${box.height}px`
  document.body.style.removeProperty("--stage-h")
}

// Created once by the first play; every layout change (content, sidebar, density, window) places it again.
function mountStage() {
  if (!stageEl()) {
    document.body.append($("#yourss-stage-template").content.cloneNode(true))
    stage.resize = new ResizeObserver(placeStage)
    stage.resize.observe(stageEl())
    stage.resize.observe($("#yourss-content") ?? document.body)
  }
}
window.addEventListener("resize", placeStage)

// The chrome of the playing card (title bar, placeholder over its media while the video is in the mini player).
function mountChrome(video) {
  const chrome = $("#yourss-player-template").content.cloneNode(true)
  $("[data-player-title]", chrome).textContent = $(".yourss-video-title", video).textContent.trim()
  video.prepend($(".yourss-playing-bar", chrome))
  $(".yourss-media", video).append($(".yourss-dock-placeholder", chrome))
}

// The expanded card spans its row: it only changes on a gesture (a play, ↩, the card back on screen), so the next
// video starting in the mini player does not reflow the grid under the reader.
function expand(video) {
  $$(".yourss-video.is-expanded").forEach((el) => el !== video && el.classList.remove("is-expanded"))
  video?.classList.add("is-expanded")
}

function releaseCard() {
  $$(".yourss-playing-bar, .yourss-dock-placeholder").forEach((el) => el.remove())
  $$(".yourss-video.is-playing, .yourss-video.is-docked").forEach((el) => el.classList.remove("is-playing", "is-docked"))
}

// The title, the channel and the next video, read from the cards; the listen mode adds the Media Session.
function describe(video) {
  const title = $(".yourss-video-title", video)?.textContent.trim() || ""
  const channel = $(".yourss-video-channel span", video)?.textContent.trim() || ""
  $$("[data-stage-title]").forEach((el) => (el.textContent = title))
  $("[data-stage-channel]").textContent = channel
  $("[data-stage-cover]").src = $(".yourss-thumbnail", video)?.src || ""
  const videos = visibleVideos()
  const next = videos[videos.indexOf(video) + 1]
  $("[data-stage-next]").textContent = next ? `Next: ${$(".yourss-video-title", next).textContent.trim()}` : ""
  hooks.onVideo?.(video, { title, channel })
}

// Playing card out of the screen: mini player when the "dock" setting is on, else the player is closed.
function onPlayingCardVisibility(video, visible) {
  stage.seen ||= visible
  // Nothing happens while the page is still scrolling to the card; the listen mode never leaves the mini player
  if (!stage.seen || listening()) {
    return
  }
  if (visible) {
    video.classList.remove("is-docked")
    expand(video)
  } else if (flag("dock")) {
    video.classList.add("is-docked")
  } else {
    closePlayer()
    return
  }
  placeStage()
}

function watchCard(video) {
  stage.observer?.disconnect()
  stage.seen = false
  stage.observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      onPlayingCardVisibility(video, entry.intersectionRatio > 0)
    }
  })
  stage.observer.observe(video)
}

// Another video asked while the player was starting (next tapped at once): it plays as soon as the player is ready.
function onReady(player) {
  stage.ready = true
  if (player.getVideoData?.().video_id !== stage.videoId) {
    player.loadVideoById(stage.videoId)
  }
}

function onState(state) {
  const YT = window.YT
  const on = state === YT.PlayerState.PLAYING || state === YT.PlayerState.BUFFERING
  stageEl()?.classList.toggle("is-playing", on)
  hooks.onState?.(on, state)
}

// End of a video: the next one in listen mode or with autoplay, else a mini player is closed.
function onEnded() {
  if (listening() || flag("autoplay")) {
    step(1)
  } else if ($(".yourss-video.is-docked")) {
    closePlayer()
  }
}

// Not embeddable (101, 150) or gone (100): the listen mode goes on with the next one.
function onError() {
  if (listening()) {
    setTimeout(() => step(1), 1500)
  }
}

export function play(videoId) {
  const video = videoById(videoId)
  if (!video || stage.videoId === videoId) {
    return
  }
  // Already in the mini player: the next video starts there, the page does not move
  const docked = listening() || $(".yourss-video.is-playing.is-docked") !== null
  releaseCard()
  stage.videoId = videoId
  video.classList.add("is-playing")
  if (!listening()) {
    mountChrome(video)
    video.classList.toggle("is-docked", docked)
  }
  focusVideo(video, false)
  if (!docked) {
    expand(video)
    // The expanded card goes to the top of the viewport (CSS scroll-margin-top clears the sticky top bar of phones).
    video.scrollIntoView({ block: "start", behavior: "smooth" })
  }
  mountStage()
  describe(video)
  placeStage()
  watchCard(video)
  loadYouTubeApi().then((YT) => {
    if (stage.videoId !== videoId) {
      return
    }
    if (!stage.player) {
      stage.player = createPlayer(YT, $("#yourss-stage-player"), videoId, { onReady, onEnded, onState, onError })
    } else if (stage.ready) {
      stage.player.loadVideoById(videoId)
    }
  })
}

// The card after (1) or before (-1) the one playing, else from the selection: what the grid shows is the queue.
export function step(delta) {
  const videos = visibleVideos()
  const index = videos.indexOf(playingCard() || focusedVideo())
  const target = videos[index < 0 ? 0 : index + delta]
  if (target) {
    play(target.dataset.videoId)
  }
}

// The listen mode starts: the video playing goes on in the mini player, else the selected card, else the first one.
export function toListen() {
  const video = playingCard()
  if (!video) {
    step(0)
    return
  }
  $$(".yourss-playing-bar, .yourss-dock-placeholder").forEach((el) => el.remove())
  video.classList.remove("is-docked")
  expand(null)
  describe(video)
  placeStage()
}

// New content in listen mode: the player stays (its iframe keeps the right to play on iOS), the new cards are the
// queue and the first one starts once they arrive (listenRefresh).
export function leaveCard() {
  stage.observer?.disconnect()
  stage.videoId = null
  releaseCard()
}

// A card resized out of the screen must not pull the page: the first card on screen keeps its place, the
// browser's own scroll anchoring is held off so it does not compensate twice.
function keepScroll(change) {
  const anchor = visibleVideos().find((el) => el.getBoundingClientRect().bottom > 0)
  const top = anchor?.getBoundingClientRect().top
  const root = document.documentElement
  root.style.overflowAnchor = "none"
  change()
  if (anchor?.isConnected) {
    scrollBy({ top: anchor.getBoundingClientRect().top - top, behavior: "instant" })
  }
  requestAnimationFrame(() => root.style.removeProperty("overflow-anchor"))
}

export function closePlayer() {
  const shown = stageEl() !== null
  stage.observer?.disconnect()
  stage.resize?.disconnect()
  stage.player?.destroy()
  Object.assign(stage, { player: null, ready: false, videoId: null, observer: null, seen: false, resize: null })
  stopPlaybackTracking()
  keepScroll(() => {
    releaseCard()
    expand(null)
    stageEl()?.remove()
    document.body.style.removeProperty("--stage-h")
  })
  if (shown) {
    hooks.onClose?.()
  }
}

// The close command of the visitor: a card the stage covered stays at the top of the screen.
export function dismissPlayer() {
  const video = listening() ? null : $(".yourss-video.is-playing:not(.is-docked)")
  closePlayer()
  video?.scrollIntoView({ block: "start", behavior: "smooth" })
}

// Back to the card of the video: the stage covers it again (in listen mode, the card is only shown).
export function undock() {
  const video = playingCard()
  if (!video) {
    return
  }
  if (!listening()) {
    video.classList.remove("is-docked")
    expand(video)
    placeStage()
  }
  focusVideo(video, false)
  video.scrollIntoView({ block: listening() ? "center" : "start", behavior: "smooth" })
}

