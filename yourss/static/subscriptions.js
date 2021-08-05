function update_channel(channelId) {
    $.get("/api/auth", function (data) {
        label = $('#channelLabel-' + channelId).val()
        enabled = $('#channelEnabled-' + channelId).is(":checked")
        $.ajax({
            url: "/api/subscription/" + channelId,
            type: "PUT",
            dataType: "json",
            contentType: "application/json",
            data: JSON.stringify({
                label: label,
                enabled: enabled
            }),
            success: function (result) {
            },
            error: function (result) {
                console.log(result)
            },
            complete: function (result) {
                load_channels()
            }
        })
    })
}

function suscribe() {
    $.get("/api/auth", function (data) {
        channelId = $('#channelId-new').val()
        channelLabel = $('#channelLabel-new').val()
        channelEnabled = $('#channelEnabled-new').is(":checked")
        $.ajax({
            url: "/api/subscription",
            type: "POST",
            dataType: "json",
            contentType: "application/json",
            data: JSON.stringify({
                channel_id: channelId,
                url: channelId,
                label: channelLabel,
                enabled: channelEnabled
            }),
            success: function (result) {
            },
            error: function (result) {
                console.log(result)
            },
            complete: function (result) {
                load_channels()
            }
        })
    })
}

function unsuscribe(channelId) {
    $.get("/api/auth", function (data) {
        $.ajax({
            url: "/api/subscription/" + channelId,
            type: "DELETE",
            dataType: "json",
            contentType: "application/json",
            success: function (result) {
            },
            error: function (result) {
                console.log(result)
            },
            complete: function (result) {
                load_channels()
            }
        })
    })
}

function channel_to_div(channel) {
    return
}

function load_channels() {
    $.get("/api/auth", function (data) {
        $.get("/api/subscription", function (data) {
            $("#myNavbarFilterByChannel").css("display", "block")
            $("#myNavbarFilterByChannelContent").html("")
            $("#myNavbarFilterByChannelContent").append(`<li><a class="dropdown-item" href="#" onclick="filter_items('.filterable', 'channel', null);">-- All --</a></li>`)

            $("#mySubscriptions").html("")
            $("#mySubscriptions").append(`
                <div class="col-lg-3 col-md-6 mb-3">
                    <div class="card h-100">
                        <div class="card-body">
                            <h5 class="card-title">Suscribe to a new channel</h5>
                            <div class="form-floating mb-3">
                                <input type="text" class="form-control" id="channelId-new" placeholder="ID or url" required>
                                <label for="channelId-new">ID or url</label>
                            </div>
                            <div class="form-floating mb-3">
                                <input type="text" class="form-control" id="channelLabel-new" placeholder="Label">
                                <label for="channelLabel-new">Label</label>
                            </div>
                            <div class="form-check form-switch">
                                <input class="form-check-input" type="checkbox" id="channelEnabled-new" checked>
                                <label class="form-check-label" for="channelEnabled-new">Enabled</label>
                            </div>
                            <div class="form-group float-end">
                                <button class="btn btn-success bi bi-save" onclick="suscribe()"> Suscribe</button>
                            </div>
                        </div>
                    </div>
                </div>
            `)
            data.sort(function (a, b) {
                return a.name.toLowerCase().localeCompare(b.name.toLowerCase())
            })
            $.each(data, function (i, channel) {
                $("#myNavbarFilterByChannelContent").append(`<li><a class="dropdown-item" href="#" onclick="filter_items('.filterable', 'channel', '${channel.channel_id}');">${channel.name}</a></li>`)
                sort_list("#myNavbarFilterByChannelContent", function (x) { return $(x).text().toLowerCase() })

                $("#mySubscriptions").append(`
                    <div class="col-lg-3 col-md-6 mb-3 filterable" data-channel="${channel.channel_id}" data-label="${channel.label}">
                        <div class="card h-100">
                            <div class="card-body">
                                <h5 class="card-title h5" style="cursor: pointer;font-weight:bold;">
                                    <img src="${channel.avatar}" width="60" height="60" class="rounded-circle">
                                    ${channel.name}
                                </h5>
                                <div class="form-floating mb-3">
                                    <input type="text" class="form-control" id="channelId-${channel.channel_id}" placeholder="" value="${channel.channel_id}" readonly>
                                    <label for="channelId-${channel.channel_id}">Channel ID</label>
                                </div>
                                <div class="form-floating mb-3">
                                    <input type="text" class="form-control" id="channelLabel-${channel.channel_id}" placeholder="Label" value="${default_str(channel.label)}">
                                    <label for="channelLabel-${channel.channel_id}">Label</label>
                                </div>
                                <div class="form-check form-switch">
                                    <input class="form-check-input" type="checkbox" id="channelEnabled-${channel.channel_id}" ${boolean_to_checked(channel.enabled)}>
                                    <label class="form-check-label" for="channelEnabled-${channel.channel_id}">Enabled</label>
                                </div>
                                <div class="form-group float-end">
                                    <button class="btn btn-outline-primary bi bi-save" onclick="update_channel('${channel.channel_id}')"> Update</button>
                                    <button class="btn btn-outline-danger bi bi-eraser" onclick="unsuscribe('${channel.channel_id}')"> Unsuscribe</button>
                                </div>
                            </div>
                        </div>
                    </div>
                `)
            })

        })
    })
}

$(document).ready(function () {
    load_channels()
})

