#!/usr/bin/env python3
"""
Bot Code - Commands, Buttons, Bot Client, etc.

Copyright::

    +===================================================+
    |                 © 2022 Someguy123                 |
    |               https://github.com/Someguy123       |
    +===================================================+
    |                                                   |
    |        Approval Bot for Discord                   |
    |        License: GNU AGPL v3                       |
    |                                                   |
    |        https://github.com/Someguy123/approvalbot  |
    |                                                   |
    |        Core Developer(s):                         |
    |                                                   |
    |          (+)  Chris (@someguy123)                 |
    |                                                   |
    +===================================================+
"""
from datetime import datetime, timezone
from decimal import ROUND_UP, Decimal
import math
from typing import Union
from privex.helpers import dec_round, empty, empty_if, DictObject
from approvalbot.core import load_config, save_config
from approvalbot.objects import MessageStore, ApprovalsDB, auto_relative, default_endtime, ApprovalOutcome, Approval, get_relative_seconds, now_plus_minutes
from approvalbot import settings
from approvalbot.settings import CONFIG, SERVER_IDS, TOKEN, VERSION, GH_URL
import interactions
import logging


log = logging.getLogger(__name__)

CommandContext = interactions.context.CommandContext
ComponentContext = interactions.context.ComponentContext

bot = interactions.Client(token=TOKEN)

@bot.event
async def on_ready():
    log.debug(f"Bot ready. Server IDs: {SERVER_IDS}")
    log.debug("Creating tables + indexes im sqlite")
    log.debug("Result from create_schemas:", await ApprovalsDB().create_schemas())
    print("Ready!")

# guild_ids = [789032594456576001] # Put your server ID in this array.

@bot.command(name="ping", scope=SERVER_IDS, description="Test that the bot is working and check for any latency issues")
async def _ping(ctx): # Defines a new "context" (ctx) command called "ping."
    await ctx.send(f"Pong! ({dec_round(bot.latency, 3)!s}ms)")


@bot.command(name="version", description="Check the bot's version + return license/source info")
async def get_version(ctx: Union[CommandContext, ComponentContext]):
    await ctx.send(f"""
    **ApprovalBot Version** v{VERSION}
    **Source:** <{GH_URL}>
    **(C) 2022 Someguy123 - Released under GNU AGPL v3.0**
    """)


def template_approve(action: str, post: str, reason:str, sender: str = "", approvals: int = 0, disapprovals: int = 0, expires_at: datetime = None, db_id=None) -> interactions.Embed:
    time_left = auto_relative(datetime.utcnow(), expires_at)
    relsecs = get_relative_seconds(datetime.utcnow(), expires_at)
    if relsecs < 0:
        time_left = "ENDED"
    
    return [
        interactions.Embed(
            title=f"Moderator Approval Request (ID: {db_id})",
            # description=f"""
            # Moderator Approval request

            # Requested by: {sender}
            # Post: {post}
            # Desired Action: {action}
            # Reason for action: {reason}

            # Approvals: {approvals}
            # Disapprovals: {disapprovals}
            # """,
            color=interactions.Color.yellow(),
            author=interactions.EmbedAuthor(name=f"Requested by: {sender}"),
            fields=[
                # interactions.EmbedField(name="Requested by", value=f"{sender}"),
                interactions.EmbedField(name="Desired Action", value=f"{action}"),
                interactions.EmbedField(name="Post", value=f"{post}"),
                interactions.EmbedField(name="Reason for Action", value=f"{reason}"),
                interactions.EmbedField(name="Voting ends at:", value=f"{'n/a' if expires_at is None else expires_at.isoformat() + ' UTC-0'}"),
                interactions.EmbedField(name="Time left (updated after each vote):", value=time_left),
            ],
            # footer=interactions.EmbedFooter(
            #     text=f"Approvals: {approvals}\nDisapprovals: {disapprovals}"
            # )
        ),
        interactions.Embed(
            title="Approvals", description=f"{approvals}", color=interactions.Color.green()
        ),
        interactions.Embed(
            title="Disapprovals", description=f"{disapprovals}", color=interactions.Color.red()
        )
    
    ]


