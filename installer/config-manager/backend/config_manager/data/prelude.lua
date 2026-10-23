-- Recording `hl` prelude for hyprtk-config-manager.
--
-- Executes the real Hyprland Lua config (hyprland.lua + its require() chain)
-- with a stub `hl` table that records every call and the source file/line it
-- came from. Output on stdout is a single JSON document:
--
--   { "calls": [ { kind, name, value, file, line }, ... ], "error": null }
--
-- Unknown hl.* names are accepted through a metatable recorder so a new
-- Hyprland API call can never crash the probe.

local calls = {}

-- Keep stdout clean for JSON: configs that print go to stderr.
local real_print = print
print = function(...)
    local parts = {}
    for i = 1, select("#", ...) do parts[#parts + 1] = tostring(select(i, ...)) end
    io.stderr:write(table.concat(parts, "\t"), "\n")
end

local function quote(s)
    s = tostring(s)
    s = s:gsub("\\", "\\\\"):gsub('"', '\\"')
    s = s:gsub("\n", "\\n"):gsub("\r", "\\r"):gsub("\t", "\\t")
    s = s:gsub("[%z\1-\31]", function(c) return string.format("\\u%04x", c:byte()) end)
    return '"' .. s .. '"'
end

local function is_array(t)
    local n = 0
    for k in pairs(t) do
        if type(k) ~= "number" then return false end
        if k < 1 or k % 1 ~= 0 then return false end
        if k > n then n = k end
    end
    for i = 1, n do
        if t[i] == nil then return false end
    end
    return true, n
end

local encode

local function encode_value(v, seen)
    local tv = type(v)
    if tv == "nil" then return "null" end
    if tv == "boolean" then return v and "true" or "false" end
    if tv == "number" then
        if v ~= v or v == math.huge or v == -math.huge then return "null" end
        if v % 1 == 0 and math.abs(v) < 1e15 then return string.format("%d", v) end
        return string.format("%.12g", v)
    end
    if tv == "string" then return quote(v) end
    if tv ~= "table" then return quote(tostring(v)) end
    if seen[v] then return "null" end
    seen[v] = true

    local arr, n = is_array(v)
    local out = {}
    if arr then
        for i = 1, n do out[i] = encode_value(v[i], seen) end
        seen[v] = nil
        return "[" .. table.concat(out, ",") .. "]"
    end
    for k, val in pairs(v) do
        if type(k) == "string" then
            out[#out + 1] = quote(k) .. ":" .. encode_value(val, seen)
        end
    end
    seen[v] = nil
    return "{" .. table.concat(out, ",") .. "}"
end

encode = function(v)
    return encode_value(v, {})
end

-- Provenance: walk out of this prelude's own frames and report the first
-- config-file frame. `record` <- hl wrapper <- config chunk = level 3.
local function provenance()
    local fallback = { file = "", line = 0 }
    for level = 3, 12 do
        local info = debug.getinfo(level, "Sl")
        if not info then break end
        local src = info.source or ""
        if src:sub(1, 1) == "@" then
            local path = src:sub(2)
            if not path:find("prelude.lua", 1, true) then
                fallback = { file = path, line = info.currentline or 0 }
                if not path:find("/config_manager/", 1, true) then
                    return fallback
                end
            end
        end
    end
    return fallback
end

local function record(kind, name, value)
    local src = provenance()
    calls[#calls + 1] = {
        kind = kind,
        name = name,
        value = value,
        file = src.file,
        line = src.line,
    }
end

local function argn(...)
    return table.pack(...)
end

local hl = {}

hl.config = function(t)
    record("config", nil, t)
end

hl.curve = function(name, t)
    record("curve", name, t)
end

hl.animation = function(t)
    record("animation", nil, t)
end

hl.bind = function(keys, dispatcher, opts)
    record("bind", keys, { keys = keys, dispatcher = dispatcher, opts = opts })
end

hl.monitor = function(t)
    record("monitor", nil, t)
end

hl.window_rule = function(t)
    record("window_rule", nil, t)
end

hl.layer_rule = function(t)
    record("layer_rule", nil, t)
end

hl.workspace_rule = function(t)
    record("workspace_rule", nil, t)
end

hl.gesture = function(t)
    record("gesture", nil, t)
end

hl.env = function(k, v)
    record("env", k, { key = k, value = v })
end

local function exec_kind(kind)
    return function(cmd)
        record("exec", kind, { command = cmd })
    end
end

hl.exec = exec_kind("exec")
hl.exec_cmd = exec_kind("exec_cmd")
hl.exec_once = exec_kind("exec_once")

hl.on = function(event, fn)
    record("on", event, { event = event })
    if type(fn) == "function" then
        local ok, err = pcall(fn)
        if not ok then
            calls[#calls + 1] = {
                kind = "error",
                name = "on:" .. tostring(event),
                value = { message = tostring(err) },
                file = provenance().file,
                line = provenance().line,
            }
        end
    end
end

-- Any hl.* we don't know: a callable, indexable proxy that records on call.
-- Hyprland 0.55's API has namespaces (hl.dsp.window.close()), so a plain
-- function fallback would crash on the first field access.
local function make_proxy(path)
    local proxy = {}
    return setmetatable(proxy, {
        __index = function(_, key)
            return make_proxy(path .. "." .. tostring(key))
        end,
        __call = function(_, ...)
            local args = argn(...)
            record("other", path, args)
            local list = {}
            for i = 1, args.n do list[i] = args[i] end
            return { __dispatch = path, args = list }
        end,
        __tostring = function()
            return "hl." .. path
        end,
    })
end

setmetatable(hl, {
    __index = function(_, key)
        return make_proxy(tostring(key))
    end,
})

_G.hl = hl

local root = os.getenv("HYPR_CM_DIR")
local main = os.getenv("HYPR_CM_MAIN") or "hyprland.lua"
local err = nil

if root and root ~= "" then
    package.path = root .. "/?.lua;" .. root .. "/?/init.lua;" .. package.path
    local ok, e = pcall(dofile, root .. "/" .. main)
    if not ok then err = tostring(e) end
else
    err = "HYPR_CM_DIR not set"
end

io.stdout:write(encode({ calls = calls, error = err }))
io.stdout:write("\n")
io.stdout:flush()
