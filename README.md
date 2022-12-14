# Discord Approval Bot

![Screenshot of ApprovalBot embed for /approval](https://i.imgur.com/RvUfQLH.png)

This is a Discord bot originally designed for [DEMOC.HORSE](https://democ.horse) - a democratically moderated Mastodon instance.

It allows chosen moderators/admins to create **Approval Requests** which may then be voted on (Approve / Disapprove) by moderators and admins,
and will print a message once a majority approval/disapproval has been reached.

The general settings of the bot such as the admin/moderator lists, and whether to show which persons voted or not - can be controlled
through slash commands such as `/add_moderator`, `/remove_moderator`, `/add_admin`, `/remove_admin`, and `/show_votes`

## Features

- **Bot Administrator list** - only admins can add/remove moderators and admins to the bot (Users with Server Administrator privilege 
    have admin powers by default, regardless of whether they're on the list or not)
- **Bot Moderator list** - moderators can create approval requests, and vote on them
- **Show / Hide Votes** - Admins can turn on or off showing votes. When `/show_votes` is enabled, when a moderator votes on an approval,
  a public message is printed in the same channel saying `XXX#1234 has approved the poll` or `XXX#1234 has disapproved the poll`
- **Settings adjustable via slash commands** - Admins can add/remove admins/moderators, as well as toggle showing votes - using slash commands
- **Settings stored in YAML file** - Settings are persistent, they're saved in a YAML file on the server in `config.yml`
- **Approval Voting** - Moderators and Admins can run `/approval` to create an approval request, which both mods/admins can vote on.
  - **Majority Alert** - When the approval or disapproval count is above 50% of the bot moderator count, the bot will print a message
                         stating that a majority (dis)approval has been reached, and that the action requiring approval can (not) be taken.

## License

ApprovalBot is released under the GNU AGPL 3.0 - see the LICENSE file for more info.

## Install

We assume you already know how to [register a Discord bot account](https://discord.com/developers/applications) and invite it using the OAUTH2 URL generator.

Since it just uses slash commands, it should only require the "bot" permission.

The bot requires Python 3.7 minimum - Python 3.8 or newer is recommended.

To actually install the bot on an Ubuntu/Debian-based system:

```sh
# First, become root (sudo su -) if you're not already.
sudo su -
# Make sure you have Python and Pip installed, as well as Pipenv
apt update
apt install python3 python3-pip
pip3 install -U pipenv

# Create a user for the bot
adduser --gecos "" --disabled-password approvalbot

# Login as the user, then clone the repo
su - approvalbot
git clone https://github.com/Someguy123/approvalbot.git

# Enter the code folder
cd approvalbot

# Copy the example .env file, and enter your bot token + server ID(s)
cp example.env .env
nano .env      # Or use vim or another editor if you prefer

# generate the pipenv environment + install deps
./run.sh install

# Start the bot and test that it works - it may take a minute for the commands to become available
# on your server after you've invited it
./run.sh start

# Once you've confirmed the bot is working okay, you can install the service
# Exit the approvalbot user, you'll need to be root to run the service installer
exit
# Enter the approvalbot folder as root
cd /home/approvalbot/approvalbot
# Run this command which will automatically install the service, enable it, and start it
./run.sh service

# Check that the service is working
systemctl status approvalbot
```

## Commands

- `/approval <action> <post> <reason>` - Request an approval vote by moderators for a given post/user
  - `action` is the action you want to take on the post/user, e.g. delete, warn, content warning, ban, etc.
  - `post` is a link to the post/user in question
  - `reason` is the reason you think `action` is necessary for this post/user

- `/add_moderator <user>` - Add a moderator to the bot's moderator list. Must be either a server admin, or in the bot's admin list to run this command.
- `/remove_moderator <user>` - Remove a moderator from the bot's moderator list. Must be a server/bot admin to run this command.
- `/remove_moderator_raw <user_string>` - Remove an moderator from the bot's moderator list with a plain string user (e.g. `John#1234`). This is to allow you to
        remove moderators who have left the server, as `/remove_moderator` expects a valid user. Must be a server/bot admin to run this command.
- `/list_moderators` - List all moderators in the bot's moderator list. Must be a server/bot admin or bot moderator to use this command.

- `/add_admin <user>` - Add an admin to the bot's admin list. Must be a server/bot admin to run this command.
- `/remove_admin <user>` - Remove an admin from the bot's admin list. Must be a server/bot admin to run this command.
- `/remove_admin_raw <user_string>` - Remove an admin from the bot's admin list with a plain string user (e.g. `John#1234`). This is to allow you to
        remove admins who have left the server, as `/remove_admin` expects a valid user. Must be a server/bot admin to run this command.
- `/list_admins` - List all admins in the bot's admin list. Must be a server/bot admin or bot moderator to use this command.

- `/show_votes <true/false>` - Enable or disable showing moderator/admin vote choices publicly. Must be a server/bot admin to run this command.

- `/ping` - Pings the bot, the bot will return `Pong! (XXX.XXXms)` with the detected latency - used to quickly test if the bot is working properly
