/**
 * YouRSS front-end behaviours (see docs/specs/ui-redesign.md).
 *
 * DOM conventions used by the templates:
 *  - a video is `.yourss-video#yourss-video-<id>` with `data-video-id` and optional `data-channel-id`;
 *    its media box is `.yourss-media` (thumbnail `img.yourss-thumbnail`, `.yourss-player-container`)
 *  - every command is a `[data-action]` element handled by the `actions` table below
 *  - a channel avatar is `img.yourss-avatar` (retried when it fails to load)
 *  - `template#yourss-empty-template` holds the empty state shown when a tab request fails
 *  - dialogs: `#yourss-modal` (player, `#yourss-modal-player`, `#yourss-modal-video-title`,
 *    `#yourss-modal-link-{rss,youtube,tab}`), `#yourss-settings`, `#yourss-shortcuts`, `#yourss-add`
 *  - an editable page lists its channels in `<body data-page-names>`; channels are added with a
 *    `form.yourss-add-form` (docs/specs/custom-pages.md)
 *
 * State classes: `is-playing`, `is-docked`, `is-watched`, `is-focused`, `is-filtered`,
 * `is-portrait` on a video; `rail`, `menu-open`, `hide-watched`, `no-watched`, `watched-ready`,
 * `density-*` on body. Elements of the watched feature carry `data-watched-feature`.
 *
 * Everything is client side: theme, density, switches and watched videos live in localStorage
 * (`yourss-*` keys) and never reach the server.
 */
