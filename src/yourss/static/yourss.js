/**
 * Scroll to top and auto-close embedded players
 */
$(window).scroll(function () {
  let height = $(window).scrollTop()
  if (height > 100) {
    $("#scroll-to-top").fadeIn()
  } else {
    $("#scroll-to-top").fadeOut()
  }
  
  // Auto-close embedded players when scrolled out of view
  $(".yourss-player-container:visible").each(function () {
    let playerElement = $(this)
    let elementTop = playerElement.offset().top
    let elementBottom = elementTop + playerElement.outerHeight()
    let viewportTop = $(window).scrollTop()
    let viewportBottom = viewportTop + $(window).height()
    
    // Check if player is completely out of viewport
    if (elementBottom < viewportTop || elementTop > viewportBottom) {
      closeAllPlayers()
      return false // Exit the loop since all players are closed
    }
  })
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

function openEmbedded(videoId) {
  closeAllPlayers()

  let height = $(`#yourss-thumbnail-${videoId}`).height()
  let selectedLang = $("#yourss-lang-selector").val() || ''
  let videoUrl = `/proxy/player/${videoId}`
  if (selectedLang) {
    videoUrl += `?lang=${selectedLang}`
  }

  $(`#yourss-thumbnail-${videoId}`).css("display", "none")
  $(`#yourss-player-${videoId}`).css("display", "block")
  $(`#yourss-player-${videoId}`).append(`
    <iframe src="${videoUrl}"
            width="100%" height="${height}"
            allow="autoplay; encrypted-media; picture-in-picture" 
            allowfullscreen="" frameborder="0"></iframe>`)
}

function openTab(videoId) {
  closeAllPlayers()
  let selectedLang = $("#yourss-lang-selector").val() || ''
  let videoUrl = `/proxy/player/${videoId}`
  if (selectedLang) {
    videoUrl += `?lang=${selectedLang}`
  }
  window.open(videoUrl, "_blank")
}

function openModal(videoId) {
  closeAllPlayers()

  let videoDiv = $(`#yourss-video-${videoId}`)
  let channelId = videoDiv.data("channel-id")
  let selectedLang = $("#yourss-lang-selector").val() || ''
  let videoUrl = `/proxy/player/${videoId}`
  if (selectedLang) {
    videoUrl += `?lang=${selectedLang}`
  }

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
