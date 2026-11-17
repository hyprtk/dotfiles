.pragma library

// Shared by every surface. A QML singleton cannot read a context property
// (verified on Qt 6.12), so the palette arrives through Bridge.palette and only
// stateless helpers live in a pragma library.
function alpha(c, value) {
    if (c === undefined || c === null)
        c = Qt.rgba(1, 1, 1, 1);
    return Qt.rgba(c.r, c.g, c.b, value);
}

function token(palette, name) {
    var map = palette && palette.syntax ? palette.syntax : ({});
    return map[name] || (palette ? palette.foreground : "#e5e7eb");
}

function clamp(value, low, high) {
    return Math.max(low, Math.min(high, value));
}

function pad(value, width) {
    var text = String(value);
    while (text.length < width)
        text = "0" + text;
    return text;
}

// Canvas 2D wants a CSS colour string, not a QML color object.
function css(c, value) {
    if (c === undefined || c === null)
        return "rgba(255,255,255," + value + ")";
    return "rgba(" + Math.round(c.r * 255) + "," + Math.round(c.g * 255) + ","
        + Math.round(c.b * 255) + "," + value + ")";
}
