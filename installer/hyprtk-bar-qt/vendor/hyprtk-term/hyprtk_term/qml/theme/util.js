.pragma library

// A QML singleton cannot read a context property (verified on Qt 6.12), so the
// palette arrives through Bridge.palette and only stateless helpers live here.
function alpha(c, value) {
    if (c === undefined || c === null)
        c = Qt.rgba(1, 1, 1, 1);
    return Qt.rgba(c.r, c.g, c.b, value);
}

function token(palette, name) {
    return palette && palette[name] !== undefined ? palette[name] : "#e5e7eb";
}

function clamp(value, low, high) {
    return Math.max(low, Math.min(high, value));
}

// Canvas 2D wants a CSS string, not a QML color object.
function css(c, value) {
    if (c === undefined || c === null)
        return "rgba(255,255,255," + value + ")";
    return "rgba(" + Math.round(c.r * 255) + "," + Math.round(c.g * 255) + ","
        + Math.round(c.b * 255) + "," + value + ")";
}

function shortTitle(text) {
    if (!text)
        return "Terminal";
    return text.length > 28 ? text.slice(0, 27) + "\u2026" : text;
}
