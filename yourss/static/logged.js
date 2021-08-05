

function load_usermenu() {
    $.get("/api/auth", function (data) {
        $.get("/api/config", function (config) {
            $("#myUserMenu").css("display", "block")
            $("#myName").html(config.name)
            if (config.avatar) {
                $("#myAvatar").attr("src", config.avatar)
            }
        })
    })
}

$(document).ready(function () {
    load_usermenu()
})

/*Scroll to top when arrow up clicked BEGIN*/
$(window).scroll(function () {
    var height = $(window).scrollTop();
    if (height > 100) {
        $('#back2Top').fadeIn();
    } else {
        $('#back2Top').fadeOut();
    }
});
$(document).ready(function () {
    $("#back2Top").click(function (event) {
        event.preventDefault();
        $("html, body").animate({ scrollTop: 0 }, "slow");
        return false;
    });

});
 /*Scroll to top when arrow up clicked END*/
