// Per-widget settings schema for the cog popup (components/WidgetSettingsPopup).
//
// Each row is { key, label, type, section, ... }. Types map to controls in the
// popup: bool | int | percent | text | choice. ``percent`` stores a 0..1 float
// (or a 0..1 multiplier) but is shown as 0..100.
.pragma library

const POSITIONS = [
    "top-left", "top-center", "top-right",
    "center-left", "center", "center-right",
    "bottom-left", "bottom-center", "bottom-right",
    "free"
]

// Effective defaults when the widget block leaves a key unset. These match the
// widgets' own fallbacks, so an untouched widget shows what it actually uses.
const WIDGET_DEFAULTS = {
    clock: {
        position: "top-left", width: 220, height: 0, opacity: 0.75, padding: 18
    },
    weather: {
        position: "top-left", width: 280, height: 0, opacity: 0.75, padding: 18
    },
    visualizer: {
        position: "bottom-center", width: 420, height: 120, opacity: 0.6, padding: 12
    },
    disk: {
        position: "bottom-left", width: 300, height: 0, opacity: 0.75, padding: 18
    },
    network: {
        position: "bottom-left", width: 300, height: 0, opacity: 0.75, padding: 18
    },
    resources: {
        position: "top-left", width: 280, height: 0, opacity: 0.75, padding: 18
    },
    sysinfo: {
        position: "bottom-left", width: 320, height: 0, opacity: 0.75, padding: 18
    }
}

const LABELS = {
    clock: "Clock", weather: "Weather", visualizer: "Visualizer", disk: "Disk",
    network: "Network", resources: "Resources", sysinfo: "System Info"
}

const COMMON = [
    { key: "position", label: "position", type: "choice", section: "Placement", choices: POSITIONS, def: "top-left" },
    { key: "layer", label: "layer", type: "choice", section: "Placement", choices: ["background", "bottom", "top"], def: "bottom" },
    { key: "margin_x", label: "X", type: "int", section: "Placement", min: 0, max: 8000, def: 40 },
    { key: "margin_y", label: "Y", type: "int", section: "Placement", min: 0, max: 8000, def: 40 },
    { key: "width", label: "width", type: "int", section: "Placement", min: 0, max: 4000, def: 280 },
    { key: "height", label: "height", type: "int", section: "Placement", min: 0, max: 4000, def: 0 },
    { key: "radius", label: "radius", type: "int", section: "Placement", min: 0, max: 60, def: 16 },
    { key: "padding", label: "padding", type: "int", section: "Placement", min: 0, max: 80, def: 18 },
    { key: "scale", label: "scale %", type: "percent", section: "Placement", min: 50, max: 200, step: 5, def: 1.0 },
    { key: "opacity", label: "opacity %", type: "percent", section: "Placement", min: 10, max: 100, step: 5, def: 0.75 },
    { key: "snap_group", label: "snap group", type: "text", section: "Placement", def: "" },
    { key: "snap_axis", label: "snap axis", type: "choice", section: "Placement", choices: ["horizontal", "vertical"], def: "horizontal" },
    { key: "snap_order", label: "snap order", type: "int", section: "Placement", min: 0, max: 99, def: 0 },

    { key: "background", label: "background", type: "text", section: "Colours", placeholder: "#rrggbb", def: "" },
    { key: "foreground", label: "foreground", type: "text", section: "Colours", placeholder: "#rrggbb", def: "" },
    { key: "accent", label: "accent", type: "text", section: "Colours", placeholder: "#rrggbb", def: "" }
]

