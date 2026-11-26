-- ─────────────────────────────────────────────────────────────────
--   HYPRTK · Hyprland
--   Part of the Hyprtk desktop suite · github.com/hyprtk
-- ─────────────────────────────────────────────────────────────────

-- ----------------------------------------------------- 
-- Autostart & Environment
-- ----------------------------------------------------- 
require("environment")
require("autostart")

-- ----------------------------------------------------- 
-- Load configuration files
-- ----------------------------------------------------- 
require("input")
require("monitors")
require("window")
require("decoration")
require("layouts")
require("misc")
require("keybindings")
require("windowrules")
require("nvidia")

-- ----------------------------------------------------- 
-- Animation
-- ----------------------------------------------------- 
-- require("animations-low")
require("animations-high")
-- -----------------------------------------------------
-- Monitor mode fallback (PiP / PBP)
-- -----------------------------------------------------
-- A monitor that withdraws modes (picture-by-picture on an ultrawide is the
-- usual case) leaves Hyprland on a mode the panel no longer offers, and the
-- desktop stops fitting until the mode is picked by hand. hypr/scripts/
-- monitor-automode writes the closest valid mode into this file and reloads;
-- it is empty the rest of the time. Loaded last so it wins over monitors.lua,
-- and kept out of monitors.lua itself because the Displays panel and the user
-- both own that file.
-- require(), not dofile(): Hyprland's sandboxed Lua has no dofile. The cache
-- entry is cleared first because require() caches across reloads, which would
-- keep whatever the file held the first time it was loaded.
package.path = (os.getenv("XDG_CACHE_HOME") or (os.getenv("HOME") .. "/.cache")) .. "/hyprtk/?.lua;" .. package.path
package.loaded["monitor-automode"] = nil
pcall(require, "monitor-automode")
