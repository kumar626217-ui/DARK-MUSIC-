import asyncio
import os
import sys
import logging
import discord
from discord.ext import commands
from discord import app_commands

from config import TOKEN, DEFAULT_PREFIX, BOT_NAME, VERSION, OWNER_IDS
import config
from database import db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("AegisMain")

class AegisBot(commands.Bot):
    def __init__(self):
        # Configure All Discord Gateway Intents (Message Content, Members, Presences, Guilds)
        intents = discord.Intents.all()

        super().__init__(
            command_prefix=commands.when_mentioned_or(DEFAULT_PREFIX, "> "),
            intents=intents,
            help_command=None,
            case_insensitive=True,
            owner_ids=set(OWNER_IDS) if OWNER_IDS else None
        )

    async def setup_hook(self):
        # 1. Initialize SQLite database and tables
        logger.info("Initializing Aegis Prime database...")
        await db.initialize()

        # 2. Load Cogs
        cogs = [
            "cogs.security",
            "cogs.antiraid",
            "cogs.automod",
            "cogs.moderation",
            "cogs.anti_tamper",
            "cogs.gmail_gateway",
            "cogs.tracker",
            "cogs.minigames",
            "cogs.economy",
            "cogs.entertainment",
            "cogs.fun_images",
            "cogs.utility",
            "cogs.voice_master",
            "cogs.tour",
            "cogs.premium",
            "cogs.music",
            "cogs.ai_assistant",
            "cogs.rpg_adventure",
            "cogs.help"
        ]

        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.info(f"Loaded module: {cog}")
            except Exception as e:
                logger.error(f"Failed to load module {cog}: {e}", exc_info=True)

        # 3. Register persistent UI views (for tickets, verification, etc.)
        from cogs.antiraid import VerificationButtonView
        from cogs.utility import TicketPanelView, CloseTicketView
        self.add_view(TicketPanelView())
        self.add_view(CloseTicketView())

        # 4. Global Slash Command Error Catcher (Prevents "The application did not respond")
        async def on_tree_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
            logger.error(f"Error in slash command: {error}", exc_info=True)
            target_guild = interaction.guild or (self.get_guild(interaction.guild_id) if interaction.guild_id else None)
            if not target_guild:
                invite_url = f"https://discord.com/oauth2/authorize?client_id={self.user.id}&permissions=8&scope=bot%20applications.commands"
                msg = (
                    "⚠️ **Spectre is not yet added to this server!**\n\n"
                    "You are currently running Spectre as a personal account User App. To use commands, protect the server, and welcome members, Spectre must be authorized as a **Server Bot**.\n\n"
                    f"👉 **[Click Here to Add Spectre to this Server]({invite_url})**\n"
                    "*(Select your server from the dropdown, then click Authorize!)*"
                )
            elif isinstance(error, app_commands.TransformerError):
                msg = f"⚠️ **Channel Error:** Could not read `{error.value}` as a valid text channel. Please select a channel from the list, or type `#channel-name`."
            elif isinstance(error, app_commands.MissingPermissions):
                msg = f"⛔ You lack required permissions to run this command: `{', '.join(error.missing_permissions)}`."
            elif isinstance(error, app_commands.BotMissingPermissions):
                msg = f"⛔ Spectre lacks required server permissions: `{', '.join(error.missing_permissions)}`."
            else:
                msg = f"⚠️ **Command Error:** `{error}`"

            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(msg, ephemeral=True)
                else:
                    await interaction.followup.send(msg, ephemeral=True)
            except Exception:
                pass

        self.tree.on_error = on_tree_error
        self.synced = False

    async def on_ready(self):
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name=f"/help • 🛡️ Guarding {len(self.guilds)} servers"
        )
        await self.change_presence(status=discord.Status.online, activity=activity)

        if not self.synced:
            logger.info("Synchronizing application command tree with Discord Gateway...")
            try:
                for guild in self.guilds:
                    try:
                        self.tree.copy_global_to(guild=guild)
                        await self.tree.sync(guild=guild)
                        logger.info(f"Instantly synced commands to guild: {guild.name} ({guild.id})")
                    except Exception as ge:
                        logger.warning(f"Could not sync directly to guild {guild.id}: {ge}")

                synced = await self.tree.sync()
                logger.info(f"Successfully synced {len(synced)} root commands globally.")
                self.synced = True
            except Exception as e:
                logger.error(f"Failed to sync slash commands: {e}")

        print("\n" + "="*60)
        print(f"       [+] {BOT_NAME} v{VERSION} IS ONLINE [+]")
        print("="*60)
        print(f"• Logged in as: {self.user} (ID: {self.user.id})")
        print(f"• Serving: {len(self.guilds)} guilds | {len(self.users)} cached members")
        print(f"• Anti-Nuke Status: ACTIVE (Audit Log Interception & Rollback)")
        print(f"• Anti-Raid Status: ACTIVE (Visual Captcha & Join Shield)")
        print(f"• Casino & Games:   ACTIVE (Blackjack, Slots, Trivia, XP)")
        print(f"• Prefix Active:    '{DEFAULT_PREFIX}' (e.g. {DEFAULT_PREFIX}play, {DEFAULT_PREFIX}help)")
        print("="*60 + "\n")

    async def on_guild_join(self, guild: discord.Guild):
        """Autonomous Multi-Server Integration: Initializes DB & syncs commands on joining any new server."""
        logger.info(f"Spectre joined a new server: '{guild.name}' (ID: {guild.id}) | Members: {guild.member_count} | Owner: {guild.owner_id}")

        # 1. Initialize Database Defaults for the newly joined server
        try:
            await db.get_security_settings(guild.id)
            await db.get_antiraid_settings(guild.id)
            await db.get_automod_settings(guild.id)
            logger.info(f"Database settings initialized for new server '{guild.name}' ({guild.id})")
        except Exception as e_db:
            logger.error(f"Failed to initialize database for new server {guild.id}: {e_db}")

        # 2. Instantly Sync Application Commands to this guild so slash commands work in 0 seconds
        try:
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logger.info(f"Slash commands instantly synced to new server: '{guild.name}' ({guild.id})")
        except Exception as e_sync:
            logger.warning(f"Could not immediately sync slash commands to new guild {guild.id}: {e_sync}")

        # 3. Post English Security Announcement in Server
        target_ch = guild.system_channel
        if not target_ch:
            for ch in guild.text_channels:
                if ch.permissions_for(guild.me).send_messages:
                    target_ch = ch
                    break

        if target_ch:
            embed = discord.Embed(
                title="🛡️ Spectre Security Sentinel Activated",
                description=(
                    f"**Greetings, {guild.name}!** Spectre has joined to guard this server.\n\n"
                    f"🔒 **Multi-Server Autonomous Defense Active:**\n"
                    f"• **Anti-Nuke Protection:** Safeguards channels, roles, webhooks, and permissions.\n"
                    f"• **Anti-Raid Shield:** Real-time token raid quarantine and account age verification.\n"
                    f"• **AutoMod & Anti-Spam:** Mass mention, ghost ping, and spam suppression.\n"
                    f"• **High-Fidelity Audio:** Stream music with `>play <song>` or `/music play`.\n"
                    f"• **Interactive AI & Mini-Games:** Ask anything with `>ai <prompt>` or play casino games.\n\n"
                    f"Type `>help` or `/help` to view all commands!"
                ),
                color=config.Colors.BLUE
            )
            embed.set_thumbnail(url=self.user.display_avatar.url)
            embed.set_footer(text="Spectre Sentinel • Enterprise Multi-Server Defense", icon_url=self.user.display_avatar.url)
            try:
                await target_ch.send(embed=embed)
            except Exception:
                pass

    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        ch_name = getattr(message.channel, "name", "DM")
        logger.info(f"[CHAT] #{ch_name} | {message.author}: '{message.content}'")

        await self.process_commands(message)

    async def on_command_error(self, ctx: commands.Context, error: Exception):
        if isinstance(error, commands.CommandNotFound):
            logger.info(f"Command not found: '{ctx.message.content}'")
            return
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"⚠️ **Missing Argument:** `{error.param.name}` is required. Type `{DEFAULT_PREFIX}help` for usage.")
        elif isinstance(error, commands.CheckFailure):
            await ctx.send("⛔ **Access Denied:** You do not have permission to execute this command.")
        elif isinstance(error, (commands.MemberNotFound, commands.UserNotFound)):
            await ctx.send(f"❌ **User Not Found:** `{error.argument}` could not be found on this server.")
        elif isinstance(error, commands.ChannelNotFound):
            await ctx.send(f"❌ **Channel Not Found:** `{error.argument}` could not be found.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"⚠️ **Invalid Argument:** `{error}`")
        else:
            logger.error(f"Error in prefix command '{ctx.command}': {error}", exc_info=True)
            await ctx.send(f"❌ **Command Error:** `{error}`")



    @commands.command(name="prefix")
    async def prefix_cmd(self, ctx: commands.Context):
        """Check the current bot prefix."""
        await ctx.send(f"ℹ️ Spectre command prefix is **`{DEFAULT_PREFIX}`**\nTry: `{DEFAULT_PREFIX}play <song>`, `{DEFAULT_PREFIX}help`, or `{DEFAULT_PREFIX}ping`")

    @commands.command(name="invite", aliases=["addbot", "add", "oauth"])
    async def invite_cmd(self, ctx: commands.Context):
        """Get the official link to add Spectre to another server."""
        invite_url = f"https://discord.com/oauth2/authorize?client_id={self.user.id}&permissions=8&scope=bot%20applications.commands"
        embed = discord.Embed(
            title="🛡️ Add Spectre to Another Server",
            description=(
                "You can add Spectre to secure as many servers as you want! Discord bots join servers using official OAuth2 authorization links.\n\n"
                f"👉 **[Click Here to Invite Spectre to Your Server]({invite_url})**\n\n"
                "**Quick Steps:**\n"
                "1. Click the link above.\n"
                "2. Choose your other server from the dropdown list.\n"
                "3. Grant **Administrator** permissions (required for Anti-Nuke rollback & quarantine).\n"
                "4. Click **Authorize**.\n\n"
                "⚠️ **Note:** If you see *'This bot is private'*, ensure **'PUBLIC BOT'** is toggled **ON** in your [Discord Developer Portal](https://discord.com/developers/applications) under **Bot**!"
            ),
            color=config.Colors.BLUE
        )
        embed.set_thumbnail(url=self.user.display_avatar.url)
        embed.set_footer(text=f"Guarding {len(self.guilds)} servers 24/7", icon_url=self.user.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name="time", aliases=["uptime"])
    async def time_cmd(self, ctx: commands.Context):
        """Check server time and bot uptime."""
        import datetime
        now = datetime.datetime.now(datetime.timezone.utc)
        latency = round(self.latency * 1000)
        embed = discord.Embed(
            title="⏰ Spectre System Time & Multi-Server Status",
            description=(
                f"• **UTC Time:** `{now.strftime('%Y-%m-%d %H:%M:%S UTC')}`\n"
                f"• **Local Server Time:** `{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n"
                f"• **Gateway Latency:** `{latency}ms`\n"
                f"• **Status:** 🟢 **100% Online & Operational**\n"
                f"• **Servers Guarded:** `{len(self.guilds)} servers`\n"
                f"• **Active Prefix:** `{DEFAULT_PREFIX}`"
            ),
            color=config.Colors.BLUE
        )
        await ctx.send(embed=embed)

async def start_keepalive_server(bot: AegisBot):
    """Lightweight 24/7 Keep-Alive HTTP health check server for Render and Cloud hosting."""
    from aiohttp import web

    app = web.Application()

    async def handle_ping(request):
        latency = round(bot.latency * 1000) if bot.is_ready() else 0
        guild_count = len(bot.guilds) if bot.is_ready() else 0
        return web.json_response({
            "status": "online",
            "system": "SPECTRE Security Matrix",
            "version": VERSION,
            "latency_ms": latency,
            "guilds": guild_count,
            "health": "OK 24/7"
        })

    app.router.add_get("/", handle_ping)
    app.router.add_get("/health", handle_ping)
    app.router.add_get("/ping", handle_ping)

    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"24/7 Keep-Alive Health Server listening on http://0.0.0.0:{port}")
    return runner

async def main():
    if not TOKEN or TOKEN.strip() == "your_bot_token_here":
        raise SystemExit(
            "DISCORD_TOKEN is missing. Set it in Render's Environment settings "
            "or in your local .env file."
        )

    bot = AegisBot()
    web_runner = await start_keepalive_server(bot)
    try:
        async with bot:
            await bot.start(TOKEN)
    finally:
        await web_runner.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Aegis Bot shutdown cleanly by user.")
    except Exception as e:
        logger.critical(f"Fatal error running Aegis Bot: {e}", exc_info=True)
