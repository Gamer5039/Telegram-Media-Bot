import os
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import random
import json

# Configuration
USER_DATA_FILE = 'user_data.json'
MAX_MEDIA_ID = 16000  # Total number of media items (9000 photos + 7000 videos)
ADMIN_ID = "6130816114"  # Your Telegram ID
ADMIN_CONTACT = "https://t.me/Epokos"
DEFAULT_CREDITS = 25
PRIVATE_CHANNEL_ID = "-1002426292636"  # Your private channel ID

# Initialize user data
def load_user_data():
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_user_data(data):
    with open(USER_DATA_FILE, 'w') as f:
        json.dump(data, f)

# Global variable declaration
user_data = {}

def migrate_user_data():
    global user_data
    user_data = load_user_data()
    new_data = {}
    modified = False
    
    for user_id, old_data in user_data.items():
        if "personal_info" not in old_data:  # Check if data needs migration
            new_data[user_id] = {
                "personal_info": {
                    "username": None,
                    "first_name": None,
                    "last_name": None,
                    "join_date": None
                },
                "stats": {
                    "credits": old_data.get("credits", DEFAULT_CREDITS),
                    "total_media_viewed": len(old_data.get("seen_media", [])),
                    "last_active": None
                },
                "referral_data": {
                    "referrals": old_data.get("referrals", []),
                    "total_referral_earnings": 0
                },
                "media_history": {
                    "seen_media": old_data.get("seen_media", []),
                    "last_media_date": None
                }
            }
            modified = True
        else:
            new_data[user_id] = old_data
    
    if modified:
        user_data = new_data
        save_user_data(user_data)
        print("User data migrated to new format")

# Initialize data at startup
migrate_user_data()

# Keyboard markup
keyboard = [
    ['🎲 Random Media', '💰 My Points'],
    ['👥 Refer Friend', '💳 Buy Credits'],
    ['📊 My Stats', '❓ Help']
]
reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def initialize_user(user_id: str, update: Update = None):
    if user_id not in user_data:
        user_info = {
            "personal_info": {
                "username": update.effective_user.username if update else None,
                "first_name": update.effective_user.first_name if update else None,
                "last_name": update.effective_user.last_name if update else None,
                "join_date": str(update.effective_user.date) if update else None
            },
            "stats": {
                "credits": DEFAULT_CREDITS,
                "total_media_viewed": 0,
                "last_active": str(update.message.date) if update else None
            },
            "referral_data": {
                "referrals": [],
                "total_referral_earnings": 0
            },
            "media_history": {
                "seen_media": [],
                "last_media_date": None
            }
        }
        user_data[user_id] = user_info
        save_user_data(user_data)
    elif update:
        # Update user info if available
        user_data[user_id]["personal_info"].update({
            "username": update.effective_user.username,
            "first_name": update.effective_user.first_name,
            "last_name": update.effective_user.last_name
        })
        user_data[user_id]["stats"]["last_active"] = str(update.message.date)
        save_user_data(user_data)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    initialize_user(user_id, update)
    await update_user_activity(user_id, update)
    
    # Handle referrals
    if context.args and context.args[0].startswith('ref_'):
        referrer_id = context.args[0].split('_')[1]
        if (referrer_id in user_data and 
            user_id not in user_data[referrer_id]["referral_data"]["referrals"] and
            referrer_id != user_id):  # Prevent self-referral
            user_data[referrer_id]["referral_data"]["referrals"].append(user_id)
            user_data[referrer_id]["stats"]["credits"] += 5
            user_data[referrer_id]["referral_data"]["total_referral_earnings"] += 5
            save_user_data(user_data)
            
            # Notify referrer
            try:
                await context.bot.send_message(
                    chat_id=referrer_id,
                    text=f"🎉 New referral! You earned 5 credits!"
                )
            except Exception as e:
                print(f"Failed to notify referrer {referrer_id}: {e}")
    
    username = user_data[user_id]["personal_info"]["first_name"] or "there"
    await update.message.reply_text(
        f"👋 Welcome, {username}!\n\n"
        "Use the menu buttons below to:\n"
        "🎲 Get random media\n"
        "💰 Check your points\n"
        "👥 Refer friends\n"
        "💳 Buy more credits\n"
        "📊 View your stats\n"
        "❓ Get help\n\n"
        f"You have: {user_data[user_id]['stats']['credits']} credits 💰",
        reply_markup=reply_markup
    )

