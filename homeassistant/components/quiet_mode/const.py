"""Constants for the Quiet Mode integration."""

DOMAIN = "quiet_mode"
DEFAULT_VOLUME = 0.12

# Helper Entities
HELPER_VOLUME = "input_number.quiet_mode_volume"
HELPER_TARGET_SELECTOR = "input_select.quiet_mode_target"
HELPER_INCLUDE_SPOTIFY = "input_boolean.qm_include_spotify"

# Dropdown Options
OPTION_ALL = "All"
OPTION_LIVING_ROOM = "Living Room"
OPTION_KITCHEN = "Kitchen"
OPTION_BEDROOM = "Bedroom"
OPTION_LOUNGE_ROOM = "Lounge Room"

# Entity Mapping for Rooms
ROOM_ENTITY_MAPPING = {
    OPTION_LIVING_ROOM: "media_player.living_room",
    OPTION_KITCHEN: "media_player.kitchen",
    OPTION_BEDROOM: "media_player.bedroom",
    OPTION_LOUNGE_ROOM: "media_player.lounge_room",
}

# All media player entities for auto-pause feature
ALL_MEDIA_PLAYERS = [
    "media_player.lounge_room",
    "media_player.living_room",
    "media_player.kitchen",
    "media_player.bedroom",
]

ENTITY_SPOTIFY = "media_player.spotify"