async def is_admin_mod(ctx: Union[CommandContext, ComponentContext]) -> bool:
    """Returns :bool:`True` if the calling user is either an admin or a moderator"""
    return (await is_admin(ctx)) or is_moderator(ctx)

def is_local_admin(n: Union[CommandContext, ComponentContext, str]) -> bool:
    """
    Returns :bool:`True` if the passed username `n` is an admin in the CONFIG
    
    if `n` is a context object, returns True if the calling user is a an admin in the CONFIG
    """
    if isinstance(n, (CommandContext, ComponentContext)):
        n = f"{n.user.username}#{n.user.discriminator}"
    
    return n in CONFIG.get('admins', [])

async def is_admin(ctx: Union[CommandContext, ComponentContext]) -> bool:
    return (await is_server_admin(ctx)) or is_local_admin(ctx)


async def is_server_admin(ctx: Union[CommandContext, ComponentContext]) -> bool:
    """Returns :bool:`True` if the calling user is a Discord Server Administrator"""
    perms = (await ctx.author.get_guild_permissions(ctx.guild_id))
    log.debug("Guild perms for user %s are: %s", f"{ctx.user.username}#{ctx.user.discriminator}", perms)
    return interactions.Permissions.ADMINISTRATOR in perms


def is_moderator(n: Union[CommandContext, ComponentContext, str]) -> bool:
    """
    Returns :bool:`True` if the passed username `n` is a moderator, or if `n` is a context 
    object - True if the calling user is a moderator
    """
    if isinstance(n, (CommandContext, ComponentContext)):
        n = f"{n.user.username}#{n.user.discriminator}"
    
    return n in CONFIG.get('moderators', [])

def get_total_mods() -> int:
    return len(CONFIG.get('moderators', []))

def get_total_admins() -> int:
    return len(CONFIG.get('admins', []))

def get_total_mods_admins() -> int:
    """
    Get total number of mods + admins, filter the combined list so only unique names so that
    a user who's both an admin + mod isn't counted twice.
    """
    combo = CONFIG.get('moderators', []) + CONFIG.get('admins', [])
    uniquecombo = set(combo)
    return len(list(uniquecombo))

def get_total_mods_admins_elig() -> int:
    """
    Return the total mods/admins that are ELIGIBLE for majority counts based on the 
    ``majority_include_admins`` / ``admins_can_vote`` settings
    """
    log.debug("get_total_mods_admins_elig - Calculating total mods/admins that are eligible")
    return get_total_mods_admins() if CONFIG.majority_include_admins and CONFIG.admins_can_vote else get_total_mods()

def get_majority_number() -> int:
    """
    Get the number of votes required for a majority vote, while automatically
    handling the ``majority_include_admins`` / ``admins_can_vote`` settings
    to determine whether to base it on admins + mods, or just mods
    """
    log.debug("get_majority_number - Getting majority number")
    if CONFIG.majority_include_admins and CONFIG.admins_can_vote:
        log.debug("get_majority_number - Admins can vote")
        return int(math.floor(get_total_mods_admins() / 2) + 1)
    log.debug("get_majority_number - Admins CANNOT vote")
    return int(math.floor(get_total_mods() / 2) + 1)
    
async def can_vote(user: Union[CommandContext, ComponentContext, str]) -> bool:
    """
    Returns ``True`` if the user ``user`` (string or command/component context) is allowed to
    vote based on the ``admins_can_vote`` setting
    """
    if CONFIG.admins_can_vote:
        return await is_admin(user) if isinstance(user, (CommandContext, ComponentContext)) else is_local_admin(user)
    return is_moderator(user)

approve_button = interactions.Button(
    style=interactions.ButtonStyle.SUCCESS,
    label="Approve",
    custom_id="approve"
)

disapprove_button = interactions.Button(
    style=interactions.ButtonStyle.DANGER,
    label="Disapprove",
    custom_id="disapprove"
)