async def media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    initialize_user(user_id, update)
    await update_user_activity(user_id, update)
    
    if user_data[user_id]["stats"]["credits"] <= 0:
        await update.message.reply_text(
            "❌ You have no credits remaining!\n"
            f"Contact admin to buy more credits: {ADMIN_CONTACT}\n"
            "Prices:\n"
            "100 credits - $5\n"
            "300 credits - $12\n"
            "500 credits - $18"
        )
        return
    
    searching_msg = await update.message.reply_text("🔍 Searching for media...")
    
    try:
        # Reset seen media if all media has been seen
        if len(user_data[user_id]["media_history"]["seen_media"]) >= MAX_MEDIA_ID:
            user_data[user_id]["media_history"]["seen_media"] = []
            save_user_data(user_data)
        
        max_attempts = 15
        for attempt in range(max_attempts):
            try:
                # Get random message ID that hasn't been seen
                available_ids = list(set(range(1, MAX_MEDIA_ID + 1)) - set(user_data[user_id]["media_history"]["seen_media"]))
                if not available_ids:
                    user_data[user_id]["media_history"]["seen_media"] = []
                    available_ids = list(range(1, MAX_MEDIA_ID + 1))
                
                message_id = random.choice(available_ids)
                
                # Try to copy the message
                sent_message = await context.bot.copy_message(
                    chat_id=update.effective_chat.id,
                    from_chat_id=PRIVATE_CHANNEL_ID,
                    message_id=message_id
                )
                
                # Update user stats
                user_data[user_id]["media_history"]["seen_media"].append(message_id)
                user_data[user_id]["media_history"]["last_media_date"] = str(update.message.date)
                user_data[user_id]["stats"]["credits"] -= 1
                user_data[user_id]["stats"]["total_media_viewed"] += 1
                save_user_data(user_data)
                
                await searching_msg.delete()
                
                if user_data[user_id]["stats"]["credits"] <= 5:
                    await update.message.reply_text(
                        f"⚠️ Warning: You only have {user_data[user_id]['stats']['credits']} credits left!\n"
                        f"Contact admin to buy more: {ADMIN_CONTACT}"
                    )
                else:
                    await update.message.reply_text(
                        f"💰 1 credit used. {user_data[user_id]['stats']['credits']} credits remaining"
                    )
                return
                
            except Exception as e:
                if "Message to copy not found" in str(e):
                    user_data[user_id]["media_history"]["seen_media"].append(message_id)
                    save_user_data(user_data)
                    continue
                print(f"Error copying message: {e}")
                continue
        
        # If we get here, all attempts failed
        await searching_msg.edit_text(
            "❌ Failed to find media. Please try again or contact admin if this persists."
        )
    except Exception as e:
        print(f"Critical error in media function: {e}")
        await update.message.reply_text(
            "❌ An error occurred while processing your request.\n"
            f"Please contact admin: {ADMIN_CONTACT}"
        )





async def update_user_activity(user_id: str, update: Update):
    """Update user's last active time"""
    if user_id in user_data:
        user_data[user_id]["stats"]["last_active"] = str(update.message.date)
        save_user_data(user_data)

def format_date(date_str):
    if not date_str:
        return "Never"
    try:
        # Remove timezone info from string
        date_str = date_str.split('+')[0]
        # Parse the date string
        date_obj = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        # Format it nicely
        return date_obj.strftime('%d %b %Y, %I:%M %p')
    except:
        return date_str

