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
 * Handle iframe/image swap for current video
 */
$(document).ready(function () {
  $("body").on("click", "img", function () {
    $("iframe").each(function () {
      if ((image_url = $(this).data("src"))) {
        video_url = $(this).attr("src")
        parent = $(this).parent()
        $(this).remove()
        $(parent).prepend(
          `<img class="card-img-top" src="${image_url}" style="cursor: pointer;" data-src="${video_url}"/>`
        )
      }
    })
    if ((video_url = $(this).data("src"))) {
      image_url = $(this).attr("src")
      height = $(this).height()
      parent = $(this).parent()
      $(this).remove()
      $(parent).prepend(
        `<iframe src="${video_url}" data-src="${image_url}" width="100%" height="${height}" allow="autoplay; encrypted-media; picture-in-picture" allowfullscreen="" frameborder="0"></iframe>`
      )
    }
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