const PER_WIDGET = {
    clock: [
        { key: "style", label: "style", type: "choice", section: "Options", choices: ["digital", "text", "dials"], def: "digital" },
        { key: "time_format", label: "time fmt", type: "text", section: "Options", def: "%H:%M" },
        { key: "date_format", label: "date fmt", type: "text", section: "Options", def: "%A, %d %B" },
        { key: "font", label: "font", type: "text", section: "Options", def: "" },
        { key: "theme", label: "theme", type: "text", section: "Options", placeholder: "theme name", def: "" },
        { key: "show_date", label: "date", type: "bool", section: "Options", def: true },
        { key: "show_seconds", label: "seconds", type: "bool", section: "Options", def: false },
        { key: "dial_count", label: "dials", type: "int", section: "Options", min: 1, max: 3, def: 1 },
        { key: "ring_thickness", label: "ring width", type: "int", section: "Options", min: 2, max: 24, def: 6 }
    ],
    weather: [
        { key: "city", label: "city", type: "text", section: "Options", def: "" },
        { key: "units", label: "units", type: "choice", section: "Options", choices: ["metric", "imperial"], def: "metric" },
        { key: "refresh_minutes", label: "refresh (m)", type: "int", section: "Options", min: 5, max: 240, step: 5, def: 15 },
        { key: "forecast_days", label: "forecast days", type: "int", section: "Options", min: 0, max: 7, def: 3 },
        { key: "show_icon", label: "icon", type: "bool", section: "Options", def: true },
        { key: "show_temp", label: "temp", type: "bool", section: "Options", def: true },
        { key: "show_condition", label: "condition", type: "bool", section: "Options", def: true },
        { key: "show_feels_like", label: "feels like", type: "bool", section: "Options", def: true },
        { key: "show_humidity", label: "humidity", type: "bool", section: "Options", def: true },
        { key: "show_wind", label: "wind", type: "bool", section: "Options", def: true },
        { key: "show_forecast", label: "forecast", type: "bool", section: "Options", def: true }
    ],
    visualizer: [
        { key: "style", label: "style", type: "choice", section: "Options", choices: ["bars", "wave", "mirror", "dots", "glow"], def: "bars" },
        { key: "bars", label: "bars", type: "int", section: "Options", min: 8, max: 128, def: 48 },
        { key: "fps", label: "fps", type: "int", section: "Options", min: 10, max: 120, def: 60 },
        { key: "color_mode", label: "colours", type: "choice", section: "Options", choices: ["accent", "gradient", "pywal", "custom"], def: "pywal" },
        { key: "color", label: "colour", type: "text", section: "Options", placeholder: "#rrggbb", def: "" },
        { key: "gradient_from", label: "grad from", type: "text", section: "Options", placeholder: "#rrggbb", def: "" },
        { key: "gradient_to", label: "grad to", type: "text", section: "Options", placeholder: "#rrggbb", def: "" },
        { key: "source", label: "source", type: "choice", section: "Options", choices: ["auto", "cava", "synthetic"], def: "auto" },
        { key: "sensitivity", label: "sensitivity %", type: "percent", section: "Options", min: 50, max: 300, step: 10, def: 1.0 },
        { key: "smoothing", label: "smoothing %", type: "percent", section: "Options", min: 0, max: 90, step: 5, def: 0.0 },
        { key: "orientation", label: "orientation", type: "choice", section: "Options", choices: ["up", "down"], def: "up" },
        { key: "peak_dots", label: "peak dots", type: "bool", section: "Options", def: false }
    ],
    disk: [
        { key: "show_bar", label: "bar", type: "bool", section: "Options", def: true },
        { key: "show_rates", label: "rates", type: "bool", section: "Options", def: true },
        { key: "columns", label: "columns", type: "int", section: "Options", min: 1, max: 2, def: 1 },
        { key: "drives_max", label: "max drives", type: "int", section: "Options", min: 1, max: 16, def: 3 }
    ],
    network: [
        { key: "show_ip", label: "IP", type: "bool", section: "Options", def: true },
        { key: "show_rates", label: "rates", type: "bool", section: "Options", def: true },
        { key: "show_graph", label: "graph", type: "bool", section: "Options", def: true }
    ],
    resources: [
        { key: "show_cpu", label: "CPU", type: "bool", section: "Options", def: true },
        { key: "show_ram", label: "RAM", type: "bool", section: "Options", def: true },
        { key: "show_swap", label: "swap", type: "bool", section: "Options", def: true },
        { key: "show_temp", label: "temp", type: "bool", section: "Options", def: true },
        { key: "show_load", label: "load", type: "bool", section: "Options", def: true }
    ],
    sysinfo: [
        { key: "refresh_seconds", label: "refresh (s)", type: "int", section: "Options", min: 1, max: 120, def: 10 },
        { key: "show_disks", label: "disks", type: "bool", section: "Options", def: true }
    ]
}

function label(id) {
    return LABELS[id] || id
}

function options(id) {
    const defaults = WIDGET_DEFAULTS[id] || {}
    const rows = []
    for (let i = 0; i < COMMON.length; i++) {
        const row = {}
        for (const key in COMMON[i])
            row[key] = COMMON[i][key]
        if (defaults[row.key] !== undefined)
            row.def = defaults[row.key]
        rows.push(row)
    }
    const extra = PER_WIDGET[id] || []
    for (let i = 0; i < extra.length; i++)
        rows.push(extra[i])
    return rows
}