@bot.command(scope=SERVER_IDS, description="Request a moderator approval vote for a given issue")
@interactions.option("The action to be taken on this post/user: delete, ban, warn, suggestive flag, etc.")
@interactions.option("A link to the post in question")
@interactions.option("The reason for this action to be taken")
@interactions.option("No more votes can be made after this many minutes")
async def approval(ctx: interactions.CommandContext, action: str, post: str, reason: str, expire_minutes: int = settings.DEFAULT_APPROVAL_END / 60):
    """
    /approval - Create an approval request for moderators/admins to vote on
    """
    full_user = f"{ctx.user.username}#{ctx.user.discriminator}"
    log.debug("/approval called - checking if user is admin/mod")
    if not await is_admin_mod(ctx):
        log.info("Rejected user %s from running command /approval as they're neither a moderator nor an admin", full_user)
        return await ctx.send("ERROR: You must be a bot moderator or server admin to use this command!", ephemeral=True)
    log.debug("/approval - creating Approval object")
    aprv = Approval(
        message_id=None, action=action, url=post, reason=reason, username=full_user,
        total_all_mods=get_total_mods_admins_elig(), outcome=ApprovalOutcome.UNKNOWN,
        end_time=now_plus_minutes(expire_minutes)
    )
    log.debug("/approval - saving Approval object")
    aprv_id = await aprv.save()
    log.debug("Approval slash command was ran by user: %s", full_user)
    log.debug(f"Command arguments: {action=} {post=} {reason=}")
    log.debug("Sending initial approval template message...")
    msg = await ctx.send(
        components=[approve_button, disapprove_button], 
        embeds=template_approve(action, post, reason, full_user, expires_at=aprv.end_time, db_id=aprv.id),
    )
    log.debug(f"Storing data into Approval under MSG ID: %s and DB ID: %s", msg.id, aprv_id)
    log.debug("/approval - setting message ID and saving object")
    aprv.message_id = int(msg.id)
    await aprv.save()
    log.debug(f"Storing data into MessageStore under MSG ID: %s", msg.id)
    MessageStore.create(msg.id, action=action, post=post, reason=reason, sender=full_user)


def has_majority(obj_approvals: Union[MessageStore, Approval, dict, int], disapprovals=None, vote_type=None, info=True):
    """
    
        >>> has_majority(4, 2)

    """
    log.debug(f"has_majority - {obj_approvals=} {disapprovals=} {vote_type=} {info=}")
    if isinstance(obj_approvals, (MessageStore, Approval)):
        approvals, disapprovals = obj_approvals.approvals, obj_approvals.disapprovals
    elif isinstance(obj_approvals, dict):
        approvals, disapprovals = obj_approvals['approvals'], obj_approvals['disapprovals']
    else:
        approvals = obj_approvals
    
    maj = get_majority_number()

    if not empty(vote_type):
        if vote_type.lower() in ['approve', 'approval', 'approvals']:
            if not empty(disapprovals):
                return approvals > disapprovals and approvals >= maj
            return approvals >= maj
        if vote_type.lower() in ['disapprove', 'disapproval', 'disapprovals']:
            if not empty(approvals):
                return disapprovals > approvals and disapprovals >= maj
            return disapprovals >= maj
    
    data = DictObject(approvals=approvals, disapprovals=disapprovals, majority_number=maj)
    data.count_majority = 'approval' if approvals > 0 else 'none'
    if not empty(disapprovals):
        data.count_majority = 'approval' if approvals > disapprovals else 'disapprovals'
    
    data.mod_majority = 'none'
    if approvals >= maj :
        data.mod_majority = 'approval'
    elif not empty(disapprovals) and disapprovals >= maj:
        data.mod_majority = 'disapproval'
    
    if info:
        return data
    return data.mod_majority

    
