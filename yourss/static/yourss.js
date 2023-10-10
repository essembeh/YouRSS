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
function toggle_filter(button) {
  if ((channel_id = $(button).data("channel-id"))) {
    if (hidden_channel_ids.includes(channel_id)) {
      hidden_channel_ids.splice(hidden_channel_ids.indexOf(channel_id), 1)
    } else {
      hidden_channel_ids.push(channel_id)
    }
  }
  $(".yourss-filter").each(function () {
    if (hidden_channel_ids.includes($(this).data("channel-id"))) {
      $(this).removeClass("btn-secondary")
      $(this).addClass("btn-outline-danger")
    } else {
      $(this).removeClass("btn-outline-danger")
      $(this).addClass("btn-secondary")
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
$(document).ready(function () {
  toggle_filter()
})

/**
 * Handle modal player
 */
function play_video(id) {
  channel_id = $(id).data("channel-id")
  channel_title = $(id).data("channel-title")
  video_id = $(id).data("video-id")
  video_title = $(id).data("video-title")

  $("#yourss-modal").data("video-id", video_id)
  $("#yourss-modal")
    .find("iframe")
    .attr(
      "src",
      `https://www.youtube-nocookie.com/embed/${video_id}?autoplay=1&control=2&rel=0`
    )
  $("#yourss-modal-channel-image").attr("src", `/api/avatar/${channel_id}`)
  $("#yourss-modal-channel-title").text(channel_title)
  $("#yourss-modal-video-title").text(video_title)
  $("#yourss-modal-link-youtube").attr(
    "href",
    `https://www.youtube.com/watch?v=${video_id}`
  )
  $("#yourss-modal-link-piped").attr(
    "href",
    `https://piped.kavin.rocks/watch?v=${video_id}`
  )
  $("#yourss-modal-link-rss").attr("href", `/api/rss/${channel_id}`)
  $("#yourss-modal").modal("show")
}
$("#yourss-modal").on("hidden.bs.modal", function (e) {
  $("#yourss-modal").find("iframe").removeAttr("src")
})
