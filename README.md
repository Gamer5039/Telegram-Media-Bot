# Telegram Media Bot

A powerful Telegram bot for managing and sharing media content with a credit-based system and comprehensive admin controls.

## Features

### User Features
- 🎯 Get random media content using credits
- 💰 Credit system with referral rewards
- 🔄 Referral system to earn more credits
- 💬 Suggestion system to provide feedback
- 📊 Check credit balance

### Admin Features
- 👥 User Management
  - Ban/Unban users
  - View user information
  - Clean chat history
  - Reset user credits
- 💳 Credit Management
  - Add credits to users
  - Reset credits
  - View credit statistics
- 📨 Broadcasting
  - Send messages to all users
  - View active users
- 📊 Statistics
  - View bot statistics
  - Monitor user activity
  - Track referrals

## Setup

### 1. Install Required Dependencies

```bash
pip install python-telegram-bot
```

### 2. Configure the Bot
- Replace `YOUR_BOT_TOKEN` in the code with your Telegram bot token.
- Set your Telegram ID as `ADMIN_ID`.
- Configure your private channel ID in `PRIVATE_CHANNEL_ID`.

### 3. Run the Bot
```bash
python telegram_bot.py
```

## Usage

### User Commands
- `/start` - Start the bot and get the welcome message.
- `/media` - Get random media content (costs 1 credit).
- `/points` - Check your credit balance.
- `/refer` - Get your referral link.
- `/buy` - Get information about buying credits.
- `/suggest` - Submit a suggestion.

### Admin Commands
- `/admin` - View all admin commands.
- `/broadcast` - Send a message to all users.
- `/add_credits [user_id] [amount]` - Add credits to a user.
- `/view_stats` - View bot statistics.
- `/ban` or `/ben [user_id]` - Ban a user.
- `/unban [user_id]` - Unban a user.
- `/delete_media [message_id]` - Delete media from channel.
- `/user_info [user_id]` - View detailed user info.
- `/view_suggestions` - View user suggestions.
- `/reset_credits [user_id]` - Reset user credits.
- `/view_active` - Show active users.
- `/clear_history [user_id]` - Clear a user's media history.
- `/clean_chat [user_id]` - Clean recent chat with a user.
- `/delete_requests` - Delete all user suggestions.
- `/view_users` - View list of all users.

## Important Notes

### Media Content
- Store media in a private channel.
- Bot will randomly select from available media.
- Supports both photos and videos.

### Credit System
- New users get 25 credits by default.
- Each media view costs 1 credit.
- Users can earn credits through referrals.
- Admins can manage user credits.

### Security
- Admin commands are protected.
- User activities are logged.
- Ban system for misuse prevention.

## File Structure

```
bot/
├── telegram_bot.py    # Main bot code
├── user_data.json      # User data storage
└── README.md           # Documentation
```

## Support
For support or inquiries, contact the admin through Telegram.

This `README.md` file covers all the essential details of your Telegram bot, including installation, usage, and features, in an easy-to-read format.