async def points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    initialize_user(user_id, update)
    
    user_info = user_data[user_id]["personal_info"]
    user_stats = user_data[user_id]["stats"]
    referral_data = user_data[user_id]["referral_data"]
    media_history = user_data[user_id]["media_history"]
    
    name = user_info["first_name"] or "User"
    last_active = format_date(user_stats["last_active"])
    last_media = format_date(media_history["last_media_date"])
    
    stats_message = (
        f"👤 {name}'s Statistics\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"💰 Credits: {user_stats['credits']}\n"
        f"📺 Media Viewed: {user_stats['total_media_viewed']}\n"
        f"🕒 Last Active: {last_active}\n"
        f"📅 Last Media: {last_media}\n\n"
        f"📊 Referral Stats\n"
        f"👥 Total Referrals: {len(referral_data['referrals'])}\n"
        f"💎 Referral Earnings: {referral_data['total_referral_earnings']} credits\n\n"
        f"💡 Tip: Use /refer to earn more credits!"
    )
    
    await update.message.reply_text(stats_message)

async def refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    initialize_user(user_id, update)
    await update_user_activity(user_id, update)
    
    bot_username = context.bot.username
    referral_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    
    referral_stats = (
        f"🔗 Your Referral Link:\n{referral_link}\n\n"
        f"👥 Total Referrals: {len(user_data[user_id]['referral_data']['referrals'])}\n"
        f"💎 Total Earnings: {user_data[user_id]['referral_data']['total_referral_earnings']} credits\n\n"
        "💡 Share your link to earn 5 credits for each new user!"
    )
    await update.message.reply_text(referral_stats)

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    initialize_user(user_id, update)
    await update_user_activity(user_id, update)
    
    username = user_data[user_id]["personal_info"]["username"] or user_id
    current_credits = user_data[user_id]["stats"]["credits"]
    
    await update.message.reply_text(
        f"💳 Purchase Credits\n\n"
        f"Current Balance: {current_credits} credits\n\n"
        f"Contact admin to buy more:\n{ADMIN_CONTACT}\n\n"
        "📊 Price List:\n"
        "• 100 credits - $5 💰\n"
        "• 300 credits - $12 💎\n"
        "• 500 credits - $18 👑\n\n"
        "💡 Tip: Use /refer to earn free credits!"
    )

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    initialize_user(user_id, update)
    await update_user_activity(user_id, update)
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("⚠️ Admin access required!")
        return
    
    admin_keyboard = [
        ['➕ Add Credits', '➖ Remove Credits'],
        ['📊 View Stats', '👥 List Users'],
        ['📢 Broadcast', '🔙 Main Menu']
    ]
    admin_markup = ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True)
    
    help_text = (
        "🔧 Admin Panel\n\n"
        "Credit Management Commands:\n\n"
        "1️⃣ Quick Edit:\n"
        "   /quick_edit [user_id] [+amount or -amount]\n"
        "   Example: /quick_edit 123456789 +100\n\n"
        "2️⃣ Search Users:\n"
        "   /search [username or ID]\n\n"
        "3️⃣ List All Users:\n"
        "   /list_users\n\n"
        "4️⃣ User Details:\n"
        "   /user_info [user_id]\n\n"
        "5️⃣ Credit History:\n"
        "   /credit_history [user_id]"

    )
    await update.message.reply_text(help_text, reply_markup=admin_markup)

