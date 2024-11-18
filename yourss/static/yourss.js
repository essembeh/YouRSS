/**
 * Scroll to top
 */
$(window).scroll(function () {
  let height = $(window).scrollTop()
  if (height > 100) {
    $("#scroll-to-top").fadeIn()
  } else {
    $("#scroll-to-top").fadeOut()
  }
})
$(document).ready(function () {
  $("#scroll-to-top").click(function (event) {
    event.preventDefault()
    $("html, body").animate({ scrollTop: 0 }, "slow")
    return false
  })
})

/**
 * Sort videos by updated date
 */
var SORT_ORDERS = [
  // sort by date
  "bi bi-sort-down",
  // sort by date, reverse
  "bi bi-sort-up",
  // sort by channel, then date
  //"bi bi-sort-alpha-down",
  // sort by channel, then date, reverse
  //"bi bi-sort-alpha-up",
]
function toggle_sort(button) {
  closeAllPlayers()
  let oldOrder = $(button).find("i").attr("class")
  let newOrder = SORT_ORDERS[(SORT_ORDERS.indexOf(oldOrder) + 1) % SORT_ORDERS.length]
  $(button).find("i").attr("class", newOrder)
  sort_videos(newOrder)
}
function sort_videos(order) {
  $("#video-container").html(
    $("#video-container")
      .children()
      .sort(function (left, right) {
        let leftChannel = $(left).data("channel-name")
        let rightChannel = $(right).data("channel-name")
        let leftDate = new Date($(left).data("published"))
        let rightDate = new Date($(right).data("published"))
        if (order === "bi bi-sort-down") {
          if (leftDate < rightDate) return 1
          if (leftDate > rightDate) return -1
        } else if (order === "bi bi-sort-up") {
          if (leftDate < rightDate) return -1
          if (leftDate > rightDate) return 1
        } else if (order === "bi bi-sort-alpha-down") {
          if (leftChannel < rightChannel) return -1
          if (leftChannel > rightChannel) return 1
          if (leftDate < rightDate) return 1
          if (leftDate > rightDate) return -1
        } else if (order === "bi bi-sort-alpha-up") {
          if (leftChannel < rightChannel) return -1
          if (leftChannel > rightChannel) return 1
          if (leftDate < rightDate) return -1
          if (leftDate > rightDate) return 1
        }
        return 0
      })
  )
}
$(document).ready(function () {
  sort_videos(SORT_ORDERS[0])
})

/**
 * Handle filter toggle
 */
function toggle_filter(button) {
  closeAllPlayers()
  let selectedChannelId = $(button).hasClass("btn-secondary") ? $(button).data("feed-uid") : null
  $(".yourss-filter").each(function () {
    if ($(this).data("feed-uid") === selectedChannelId) {
      $(this).addClass("btn-primary")
      $(this).removeClass("btn-secondary")
    } else {
      $(this).addClass("btn-secondary")
      $(this).removeClass("btn-primary")
    }
  })
  $(".yourss-filterable").each(function () {
    if (selectedChannelId === null) {
      $(this).css("display", "block")
    } else if ($(this).data("feed-uid") === selectedChannelId) {
      $(this).css("display", "block")
    } else {
      $(this).css("display", "none")
    }
  })
}

/**
 * Handle modal player
 */
function closeAllPlayers() {
  $(".yourss-player-container").each(function () {
    $(this).children().remove()
    $(this).css("display", "none")
  })
  $(".yourss-thumbnail").each(function () {
    $(this).css("display", "block")
  })
}

function getVideoPlayerUrl(videoId) {
  return `https://www.youtube-nocookie.com/embed/${videoId}?autoplay=1&control=2&rel=0`
}

function openEmbedded(videoId) {
  closeAllPlayers()

  let height = $(`#yourss-thumbnail-${videoId}`).height()
  let videoUrl = getVideoPlayerUrl(videoId)

  $(`#yourss-thumbnail-${videoId}`).css("display", "none")
  $(`#yourss-player-${videoId}`).css("display", "block")
  $(`#yourss-player-${videoId}`).append(`
    <iframe src="${videoUrl}"
            width="100%" height="${height}"
            allow="autoplay; encrypted-media; picture-in-picture" 
            allowfullscreen=""frameborder="0"></iframe>`)
}

function openTab(videoId) {
  closeAllPlayers()
  let videoUrl = getVideoPlayerUrl(videoId)
  window.open(videoUrl, "_blank")
}

function openModal(videoId) {
  closeAllPlayers()

  let videoDiv = $(`#yourss-video-${videoId}`)
  let channelId = videoDiv.data("channel-id")
  let videoUrl = getVideoPlayerUrl(videoId)

  $("#yourss-modal").find("iframe").attr("src", videoUrl)
  $("#yourss-modal-video-title").html(videoDiv.find(".yourss-video-title").html())
  $("#yourss-modal-link-youtube").attr("href", `https://www.youtube.com/watch?v=${videoId}`)
  $("#yourss-modal-link-tab").attr("href", videoUrl)
  $("#yourss-modal-link-piped").attr("href", `https://piped.kavin.rocks/watch?v=${videoId}`)
  if (channelId) {
    $("#yourss-modal-link-rss").attr("href", `/proxy/rss/${channelId}`)
    $("#yourss-modal-link-rss").css("display", "block")
  } else {
    $("#yourss-modal-link-rss").css("display", "none")
  }
  $("#yourss-modal").modal("show")
}
$("#yourss-modal").on("hidden.bs.modal", function (e) {
  $("#yourss-modal").find("iframe").removeAttr("src")
})