async def handle_majority(m: Approval, ctx: Union[CommandContext, ComponentContext]):
    # if m.approvals > m.disapprovals and m.approvals >  (int(dec_round(Decimal(len(CONFIG.moderators)) / 2, rounding=ROUND_UP))):
    if m.approvals > m.disapprovals and m.approvals >= get_majority_number():
        await ctx.send(f":green_circle: :green_circle: :green_circle: The poll for post/user/action '<{m.post}>' has reached majority moderator **approval**! The action may now be taken :)")
        
    # if m.disapprovals > m.approvals and m.disapprovals > (int(dec_round(Decimal(len(CONFIG.moderators)) / 2, rounding=ROUND_UP))):
    if m.disapprovals > m.approvals and m.disapprovals >= get_majority_number():
        await ctx.send(f":red_circle: :red_circle: :red_circle: The poll for post/user/action '<{m.post}>' has reached majority moderator **DIS-approval**! The action should not be taken")
        


@bot.component("approve")
async def approve_handler(ctx: CommandContext):
    full_user = f"{ctx.user.username}#{ctx.user.discriminator}"

    if not await is_admin_mod(ctx):
        log.info("Rejected user %s from pressing approve button as they're neither a moderator nor an admin", full_user)
        return await ctx.send("ERROR: You must be a bot moderator or server admin to vote on polls!", ephemeral=True)
    
    if not await can_vote(ctx):
        log.info("Rejected user %s from pressing approve button as they're not allowed to vote", full_user)
        return await ctx.send("ERROR: You must be a moderator to vote!", ephemeral=True)
    
    log.debug("Approve button was clicked. Context message ID: %s | Context user: %s", ctx.message.id, full_user)
    # log.debug("Loading MessageStore for MSG ID: %s", ctx.message.id)
    log.debug("Loading Approval for MSG ID: %s", ctx.message.id)
    # m = MessageStore(ctx.message.id)
    aprv = await Approval.from_db(int(ctx.message.id))

    log.debug("Approval object before approving: %s", aprv)

    if aprv.end_time < datetime.utcnow().astimezone(tz=timezone.utc):
        log.info("Rejected user %s from pressing approve button as the approval request has expired", full_user)
        return await ctx.send("ERROR: This approval poll has ended", ephemeral=True)
    # if aprv.timestamp
    aprv.total_all_mods = get_total_mods_admins_elig()
    log.debug("Calling Approval.approve() for username: %s", full_user)
    await aprv.approve(full_user)
    majcheck = has_majority(aprv)
    if majcheck['mod_majority'] == 'approval':
        aprv.outcome = ApprovalOutcome.APPROVE
    elif majcheck['count_majority'] == 'approval':
        aprv.outcome = ApprovalOutcome.APPROVE_NOMAJ
    if majcheck['mod_majority'] == 'disapproval':
        aprv.outcome = ApprovalOutcome.DISAPPROVE
    elif majcheck['count_majority'] == 'disapproval':
        aprv.outcome = ApprovalOutcome.DISAPPROVE_NOMAJ
    await aprv.save()
    # log.debug("Successfully loaded - MessageStore contents: %r", m)
    # log.debug("Calling MessageStore.approve() for username: %s", full_user)
    # m.approve(full_user)
    log.debug("Editing approval discord message with updated approvals/disapprovals")
    await ctx.edit(embeds=template_approve(aprv.action, aprv.url, aprv.reason, aprv.username, 
        aprv.approvals, aprv.disapprovals, aprv.end_time, db_id=aprv.id), components=[approve_button, disapprove_button])
    # await ctx.edit(f"Button got clicked uwu Message ID is: {ctx.message.id} | passed value: {v}")
    if CONFIG.get('show_votes', False):
        await ctx.send(f":green_circle: {full_user} approved the poll for action on post/user <{aprv.url}>")
    # m.reload()

    await handle_majority(aprv, ctx)