async def add_credits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    initialize_user(user_id, update)
    await update_user_activity(user_id, update)
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("⚠️ Admin access required!")
        return
    
    try:
        target_id = str(context.args[0])
        amount = int(context.args[1])
        
        if amount <= 0:
            await update.message.reply_text("❌ Amount must be positive!")
            return
            
        if target_id not in user_data:
            await update.message.reply_text("❌ User not found!")
            return
            
        initialize_user(target_id)
        
        # Add credit history entry
        history_entry = {
            "date": str(update.message.date),
            "amount": amount,
            "by_admin": user_id,
            "previous_balance": current_credits,
            "new_balance": current_credits + amount
        }
        if "credit_history" not in user_data[target_id]:
            user_data[target_id]["credit_history"] = []
        user_data[target_id]["credit_history"].append(history_entry)
        user_data[target_id]["stats"]["credits"] += amount
        save_user_data(user_data)
        
        user_info = user_data[target_id]["personal_info"]
        username = user_info["username"] or "Unknown"
        first_name = user_info["first_name"] or "Unknown"
        
        await update.message.reply_text(
            f"✅ Added {amount} credits to user:\n"
            f"🆔 ID: {target_id}\n"
            f"👤 Username: @{username}\n"
            f"📝 Name: {first_name}\n"
            f"💰 New Balance: {user_data[target_id]['stats']['credits']} credits"
        )
    except (IndexError, ValueError):
        await update.message.reply_text(
            "❌ Invalid format!\n"
            "Usage: /add_credits [user_id] [amount]\n"
            "Example: /add_credits 123456789 100"
        )

async def remove_credits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    initialize_user(user_id, update)
    await update_user_activity(user_id, update)
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("⚠️ Admin access required!")
        return
    
    try:
        target_id = str(context.args[0])
        amount = int(context.args[1])
        
        if amount <= 0:
            await update.message.reply_text("❌ Amount must be positive!")
            return
            
        if target_id not in user_data:
            await update.message.reply_text("❌ User not found!")
            return
            
        if user_data[target_id]["stats"]["credits"] < amount:
            await update.message.reply_text(
                f"❌ User only has {user_data[target_id]['stats']['credits']} credits!"
            )
            return
            
        user_data[target_id]["stats"]["credits"] -= amount
        save_user_data(user_data)
        
        user_info = user_data[target_id]["personal_info"]
        username = user_info["username"] or "Unknown"
        first_name = user_info["first_name"] or "Unknown"
        
        await update.message.reply_text(
            f"✅ Removed {amount} credits from user:\n"
            f"🆔 ID: {target_id}\n"
            f"👤 Username: @{username}\n"
            f"📝 Name: {first_name}\n"
            f"💰 New Balance: {user_data[target_id]['stats']['credits']} credits"
        )
    except (IndexError, ValueError):
        await update.message.reply_text(
            "❌ Invalid format!\n"
            "Usage: /remove_credits [user_id] [amount]\n"
            "Example: /remove_credits 123456789 50"
        )

async def user_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    initialize_user(user_id, update)
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("⚠️ Admin access required!")
        return
        
    try:
        target_id = str(context.args[0])
        
        if target_id not in user_data:
            await update.message.reply_text("❌ User not found!")
            return
            
        user = user_data[target_id]
        personal = user["personal_info"]
        stats = user["stats"]
        referral = user["referral_data"]
        
        info_text = (
            f"👤 User Information:\n\n"
            f"🆔 User ID: {target_id}\n"
            f"👤 Username: @{personal['username'] or 'None'}\n"
            f"📝 Name: {personal['first_name'] or 'None'} {personal['last_name'] or ''}\n"
            f"📅 Join Date: {personal['join_date'] or 'Unknown'}\n\n"
            f"📊 Statistics:\n"
            f"💰 Credits: {stats['credits']}\n"
            f"📺 Media Viewed: {stats['total_media_viewed']}\n"
            f"⏱ Last Active: {stats['last_active'] or 'Never'}\n\n"
            f"👥 Referral Info:\n"
            f"🔗 Total Referrals: {len(referral['referrals'])}\n"
            f"💎 Referral Earnings: {referral['total_referral_earnings']}"
        )
        
        await update.message.reply_text(info_text)
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /user_info [user_id]")

