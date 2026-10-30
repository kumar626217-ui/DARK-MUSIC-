import os
from dotenv import load_dotenv

load_dotenv()

# Discord Bot Token & Prefix
TOKEN = os.getenv("DISCORD_TOKEN", "")
DEFAULT_PREFIX = os.getenv("DEFAULT_PREFIX", ">")

# Owner IDs (Parsed from comma separated string or list)
raw_owners = os.getenv("OWNER_IDS", "")
OWNER_IDS = [int(oid.strip()) for oid in raw_owners.split(",") if oid.strip().isdigit()]

# AI & Music API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "") or GEMINI_API_KEY
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "") or GOOGLE_API_KEY

# Gmail Gateway Configuration (Emergency Alerts & Member Messages)
GMAIL_USER = os.getenv("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
GMAIL_ALERT_RECEIVER = os.getenv("GMAIL_ALERT_RECEIVER", "") or GMAIL_USER

# Anti-Crack & Master Vault Security
VAULT_MASTER_PIN = os.getenv("VAULT_MASTER_PIN", "998877")  # 6-digit owner override PIN

# Theme Colors (Hex)
class Colors:
    RED = 0xED4245          # Security Alert / Danger
    GREEN = 0x57F287        # Success / Safe
    BLUE = 0x5865F2         # Info / Primary
    GOLD = 0xFEE75C         # Warning / Economy
    PURPLE = 0x9B59B6       # Premium / Royal
    DARK = 0x2B2D31         # Stealth Dark / Obsidian Style
    EMBED_BG = 0x202225     # Background dark
    # Aliases
    PRIMARY = BLUE
    SUCCESS = GREEN
    WARNING = GOLD
    DANGER = RED

# Module-level color aliases for convenience
COLOR_PRIMARY = Colors.BLUE
COLOR_SUCCESS = Colors.GREEN
COLOR_WARNING = Colors.GOLD
COLOR_DANGER = Colors.RED

# Bot Constants
VERSION = "3.5.0-FORTRESS-ULTRA"
BOT_NAME = "SPECTRE"

# Security Action Limits (Default Thresholds per 10-second rolling window)
DEFAULT_LIMITS = {
    "anti_ban": 0,           # 0 = strictly forbidden unless whitelisted
    "anti_kick": 0,          # 0 = strictly forbidden unless whitelisted
    "anti_channel_del": 1,   # Max channel deletions allowed
    "anti_channel_create": 2,# Max channel creations
    "anti_role_del": 1,      # Max role deletions allowed
    "anti_role_create": 2,   # Max role creations
    "anti_role_give": 0,     # 0 = strictly forbidden unless whitelisted
    "anti_bot_add": 0,       # 0 = strictly forbidden unless whitelisted
    "anti_webhook": 1,       # Max webhooks created/deleted
    "anti_prune": 0,         # Pruning blocked completely
    "anti_guild_edit": 1     # Max server edits
}

# Default Punishment: 'ban', 'kick', or 'quarantine' (strips dangerous roles)
DEFAULT_PUNISHMENT = "ban"

# Anti-Raid Defaults
DEFAULT_RAID_CONFIG = {
    "join_limit": 5,         # Joins allowed in window
    "join_window": 8,        # Window in seconds
    "min_account_age": 72,   # Minimum account age in hours (e.g. 3 days)
    "require_avatar": True,  # Flag/quarantine accounts with default avatars
    "verification_type": "captcha" # 'captcha', 'button', or 'disabled'
}
