/**
 * The YouTube player: inside a card (docked when the card leaves the screen) or in the fullscreen dialog.
 */
import { $, $$, flag, focusVideo, focusedVideo, videoById, visibleVideos } from "yourss/core"
import { setWatched } from "yourss/watched"

/* ---------- YouTube IFrame API, loaded on the first play ---------- */
let ytApi = null

function loadYouTubeApi() {
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
function createPlayer(YT, host, videoId, onEnded) {
  const mount = document.createElement("div")
  // The shield keeps the mouse off the video: YouTube no longer dims it on hover
  const shield = document.createElement("div")
  shield.className = "yourss-player-shield"
  shield.dataset.action = "toggle-pause"
  host.replaceChildren(mount, shield)
  return new YT.Player(mount, {
    videoId,
    host: PLAYER_HOST,
    width: "100%",
    height: "100%",
    playerVars: { autoplay: 1 },
    events: {
      onStateChange: (event) => {
        trackPlayback(event.data === YT.PlayerState.PLAYING, videoId)
        if (event.data === YT.PlayerState.ENDED) {
          onEnded?.()
        }
      },
    },
  })
}

// While YouTube has the focus (a click on one of its controls), the shield steps aside: its menus and keys work.
// A click elsewhere in the page takes the focus back, and the shield with it.
function syncShields() {
  for (const shield of $$(".yourss-player-shield")) {
    shield.classList.toggle("is-off", $(":scope > iframe", shield.parentElement) === document.activeElement)
  }
}
// Chromium sends a blur to the window, Firefox sends nothing: the focus is also checked a few times a second
window.addEventListener("blur", syncShields)
document.addEventListener("focusin", syncShields)
setInterval(() => document.body.classList.contains("improved-player") && syncShields(), 250)

// Pause or resume a player: false when there is none (or not ready yet).
function toggle(player) {
  const state = player?.getPlayerState?.()
  if (state === undefined) {
    return false
  }
  const playing = state === window.YT.PlayerState.PLAYING || state === window.YT.PlayerState.BUFFERING
  if (playing) {
    player.pauseVideo()
  } else {
    player.playVideo()
  }
  return true
}

// The player in use: the fullscreen dialog when open, else the one of a card.
const activePlayer = () => ($("#yourss-modal").open ? modal.player : embedded.player)

// Click on the shield: pause or resume the player under it; double click: fullscreen.
export function togglePause(shield) {
  toggle(shield.closest("#yourss-modal-player") ? modal.player : embedded.player)
}

export const togglePlayback = () => toggle(activePlayer())

// Jump in the player in use: false without one, the keys keep their role.
export function seekBy(seconds) {
  const player = activePlayer()
  if (!player?.getCurrentTime) {
    return false
  }
  player.seekTo(Math.max(0, player.getCurrentTime() + seconds), true)
  return true
}

// The host goes fullscreen, not the iframe: the shield stays on top and a double click comes back.
const activeHost = () => ($("#yourss-modal").open ? $("#yourss-modal-player") : $(".yourss-player-container"))

export function toggleFullscreen(host = activeHost()) {
  if (document.fullscreenElement) {
    document.exitFullscreen()
  } else if (host?.requestFullscreen) {
    host.requestFullscreen()
  } else {
    return false
  }
  return true
}

export function toggleMute() {
  const player = activePlayer()
  if (!player?.isMuted) {
    return false
  }
  if (player.isMuted()) {
    player.unMute()
  } else {
    player.mute()
  }
  return true
}

// Captions go through an undocumented module of the player: should YouTube drop it, the key does nothing.
export function toggleCaptions() {
  const player = activePlayer()
  try {
    const track = player.getOption("captions", "track")
    if (track && Object.keys(track).length > 0) {
      player.unloadModule("captions")
    } else {
      player.loadModule("captions")
    }
    return true
  } catch {
    return false
  }
}

/* ---------- player embedded in a card (one at a time), closed or docked when the card leaves the screen ---------- */
const embedded = { player: null, videoId: null, observer: null, seen: false }
const CHROME = ".yourss-playing-bar, .yourss-player-container, .yourss-dock-bar, .yourss-dock-placeholder"

// The chrome of the player lives in one <template>: a card only carries it while it plays, which keeps the cards light.
function mountChrome(video) {
  const chrome = $("#yourss-player-template").content.cloneNode(true)
  const title = $(".yourss-video-title", video).textContent.trim()
  $$("[data-player-title]", chrome).forEach((el) => (el.textContent = title))
  const media = $(".yourss-media", video)
  video.prepend($(".yourss-playing-bar", chrome))
  media.append($(".yourss-player-container", chrome), $(".yourss-dock-bar", chrome))
  media.after($(".yourss-dock-placeholder", chrome))
  return $(".yourss-player-container", video)
}

export function closePlayer() {
  embedded.observer?.disconnect()
  embedded.player?.destroy()
  Object.assign(embedded, { player: null, videoId: null, observer: null, seen: false })
  stopPlaybackTracking()
  $$(CHROME).forEach((el) => el.remove())
  $$(".yourss-video.is-playing, .yourss-video.is-docked").forEach((el) => {
    el.classList.remove("is-playing", "is-docked")
    el.style.minHeight = ""
  })
}

// The close command of the visitor: the card, back to its place in the grid, stays at the top of the screen.
export function dismissPlayer() {
  const video = $(".yourss-video.is-playing:not(.is-docked)")
  closePlayer()
  video?.scrollIntoView({ block: "start", behavior: "smooth" })
}

// Playing card out of the screen: mini player when the "dock" setting is on, else the player is closed.
function onPlayingCardVisibility(video, visible) {
  embedded.seen ||= visible
  // Nothing happens while the page is still scrolling to the card
  if (!embedded.seen) {
    return
  }
  if (flag("dock")) {
    // The card keeps its height while its player floats: the page does not shift under the reader
    video.style.minHeight = visible ? "" : `${video.offsetHeight}px`
    video.classList.toggle("is-docked", !visible)
  } else if (!visible) {
    closePlayer()
  }
}

export function play(videoId) {
  if (embedded.videoId === videoId) {
    return
  }
  closePlayer()
  const video = videoById(videoId)
  if (!video) {
    return
  }
  embedded.videoId = videoId
  video.classList.add("is-playing")
  const container = mountChrome(video)
  focusVideo(video, false)
  // The expanded card goes to the top of the viewport (CSS scroll-margin-top clears the sticky top bar of phones).
  video.scrollIntoView({ block: "start", behavior: "smooth" })

  loadYouTubeApi().then((YT) => {
    if (embedded.videoId !== videoId) {
      return
    }
    embedded.player = createPlayer(YT, container, videoId, playNext)
    embedded.observer = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        onPlayingCardVisibility(video, entry.intersectionRatio > 0)
      }
    })
    embedded.observer.observe(video)
  })
}

