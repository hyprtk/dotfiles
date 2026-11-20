-- ----------------------------------------------------- 
-- Window rules
-- ----------------------------------------------------- 

hl.window_rule({
    name = "windowrule-1",
    match = {
        title = "(^(Microsoft-edge)$)",
    },
    float = false,
})

hl.window_rule({
    name = "windowrule-2",
    match = {
        title = "^(Brave-browser)$",
    },
    float = false,
    size = "600 400",
})

hl.window_rule({
    name = "windowrule-3",
    match = {
        title = "^(Chromium)$",
    },
    float = false,
})

hl.window_rule({
    name = "windowrule-4",
    match = {
        title = "^(pavucontrol)$",
    },
    float = false,
})

hl.window_rule({
    name = "windowrule-5",
    match = {
        title = "^(blueman-manager)$",
    },
    float = false,
})

-- Specific to launching floating terminal windows
hl.window_rule({
    name = "windowrule-6",
    match = {
        class = "floating",
    },
    float = true,
    size = "800 600",
})

-- gum menus: menu.sh re-execs rofi-free scripts in alacritty tagged
-- app-id/class "hyprtk-menu" (title "Hyprtk Menu") so power/wallpaper menus
-- float instead of tiling. Class covers Wayland-native app-ids; title covers
-- terminals that only set the title.
hl.window_rule({
    name = "windowrule-hyprtk-menu",
    match = {
        class = "hyprtk-menu",
    },
    float = true,
    center = true,
    size = "600 450",
})

hl.window_rule({
    name = "windowrule-hyprtk-menu-title",
    match = {
        title = "^(Hyprtk Menu)$",
    },
    float = true,
    center = true,
    size = "600 450",
})

-- Updates module: installupdates.sh relaunches itself in a terminal tagged
-- app-id/class "hyprtk-updates" (title "Hyprtk Updates") — float it instead of
-- tiling it full-screen. Two rules: class for Wayland-native app-ids, title for
-- terminals that only set the window title.
hl.window_rule({
    name = "windowrule-updates",
    match = {
        class = "hyprtk-updates",
    },
    float = true,
    center = true,
    size = "1000 650",
})

hl.window_rule({
    name = "windowrule-updates-title",
    match = {
        title = "^(Hyprtk Updates)$",
    },
    float = true,
    center = true,
    size = "1000 650",
})


-- hyprtk-calc: a utility window, not a document. Without this it tiles to the
-- whole work area and ignores the size it asks for. The class is the desktop
-- id it sets through setDesktopFileName.
hl.window_rule({
    name = "windowrule-hyprtk-calc",
    match = {
        class = "hyprtk-calc",
    },
    float = true,
    center = true,
    size = "480 740",
})

-- hyprtk-shot's launcher. The capture overlay shares the class but titles
-- itself "hyprtk-shot" and asks the compositor for fullscreen, so it is
-- deliberately not matched here.
hl.window_rule({
    name = "windowrule-hyprtk-shot",
    match = {
        class = "hyprtk-shot",
        title = "^(Screenshot)$",
    },
    float = true,
    center = true,
    size = "560 640",
})

-- hyprtk-rec: one window, and its title changes ("Recording") while it runs.
hl.window_rule({
    name = "windowrule-hyprtk-rec",
    match = {
        class = "hyprtk-rec",
    },
    float = true,
    center = true,
    size = "560 720",
})
