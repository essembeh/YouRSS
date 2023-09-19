/**
 * Scroll to top
 */
$(window).scroll(function () {
  var height = $(window).scrollTop()
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
$(document).ready(function () {
  $("#video-container").html(
    $("#video-container")
      .children()
      .sort(function (a, b) {
        a_date = new Date($(a).data("published")).getTime()
        b_date = new Date($(b).data("published")).getTime()
        if (a_date < b_date) return 1
        if (a_date > b_date) return -1
        return 0
      })
  )
})

/**
 * Handle filter toggle
 */
var hidden_channel_ids = []

function toggle_filter(channel_id) {
  if (hidden_channel_ids.includes(channel_id)) {
    hidden_channel_ids.splice(hidden_channel_ids.indexOf(channel_id), 1)
  } else {
    hidden_channel_ids.push(channel_id)
  }
  $(".yourss-filter").each(function () {
    if (hidden_channel_ids.includes($(this).data("channel-id"))) {
      $(this).removeClass("btn-secondary")
      $(this).addClass("btn-outline-secondary")
    } else {
      $(this).addClass("btn-secondary")
      $(this).removeClass("btn-outline-secondary")
    }
  })
  $(".yourss-filterable").each(function () {
    if (hidden_channel_ids.includes($(this).data("channel-id"))) {
      $(this).css("display", "none")
    } else {
      $(this).css("display", "block")
    }
  })
}

/**
 * Handle modal player
 */
function play_video(id) {
  video_id = $(id).data("video-id")
  $("#yourss-modal").data("video-id", video_id)
  $("#yourss-modal").find("iframe").attr("src", `https://www.youtube-nocookie.com/embed/${video_id}?autoplay=1&control=2&rel=0`)
  $("#yourss-modal").find(".modal-title").text($(id).data("channel-title") + ", " + $(id).data("video-title"))
  $("#yourss-modal").modal("show")
}
$("#yourss-modal").on("hidden.bs.modal", function (e) {
  $("#yourss-modal").find("iframe").removeAttr("src")
})
function open_external_video(base_url) {
  video_id = $("#yourss-modal").data("video-id")
  window.open(`${base_url}/watch?v=${video_id}`)
  $("#yourss-modal").modal("hide")
}
