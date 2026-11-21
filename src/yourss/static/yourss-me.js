/**
 * The /me page: folders kept in localStorage (`yourss-me`), copied to other devices by URL, QR code or JSON file.
 * The server only ever sees the channels of the folder being opened (docs/specs/me-page.md).
 */
import { $, $$, on, store } from "yourss/core"

export const isMePage = "me" in document.body.dataset

const VERSION = 1
const NAME = /^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$/
const SUBSCRIPTION = /^(?:UC[\w-]{22}|PL[\w-]{32})$/
const IMPORT_PREFIX = "#import="
const EMPTY = () => ({ version: VERSION, folders: [] })

const maxFolders = () => Number(document.body.dataset.meMaxFolders)
const maxChannels = () => Number(document.body.dataset.pageMax)

/* ---------- model ---------- */
// A clean copy of an untrusted config, or an error naming what is wrong
function parsed(raw) {
  if (raw?.version !== VERSION || !Array.isArray(raw.folders)) {
    throw new Error("this is not a YouRSS configuration")
  }
  const folders = raw.folders.map((folder) => {
    if (typeof folder?.name !== "string" || !NAME.test(folder.name)) {
      throw new Error("a folder has an invalid name")
    }
    if (!Array.isArray(folder.channels) || !folder.channels.every((id) => typeof id === "string" && SUBSCRIPTION.test(id))) {
      throw new Error(`${folder.name} holds an invalid channel`)
    }
    if (new Set(folder.channels).size !== folder.channels.length) {
      throw new Error(`${folder.name} holds the same channel twice`)
    }
    return { name: folder.name, channels: [...folder.channels] }
  })
  if (new Set(folders.map((folder) => folder.name)).size !== folders.length) {
    throw new Error("two folders have the same name")
  }
  return { version: VERSION, folders }
}

// Only what comes from elsewhere is held to the limits: lowering them must not lose the folders already here
function withinLimits(config) {
  if (config.folders.length > maxFolders()) {
    throw new Error(`this instance allows at most ${maxFolders()} folders`)
  }
  const crowded = config.folders.find((folder) => folder.channels.length > maxChannels())
  if (crowded) {
    throw new Error(`${crowded.name} holds more than the ${maxChannels()} channels this instance allows`)
  }
  return config
}

function read() {
  try {
    return parsed(JSON.parse(store.get("me")))
  } catch {
    return EMPTY()
  }
}

function save(config, { exported = false } = {}) {
  const text = JSON.stringify(config)
  store.set("me", text)
  store.set("me-dirty", exported ? "0" : "1")
  if (store.get("me") !== text) {
    alert("This browser refuses to store your folders (private mode or full storage)")
    return false
  }
  return true
}

/* ---------- shared formats ---------- */
// `1;music:UC…,PL…;tech:UC…`: names and ids never hold a separator, the text needs no encoding
const encoded = (config) =>
  [config.version, ...config.folders.map((folder) => `${folder.name}:${folder.channels.join(",")}`)].join(";")

function decoded(text) {
  const [version, ...parts] = text.split(";")
  const folders = parts.map((part) => {
    const [name, channels = ""] = part.split(":")
    return { name, channels: channels.split(",").filter(Boolean) }
  })
  return { version: Number(version), folders }
}

const shareUrl = () => `${location.origin}/me${IMPORT_PREFIX}${encoded(read())}`

// An import replaces the folders of this device, never its settings or its watched videos
function replaceWith(raw) {
  let config
  try {
    config = withinLimits(parsed(raw))
  } catch (error) {
    alert(`Import refused: ${error.message}`)
    return false
  }
  const current = read()
  if (JSON.stringify(current) === JSON.stringify(config)) {
    return false
  }
  const channels = config.folders.reduce((total, folder) => total + folder.channels.length, 0)
  const summary = `${config.folders.length} folder(s) and ${channels} channel(s)`
  if (current.folders.length > 0 && !confirm(`Replace the folders of this device with ${summary}?`)) {
    return false
  }
  return save(config, { exported: true })
}

