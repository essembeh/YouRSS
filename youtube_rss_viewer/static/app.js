function video_to_div(video) {
    time_label = moment(video.video_updated).fromNow();
    return `
    <div class="col-xl-2 col-lg-3 col-md-4 col-sm-6 mb-3">
        <div class="card h-100" data-thumbnail="${video.video_thumbnail}" data-video="${video.video_id}">
            <img src="${video.video_thumbnail}" class="card-img-top" alt="${video.video_title}"/>
            <div class="card-body">
                <h5 class="card-title">${video.channel_name}: <span class="fw-normal">${video.video_title}</span></h5>
                <p class="card-text"><small class="text-muted">${time_label}</small></p>
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

    // Loading for videos
    $('body').on('click', '.card', function()
    {
        $('#channel-content .card').each(function() {
            $img = $(this).find('.card-img-top');
            if(!$img.length) {
                $(this).find('iframe').remove();
                $(this).prepend(`<img src="${$(this).data('thumbnail')}" class="card-img-top" alt="video"/>`);
            }
        });

        var $img = $(this).find('.card-img-top');
        var height = $img.height();

        $img.remove();
        $(this).prepend(`
            <iframe width="100%" height="${height}" src="https://www.youtube-nocookie.com/embed/${$(this).data('video')}" allowfullscreen="" frameborder="0"></iframe>
        `);
    })

})