async def view_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    initialize_user(user_id, update)
    await update_user_activity(user_id, update)
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("⚠️ Admin access required!")
        return
    
    total_users = len(user_data)
    total_credits = sum(data["stats"]["credits"] for data in user_data.values())
    total_media_views = sum(data["stats"]["total_media_viewed"] for data in user_data.values())
    total_refs = sum(len(data["referral_data"]["referrals"]) for data in user_data.values())
    
    # Get active users in last 24 hours
    now = datetime.now()
    active_users = sum(1 for data in user_data.values() 
                      if data["stats"]["last_active"] and 
                      (now - datetime.strptime(data["stats"]["last_active"].split('+')[0], '%Y-%m-%d %H:%M:%S')).days < 1)
    
    stats = (
        "📊 Bot Statistics\n"
        "━━━━━━━━━━━━━━━\n\n"
        f"👥 Total Users: {total_users}\n"
        f"🟢 Active (24h): {active_users}\n"
        f"💰 Total Credits: {total_credits}\n"
        f"📺 Total Views: {total_media_views}\n"
        f"🔗 Total Referrals: {total_refs}\n\n"
        "👑 Top Users:\n"
    )
    
    # Add top 5 users by media views
    sorted_users = sorted(user_data.items(), key=lambda x: x[1]["stats"]["total_media_viewed"], reverse=True)[:5]
    for i, (uid, data) in enumerate(sorted_users, 1):
        username = data["personal_info"]["username"] or "Unknown"
        views = data["stats"]["total_media_viewed"]
        stats += f"{i}. @{username}: {views} views\n"
    
    await update.message.reply_text(stats)

async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    initialize_user(user_id, update)
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("⚠️ Admin access required!")
        return
    
    user_list = "👥 User List:\n\n"
    for uid, data in user_data.items():
        username = data["personal_info"]["username"] or "Unknown"
        name = data["personal_info"]["first_name"] or "Unknown"
        credits = data["stats"]["credits"]
        total_views = data["stats"]["total_media_viewed"]
        last_active = format_date(data["stats"]["last_active"]) if data["stats"]["last_active"] else "Never"
        
        user_list += (
            f"━━━━━━━━━━━━━━━\n"
            f"🆔 ID: {uid}\n"
            f"👤 @{username}\n"
            f"📝 Name: {name}\n"
            f"💰 Credits: {credits}\n"
            f"👁 Views: {total_views}\n"
            f"⏰ Last Active: {last_active}\n"
        )
    
    # Split message if too long
    if len(user_list) > 4000:
        parts = [user_list[i:i+4000] for i in range(0, len(user_list), 4000)]
        for part in parts:
            await update.message.reply_text(part)
    else:
        await update.message.reply_text(user_list)

async def search_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    initialize_user(user_id, update)
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("⚠️ Admin access required!")
        return
    
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide username or ID\n"
            "Example: /search username\n"
            "or: /search 123456789"
        )
        return
    
    search_term = context.args[0].lower()
    found_users = []
    
    for uid, data in user_data.items():
        username = (data["personal_info"]["username"] or "").lower()
        name = (data["personal_info"]["first_name"] or "").lower()
        
        if (search_term in username or 
            search_term in name or 
            search_term in uid):
            found_users.append((uid, data))
    
    if not found_users:
        await update.message.reply_text("❌ कोई यूजर नहीं मिला!")
        return
    
    response = "🔍 खोज के नतीजे:\n\n"
    for uid, data in found_users:
        username = data["personal_info"]["username"] or "Unknown"
        name = data["personal_info"]["first_name"] or "Unknown"
        credits = data["stats"]["credits"]
        response += (
            f"━━━━━━━━━━━━━━━\n"
            f"🆔 ID: {uid}\n"
            f"👤 @{username}\n"
            f"📝 Name: {name}\n"
            f"💰 Credits: {credits}\n\n"
            f"➕ Add credits:\n/add_credits {uid} amount\n"
            f"➖ Remove credits:\n/remove_credits {uid} amount\n"
            "━━━━━━━━━━━━━━━\n\n"
        )
    
    await update.message.reply_text(response)