function importFromUrl() {
  if (!location.hash.startsWith(IMPORT_PREFIX)) {
    return
  }
  const text = location.hash.slice(IMPORT_PREFIX.length)
  // Gone before anything else: a reload must not import it again
  history.replaceState(history.state, "", location.pathname + location.search)
  try {
    replaceWith(decoded(decodeURIComponent(text)))
  } catch {
    alert("Import refused: this address is damaged")
  }
}

/* ---------- sidebar ---------- */
function folderRow({ name, channels }) {
  const row = $("#yourss-me-folder-template").content.firstElementChild.cloneNode(true)
  const summary = $("summary", row)
  const list = $("ul", row)
  row.dataset.folder = name
  summary.title = `The latest videos of ${name}`
  summary.setAttribute("hx-get", `/htmx/me/${name}?ids=${channels.join(",")}`)
  summary.setAttribute("hx-push-url", `/me/${name}`)
  $(".yourss-label", summary).textContent = name
  $("[data-folder-count]", row).dataset.folderCount = name
  list.id = `yourss-folder-list-${name}`
  list.dataset.folderList = name
  return row
}

const markDirty = () => $('[data-action="me-share"]')?.classList.toggle("is-dirty", store.get("me-dirty") === "1")

// Runs before the folder of the URL is opened: the rows it looks for must exist
export function initMe() {
  if (!isMePage) {
    return
  }
  importFromUrl()
  // A link opened in a tab already on this address only changes its fragment: the page does not load again
  window.addEventListener("hashchange", () => {
    if (location.hash.startsWith(IMPORT_PREFIX)) {
      importFromUrl()
      location.reload()
    }
  })
  const { folders } = read()
  const holder = $("#yourss-me-folders")
  holder.replaceChildren(...folders.map(folderRow))
  htmx.process(holder)
  $("#yourss-me-empty")?.toggleAttribute("hidden", folders.length > 0)
  $("#yourss-me-start")?.toggleAttribute("hidden", folders.length > 0)
  $("#yourss-me-choose")?.toggleAttribute("hidden", folders.length === 0)
  markDirty()
  navigator.storage?.persist?.().catch(() => {})
}

/* ---------- editing: every change reloads the page, like an edit of a custom page ---------- */
const go = (name) => location.assign(name ? `/me/${name}` : "/me")

function newFolder() {
  const name = prompt("Name of the new folder (letters, digits, - and _)")?.trim()
  if (!name) {
    return
  }
  const config = read()
  if (!NAME.test(name)) {
    alert("A folder name holds letters, digits, - and _, at most 32 characters")
  } else if (config.folders.some((folder) => folder.name === name)) {
    alert(`The folder ${name} already exists`)
  } else if (config.folders.length >= maxFolders()) {
    alert(`This instance allows at most ${maxFolders()} folders`)
  } else {
    config.folders.push({ name, channels: [] })
    if (save(config)) {
      go(name)
    }
  }
}

function removeFolder(el) {
  const name = el.closest("[data-folder]").dataset.folder
  if (confirm(`Remove the folder ${name} and its channels?`)) {
    const config = read()
    config.folders = config.folders.filter((folder) => folder.name !== name)
    if (save(config)) {
      go(null)
    }
  }
}

function setChannels(name, channels) {
  const config = read()
  const folder = config.folders.find((item) => item.name === name)
  if (folder) {
    folder.channels = channels
    if (save(config)) {
      go(name)
    }
  }
}

// The add dialog names its folder: the row of the button, else the open one
export function meOpenAdd(el) {
  const row = el?.closest?.("[data-folder]") || $("details.yourss-folder[open]")
  if (row) {
    $("#yourss-add").dataset.folder = row.dataset.folder
  }
  return Boolean(row)
}

