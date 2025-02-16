# Telegram Media Bot

A Telegram bot that provides access to media (photos and videos) from a private channel using a credit system.

## Setup Instructions

1. Install Python requirements:
```bash
pip install -r requirements.txt
```

2. Get your Telegram Bot Token:
- Open Telegram and search for @BotFather
- Send `/newbot` command
- Follow prompts to create your bot
- Save the API token you receive

3. Configure the bot:
- Open `telegram_bot.py`
- Replace `YOUR_BOT_TOKEN` with your actual bot token
- Set `ADMIN_ID` to your Telegram user ID
- Set `PRIVATE_CHANNEL_ID` to your channel ID (format: -100xxxxxxxxxx)

4. Run the bot:
```bash
python telegram_bot.py
```

## Features

- Credit system (25 credits per new user)
- Random photo/video sharing from private channel
- Referral system (5 bonus credits per referral)
- Admin panel for managing credits
- Custom keyboard interface

## Commands

User Commands:
- `/start` - Start the bot
- `/video` - Get random video (costs 1 credit)
- `/photo` - Get random photo (costs 1 credit)
- `/points` - Check remaining credits
- `/refer` - Generate referral link
- `/buy` - Contact admin to buy credits

Admin Commands:
- `/admin` - View admin commands
- `/add_credits` - Add credits to user
- `/view_stats` - View bot statistics