async def quick_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    initialize_user(user_id, update)
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("⚠️ Admin access required!")
        return
    
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "❌ Correct Format:\n"
            "/quick_edit [user_id] [+amount or -amount]\n\n"
            "Examples:\n"
            "➕ To add credits:\n"
            "/quick_edit 123456789 +100\n\n"
            "➖ To remove credits:\n"
            "/quick_edit 123456789 -50"
        )
        return
    
    target_id = str(context.args[0])
    amount_str = context.args[1]
    
    try:
        if not amount_str.startswith('+') and not amount_str.startswith('-'):
            raise ValueError("Amount must start with + or -")
        amount = int(amount_str)
        
        if target_id not in user_data:
            await update.message.reply_text("❌ यूजर नहीं मिला!")
            return
        
        current_credits = user_data[target_id]["stats"]["credits"]
        
        if amount < 0 and abs(amount) > current_credits:
            await update.message.reply_text(
                f"❌ यूजर के पास सिर्फ {current_credits} क्रेडिट हैं!"
            )
            return
        
        user_data[target_id]["stats"]["credits"] += amount
        save_user_data(user_data)
        
        user_info = user_data[target_id]["personal_info"]
        username = user_info["username"] or "Unknown"
        name = user_info["first_name"] or "Unknown"
        new_balance = user_data[target_id]["stats"]["credits"]
        
        action = "Added" if amount > 0 else "Removed"
        amount_display = abs(amount)
        
        await update.message.reply_text(
            f"✅ {action} {amount_display} credits:\n\n"
            f"👤 @{username} ({name})\n"
            f"🆔 ID: {target_id}\n"
            f"💰 New Balance: {new_balance} credits"
        )
        
        # Notify user
        try:
            if amount > 0:
                notify_msg = f"🎉 You received {amount_display} credits!\n💰 New Balance: {new_balance} credits"
            else:
                notify_msg = f"📛 {amount_display} credits have been deducted\n💰 New Balance: {new_balance} credits"
            await context.bot.send_message(chat_id=target_id, text=notify_msg)
        except Exception as e:
            print(f"Failed to notify user {target_id}: {e}")
            
    except ValueError as e:
        await update.message.reply_text(
            "❌ गलत फॉर्मेट!\n"
            "सही फॉर्मेट: /quick_edit [user_id] [+amount या -amount]\n"
            "Example: /quick_edit 123456789 +100"
        )

