/**
 * Sort a list of elements given natural order using given getter
 * @param {*} id 
 * @param {*} mygetter 
 */
function sort_list(id, mygetter) {
    result = $(id).children().sort(function (a, b) {
        aa = mygetter(a)
        bb = mygetter(b)
        if (aa < bb)
            return -1
        if (aa > bb)
            return 1
        return 0
    })
    $(id).html(result)
}

/**
 * Hide / show items given expected value and a given data key
 * @param {*} selector 
 * @param {*} data_key 
 * @param {*} expected 
 */
function filter_items(selector, data_key, expected) {
    $(selector).each(function () {
        if (expected === null || $(this).data(data_key) === expected) {
            $(this).css("display", "block")
        } else {
            $(this).css("display", "none")
        }
    })

}
