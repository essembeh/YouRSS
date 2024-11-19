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
