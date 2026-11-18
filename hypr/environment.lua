-- ----------------------------------------------------- 
-- Environment Variables
-- ----------------------------------------------------- 

hl.env("WLR_NO_HARDWARE_CURSORS", "1")
hl.env("WLR_RENDERER_ALLOW_SOFTWARE", "1")
hl.env("XCURSOR_THEME", "Adwaita")
hl.env("XCURSOR_SIZE", "24")
hl.env("GTK_THEME", "Kripton-v40:dark")
hl.env("XDG_SESSION_TYPE", "wayland")
-- Preferred terminal for the session: hyprtk-bar's quick links, hyprtk-fm's
-- "Open terminal here", the editor's terminal action and anything else that
-- honours $TERMINAL resolve this to the suite's terminal. Alacritty stays
-- installed as the fallback (and because the gum menus tag their window with
-- `--class`, which hyprtk-term does not implement).
hl.env("TERMINAL", "hyprtk-term")

-- GUI apps (bar, launchers) need ~/.local/bin on PATH; the login session does
-- not add it, which made `command -v hyprtk-fm` fall back to Thunar.
local hypr_home = os.getenv("HOME")
if hypr_home then
    hl.env("PATH", hypr_home .. "/.local/bin:" .. (os.getenv("PATH") or ""))
end

-- Suite file manager: hyprtk-bar's quick links and tools honouring
-- $FILEMANAGER resolve this instead of the distro default (Thunar remains the
-- fallback in the Super+F bind).
hl.env("FILEMANAGER", "hyprtk-fm")