async def credit_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    initialize_user(user_id, update)
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("⚠️ Admin access required!")
        return
    
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide user ID\n"
            "Example: /credit_history 123456789"
        )
        return
    
    target_id = str(context.args[0])
    if target_id not in user_data:
        await update.message.reply_text("❌ यूजर नहीं मिला!")
        return
    
    user = user_data[target_id]
    history = user.get("credit_history", [])
    username = user["personal_info"]["username"] or "Unknown"
    name = user["personal_info"]["first_name"] or "Unknown"
    
    if not history:
        await update.message.reply_text(
            f"👤 @{username} ({name})\n"
            f"🆔 ID: {target_id}\n"
            "📝 No credit history found"
        )
        return
    
    response = f"📊 Credit History - @{username}\n\n"
    
    for entry in reversed(history[-10:]):  # Show last 10 entries
        date = format_date(entry["date"])
        amount = entry["amount"]
        symbol = "+" if amount > 0 else ""
        response += (
            f"📅 {date}\n"
            f"💰 {symbol}{amount} credits\n"
            f"💳 Balance: {entry['new_balance']}\n"
            "➖➖➖➖➖➖\n"
        )
    
    await update.message.reply_text(response)

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    initialize_user(user_id, update)
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("⚠️ Admin access required!")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /broadcast [message]")
        return
    
    message = ' '.join(context.args)
    success_count = 0
    fail_count = 0
    
    status_msg = await update.message.reply_text("📢 Broadcasting message...")
    
    for user_id in user_data:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"📢 Broadcast Message:\n\n{message}"
            )
            success_count += 1
        except Exception as e:
            print(f"Failed to send broadcast to {user_id}: {e}")
            fail_count += 1
    
    await status_msg.edit_text(
        f"📢 Broadcast Complete\n\n"
        f"✅ Successfully sent: {success_count}\n"
        f"❌ Failed: {fail_count}"
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    initialize_user(user_id, update)
    await update_user_activity(user_id, update)
    
    text = update.message.text
    
    # Admin menu handlers
    if user_id == ADMIN_ID:
        if text == '➕ Add Credits':
            await update.message.reply_text("Use: /add_credits [user_id] [amount]")
            return
        elif text == '➖ Remove Credits':
            await update.message.reply_text("Use: /remove_credits [user_id] [amount]")
            return
        elif text == '📊 View Stats':
            await view_stats(update, context)
            return
        elif text == '👤 User Info':
            await update.message.reply_text("Use: /user_info [user_id]")
            return
        elif text == '📢 Broadcast':
            await update.message.reply_text("Use: /broadcast [message]")
            return
        elif text == '🔙 Main Menu':
            await start(update, context)
            return
    
    # Regular menu handlers
    if text == '🎲 Random Media':
        await media(update, context)
    elif text == '💰 My Points' or text == '📊 My Stats':
        await points(update, context)
    elif text == '👥 Refer Friend':
        await refer(update, context)
    elif text == '💳 Buy Credits':
        await buy(update, context)
    elif text == '❓ Help':
        username = user_data[user_id]["personal_info"]["first_name"] or "there"
        help_text = (
            f"👋 Hello {username}!\n\n"
            "Here's what you can do:\n\n"
            "🎲 Random Media - Get random photo/video\n"
            "💰 My Points - Check your balance\n"
            "👥 Refer Friend - Get referral link\n"
            "💳 Buy Credits - Purchase more credits\n"
            "📊 My Stats - View detailed statistics\n\n"
            f"Need help? Contact: {ADMIN_CONTACT}"
        )
        await update.message.reply_text(help_text)


async def shutdown(app):
    try:
        if app:
            await app.stop()
            await app.shutdown()
    except Exception as e:
        print(f"Error during shutdown: {e}")

def main():
    try:
        # Build application
        application = Application.builder().token("7918104066:AAGWoTR7LzgJwJTvVID9mUbsDJiVNcsAr3k").build()
        
        # Basic commands
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("media", media))
        application.add_handler(CommandHandler("points", points))
        application.add_handler(CommandHandler("refer", refer))
        application.add_handler(CommandHandler("buy", buy))
        
        # Admin commands
        application.add_handler(CommandHandler("admin", admin))
        application.add_handler(CommandHandler("add_credits", add_credits))
        application.add_handler(CommandHandler("remove_credits", remove_credits))
        application.add_handler(CommandHandler("view_stats", view_stats))
        application.add_handler(CommandHandler("user_info", user_info))
        application.add_handler(CommandHandler("broadcast", broadcast))
        application.add_handler(CommandHandler("list_users", list_users))
        application.add_handler(CommandHandler("search", search_user))
        application.add_handler(CommandHandler("quick_edit", quick_edit))
        application.add_handler(CommandHandler("credit_history", credit_history))
        
        # Text handler for menu buttons
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

        # Add error handler
        async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            error_msg = f"Exception while handling an update: {context.error}"
            print(error_msg)
            if update and update.effective_message:
                await update.effective_message.reply_text(
                    "❌ An error occurred while processing your request.\n"
                    f"Please contact admin: {ADMIN_CONTACT}"
                )

        application.add_error_handler(error_handler)
        
        print("🤖 Bot is running...")
        application.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        print(f"Critical error: {e}")
    finally:
        if 'application' in locals():
            import asyncio
            asyncio.run(shutdown(application))

if __name__ == "__main__":
    main()