const addFolder = () => $("#yourss-add").dataset.folder
export const meChannels = () => read().folders.find((folder) => folder.name === addFolder())?.channels ?? []
export const meSetChannels = (channels) => setChannels(addFolder(), channels)

export function meRemoveChannel(el) {
  const name = el.closest("[data-folder]").dataset.folder
  if (confirm(`Remove ${el.dataset.name} from ${name}?`)) {
    const channels = read().folders.find((folder) => folder.name === name)?.channels ?? []
    setChannels(name, channels.filter((id) => id !== el.dataset.id))
  }
}

/* ---------- share dialog ---------- */
function markExported() {
  store.set("me-dirty", "0")
  markDirty()
}

function openShare() {
  document.body.classList.remove("menu-open")
  const dialog = $("#yourss-me-share")
  $("#yourss-me-url").value = shareUrl()
  $("#yourss-me-qr").hidden = true
  $("#yourss-me-qr-error").hidden = true
  dialog.showModal()
}

async function copyUrl(el) {
  const input = $("#yourss-me-url")
  try {
    await navigator.clipboard.writeText(input.value)
    el.textContent = "Address copied"
  } catch {
    // No clipboard access (plain http): the address is selected for a manual copy
    input.focus()
    input.select()
  }
  markExported()
}

function downloadJson() {
  const url = URL.createObjectURL(new Blob([JSON.stringify(read(), null, 2)], { type: "application/json" }))
  const link = document.createElement("a")
  link.href = url
  link.download = "yourss-me.json"
  link.click()
  URL.revokeObjectURL(url)
  markExported()
}

function loadQrLibrary() {
  if (window.qrcode) {
    return Promise.resolve()
  }
  return new Promise((resolve, reject) => {
    const script = document.createElement("script")
    script.src = $("#yourss-me-share").dataset.qrSrc
    script.onload = resolve
    script.onerror = reject
    document.head.append(script)
  })
}

function drawQr(canvas, text) {
  const QUIET_ZONE = 4
  const qr = window.qrcode(0, "L")
  qr.addData(text, "Byte")
  qr.make()
  const modules = qr.getModuleCount()
  const scale = Math.max(3, Math.floor(720 / (modules + 2 * QUIET_ZONE)))
  canvas.width = canvas.height = (modules + 2 * QUIET_ZONE) * scale
  const context = canvas.getContext("2d")
  context.fillStyle = "#fff"
  context.fillRect(0, 0, canvas.width, canvas.height)
  context.fillStyle = "#000"
  for (let row = 0; row < modules; row++) {
    for (let col = 0; col < modules; col++) {
      if (qr.isDark(row, col)) {
        context.fillRect((col + QUIET_ZONE) * scale, (row + QUIET_ZONE) * scale, scale, scale)
      }
    }
  }
}

async function showQr() {
  const canvas = $("#yourss-me-qr")
  const error = $("#yourss-me-qr-error")
  try {
    await loadQrLibrary()
    drawQr(canvas, $("#yourss-me-url").value)
    canvas.hidden = false
    error.hidden = true
    markExported()
  } catch {
    canvas.hidden = true
    error.hidden = false
  }
}

async function importFile(file) {
  try {
    if (replaceWith(JSON.parse(await file.text()))) {
      go(null)
    }
  } catch {
    alert("Import refused: this file is not valid JSON")
  }
}

on("change", (event) => {
  if (event.target.id === "yourss-me-file" && event.target.files[0]) {
    importFile(event.target.files[0])
    event.target.value = ""
  }
})

// The commands of the page, merged in the `actions` table of yourss.js
export const meActions = {
  "me-new-folder": newFolder,
  "me-remove-folder": removeFolder,
  "me-share": openShare,
  "me-copy-url": copyUrl,
  "me-download": downloadJson,
  "me-show-qr": showQr,
  "me-import": () => $("#yourss-me-file").click(),
}

// The keys of this page survive the reset of the settings
export const ME_KEYS = ["me", "me-dirty"]