@bot.component("disapprove")
async def disapprove_handler(ctx: CommandContext):
    full_user = f"{ctx.user.username}#{ctx.user.discriminator}"

    if not await is_admin_mod(ctx):
        log.info("Rejected user %s from pressing disapprove button as they're neither a moderator nor an admin", full_user)
        return await ctx.send("ERROR: You must be a bot moderator or server admin to vote on polls!", ephemeral=True)

    if not await can_vote(ctx):
        log.info("Rejected user %s from pressing disapprove button as they're not allowed to vote", full_user)
        return await ctx.send("ERROR: You must be a moderator to vote!", ephemeral=True)

    log.debug("Disapprove button was clicked. Context message ID: %s | Context user: %s", ctx.message.id, full_user)
    # log.debug("Loading MessageStore for MSG ID: %s", ctx.message.id)
    log.debug("Loading Approval for MSG ID: %s", ctx.message.id)
    # m = MessageStore(ctx.message.id)
    aprv = await Approval.from_db(int(ctx.message.id))
    log.debug("Approval object before disapproving: %s", aprv)

    if aprv.end_time < datetime.utcnow().astimezone(tz=timezone.utc):
        log.info("Rejected user %s from pressing disapprove button as the approval request has expired", full_user)
        return await ctx.send("ERROR: This approval poll has ended", ephemeral=True)
    # if aprv.timestamp
    aprv.total_all_mods = get_total_mods_admins_elig()
    log.debug("Calling Approval.disapprove() for username: %s", full_user)

    await aprv.disapprove(full_user)
    majcheck = has_majority(aprv)
    if majcheck['mod_majority'] == 'approval':
        aprv.outcome = ApprovalOutcome.APPROVE
    elif majcheck['count_majority'] == 'approval':
        aprv.outcome = ApprovalOutcome.APPROVE_NOMAJ
    if majcheck['mod_majority'] == 'disapproval':
        aprv.outcome = ApprovalOutcome.DISAPPROVE
    elif majcheck['count_majority'] == 'disapproval':
        aprv.outcome = ApprovalOutcome.DISAPPROVE_NOMAJ
    await aprv.save()

    # log.debug("Successfully loaded - MessageStore contents: %r", m)
    # log.debug("Calling MessageStore.disapprove() for username: %s", full_user)
    # m.disapprove(full_user)
    log.debug("Editing approval discord message with updated approvals/disapprovals")
    # await ctx.edit(embeds=template_approve(m.action, m.post, m.reason, m.sender, m.approvals, m.disapprovals), components=[approve_button, disapprove_button])
    await ctx.edit(embeds=template_approve(aprv.action, aprv.url, aprv.reason, aprv.username, 
        aprv.approvals, aprv.disapprovals, aprv.end_time, db_id=aprv.id), components=[approve_button, disapprove_button])

    if CONFIG.get('show_votes', False):
        await ctx.send(f":red_circle: {full_user} disapproved the poll for action on post/user <{aprv.url}>")

    await handle_majority(aprv, ctx)

    # await ctx.edit(f"Button got clicked uwu Message ID is: {ctx.message.id} | passed value: {v}")
    # await ctx.send("You clicked the Button :O", ephemeral=True)
    
@bot.command(scope=SERVER_IDS, description="Add a moderator to the bot (ADMIN ONLY)")
@interactions.option("The name of the moderator to add")
async def add_moderator(ctx: interactions.CommandContext, name: interactions.OptionType.USER):
    call_user = f"{ctx.user.username}#{ctx.user.discriminator}"

    # perms = (await ctx.author.get_guild_permissions(ctx.guild_id))
    log.info("User %s is adding moderator user via command: %s (repr: %s)", call_user, name, repr(name))
    
    if not await is_admin(ctx):
        log.debug("Non-administrator %s called /add_moderator - letting them know this isn't allowed and aborting the command...", call_user)
        await ctx.send("ERROR: Only server administrators can add moderators to the bot!", ephemeral=True)
        return
    
    if 'moderators' not in CONFIG or not isinstance(CONFIG.moderators, list):
        CONFIG.moderators = []
    
    full_user = f"{name.username}#{name.discriminator}"
    if full_user in CONFIG.moderators:
        log.debug("User %s tried to add a moderator that's already on the list: %s", call_user, full_user)
        await ctx.send(f"ERROR: user '{full_user}' is already configured as a bot moderator", ephemeral=True)
        return
    
    CONFIG.moderators.append(full_user)
    save_config()
    await ctx.send(f"Added moderator to bot: {full_user}")

