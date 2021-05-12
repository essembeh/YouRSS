function video_to_div(video) {
    time_label = moment(video.video_updated).fromNow();
    return `
    <div class="accordion-item">
        <div class="accordion-header" 
            id="video-infos-${video.video_id}">
            <button class="accordion-button collapsed" 
                    type="button" 
                    data-bs-toggle="collapse" 
                    data-bs-target="#video-player-${video.video_id}" 
                    aria-expanded="false" 
                    aria-controls="video-player-${video.video_id}">
                <span><b>${video.channel_name}</b>: ${video.video_title}</span><span class="badge rounded-pill bg-secondary" style="font-size: .70em;">${time_label}</span> 
            </button>
        </div>
        <div class="accordion-collapse collapse" 
            id="video-player-${video.video_id}"
            aria-labelledby="video-infos-${video.video_id}"
            data-bs-parent="#channel-content">
            <div class="accordion-body">
                <iframe class="youtube-plugin-video" 
                        style=""
                        width="100%"
                        height="50%"
                        data-src="https://www.youtube-nocookie.com/embed/${video.video_id}" 
                        allowfullscreen="" 
                        frameborder="0">
                </iframe>
                <div>
                    <p>${video.video_description.replace(/\n/g, "<br />")}</p>
                </div>
            </div>
        </div>
    </div>
`
}
function load_feed(query) {
    url = "/fetch/" + query
    console.log("Loaf feed from: " + url)
    var jqxhr = $.getJSON(url, function (data) {
        // display videos
        channel_content = $('#channel-content')
        $.each(data, function (i, video) {
            channel_content.append(video_to_div(video))
        });
    })
        .fail(function () {
            console.log("fail");
        })
}

$(document).ready(function () {
    params = new URLSearchParams(window.location.search)
    if (!params.get('q')) {
        params.set("q", "UCa_Dlwrwv3ktrhCy91HpVRw,Jonnyswitzerland")
        window.history.replaceState({}, document.title, window.location.pathname + "?" + params.toString());
        params = new URLSearchParams(window.location.search)
    }
    query = params.get('q')
    if (query) {
        load_feed(query)
    } else {
        load_feed("UCa_Dlwrwv3ktrhCy91HpVRw")
    }

    // lazy loading for videos
    $('body').on('shown.bs.collapse', '.accordion-collapse', function () {
        $(this).find("iframe").prop("src", function () {
            return $(this).data("src");
        });
    })
    $('body').on('hidden.bs.collapse', '.accordion-collapse', function () {
        $(this).find("iframe").prop("src", function () {
            return "";
        });
    })

})
