/**
 * Shared helpers: DOM queries, the localStorage wrapper, the videos of the page.
 */
export const $ = (selector, root = document) => root.querySelector(selector)
export const $$ = (selector, root = document) => [...root.querySelectorAll(selector)]
export const on = (name, handler, options) => document.addEventListener(name, handler, options)

/* ---------- storage: plain strings under a `yourss-` prefix, never fatal ---------- */
export const store = {
  get(key) {
    try {
      return localStorage.getItem(`yourss-${key}`)
    } catch {
      return null
    }
  },
  set(key, value) {
    try {
      localStorage.setItem(`yourss-${key}`, value)
    } catch {
      /* private mode */
    }
  },
  clear() {
    try {
      Object.keys(localStorage)
        .filter((key) => key.startsWith("yourss-"))
        .forEach((key) => localStorage.removeItem(key))
    } catch {
      /* private mode */
    }
  },
}

// On / off settings, all off until the user turns them on
export const flag = (name) => store.get(name) === "1"

// The listen mode (yourss-listen.js) is on: the player stays in its mini player, the cards are a queue
export const listening = () => document.body.classList.contains("listening")

/* ---------- videos of the page ---------- */
export const videoOf = (el) => el.closest(".yourss-video")
export const videoById = (id) => $(`#yourss-video-${CSS.escape(id)}`)
export const visibleVideos = () => $$(".yourss-video").filter((el) => el.offsetParent !== null)

/* ---------- keyboard focus on a card ---------- */
export const focusedVideo = () => $(".yourss-video.is-focused")

export function focusVideo(video, scroll = true) {
  $$(".yourss-video.is-focused").forEach((el) => el.classList.remove("is-focused"))
  video?.classList.add("is-focused")
  if (video && scroll) {
    video.scrollIntoView({ block: "nearest", behavior: "smooth" })
  }
}
