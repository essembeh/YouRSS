/**
 * Load feed videos
 */
function load_user_feeds() {
    $.get("/api/auth", function (data) {
        $.get("/api/config", function (config) {
            $("#myNavbarFilterByChannel").css("display", "block")
            $("#myNavbarFilterByLabel").css("display", "block")
            $("#myNavbarFilterByChannelContent").html("")
            $("#myNavbarFilterByLabelContent").html("")
            $("#myNavbarFilterByChannelContent").append(`<li><a class="dropdown-item" href="#" onclick="filter_items('.filterable', 'channel', null);">-- All --</a></li>`)
            $("#myNavbarFilterByLabelContent").append(`<li><a class="dropdown-item" href="#" onclick="filter_items('.filterable', 'label', null);">-- All --</a></li>`)

            $("#myVideos").html("")
            $.each(config.labels, function (i, label) {
                $("#myNavbarFilterByLabelContent").append(`<li><a class="dropdown-item" href="#" onclick="filter_items('.filterable', 'label', '${label}');">${label}</a></li>`)
            })
            sort_list("#myNavbarFilterByLabelContent", function (x) { return $(x).text().toLowerCase() })

            $.get("/api/subscription", function (channels) {
                $.each(channels, function (i, channel) {
                    if (channel.enabled) {
                        $("#myNavbarFilterByChannelContent").append(`<li><a class="dropdown-item" href="#" onclick="filter_items('.filterable', 'channel', '${channel.channel_id}');">${channel.name}</a></li>`)
                        sort_list("#myNavbarFilterByChannelContent", function (x) { return $(x).text().toLowerCase() })
                        $.get("/api/channel/" + channel.channel_id + "/fetch", function (feed) {
                            $.each(feed.videos, function (i, video) {
                                console.log(">>>" + video.title)
                                fixedTitle = string_sentence_case(video.title)
                                console.log(">>>" + fixedTitle)
                                $("#myVideos").append(`
                                    <div class="col-xxl-2 col-xl-3 col-lg-3 col-md-4 col-sm-6 mb-3 filterable" data-channel="${channel.channel_id}" data-published="${video.published}" data-updated="${video.updated}" data-label="${channel.label}">
                                        <div class="card h-100" data-thumbnail="${video.thumbnail_url}" data-video="${video.id}">
                                            <img class="card-img-top" src="${video.thumbnail_url}" style="cursor: pointer" alt="${video.title}" data-src="https://www.youtube-nocookie.com/embed/${video.video_id}?autoplay=1"/>
                                            <div class="card-body d-flex flex-column">
                                                <h5 class="card-title h5" style="cursor: pointer;font-weight:bold;" onclick="window.open('${feed.link}')">
                                                    <img src="${channel.avatar}" width="30" height="30" class="rounded-circle">
                                                    ${channel.name}
                                                </h5>
                                                <p class="card-text" style="cursor: pointer;" onclick="window.open('${video.link}')">${fixedTitle}</p>
                                                <p class="card-text mt-auto"><small class="text-muted">${moment(video.published).fromNow()}</small></p>
                                            </div>
                                        </div>
                                    </div>
                                `)
                            })
                            sort_list("#myVideos", function (x) { return new Date($(x).data("published")).getTime() * -1 })
                        })
                    }
                })
            })
        })
    })
}

$(document).ready(function () {
    $("body").on("click", "img", function () {
        $("iframe").each(function () {
            if (image_url = $(this).data("src")) {
                video_url = $(this).attr("src")
                parent = $(this).parent()
                $(this).remove()
                $(parent).prepend(`<img class="card-img-top" src="${image_url}" style="cursor: pointer;" data-src="${video_url}"/>`)
            }
        })
        if (video_url = $(this).data("src")) {
            image_url = $(this).attr("src")
            height = $(this).height()
            parent = $(this).parent()
            $(this).remove()
            $(parent).prepend(`<iframe src="${video_url}" data-src="${image_url}" width="100%" height="${height}" allowfullscreen="" frameborder="0"></iframe>`)
        }
    })
    load_user_feeds()
})