// Play the video after (step 1) or before (step -1) the one playing, else the focused one.
export function playRelative(step) {
  const videos = visibleVideos()
  const index = videos.indexOf($(".yourss-video.is-playing") || focusedVideo())
  const target = videos[index < 0 ? 0 : index + step]
  if (target) {
    play(target.dataset.videoId)
  }
}

// End of a video: next one with autoplay, else a mini player is closed.
function playNext() {
  if (flag("autoplay")) {
    playRelative(1)
  } else if ($(".yourss-video.is-docked")) {
    closePlayer()
  }
}

export function undock() {
  const video = $(".yourss-video.is-docked")
  if (video) {
    video.classList.remove("is-docked")
    video.style.minHeight = ""
    video.scrollIntoView({ block: "start", behavior: "smooth" })
  }
}

/* ---------- player in the fullscreen dialog ---------- */
const modal = { player: null }

export function destroyModalPlayer() {
  stopPlaybackTracking()
  modal.player?.destroy()
  modal.player = null
  $("#yourss-modal-player").replaceChildren()
}

export function openModal(videoId) {
  closePlayer()
  const video = videoById(videoId)
  const channelId = video?.dataset.channelId
  $("#yourss-modal-video-title").textContent = video ? $(".yourss-video-title", video).textContent.trim() : ""
  $("#yourss-modal-link-youtube").href = `https://www.youtube.com/watch?v=${videoId}`
  $("#yourss-modal-link-tab").href = `${PLAYER_HOST}/embed/${videoId}?autoplay=1`
  const rssLink = $("#yourss-modal-link-rss")
  rssLink.href = channelId ? `https://www.youtube.com/feeds/videos.xml?channel_id=${encodeURIComponent(channelId)}` : "#"
  rssLink.hidden = !channelId
  if (!$("#yourss-modal").open) {
    $("#yourss-modal").showModal()
  }
  loadYouTubeApi().then((YT) => {
    destroyModalPlayer()
    modal.player = createPlayer(YT, $("#yourss-modal-player"), videoId)
  })
}
