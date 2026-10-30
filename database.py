import aiosqlite
import json
import logging
import os
from typing import Optional, Dict, Any, List, Tuple

DB_PATH = os.path.join(os.path.dirname(__file__), "aegis_prime.db")
logger = logging.getLogger("AegisDB")

class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    async def initialize(self):
        """Initializes tables and indexes."""
        async with aiosqlite.connect(self.db_path) as db:
            # High-performance concurrent Write-Ahead Logging
            await db.execute("PRAGMA journal_mode=WAL;")
            await db.execute("PRAGMA synchronous=NORMAL;")

            # 1. Guild Security & Anti-Nuke Settings
            await db.execute("""
                CREATE TABLE IF NOT EXISTS security_settings (
                    guild_id INTEGER PRIMARY KEY,
                    antinuke_enabled INTEGER DEFAULT 1,
                    punishment TEXT DEFAULT 'ban',
                    log_channel_id INTEGER DEFAULT 0,
                    alert_channel_id INTEGER DEFAULT 0,
                    quarantine_role_id INTEGER DEFAULT 0,
                    panic_mode INTEGER DEFAULT 0,
                    limits_json TEXT DEFAULT '{}'
                )
            """)

            # 2. Whitelist Table (Multi-Tier Trust)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS whitelist (
                    guild_id INTEGER,
                    user_id INTEGER,
                    category TEXT,
                    added_by INTEGER,
                    PRIMARY KEY (guild_id, user_id, category)
                )
            """)

            # Nightmode Defense Tables
            await db.execute("""
                CREATE TABLE IF NOT EXISTS nightmode_settings (
                    guild_id INTEGER PRIMARY KEY,
                    enabled INTEGER DEFAULT 0,
                    activated_at TEXT,
                    activated_by INTEGER
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS nightmode_role_whitelist (
                    guild_id INTEGER,
                    role_id INTEGER,
                    added_by INTEGER,
                    PRIMARY KEY (guild_id, role_id)
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS nightmode_backups (
                    guild_id INTEGER,
                    role_id INTEGER,
                    permissions_value INTEGER,
                    PRIMARY KEY (guild_id, role_id)
                )
            """)

            # 3. Anti-Raid & Verification
            await db.execute("""
                CREATE TABLE IF NOT EXISTS antiraid_settings (
                    guild_id INTEGER PRIMARY KEY,
                    antiraid_enabled INTEGER DEFAULT 1,
                    join_limit INTEGER DEFAULT 5,
                    join_window INTEGER DEFAULT 8,
                    min_account_age_hours INTEGER DEFAULT 72,
                    require_avatar INTEGER DEFAULT 1,
                    verification_enabled INTEGER DEFAULT 0,
                    verification_channel_id INTEGER DEFAULT 0,
                    verified_role_id INTEGER DEFAULT 0,
                    verification_type TEXT DEFAULT 'captcha'
                )
            """)

            # 4. Automod Settings
            await db.execute("""
                CREATE TABLE IF NOT EXISTS automod_settings (
                    guild_id INTEGER PRIMARY KEY,
                    antispam_enabled INTEGER DEFAULT 1,
                    antilink_enabled INTEGER DEFAULT 0,
                    antiinvite_enabled INTEGER DEFAULT 1,
                    antimassmention_enabled INTEGER DEFAULT 1,
                    max_mentions INTEGER DEFAULT 5,
                    antighostping_enabled INTEGER DEFAULT 1,
                    antizalgo_enabled INTEGER DEFAULT 0,
                    automod_log_channel_id INTEGER DEFAULT 0,
                    antieveryone_enabled INTEGER DEFAULT 1,
                    everyone_timeout_minutes INTEGER DEFAULT 60
                )
            """)

            # Migrations for existing DBs
            try:
                await db.execute("ALTER TABLE automod_settings ADD COLUMN antieveryone_enabled INTEGER DEFAULT 1")
            except Exception:
                pass
            try:
                await db.execute("ALTER TABLE automod_settings ADD COLUMN everyone_timeout_minutes INTEGER DEFAULT 60")
            except Exception:
                pass
            try:
                await db.execute("ALTER TABLE automod_settings ADD COLUMN anticaps_enabled INTEGER DEFAULT 1")
            except Exception:
                pass
            try:
                await db.execute("ALTER TABLE automod_settings ADD COLUMN caps_percentage INTEGER DEFAULT 70")
            except Exception:
                pass
            try:
                await db.execute("ALTER TABLE automod_settings ADD COLUMN progressive_strikes_enabled INTEGER DEFAULT 1")
            except Exception:
                pass
            try:
                await db.execute("ALTER TABLE automod_settings ADD COLUMN zero_bypass_enabled INTEGER DEFAULT 0")
            except Exception:
                pass

            # 5. Server Backups
            await db.execute("""
                CREATE TABLE IF NOT EXISTS backups (
                    backup_id TEXT PRIMARY KEY,
                    guild_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    name TEXT,
                    data_json TEXT
                )
            """)

            # 6. Economy
            await db.execute("""
                CREATE TABLE IF NOT EXISTS economy (
                    guild_id INTEGER,
                    user_id INTEGER,
                    wallet INTEGER DEFAULT 1000,
                    bank INTEGER DEFAULT 0,
                    last_daily TEXT,
                    last_work TEXT,
                    last_crime TEXT,
                    last_rob TEXT,
                    PRIMARY KEY (guild_id, user_id)
                )
            """)

            # 7. Leveling / XP
            await db.execute("""
                CREATE TABLE IF NOT EXISTS leveling (
                    guild_id INTEGER,
                    user_id INTEGER,
                    xp INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 0,
                    last_message TEXT,
                    PRIMARY KEY (guild_id, user_id)
                )
            """)

            # 8. Warnings / Moderation Logs
            await db.execute("""
                CREATE TABLE IF NOT EXISTS warnings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER,
                    user_id INTEGER,
                    moderator_id INTEGER,
                    reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 9. Tickets
            await db.execute("""
                CREATE TABLE IF NOT EXISTS ticket_settings (
                    guild_id INTEGER PRIMARY KEY,
                    category_id INTEGER DEFAULT 0,
                    log_channel_id INTEGER DEFAULT 0,
                    support_role_id INTEGER DEFAULT 0,
                    panel_channel_id INTEGER DEFAULT 0,
                    ticket_count INTEGER DEFAULT 0
                )
            """)

            # 10. Giveaways
            await db.execute("""
                CREATE TABLE IF NOT EXISTS giveaways (
                    message_id INTEGER PRIMARY KEY,
                    channel_id INTEGER,
                    guild_id INTEGER,
                    prize TEXT,
                    winners_count INTEGER,
                    ends_at REAL,
                    ended INTEGER DEFAULT 0,
                    host_id INTEGER
                )
            """)

            # 11. Premium Subscriptions
            await db.execute("""
                CREATE TABLE IF NOT EXISTS premium (
                    guild_id INTEGER PRIMARY KEY,
                    tier TEXT DEFAULT 'free',
                    expires_at REAL DEFAULT 0,
                    activated_by INTEGER DEFAULT 0
                )
            """)

            # 12. Server Tour (Owner Exclusive)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS server_tour (
                    guild_id INTEGER PRIMARY KEY,
                    stops_json TEXT DEFAULT '[]',
                    configured_by INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 13. AI Assistant Settings
            await db.execute("""
                CREATE TABLE IF NOT EXISTS ai_settings (
                    guild_id INTEGER PRIMARY KEY,
                    ai_channel_id INTEGER DEFAULT 0,
                    model TEXT DEFAULT 'gemini-1.5-flash',
                    system_instruction TEXT DEFAULT 'You are Aegis AI, the intelligent sentinel and assistant of this Discord server.'
                )
            """)

            # 14. Server Vault & Anti-Crack Protection
            await db.execute("""
                CREATE TABLE IF NOT EXISTS server_vault (
                    guild_id INTEGER PRIMARY KEY,
                    is_locked INTEGER DEFAULT 0,
                    master_pin TEXT DEFAULT '',
                    email_alerts INTEGER DEFAULT 1,
                    last_unlocked TIMESTAMP
                )
            """)

            # 15. Honeypot Deception Traps
            await db.execute("""
                CREATE TABLE IF NOT EXISTS honeypots (
                    guild_id INTEGER,
                    target_id INTEGER,
                    name TEXT,
                    type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (guild_id, target_id)
                )
            """)

            # 16. Server Blackbox Forensic Flight Recorder
            await db.execute("""
                CREATE TABLE IF NOT EXISTS blackbox_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER,
                    event_type TEXT,
                    actor_id INTEGER,
                    details_json TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 17. Invites & Analytics Tracker
            await db.execute("""
                CREATE TABLE IF NOT EXISTS invites_tracker (
                    guild_id INTEGER,
                    inviter_id INTEGER,
                    joins INTEGER DEFAULT 0,
                    leaves INTEGER DEFAULT 0,
                    fake INTEGER DEFAULT 0,
                    PRIMARY KEY (guild_id, inviter_id)
                )
            """)

            # 18. Gmail Gateway Configuration
            await db.execute("""
                CREATE TABLE IF NOT EXISTS gmail_settings (
                    guild_id INTEGER PRIMARY KEY,
                    receiver_email TEXT DEFAULT '',
                    alerts_enabled INTEGER DEFAULT 1,
                    dms_forwarded INTEGER DEFAULT 1
                )
            """)

            # 19. RPG Hero Profiles
            await db.execute("""
                CREATE TABLE IF NOT EXISTS rpg_profiles (
                    guild_id INTEGER,
                    user_id INTEGER,
                    level INTEGER DEFAULT 1,
                    xp INTEGER DEFAULT 0,
                    hp INTEGER DEFAULT 100,
                    max_hp INTEGER DEFAULT 100,
                    mana INTEGER DEFAULT 50,
                    max_mana INTEGER DEFAULT 50,
                    attack INTEGER DEFAULT 15,
                    defense INTEGER DEFAULT 10,
                    weapon TEXT DEFAULT 'Rusted Dagger',
                    armor TEXT DEFAULT 'Leather Tunic',
                    pickaxe TEXT DEFAULT 'Wooden Pickaxe',
                    rod TEXT DEFAULT 'Bamboo Rod',
                    kills INTEGER DEFAULT 0,
                    dungeons_cleared INTEGER DEFAULT 0,
                    PRIMARY KEY (guild_id, user_id)
                )
            """)

            # 20. RPG Inventory
            await db.execute("""
                CREATE TABLE IF NOT EXISTS rpg_inventory (
                    guild_id INTEGER,
                    user_id INTEGER,
                    item_name TEXT,
                    item_type TEXT,
                    quantity INTEGER DEFAULT 1,
                    rarity TEXT DEFAULT 'Common',
                    PRIMARY KEY (guild_id, user_id, item_name)
                )
            """)

            # 21. RPG Pets
            await db.execute("""
                CREATE TABLE IF NOT EXISTS rpg_pets (
                    guild_id INTEGER,
                    user_id INTEGER,
                    pet_name TEXT,
                    pet_type TEXT,
                    pet_level INTEGER DEFAULT 1,
                    hunger INTEGER DEFAULT 100,
                    happiness INTEGER DEFAULT 100,
                    PRIMARY KEY (guild_id, user_id)
                )
            """)

            # 22. World Boss Raid
            await db.execute("""
                CREATE TABLE IF NOT EXISTS world_boss (
                    guild_id INTEGER PRIMARY KEY,
                    boss_name TEXT DEFAULT 'Void Sovereign Chronos',
                    current_hp INTEGER DEFAULT 5000,
                    max_hp INTEGER DEFAULT 5000,
                    reward_pool INTEGER DEFAULT 25000,
                    is_alive INTEGER DEFAULT 1
                )
            """)

            # 23. Member Welcome & Onboarding Settings
            await db.execute("""
                CREATE TABLE IF NOT EXISTS welcome_settings (
                    guild_id INTEGER PRIMARY KEY,
                    enabled INTEGER DEFAULT 1,
                    channel_id INTEGER DEFAULT 0,
                    custom_message TEXT DEFAULT '',
                    embed_enabled INTEGER DEFAULT 1
                )
            """)

            # 24. Global Dynamic Config (YouTube/Google API Keys & Master Settings)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS global_config (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

            await db.commit()
            logger.info("Aegis Prime Database initialized successfully.")

    # ================= Security Settings =================
    async def get_security_settings(self, guild_id: int) -> Dict[str, Any]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM security_settings WHERE guild_id = ?", (guild_id,))
            row = await cursor.fetchone()
            if row:
                data = dict(row)
                data["limits"] = json.loads(data.get("limits_json") or "{}")
                return data
            else:
                # Default insert
                await db.execute(
                    "INSERT INTO security_settings (guild_id) VALUES (?)",
                    (guild_id,)
                )
                await db.commit()
                return {
                    "guild_id": guild_id,
                    "antinuke_enabled": 1,
                    "punishment": "ban",
                    "log_channel_id": 0,
                    "alert_channel_id": 0,
                    "quarantine_role_id": 0,
                    "panic_mode": 0,
                    "limits": {}
                }

    async def update_security_settings(self, guild_id: int, **kwargs):
        if "limits" in kwargs:
            kwargs["limits_json"] = json.dumps(kwargs.pop("limits"))
        keys = list(kwargs.keys())
        values = list(kwargs.values())
        set_clause = ", ".join(f"{k} = ?" for k in keys)
        values.append(guild_id)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(f"UPDATE security_settings SET {set_clause} WHERE guild_id = ?", values)
            await db.commit()

    # ================= Whitelist =================
    async def is_whitelisted(self, guild_id: int, user_id: int, category: str = "all") -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT 1 FROM whitelist WHERE guild_id = ? AND user_id = ? AND category IN ('owner', 'extra_owner', 'all', ?)",
                (guild_id, user_id, category)
            )
            return bool(await cursor.fetchone())

    async def add_whitelist(self, guild_id: int, user_id: int, category: str, added_by: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO whitelist (guild_id, user_id, category, added_by) VALUES (?, ?, ?, ?)",
                (guild_id, user_id, category, added_by)
            )
            await db.commit()

    async def remove_whitelist(self, guild_id: int, user_id: int, category: Optional[str] = None):
        async with aiosqlite.connect(self.db_path) as db:
            if category:
                await db.execute(
                    "DELETE FROM whitelist WHERE guild_id = ? AND user_id = ? AND category = ?",
                    (guild_id, user_id, category)
                )
            else:
                await db.execute(
                    "DELETE FROM whitelist WHERE guild_id = ? AND user_id = ?",
                    (guild_id, user_id)
                )
            await db.commit()

    async def get_whitelist(self, guild_id: int) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM whitelist WHERE guild_id = ?", (guild_id,))
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_whitelisted_bots(self, guild_id: int) -> List[int]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT user_id FROM whitelist WHERE guild_id = ? AND category IN ('anti_bot_add', 'bot')",
                (guild_id,)
            )
            rows = await cursor.fetchall()
            return [r[0] for r in rows]

    async def is_bot_whitelisted(self, guild_id: int, bot_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT 1 FROM whitelist WHERE guild_id = ? AND user_id = ? AND category IN ('anti_bot_add', 'bot')",
                (guild_id, bot_id)
            )
            return bool(await cursor.fetchone())

    # ================= Anti-Raid & Verification =================
    async def get_antiraid_settings(self, guild_id: int) -> Dict[str, Any]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM antiraid_settings WHERE guild_id = ?", (guild_id,))
            row = await cursor.fetchone()
            if row:
                return dict(row)
            await db.execute("INSERT INTO antiraid_settings (guild_id) VALUES (?)", (guild_id,))
            await db.commit()
            return {
                "guild_id": guild_id,
                "antiraid_enabled": 1,
                "join_limit": 5,
                "join_window": 8,
                "min_account_age_hours": 72,
                "require_avatar": 1,
                "verification_enabled": 0,
                "verification_channel_id": 0,
                "verified_role_id": 0,
                "verification_type": "captcha"
            }

    async def update_antiraid_settings(self, guild_id: int, **kwargs):
        keys = list(kwargs.keys())
        values = list(kwargs.values())
        set_clause = ", ".join(f"{k} = ?" for k in keys)
        values.append(guild_id)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(f"UPDATE antiraid_settings SET {set_clause} WHERE guild_id = ?", values)
            await db.commit()

    # ================= Automod Settings =================
    async def get_automod_settings(self, guild_id: int) -> Dict[str, Any]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM automod_settings WHERE guild_id = ?", (guild_id,))
            row = await cursor.fetchone()
            if row:
                res = dict(row)
                if "antieveryone_enabled" not in res:
                    res["antieveryone_enabled"] = 1
                if "everyone_timeout_minutes" not in res:
                    res["everyone_timeout_minutes"] = 60
                if "anticaps_enabled" not in res:
                    res["anticaps_enabled"] = 1
                if "caps_percentage" not in res:
                    res["caps_percentage"] = 70
                if "progressive_strikes_enabled" not in res:
                    res["progressive_strikes_enabled"] = 1
                if "zero_bypass_enabled" not in res:
                    res["zero_bypass_enabled"] = 0
                return res
            await db.execute("INSERT INTO automod_settings (guild_id) VALUES (?)", (guild_id,))
            await db.commit()
            return {
                "guild_id": guild_id,
                "antispam_enabled": 1,
                "antilink_enabled": 0,
                "antiinvite_enabled": 1,
                "antimassmention_enabled": 1,
                "max_mentions": 5,
                "antighostping_enabled": 1,
                "antizalgo_enabled": 0,
                "automod_log_channel_id": 0,
                "antieveryone_enabled": 1,
                "everyone_timeout_minutes": 60,
                "anticaps_enabled": 1,
                "caps_percentage": 70,
                "progressive_strikes_enabled": 1,
                "zero_bypass_enabled": 0
            }

    async def update_automod_settings(self, guild_id: int, **kwargs):
        keys = list(kwargs.keys())
        values = list(kwargs.values())
        set_clause = ", ".join(f"{k} = ?" for k in keys)
        values.append(guild_id)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(f"UPDATE automod_settings SET {set_clause} WHERE guild_id = ?", values)
            await db.commit()

    # ================= Server Backups =================
    async def save_backup(self, backup_id: str, guild_id: int, name: str, data: Dict[str, Any]):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO backups (backup_id, guild_id, name, data_json) VALUES (?, ?, ?, ?)",
                (backup_id, guild_id, name, json.dumps(data))
            )
            await db.commit()

    async def get_backup(self, backup_id: str) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM backups WHERE backup_id = ?", (backup_id,))
            row = await cursor.fetchone()
            if row:
                res = dict(row)
                res["data"] = json.loads(res["data_json"])
                return res
            return None

    async def list_backups(self, guild_id: int) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT backup_id, created_at, name FROM backups WHERE guild_id = ? ORDER BY created_at DESC", (guild_id,))
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    # ================= Economy =================
    async def get_economy(self, guild_id: int, user_id: int) -> Dict[str, Any]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM economy WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
            row = await cursor.fetchone()
            if row:
                return dict(row)
            await db.execute("INSERT INTO economy (guild_id, user_id, wallet, bank) VALUES (?, ?, 1000, 0)", (guild_id, user_id))
            await db.commit()
            return {
                "guild_id": guild_id,
                "user_id": user_id,
                "wallet": 1000,
                "bank": 0,
                "last_daily": None,
                "last_work": None,
                "last_crime": None,
                "last_rob": None
            }

    async def update_economy(self, guild_id: int, user_id: int, **kwargs):
        # Ensure user exists in economy table first
        await self.get_economy(guild_id, user_id)

        # Handle wallet_delta or wallet_change
        if "wallet_delta" in kwargs or "wallet_change" in kwargs:
            delta = kwargs.pop("wallet_delta", None)
            if delta is None:
                delta = kwargs.pop("wallet_change")
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "UPDATE economy SET wallet = MAX(0, wallet + ?) WHERE guild_id = ? AND user_id = ?",
                    (delta, guild_id, user_id)
                )
                await db.commit()

        # Handle bank_delta or bank_change
        if "bank_delta" in kwargs or "bank_change" in kwargs:
            delta = kwargs.pop("bank_delta", None)
            if delta is None:
                delta = kwargs.pop("bank_change")
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "UPDATE economy SET bank = MAX(0, bank + ?) WHERE guild_id = ? AND user_id = ?",
                    (delta, guild_id, user_id)
                )
                await db.commit()

        if kwargs:
            keys = list(kwargs.keys())
            values = list(kwargs.values())
            set_clause = ", ".join(f"{k} = ?" for k in keys)
            values.extend([guild_id, user_id])
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(f"UPDATE economy SET {set_clause} WHERE guild_id = ? AND user_id = ?", values)
                await db.commit()

    async def get_economy_leaderboard(self, guild_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT user_id, (wallet + bank) as net_worth, wallet, bank FROM economy WHERE guild_id = ? ORDER BY net_worth DESC LIMIT ?",
                (guild_id, limit)
            )
            return [dict(r) for r in await cursor.fetchall()]

    # ================= Leveling =================
    async def get_leveling(self, guild_id: int, user_id: int) -> Dict[str, Any]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM leveling WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
            row = await cursor.fetchone()
            if row:
                return dict(row)
            await db.execute("INSERT INTO leveling (guild_id, user_id, xp, level) VALUES (?, ?, 0, 0)", (guild_id, user_id))
            await db.commit()
            return {"guild_id": guild_id, "user_id": user_id, "xp": 0, "level": 0, "last_message": None}

    async def update_leveling(self, guild_id: int, user_id: int, **kwargs):
        keys = list(kwargs.keys())
        values = list(kwargs.values())
        set_clause = ", ".join(f"{k} = ?" for k in keys)
        values.extend([guild_id, user_id])
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(f"UPDATE leveling SET {set_clause} WHERE guild_id = ? AND user_id = ?", values)
            await db.commit()

    async def get_level_leaderboard(self, guild_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT user_id, xp, level FROM leveling WHERE guild_id = ? ORDER BY xp DESC LIMIT ?",
                (guild_id, limit)
            )
            return [dict(r) for r in await cursor.fetchall()]

    # ================= Warnings =================
    async def add_warning(self, guild_id: int, user_id: int, moderator_id: int, reason: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO warnings (guild_id, user_id, moderator_id, reason) VALUES (?, ?, ?, ?)",
                (guild_id, user_id, moderator_id, reason)
            )
            await db.commit()

    async def get_warnings(self, guild_id: int, user_id: int) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM warnings WHERE guild_id = ? AND user_id = ? ORDER BY created_at DESC",
                (guild_id, user_id)
            )
            return [dict(r) for r in await cursor.fetchall()]

    async def clear_warnings(self, guild_id: int, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM warnings WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
            await db.commit()

    # ================= Premium =================
    async def get_premium(self, guild_id: int) -> Dict[str, Any]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM premium WHERE guild_id = ?", (guild_id,))
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return {"guild_id": guild_id, "tier": "free", "expires_at": 0, "activated_by": 0}

    async def set_premium(self, guild_id: int, tier: str, expires_at: float, activated_by: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO premium (guild_id, tier, expires_at, activated_by)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                    tier=excluded.tier,
                    expires_at=excluded.expires_at,
                    activated_by=excluded.activated_by
            """, (guild_id, tier, expires_at, activated_by))
            await db.commit()

    async def is_premium(self, guild_id: int) -> bool:
        data = await self.get_premium(guild_id)
        if data["tier"] in ["gold", "diamond", "infinity"]:
            if data["expires_at"] == 0:
                return True
            import time
            return data["expires_at"] > time.time()
        return False

    # ================= Server Tour =================
    async def get_tour(self, guild_id: int) -> Dict[str, Any]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM server_tour WHERE guild_id = ?", (guild_id,))
            row = await cursor.fetchone()
            if row:
                res = dict(row)
                res["stops"] = json.loads(res.get("stops_json") or "[]")
                return res
            return {"guild_id": guild_id, "stops": [], "stops_json": "[]", "configured_by": 0}

    async def set_tour(self, guild_id: int, stops: list, configured_by: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO server_tour (guild_id, stops_json, configured_by)
                VALUES (?, ?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                    stops_json=excluded.stops_json,
                    configured_by=excluded.configured_by
            """, (guild_id, json.dumps(stops), configured_by))
            await db.commit()

    # ================= AI Assistant =================
    async def get_ai_settings(self, guild_id: int) -> Dict[str, Any]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM ai_settings WHERE guild_id = ?", (guild_id,))
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return {
                "guild_id": guild_id,
                "ai_channel_id": 0,
                "model": "gemini-1.5-flash",
                "system_instruction": "You are Aegis AI, the intelligent sentinel and assistant of this Discord server."
            }

    async def update_ai_settings(self, guild_id: int, **kwargs):
        data = await self.get_ai_settings(guild_id)
        data.update(kwargs)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO ai_settings (guild_id, ai_channel_id, model, system_instruction)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                    ai_channel_id=excluded.ai_channel_id,
                    model=excluded.model,
                    system_instruction=excluded.system_instruction
            """, (guild_id, data["ai_channel_id"], data["model"], data["system_instruction"]))
            await db.commit()

    # ================= Server Vault & Anti-Crack =================
    async def get_vault(self, guild_id: int) -> Dict[str, Any]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM server_vault WHERE guild_id = ?", (guild_id,))
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return {"guild_id": guild_id, "is_locked": 0, "master_pin": "", "email_alerts": 1, "last_unlocked": None}

    async def update_vault(self, guild_id: int, **kwargs):
        data = await self.get_vault(guild_id)
        data.update(kwargs)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO server_vault (guild_id, is_locked, master_pin, email_alerts, last_unlocked)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                    is_locked=excluded.is_locked,
                    master_pin=excluded.master_pin,
                    email_alerts=excluded.email_alerts,
                    last_unlocked=excluded.last_unlocked
            """, (guild_id, data["is_locked"], data["master_pin"], data["email_alerts"], data["last_unlocked"]))
            await db.commit()

    # ================= Honeypots =================
    async def add_honeypot(self, guild_id: int, target_id: int, name: str, htype: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO honeypots (guild_id, target_id, name, type)
                VALUES (?, ?, ?, ?)
            """, (guild_id, target_id, name, htype))
            await db.commit()

    async def get_honeypots(self, guild_id: int) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM honeypots WHERE guild_id = ?", (guild_id,))
            return [dict(r) for r in await cursor.fetchall()]

    async def is_honeypot(self, guild_id: int, target_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT 1 FROM honeypots WHERE guild_id = ? AND target_id = ?", (guild_id, target_id))
            return (await cursor.fetchone()) is not None

    async def delete_honeypot(self, guild_id: int, target_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM honeypots WHERE guild_id = ? AND target_id = ?", (guild_id, target_id))
            await db.commit()

    async def clear_honeypots(self, guild_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM honeypots WHERE guild_id = ?", (guild_id,))
            await db.commit()

    # ================= Blackbox Forensics =================
    async def log_blackbox(self, guild_id: int, event_type: str, actor_id: int, details: dict):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO blackbox_logs (guild_id, event_type, actor_id, details_json)
                VALUES (?, ?, ?, ?)
            """, (guild_id, event_type, actor_id, json.dumps(details)))
            await db.commit()

    async def get_blackbox_logs(self, guild_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM blackbox_logs WHERE guild_id = ? ORDER BY id DESC LIMIT ?",
                (guild_id, limit)
            )
            rows = await cursor.fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d["details"] = json.loads(d.get("details_json") or "{}")
                result.append(d)
            return result

    async def clear_blackbox(self, guild_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM blackbox_logs WHERE guild_id = ?", (guild_id,))
            await db.commit()

    # ================= Tracker & Invites =================
    async def record_invite_join(self, guild_id: int, inviter_id: int, is_fake: bool = False):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO invites_tracker (guild_id, inviter_id, joins, leaves, fake)
                VALUES (?, ?, 1, 0, ?)
                ON CONFLICT(guild_id, inviter_id) DO UPDATE SET
                    joins = joins + 1,
                    fake = fake + excluded.fake
            """, (guild_id, inviter_id, 1 if is_fake else 0))
            await db.commit()

    async def record_invite_leave(self, guild_id: int, inviter_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO invites_tracker (guild_id, inviter_id, joins, leaves, fake)
                VALUES (?, ?, 0, 1, 0)
                ON CONFLICT(guild_id, inviter_id) DO UPDATE SET
                    leaves = leaves + 1
            """, (guild_id, inviter_id))
            await db.commit()

    async def get_invites(self, guild_id: int, inviter_id: int) -> Dict[str, Any]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM invites_tracker WHERE guild_id = ? AND inviter_id = ?", (guild_id, inviter_id))
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return {"guild_id": guild_id, "inviter_id": inviter_id, "joins": 0, "leaves": 0, "fake": 0}

    async def get_top_inviters(self, guild_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT inviter_id, joins, leaves, fake, (joins - leaves) as net_joins FROM invites_tracker WHERE guild_id = ? ORDER BY net_joins DESC LIMIT ?",
                (guild_id, limit)
            )
            return [dict(r) for r in await cursor.fetchall()]

    # ================= Gmail Gateway Settings =================
    async def get_gmail_settings(self, guild_id: int) -> Dict[str, Any]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM gmail_settings WHERE guild_id = ?", (guild_id,))
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return {"guild_id": guild_id, "receiver_email": "", "alerts_enabled": 1, "dms_forwarded": 1}

    async def update_gmail_settings(self, guild_id: int, **kwargs):
        data = await self.get_gmail_settings(guild_id)
        data.update(kwargs)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO gmail_settings (guild_id, receiver_email, alerts_enabled, dms_forwarded)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                    receiver_email=excluded.receiver_email,
                    alerts_enabled=excluded.alerts_enabled,
                    dms_forwarded=excluded.dms_forwarded
            """, (guild_id, data["receiver_email"], data["alerts_enabled"], data["dms_forwarded"]))
            await db.commit()

    # ================= RPG System Database Layer =================
    async def get_rpg_profile(self, guild_id: int, user_id: int) -> Dict[str, Any]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM rpg_profiles WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
            row = await cursor.fetchone()
            if row:
                return dict(row)
            # Create default profile
            await db.execute("""
                INSERT INTO rpg_profiles (guild_id, user_id) VALUES (?, ?)
            """, (guild_id, user_id))
            await db.commit()
            return {
                "guild_id": guild_id, "user_id": user_id, "level": 1, "xp": 0,
                "hp": 100, "max_hp": 100, "mana": 50, "max_mana": 50,
                "attack": 15, "defense": 10, "weapon": "Rusted Dagger",
                "armor": "Leather Tunic", "pickaxe": "Wooden Pickaxe",
                "rod": "Bamboo Rod", "kills": 0, "dungeons_cleared": 0
            }

    async def update_rpg_profile(self, guild_id: int, user_id: int, **kwargs):
        curr = await self.get_rpg_profile(guild_id, user_id)
        curr.update(kwargs)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE rpg_profiles SET
                    level = ?, xp = ?, hp = ?, max_hp = ?, mana = ?, max_mana = ?,
                    attack = ?, defense = ?, weapon = ?, armor = ?, pickaxe = ?,
                    rod = ?, kills = ?, dungeons_cleared = ?
                WHERE guild_id = ? AND user_id = ?
            """, (
                curr["level"], curr["xp"], curr["hp"], curr["max_hp"], curr["mana"], curr["max_mana"],
                curr["attack"], curr["defense"], curr["weapon"], curr["armor"], curr["pickaxe"],
                curr["rod"], curr["kills"], curr["dungeons_cleared"], guild_id, user_id
            ))
            await db.commit()

    async def get_rpg_inventory(self, guild_id: int, user_id: int) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM rpg_inventory WHERE guild_id = ? AND user_id = ? AND quantity > 0 ORDER BY rarity DESC, item_name ASC",
                (guild_id, user_id)
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def add_rpg_item(self, guild_id: int, user_id: int, item_name: str, item_type: str = "Resource", quantity: int = 1, rarity: str = "Common"):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO rpg_inventory (guild_id, user_id, item_name, item_type, quantity, rarity)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(guild_id, user_id, item_name) DO UPDATE SET
                    quantity = quantity + excluded.quantity
            """, (guild_id, user_id, item_name, item_type, quantity, rarity))
            await db.commit()

    async def remove_rpg_item(self, guild_id: int, user_id: int, item_name: str, quantity: int = 1) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT quantity FROM rpg_inventory WHERE guild_id = ? AND user_id = ? AND item_name = ?", (guild_id, user_id, item_name))
            row = await cursor.fetchone()
            if not row or row["quantity"] < quantity:
                return False
            new_qty = row["quantity"] - quantity
            if new_qty <= 0:
                await db.execute("DELETE FROM rpg_inventory WHERE guild_id = ? AND user_id = ? AND item_name = ?", (guild_id, user_id, item_name))
            else:
                await db.execute("UPDATE rpg_inventory SET quantity = ? WHERE guild_id = ? AND user_id = ? AND item_name = ?", (new_qty, guild_id, user_id, item_name))
            await db.commit()
            return True

    async def get_rpg_pet(self, guild_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM rpg_pets WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def set_rpg_pet(self, guild_id: int, user_id: int, pet_name: str, pet_type: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO rpg_pets (guild_id, user_id, pet_name, pet_type, pet_level, hunger, happiness)
                VALUES (?, ?, ?, ?, 1, 100, 100)
                ON CONFLICT(guild_id, user_id) DO UPDATE SET
                    pet_name = excluded.pet_name,
                    pet_type = excluded.pet_type,
                    pet_level = 1,
                    hunger = 100,
                    happiness = 100
            """, (guild_id, user_id, pet_name, pet_type))
            await db.commit()

    async def update_rpg_pet(self, guild_id: int, user_id: int, **kwargs):
        pet = await self.get_rpg_pet(guild_id, user_id)
        if not pet:
            return
        pet.update(kwargs)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE rpg_pets SET pet_level = ?, hunger = ?, happiness = ?
                WHERE guild_id = ? AND user_id = ?
            """, (pet["pet_level"], pet["hunger"], pet["happiness"], guild_id, user_id))
            await db.commit()

    async def get_world_boss(self, guild_id: int) -> Dict[str, Any]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM world_boss WHERE guild_id = ?", (guild_id,))
            row = await cursor.fetchone()
            if row:
                return dict(row)
            await db.execute("""
                INSERT INTO world_boss (guild_id, boss_name, current_hp, max_hp, reward_pool, is_alive)
                VALUES (?, 'Void Sovereign Chronos', 5000, 5000, 25000, 1)
            """, (guild_id,))
            await db.commit()
            return {
                "guild_id": guild_id, "boss_name": "Void Sovereign Chronos",
                "current_hp": 5000, "max_hp": 5000, "reward_pool": 25000, "is_alive": 1
            }

    async def damage_world_boss(self, guild_id: int, damage: int) -> Tuple[int, int, bool]:
        """Damages boss and returns (current_hp, max_hp, was_killed)."""
        boss = await self.get_world_boss(guild_id)
        new_hp = max(0, boss["current_hp"] - damage)
        killed = (new_hp == 0 and boss["is_alive"] == 1)
        async with aiosqlite.connect(self.db_path) as db:
            if killed:
                await db.execute("""
                    UPDATE world_boss SET current_hp = 0, is_alive = 0 WHERE guild_id = ?
                """, (guild_id,))
            else:
                await db.execute("""
                    UPDATE world_boss SET current_hp = ? WHERE guild_id = ?
                """, (new_hp, guild_id))
            await db.commit()
        return new_hp, boss["max_hp"], killed

    async def respawn_world_boss(self, guild_id: int, boss_name: str, max_hp: int, reward_pool: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE world_boss SET boss_name = ?, current_hp = ?, max_hp = ?, reward_pool = ?, is_alive = 1
                WHERE guild_id = ?
            """, (boss_name, max_hp, max_hp, reward_pool, guild_id))
            await db.commit()


    async def get_rpg_leaderboard(self, guild_id: int, limit: int = 10) -> list:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM rpg_profiles WHERE guild_id = ? ORDER BY level DESC, xp DESC LIMIT ?",
                (guild_id, limit)
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


    async def get_user_whitelist(self, guild_id: int, user_id: int) -> List[str]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT category FROM whitelist WHERE guild_id = ? AND user_id = ?",
                (guild_id, user_id)
            )
            rows = await cursor.fetchall()
            return [r[0] for r in rows]

    async def set_user_whitelist(self, guild_id: int, user_id: int, categories: List[str], added_by: int):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT category FROM whitelist WHERE guild_id = ? AND user_id = ? AND category IN ('extra_owner', 'owner')",
                (guild_id, user_id)
            )
            owners = [r[0] for r in await cursor.fetchall()]

            await db.execute(
                "DELETE FROM whitelist WHERE guild_id = ? AND user_id = ?",
                (guild_id, user_id)
            )
            for o in owners:
                await db.execute(
                    "INSERT OR REPLACE INTO whitelist (guild_id, user_id, category, added_by) VALUES (?, ?, ?, ?)",
                    (guild_id, user_id, o, added_by)
                )
            for cat in categories:
                await db.execute(
                    "INSERT OR REPLACE INTO whitelist (guild_id, user_id, category, added_by) VALUES (?, ?, ?, ?)",
                    (guild_id, user_id, cat, added_by)
                )
            await db.commit()

    # ================= Nightmode =================
    async def get_nightmode_settings(self, guild_id: int) -> dict:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM nightmode_settings WHERE guild_id = ?", (guild_id,))
            row = await cursor.fetchone()
            if row:
                return dict(row)
            await db.execute("INSERT OR IGNORE INTO nightmode_settings (guild_id, enabled) VALUES (?, 0)", (guild_id,))
            await db.commit()
            return {"guild_id": guild_id, "enabled": 0, "activated_at": None, "activated_by": None}

    async def update_nightmode_settings(self, guild_id: int, **kwargs):
        if not kwargs:
            return
        fields = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [guild_id]
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(f"UPDATE nightmode_settings SET {fields} WHERE guild_id = ?", values)
            await db.commit()

    async def add_nightmode_role_whitelist(self, guild_id: int, role_id: int, added_by: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO nightmode_role_whitelist (guild_id, role_id, added_by) VALUES (?, ?, ?)",
                (guild_id, role_id, added_by)
            )
            await db.commit()

    async def remove_nightmode_role_whitelist(self, guild_id: int, role_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM nightmode_role_whitelist WHERE guild_id = ? AND role_id = ?",
                (guild_id, role_id)
            )
            await db.commit()

    async def get_nightmode_role_whitelists(self, guild_id: int) -> List[int]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT role_id FROM nightmode_role_whitelist WHERE guild_id = ?", (guild_id,))
            rows = await cursor.fetchall()
            return [r[0] for r in rows]

    async def save_nightmode_backup(self, guild_id: int, role_id: int, permissions_value: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO nightmode_backups (guild_id, role_id, permissions_value) VALUES (?, ?, ?)",
                (guild_id, role_id, permissions_value)
            )
            await db.commit()

    async def get_nightmode_backups(self, guild_id: int) -> List[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM nightmode_backups WHERE guild_id = ?", (guild_id,))
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def clear_nightmode_backups(self, guild_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM nightmode_backups WHERE guild_id = ?", (guild_id,))
            await db.commit()

# ================= Welcome Settings =================
    async def get_welcome_settings(self, guild_id: int) -> Dict[str, Any]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM welcome_settings WHERE guild_id = ?", (guild_id,))
            row = await cursor.fetchone()
            if row:
                return dict(row)
            else:
                await db.execute(
                    "INSERT INTO welcome_settings (guild_id, enabled, channel_id, custom_message, embed_enabled) VALUES (?, 1, 0, '', 1)",
                    (guild_id,)
                )
                await db.commit()
                return {
                    "guild_id": guild_id,
                    "enabled": 1,
                    "channel_id": 0,
                    "custom_message": "",
                    "embed_enabled": 1
                }

    async def update_welcome_settings(self, guild_id: int, **kwargs):
        if not kwargs:
            return
        keys = list(kwargs.keys())
        values = list(kwargs.values())
        set_clause = ", ".join(f"{k} = ?" for k in keys)
        values.append(guild_id)

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT 1 FROM welcome_settings WHERE guild_id = ?", (guild_id,))
            if not await cursor.fetchone():
                await db.execute("INSERT INTO welcome_settings (guild_id) VALUES (?)", (guild_id,))
            await db.execute(f"UPDATE welcome_settings SET {set_clause} WHERE guild_id = ?", values)
            await db.commit()

    async def get_global_config(self, key: str) -> Optional[str]:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS global_config (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            cursor = await db.execute("SELECT value FROM global_config WHERE key = ?", (key,))
            row = await cursor.fetchone()
            return row[0] if row else None

    async def set_global_config(self, key: str, value: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS global_config (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            await db.execute(
                "INSERT OR REPLACE INTO global_config (key, value) VALUES (?, ?)",
                (key, value)
            )
            await db.commit()

db = Database()
