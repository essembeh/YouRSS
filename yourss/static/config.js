
function update_settings() {
    $.get("/api/auth", function (data) {
        username = $("#inputUsername").val()
        email = $("#inputEmail").val()
        avatar = $("#inputAvatar").val()
        $.ajax({
            url: "/api/config",
            type: "PUT",
            dataType: "json",
            contentType: "application/json",
            data: JSON.stringify({
                name: username,
                email: email,
                avatar: avatar
            }),
            success: function (result) {
                load_usermenu()
            },
            error: function (result) {
                console.log(result)
                alert("Error updating settings")
            },
            complete: function (result) {
                load_config()
            }
        })
    })
}
function update_password() {
    password1 = $("#inputPassword1").val()
    password2 = $("#inputPassword2").val()
    old_password = $("#inputPassword0").val()

    if (password1 === password2) {
        $.get("/api/auth", function (data) {
            $.ajax({
                url: "/api/config",
                type: "PUT",
                dataType: "json",
                contentType: "application/json",
                data: JSON.stringify({
                    password: password1,
                    old_password: old_password
                }),
                success: function (result) {
                },
                error: function (result) {
                    console.log(result)
                    alert("Error updating password")
                },
                complete: function (result) {
                    load_config()
                    $("#inputPassword0").val("")
                    $("#inputPassword1").val("")
                    $("#inputPassword2").val("")
                }
            })
        })
    }
}

function load_config() {
    $.get("/api/auth", function (data) {
        $.get("/api/config", function (config) {
            $("#inputUsername").val(config.name)
            $("#inputEmail").val(config.email)
            $("#inputAvatar").val(config.avatar)
            if (config.avatar) {
                $("#userAvatar").attr("src", config.avatar)
            }
        })
    })
}

$(document).ready(function () {
    load_config()
})

