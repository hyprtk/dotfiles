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

hl.window_rule({
    name = "windowrule-7",
    match = {
        class = "dev.hyprtk.theme_gui",
    },
    float = true,
    size = "1100 700",
})

-- hyprtk-menu settings window (floating)
hl.window_rule({
    name = "windowrule-settings",
    match = {
        title = "(^(hyprtk-menu settings)$)",
    },
    float = true,
    center = true,
    size = "360 400",
})

-- hyprtk-bar settings window (floating)
hl.window_rule({
    name = "windowrule-bar-settings",
    match = {
        title = "(^(hyprtk-bar settings)$)",
    },
    float = true,
    center = true,
    size = "640 540",
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

