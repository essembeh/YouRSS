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
  old_order = $(button).find("i").attr("class")
  new_order =
    SORT_ORDERS[(SORT_ORDERS.indexOf(old_order) + 1) % SORT_ORDERS.length]
  $(button).find("i").attr("class", new_order)
  sort_videos(new_order)
}
function sort_videos(order) {
  $("#video-container").html(
    $("#video-container")
      .children()
      .sort(function (a, b) {
        a_channel = $(a).data("channel-title")
        a_date = new Date($(a).data("published"))
        b_channel = $(b).data("channel-title")
        b_date = new Date($(b).data("published"))
        if (order === "bi bi-sort-down") {
          if (a_date < b_date) return 1
          if (a_date > b_date) return -1
        } else if (order === "bi bi-sort-up") {
          if (a_date < b_date) return -1
          if (a_date > b_date) return 1
        } else if (order === "bi bi-sort-alpha-down") {
          if (a_channel < b_channel) return -1
          if (a_channel > b_channel) return 1
          if (a_date < b_date) return 1
          if (a_date > b_date) return -1
        } else if (order === "bi bi-sort-alpha-up") {
          if (a_channel < b_channel) return -1
          if (a_channel > b_channel) return 1
          if (a_date < b_date) return -1
          if (a_date > b_date) return 1
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
  selected_channel_id = $(button).hasClass("btn-secondary")
    ? $(button).data("channel-id")
    : null
  $(".yourss-filter").each(function () {
    if ($(this).data("channel-id") === selected_channel_id) {
      $(this).addClass("btn-primary")
      $(this).removeClass("btn-secondary")
    } else {
      $(this).addClass("btn-secondary")
      $(this).removeClass("btn-primary")
    }
  })
  $(".yourss-filterable").each(function () {
    if (selected_channel_id === null) {
      $(this).css("display", "block")
    } else if ($(this).data("channel-id") === selected_channel_id) {
      $(this).css("display", "block")
    } else {
      $(this).css("display", "none")
    }
  })
}

/**
 * Handle mark as read
 */
function mark_as_read(date) {
  if (date) {
    mark_date = new Date(date)
    $(".yourss-filterable").each(function () {
      video_date = new Date($(this).data("published"))
      video_mark = $(this).find(".new-item")
      if (video_date > mark_date) {
        video_mark.addClass("bi-record-fill")
        video_mark.removeClass("bi-record")
      } else {
        video_mark.addClass("bi-record")
        video_mark.removeClass("bi-record-fill")
      }
    })
    Cookies.set("mark-date:" + window.location.pathname, date)
  }
}
$(document).ready(function () {
  mark_as_read(Cookies.get("mark-date:" + window.location.pathname))
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
