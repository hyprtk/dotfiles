.pragma library

// Shared by every surface. A QML singleton cannot read a context property
// (verified on Qt 6.12), so the palette arrives through Bridge.palette and only
// stateless helpers live in a pragma library.

function alpha(c, value) {
    if (c === undefined || c === null)
        c = Qt.rgba(1, 1, 1, 1);
    return Qt.rgba(c.r, c.g, c.b, value);
}

// Mix two colours: 0 keeps a, 1 is b.
function mix(a, b, amount) {
    if (a === undefined || a === null)
        a = Qt.rgba(0, 0, 0, 1);
    if (b === undefined || b === null)
        b = Qt.rgba(1, 1, 1, 1);
    return Qt.rgba(a.r + (b.r - a.r) * amount,
                   a.g + (b.g - a.g) * amount,
                   a.b + (b.b - a.b) * amount,
                   1);
}

// Readable text on top of an arbitrary background.
function onColor(background) {
    if (background === undefined || background === null)
        return "#11111b";
    var luma = 0.2126 * background.r + 0.7152 * background.g + 0.0722 * background.b;
    return luma > 0.55 ? "#11111b" : "#f4f7ff";
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