@bot.command(scope=SERVER_IDS, description="List moderators on the bot")
async def list_moderators(ctx: interactions.CommandContext):
    call_user = f"{ctx.user.username}#{ctx.user.discriminator}"

    # perms = (await ctx.author.get_guild_permissions(ctx.guild_id))
    log.info("User %s is requesting the moderator list", call_user)
    
    if not await is_admin_mod(ctx):
        log.debug("Non-administrator/mod %s called /list_moderators - letting them know this isn't allowed and aborting the command...", call_user)
        await ctx.send("ERROR: Only admins/mods can list the moderator list!", ephemeral=True)
        return
    
    if 'moderators' not in CONFIG or not isinstance(CONFIG.moderators, list):
        CONFIG.moderators = []
    
    modlist = ""
    for m in CONFIG.moderators:
        modlist += f" - {m}\n"
    await ctx.send(f"Moderator list:\n{modlist}")

async def _remove_moderator(ctx, full_user: str):
    call_user = f"{ctx.user.username}#{ctx.user.discriminator}"
    # perms = (await ctx.author.get_guild_permissions(ctx.guild_id))
    log.info("User %s is removing moderator user via command: %s (repr: %s)", call_user, full_user, repr(full_user))
    # log.debug("Guild perms are: %s", perms)
    # if not (perms.ADMINISTRATOR in perms):
    if not await is_admin(ctx):
        log.debug("Non-administrator %s called /remove_moderator - letting them know this isn't allowed and aborting the command...", call_user)
        await ctx.send("ERROR: Only server administrators can remove moderators from the bot!", ephemeral=True)
        return
    
    if 'moderators' not in CONFIG or not isinstance(CONFIG.moderators, list):
        CONFIG.moderators = []
    
    # full_user = f"{name.username}#{name.discriminator}"
    if full_user not in CONFIG.moderators:
        log.debug("User %s tried to remove a moderator that's not on the list: %s", call_user, full_user)
        await ctx.send(f"ERROR: user '{full_user}' is already not a bot moderator", ephemeral=True)
        return
    
    CONFIG.moderators.remove(full_user)
    save_config()

    await ctx.send(f"Removed moderator from bot: {full_user}")

@bot.command(scope=SERVER_IDS, description="Remove a moderator from the bot (ADMIN ONLY)")
@interactions.option("The name of the moderator to remove")
async def remove_moderator(ctx: interactions.CommandContext, name: interactions.OptionType.USER):
    await _remove_moderator(ctx, f"{name.username}#{name.discriminator}")


@bot.command(scope=SERVER_IDS, description="Remove a moderator from the bot - raw string name (ADMIN ONLY)")
@interactions.option("The name of the moderator to remove")
async def remove_moderator_raw(ctx: interactions.CommandContext, name: str):
    await _remove_moderator(ctx, name)


@bot.command(scope=SERVER_IDS, description="Add an administrator to the bot (ADMIN ONLY)")
@interactions.option("The name of the admin to add")
async def add_admin(ctx: interactions.CommandContext, name: interactions.OptionType.USER):
    call_user = f"{ctx.user.username}#{ctx.user.discriminator}"

    # perms = (await ctx.author.get_guild_permissions(ctx.guild_id))
    log.info("User %s is adding admin user via command: %s (repr: %s)", call_user, name, repr(name))
    
    if not await is_admin(ctx):
        log.debug("Non-administrator %s called /add_admin - letting them know this isn't allowed and aborting the command...", call_user)
        await ctx.send("ERROR: Only server administrators can add admins to the bot!", ephemeral=True)
        return
    
    if 'admins' not in CONFIG or not isinstance(CONFIG.admins, list):
        CONFIG.admins = []
    
    full_user = f"{name.username}#{name.discriminator}"
    if full_user in CONFIG.admins:
        log.debug("User %s tried to add a admin that's already on the list: %s", call_user, full_user)
        await ctx.send(f"ERROR: user '{full_user}' is already configured as a bot admin", ephemeral=True)
        return
    
    CONFIG.admins.append(full_user)
    save_config()
    await ctx.send(f"Added admin to bot: {full_user}")

