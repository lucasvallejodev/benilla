-- The game actions a pad button can hold instead of an action slot. `command` is the binding
-- command the Rust side runs: a stock 1.12 one (JUMP, TOGGLEAUTORUN, ...), one of this addon's
-- (Bindings.xml), or a native one with a leading "@" that the Rust side handles itself.

local P = BenillaPad
local A = {}
P.Actions = A

local function add(id, label, icon, command)
    A[id] = { id = id, label = label, icon = icon, command = command }
end

add("jump", "Jump", "Interface\\Icons\\Ability_Rogue_Sprint", "JUMP")
add("interact", "Interact / Loot", "Interface\\Cursor\\Pickup", "@INTERACT")
add("back", "Back / Stop casting", "Interface\\Buttons\\UI-GroupLoot-Pass-Up", "BENILLAPAD_BACK")
add("inspect", "Inspect", "Interface\\Icons\\INV_Misc_Spyglass_03", "BENILLAPAD_INSPECT")
add("targetenemy", "Target enemy", "Interface\\Cursor\\Attack", "BENILLAPAD_TARGETENEMY")
add("targetfriend", "Target friend", "Interface\\Icons\\Spell_Holy_FlashHeal", "BENILLAPAD_TARGETFRIEND")
add("targetself", "Target yourself", "Interface\\Icons\\Spell_Holy_PowerWordShield", "BENILLAPAD_TARGETSELF")
add("attack", "Attack", "Interface\\Icons\\INV_Sword_04", "BENILLAPAD_ATTACK")
add("autorun", "Auto run", P.ART .. "AutoRun", "TOGGLEAUTORUN")
add("sit", "Sit / Stand", "Interface\\Icons\\Spell_Nature_Sleep", "SITORSTAND")
add("wheel", "Window wheel", P.ART .. "Wheel", "BENILLAPAD_WHEEL")
add("consumables", "Consumables wheel", "Interface\\Icons\\INV_Potion_54", "BENILLAPAD_CONSUMABLES")
add("questitem", "Use quest item", "Interface\\Icons\\INV_Misc_Note_02", "BENILLAPAD_QUESTITEM")
add("botwheel", "Bot wheel", "Interface\\Icons\\Ability_Tracking", "BENILLAPAD_BOTWHEEL")
add("quickchat", "Quick Chat", "Interface\\Icons\\INV_Letter_15", "BENILLAPAD_CHAT")
add("menu", "Controller menu", P.ART .. "Menu", "BENILLAPAD_MENU")

-- The bodies of this addon's action rows (Bindings.xml).

function BenillaPad_Back()
    if SpellIsTargeting() then
        SpellStopTargeting()
    elseif CastingBarFrame and CastingBarFrame:IsVisible() then
        SpellStopCasting()
    else
        ClearTarget()
    end
end

-- 1.12 inspects players only, within CheckInteractDistance's inspect range (index 1).
function BenillaPad_Inspect()
    local why
    if not UnitExists("target") then
        why = "Inspect: no target"
    elseif not UnitIsPlayer("target") then
        why = "Inspect: only players can be inspected"
    elseif not CheckInteractDistance("target", 1) then
        why = "Inspect: too far away"
    end
    if why then
        UIErrorsFrame:AddMessage(why, 1.0, 0.1, 0.1, 1.0, 5)
        return
    end
    InspectUnit("target")
end

-- Select: the controller menu.
function BenillaPad_Menu()
    P.Menu.Toggle()
end
