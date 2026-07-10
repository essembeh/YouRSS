/**
 * YouTube IFrame API loading (lazy: only on first video open)
 */
let ytApiPromise = null

function loadYouTubeApi() {
  if (ytApiPromise === null) {
    ytApiPromise = new Promise((resolve) => {
      // The API calls this global once iframe_api.js is ready
      window.onYouTubeIframeAPIReady = () => resolve(window.YT)
      const script = document.createElement("script")
      script.src = "https://www.youtube.com/iframe_api"
      document.head.appendChild(script)
    })
  }
  return ytApiPromise
}

/**
 * Player state: at most one embedded player and one modal player at a time.
 */
let embeddedPlayer = null
let embeddedContainerId = null
let modalPlayer = null
let playerObserver = null

function playerVars() {
  return { autoplay: 1 }
}

function playerHost() {
  // Keep the no-cookie domain when configured (see body[data-player-host]).
  return document.body.dataset.playerHost || undefined
}

/**
 * Close/destroy the embedded player and restore its thumbnail.
 */
function closeAllPlayers() {
  if (playerObserver !== null) {
    playerObserver.disconnect()
    playerObserver = null
  }
  if (embeddedPlayer !== null) {
    embeddedPlayer.destroy()
    embeddedPlayer = null
  }
  document.querySelectorAll(".yourss-player-container").forEach((el) => {
    el.replaceChildren()
    el.style.display = "none"
  })
  document.querySelectorAll(".yourss-thumbnail").forEach((el) => {
    el.style.display = "block"
  })
  embeddedContainerId = null
}

function openEmbedded(videoId) {
  closeAllPlayers()

  const thumbnail = document.querySelector(`#yourss-thumbnail-${videoId}`)
  const container = document.querySelector(`#yourss-player-${videoId}`)
  if (thumbnail === null || container === null) {
    return
  }

  const height = thumbnail.offsetHeight
  thumbnail.style.display = "none"
  container.style.display = "block"
  embeddedContainerId = container.id

  // YT.Player replaces its target element with an <iframe>, so give it a fresh
  // child (not the container itself, which we keep to observe/restore).
  const mount = document.createElement("div")
  container.replaceChildren(mount)

  loadYouTubeApi().then((YT) => {
    // The user may have closed/changed player while the API was loading.
    if (embeddedContainerId !== container.id) {
      return
    }
    embeddedPlayer = new YT.Player(mount, {
      videoId,
      host: playerHost(),
      width: "100%",
      height,
      playerVars: playerVars(),
    })

    // Auto-close when the player scrolls fully out of view.
    playerObserver = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.intersectionRatio === 0) {
            closeAllPlayers()
          }
        }
      },
      { threshold: 0 }
    )
    playerObserver.observe(container)
  })
}

function openTab(videoId) {
  closeAllPlayers()
  window.open(`https://www.youtube-nocookie.com/embed/${videoId}?autoplay=1`, "_blank")
}

function openModal(videoId) {
  closeAllPlayers()

  const videoDiv = document.querySelector(`#yourss-video-${videoId}`)
  const channelId = videoDiv ? videoDiv.dataset.channelId : null

  const titleEl = videoDiv
    ? videoDiv.querySelector(".yourss-video-title")
    : null
  document.querySelector("#yourss-modal-video-title").innerHTML = titleEl
    ? titleEl.innerHTML
    : ""

  document.querySelector("#yourss-modal-link-youtube").href = `https://www.youtube.com/watch?v=${videoId}`
  document.querySelector("#yourss-modal-link-tab").href = `https://www.youtube-nocookie.com/embed/${videoId}?autoplay=1`
  document.querySelector("#yourss-modal-link-piped").href = `https://piped.kavin.rocks/watch?v=${videoId}`

  const rssLink = document.querySelector("#yourss-modal-link-rss")
  if (channelId) {
    rssLink.href = `/proxy/rss/${channelId}`
    rssLink.style.display = "block"
  } else {
    rssLink.style.display = "none"
  }

  const modalEl = document.querySelector("#yourss-modal")
  const modalHost = document.querySelector("#yourss-modal-player")
  loadYouTubeApi().then((YT) => {
    if (modalPlayer !== null) {
      modalPlayer.destroy()
      modalPlayer = null
    }
    // YT.Player replaces its target; give it a fresh child each time.
    const mount = document.createElement("div")
    modalHost.replaceChildren(mount)
    modalPlayer = new YT.Player(mount, {
      videoId,
      host: playerHost(),
      width: "100%",
      height: "100%",
      playerVars: playerVars(),
    })
  })
  bootstrap.Modal.getOrCreateInstance(modalEl).show()
}

/**
 * Density setting (compact/normal/large), persisted in localStorage.
 */
const DENSITIES = ["compact", "normal", "large"]

function applyDensity(density) {
  if (!DENSITIES.includes(density)) {
    density = "normal"
  }
  DENSITIES.forEach((d) => {
    document.body.classList.toggle(`density-${d}`, d === density)
  })
  try {
    localStorage.setItem("yourss-density", density)
  } catch (e) {
    /* localStorage may be unavailable (private mode) */
  }
}

function currentDensity() {
  try {
    return localStorage.getItem("yourss-density") || "normal"
  } catch (e) {
    return "normal"
  }
}

// Apply as early as possible to avoid a layout flash.
applyDensity(currentDensity())

/**
 * Scroll-to-top button + page-level listeners.
 */
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".yourss-density-option").forEach((el) => {
    el.classList.toggle("active", el.dataset.density === currentDensity())
    el.addEventListener("click", (event) => {
      event.preventDefault()
      applyDensity(el.dataset.density)
      document.querySelectorAll(".yourss-density-option").forEach((o) => {
        o.classList.toggle("active", o.dataset.density === el.dataset.density)
      })
    })
  })

  const scrollTop = document.querySelector("#scroll-to-top")

  window.addEventListener("scroll", () => {
    if (scrollTop !== null) {
      scrollTop.classList.toggle("visible", window.scrollY > 100)
    }
  })

  if (scrollTop !== null) {
    scrollTop.addEventListener("click", (event) => {
      event.preventDefault()
      window.scrollTo({ top: 0, behavior: "smooth" })
    })
  }

  const modalEl = document.querySelector("#yourss-modal")
  if (modalEl !== null) {
    modalEl.addEventListener("hidden.bs.modal", () => {
      if (modalPlayer !== null) {
        modalPlayer.destroy()
        modalPlayer = null
      }
      const modalHost = document.querySelector("#yourss-modal-player")
      if (modalHost !== null) {
        modalHost.replaceChildren()
      }
    })

    // External links open a new tab; close the modal without cancelling the
    // navigation (data-bs-dismiss would prevent the target=_blank open).
    document.querySelectorAll(".yourss-modal-external").forEach((link) => {
      link.addEventListener("click", () => {
        bootstrap.Modal.getOrCreateInstance(modalEl).hide()
      })
    })
  }
})