@bot.command(scope=SERVER_IDS, description="List administrators on the bot")
async def list_admins(ctx: interactions.CommandContext):
    call_user = f"{ctx.user.username}#{ctx.user.discriminator}"

    # perms = (await ctx.author.get_guild_permissions(ctx.guild_id))
    log.info("User %s is requesting the admin list", call_user)
    
    if not await is_admin_mod(ctx):
        log.debug("Non-administrator/mod %s called /list_admins - letting them know this isn't allowed and aborting the command...", call_user)
        await ctx.send("ERROR: Only admins/mods can list the admin list!", ephemeral=True)
        return
    
    if 'admins' not in CONFIG or not isinstance(CONFIG.admins, list):
        CONFIG.admins = []
    
    adminlist = ""
    for m in CONFIG.admins:
        adminlist += f" - {m}\n"
    await ctx.send(f"Admin list:\n{adminlist}")

async def _remove_admin(ctx, full_user):
    call_user = f"{ctx.user.username}#{ctx.user.discriminator}"
    # perms = (await ctx.author.get_guild_permissions(ctx.guild_id))
    log.info("User %s is removing admin user via command: %s (repr: %s)", call_user, full_user, repr(full_user))
    # log.debug("Guild perms are: %s", perms)
    # if not (perms.ADMINISTRATOR in perms):
    if not await is_admin(ctx):
        log.debug("Non-administrator %s called /remove_admin - letting them know this isn't allowed and aborting the command...", call_user)
        await ctx.send("ERROR: Only administrators can remove admins from the bot!", ephemeral=True)
        return
    
    if 'admins' not in CONFIG or not isinstance(CONFIG.admins, list):
        CONFIG.admins = []
    
    # full_user = 
    if full_user not in CONFIG.admins:
        log.debug("User %s tried to remove an admin that's not on the list: %s", call_user, full_user)
        await ctx.send(f"ERROR: user '{full_user}' is already not a bot admin", ephemeral=True)
        return
    
    CONFIG.admins.remove(full_user)
    save_config()

    await ctx.send(f"Removed admin from bot: {full_user}")

@bot.command(scope=SERVER_IDS, description="Remove an administrator from the bot (ADMIN ONLY)")
@interactions.option("The name of the admin to remove")
async def remove_admin(ctx: interactions.CommandContext, name: interactions.OptionType.USER):
    await _remove_admin(ctx, f"{name.username}#{name.discriminator}")

@bot.command(scope=SERVER_IDS, description="Remove an administrator from the bot - raw string name (ADMIN ONLY)")
@interactions.option("The name of the admin to remove")
async def remove_admin_raw(ctx: interactions.CommandContext, name: str):
    await _remove_admin(ctx, name)



@bot.command(scope=SERVER_IDS, description="Enable or disable displaying who voted and whether they voted approve/disapprove")
@interactions.option("Do we display who voted on which option when people vote?")
async def show_votes(ctx: interactions.CommandContext, enable: bool):
    call_user = f"{ctx.user.username}#{ctx.user.discriminator}"

    if not await is_admin(ctx):
        log.debug("Non-administrator %s called /show_votes - letting them know this isn't allowed and aborting the command...", call_user)
        await ctx.send("ERROR: Only server administrators can remove moderators from the bot!", ephemeral=True)
        return
    
    if enable:
        CONFIG.show_votes = True
        await ctx.send(" :green_circle: Showing votes has been enabled")
    else:
        CONFIG.show_votes = False
        await ctx.send(" :red_circle: Showing votes has been disabled")
    
    save_config()


if __name__ == '__main__':
    bot.start()