;(() => {
  "use strict"

  const $ = (selector, root = document) => root.querySelector(selector)
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)]
  const on = (name, handler) => document.addEventListener(name, handler)

  /* ---------- storage: plain strings under a `yourss-` prefix, never fatal ---------- */
  const store = {
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

  /* ---------- settings: theme, density and on/off flags ---------- */
  const THEMES = ["neon", "dark", "light"]
  const DENSITIES = ["compact", "normal", "large"]
  // On / off settings, all off until the user turns them on
  const flag = (name) => store.get(name) === "1"
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

  /* ---------- videos of the page ---------- */
  const videoOf = (el) => el.closest(".yourss-video")
  const videoById = (id) => $(`#yourss-video-${CSS.escape(id)}`)
  const visibleVideos = () => $$(".yourss-video").filter((el) => el.offsetParent !== null)

  /* ---------- watched videos: {video id: timestamp}, oldest entries dropped past a cap ---------- */
  const WATCHED_MAX = 3000

  function readWatched() {
    try {
      return JSON.parse(store.get("watched") || "{}")
    } catch {
      return {}
    }
  }

  function writeWatched(map) {
    const ids = Object.keys(map).sort((a, b) => map[a] - map[b])
    ids.slice(0, Math.max(0, ids.length - WATCHED_MAX)).forEach((id) => delete map[id])
    store.set("watched", JSON.stringify(map))
    applyWatched()
  }

  function setWatched(ids, watched = true) {
    // Nothing is recorded while "Show new videos" is off
    if (!flag("new-videos")) {
      return
    }
    const map = readWatched()
    const now = Date.now()
    for (const id of ids) {
      if (watched) {
        map[id] = now
      } else {
        delete map[id]
      }
    }
    writeWatched(map)
  }

  // Index of the feed (video id + channel), captured while its cards are on screen, so that the
  // counters stay correct after an in-page navigation to a channel homepage.
  let feedIndex = []

  function captureFeed() {
    const cards = $$(".yourss-video[data-video-id][data-channel-id]")
    if (cards.length > 0) {
      feedIndex = cards.map((el) => ({ id: el.dataset.videoId, channel: el.dataset.channelId }))
    }
  }

  function applyWatched() {
    const map = readWatched()
    $$(".yourss-video[data-video-id]").forEach((el) => el.classList.toggle("is-watched", el.dataset.videoId in map))
    document.body.classList.add("watched-ready")
    const counts = { "*": 0 }
    for (const item of feedIndex) {
      if (!(item.id in map)) {
        counts[item.channel] = (counts[item.channel] || 0) + 1
        counts["*"] += 1
      }
    }
    $$(".yourss-count[data-channel-id]").forEach((badge) => {
      const count = counts[badge.dataset.channelId] || 0
      badge.textContent = count
      badge.hidden = count === 0
    })
  }

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
    host.replaceChildren(mount)
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

  /* ---------- player embedded in a card (one at a time), closed or docked when the card leaves the screen ---------- */
  const embedded = { player: null, videoId: null, observer: null, seen: false }

  function closePlayer() {
    embedded.observer?.disconnect()
    embedded.player?.destroy()
    Object.assign(embedded, { player: null, videoId: null, observer: null, seen: false })
    stopPlaybackTracking()
    $$(".yourss-player-container").forEach((el) => {
      el.replaceChildren()
      el.classList.remove("is-active")
    })
    $$(".yourss-video.is-playing, .yourss-video.is-docked").forEach((el) => el.classList.remove("is-playing", "is-docked"))
  }

  // Playing card out of the screen: mini player when the "dock" setting is on, else the player is closed.
  function onPlayingCardVisibility(video, visible) {
    embedded.seen ||= visible
    // Nothing happens while the page is still scrolling to the card
    if (!embedded.seen) {
      return
    }
    if (flag("dock")) {
      video.classList.toggle("is-docked", !visible)
    } else if (!visible) {
      closePlayer()
    }
  }

  function play(videoId) {
    if (embedded.videoId === videoId) {
      return
    }
    closePlayer()
    const video = videoById(videoId)
    const container = video && $(".yourss-player-container", video)
    if (!container) {
      return
    }
    embedded.videoId = videoId
    video.classList.add("is-playing")
    container.classList.add("is-active")
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
  function playRelative(step) {
    const videos = visibleVideos()
    const index = videos.indexOf($(".yourss-video.is-playing") || focusedVideo())
    const target = videos[index < 0 ? 0 : index + step]
    if (target) {
      play(target.dataset.videoId)
    }
  }

  function playNext() {
    if (flag("autoplay")) {
      playRelative(1)
    }
  }

  function undock() {
    const video = $(".yourss-video.is-docked")
    if (video) {
      video.classList.remove("is-docked")
      video.scrollIntoView({ block: "start", behavior: "smooth" })
    }
  }

  /* ---------- player in the fullscreen dialog ---------- */
  const modal = { player: null }

  function destroyModalPlayer() {
    stopPlaybackTracking()
    modal.player?.destroy()
    modal.player = null
    $("#yourss-modal-player").replaceChildren()
  }

  function openModal(videoId) {
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

  /* ---------- keyboard focus on a card ---------- */
  const focusedVideo = () => $(".yourss-video.is-focused")

  function focusVideo(video, scroll = true) {
    $$(".yourss-video.is-focused").forEach((el) => el.classList.remove("is-focused"))
    video?.classList.add("is-focused")
    if (video && scroll) {
      video.scrollIntoView({ block: "nearest", behavior: "smooth" })
    }
  }

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
    $(".yourss-home-link")?.classList.toggle("active", wanted === null)
  }

  // Go to the entry after (step 1) or before (step -1) the active one: Home, then each channel and playlist.
  function moveChannel(step) {
    const entries = $$(".yourss-home-link, .yourss-channel .yourss-nav-item, .yourss-playlist .yourss-nav-item")
    const target = entries[entries.findIndex((el) => el.classList.contains("active")) + step]
    if (target) {
      target.click()
      target.scrollIntoView({ block: "nearest" })
    }
  }

  // Open what the URL names when the page shows something else (fresh load, pasted URL).
  function syncChannelFromUrl() {
    const wanted = selectionFromUrl()
    const shown = $("#yourss-content [data-channel-page]")?.dataset.channelPage
    const listed = wanted && $(`.yourss-${wanted.kind}[data-${wanted.kind}-id="${CSS.escape(wanted.id)}"]`)
    if (listed && wanted.id !== shown) {
      htmx.ajax("GET", `/htmx/${wanted.kind}/${encodeURIComponent(wanted.id)}`, { target: "#yourss-content" })
    }
    markActiveChannel()
  }

  /* ---------- editable page: its channels live in its address (docs/specs/custom-pages.md) ---------- */
  const editable = "pageNames" in document.body.dataset
  const pageNames = () => (document.body.dataset.pageNames || "").split(",").filter(Boolean)
  const EDITED_FLAG = "yourss-edited"
  const PAGE_PATH = /^\/(?:UC[\w-]{22}|PL[\w-]{32})(?:,(?:UC[\w-]{22}|PL[\w-]{32}))*$/

  // Navigate to the page made of `names`. The next page asks for a new bookmark, or, when it is the
  // first one built from the home page, shows how to add more subscriptions.
  function goToPage(names) {
    try {
      sessionStorage.setItem(EDITED_FLAG, pageNames().length === 0 ? "first" : "1")
    } catch {
      /* private mode */
    }
    location.assign(names.length > 0 ? `/${names.join(",")}` : "/")
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
      resume.href = page
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
    modal: (el) => openModal(videoOf(el).dataset.videoId),
    "close-player": closePlayer,
    undock,
    "toggle-watched": (el) => {
      const video = videoOf(el)
      setWatched([video.dataset.videoId], !video.classList.contains("is-watched"))
    },
    "mark-feed-watched": () => setWatched(feedIndex.map((item) => item.id)),
    // The videos listed on the channel page, plus the ones the feed knows for this channel.
    "mark-channel-watched": (el) => {
      const onPage = $$("#tab-content .yourss-video[data-video-id]").map((video) => video.dataset.videoId)
      const inFeed = feedIndex.filter((item) => item.channel === el.dataset.channelId).map((item) => item.id)
      setWatched([...onPage, ...inFeed])
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
      if (typing) {
        event.target.value = ""
        event.target.blur()
        applySearch()
      } else if (!$("dialog[open]")) {
        closePlayer()
      }
      return
    }
    if (typing || event.ctrlKey || event.metaKey || event.altKey) {
      return
    }
    // x closes the player wherever it is: fullscreen dialog, card or mini player
    if (event.key === "x" && $("#yourss-modal").open) {
      $("#yourss-modal").close()
      return
    }
    // No other page shortcut while a dialog is open.
    if ($("dialog[open]")) {
      return
    }
    const video = focusedVideo()
    const shortcuts = {
      "/": () => $("#yourss-search")?.focus(),
      "?": () => $("#yourss-shortcuts").showModal(),
      ArrowRight: () => moveFocus("right"),
      ArrowLeft: () => moveFocus("left"),
      // With Shift, up / down walk the sidebar (Home, then each channel) instead of the grid
      ArrowDown: () => (event.shiftKey ? moveChannel(1) : moveFocus("down")),
      ArrowUp: () => (event.shiftKey ? moveChannel(-1) : moveFocus("up")),
      n: () => playRelative(1),
      p: () => playRelative(-1),
      // Without a selection, Space keeps its usual role: scrolling the page
      " ": () => (video ? play(video.dataset.videoId) : false),
      o: () => video && openModal(video.dataset.videoId),
      w: () => video && setWatched([video.dataset.videoId], !video.classList.contains("is-watched")),
      h: () => flag("new-videos") && setSetting("hide-watched", flag("hide-watched") ? "0" : "1"),
      a: openAddDialog,
      x: closePlayer,
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
  }

  on("htmx:afterSettle", refresh)
  on("htmx:pushedIntoHistory", markActiveChannel)
  on("htmx:historyRestore", () => {
    closePlayer()
    captureFeed()
    syncChannelFromUrl()
    refresh()
  })

  // Replacing content kills the player inside it; appending (infinite scroll) must not.
  on("htmx:beforeSwap", (event) => {
    const swap = event.detail.elt.getAttribute("hx-swap") || "innerHTML"
    if (!swap.startsWith("afterend") && !swap.startsWith("beforeend")) {
      closePlayer()
    }
  })

  // A failed tab request must not leave the previous tab on screen: show the empty state.
  function showTabFailure(event) {
    if (event.detail.target?.id === "tab-content") {
      closePlayer()
      event.detail.target.replaceChildren($("#yourss-empty-template").content.cloneNode(true))
    }
  }
  on("htmx:responseError", showTabFailure)
  on("htmx:sendError", showTabFailure)

  /* ---------- boot: this script is the last element of <body>, the DOM is ready ---------- */
  document.addEventListener("error", retryAvatar, true)
  window.addEventListener("scroll", () => $("#scroll-to-top").classList.toggle("visible", window.scrollY > 300), {
    passive: true,
  })
  $("#yourss-modal").addEventListener("close", destroyModalPlayer)
  applySettings()
  initEditablePage()
  captureFeed()
  syncChannelFromUrl()
  refresh()

  // Handy from the browser console and from tests.
  window.yourss = { play, openModal, closePlayer, setSetting, setWatched, store }
})()
