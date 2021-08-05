/**
 * Sort a list of elements given natural order using given getter
 * @param {*} container 
 * @param {*} mygetter 
 */
function sort_list(container, mygetter) {
    result = $(container).children().sort(function (a, b) {
        aa = mygetter(a)
        bb = mygetter(b)
        if (aa < bb)
            return -1
        if (aa > bb)
            return 1
        return 0
    })
    $(container).html(result)
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

/**
 * Fix sentence case, youtubers love CAPS :)
 * @param {*} str 
 * @returns 
 */
function string_sentence_case(str) {
    return str.toLowerCase().replace(/\.\s+([a-z])[^\.]|^(\s*[a-z])[^\.]/g, s => s.replace(/([a-z])/, s => s.toUpperCase()))
}

/**
 * Helper to build input checked when boolean value is True
 * @param {*} value 
 * @returns 
 */
function boolean_to_checked(value) {
    return value ? "checked" : ""
}

/**
 * Default string when None
 * @param {*} value 
 * @returns 
 */
function default_str(value) {
    return value ? value : ""
}
