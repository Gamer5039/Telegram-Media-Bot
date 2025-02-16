import os
import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import random
import json

# Configuration
USER_DATA_FILE = 'user_data.json'
MAX_MEDIA_ID = 16000  # Total number of media items (9000 photos + 7000 videos)
ADMIN_ID = "61xxxxxx14"  # Your Telegram ID
ADMIN_CONTACT = "https://t.me/Epokos"
DEFAULT_CREDITS = 25
PRIVATE_CHANNEL_ID = "-100xxxxxxxx36"  # Your private channel ID
SUGGESTION_COOLDOWN = 3600  # 1 hour in seconds
ADMIN_COMMANDS = {
    'add_credits': 2,
    'ban': 1,
    'unban': 1,
    'delete_media': 1,
    'user_info': 1,
    'broadcast': 0,  # 0 means variable arguments
    'view_stats': 0,
    'reset_credits': 1,
    'view_active': 0,
    'clear_history': 1,
    'clean_chat': 1,
    'delete_requests': 0,
    'view_users': 0
}

# Initialize user data
def load_user_data():
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_user_data(data):
    with open(USER_DATA_FILE, 'w') as f:
        json.dump(data, f)

user_data = load_user_data()

def migrate_user_data():
    modified = False
    for user_id in user_data:
        if "seen_media" not in user_data[user_id]:
            user_data[user_id]["seen_media"] = []
            modified = True
    if modified:
        save_user_data(user_data)

migrate_user_data()

# Keyboard markup
keyboard = [
    ['MEDIA'],
    ['POINTS', '/refer']
]
reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def initialize_user(user_id: str):
    if user_id not in user_data:
        user_data[user_id] = {
            "credits": DEFAULT_CREDITS,
            "referrals": [],
            "seen_media": [],
            "banned": False,  # Ensure banned status is initialized
            "credit_history": [],
            "join_date": str(datetime.datetime.now()),
            "last_suggestion": None,
            "suggestions": []
        }
        save_user_data(user_data)
    elif "banned" not in user_data[user_id]:
        # Update existing user data with missing fields
        user_data[user_id].update({
            "banned": False,
            "credit_history": [],
            "join_date": str(datetime.datetime.now()),
            "last_suggestion": None,
            "suggestions": []
        })
        save_user_data(user_data)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    initialize_user(user_id)
    
    # Handle referrals
    if context.args and context.args[0].startswith('ref_'):
        referrer_id = context.args[0].split('_')[1]
        if referrer_id in user_data and user_id not in user_data[referrer_id]["referrals"]:
            user_data[referrer_id]["referrals"].append(user_id)
            user_data[referrer_id]["credits"] += 5
            save_user_data(user_data)
    
    user_name = update.effective_user.first_name
    await update.message.reply_text(
        f"𝗛𝗲𝘆 👋, {user_name}! 🤩\n"
        "Welcome to PrmXo_bot 🎉\n\n"
        "🔥 I'm here to send you exclusive adult /Media from various categories!\n\n"
        "⚠️ Disclaimer: this is for only 18+. This Service is strictly for adults. By Continuing, you confirm you are 18+\n\n"
        "💡Enjoy responsibly and have fun!\n\n"
        "/media - Get a random photo or video\n"
        "/points - Check your points\n"
        "/refer - Generate referral link\n"
        "/buy - Buy points from admin\n"
        "/help - How to Use",
        reply_markup=reply_markup
    )

async def media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    initialize_user(user_id)
    
    if user_data[user_id]["banned"]:
        await update.message.reply_text("❌ You have been banned from using this bot!")
        return
    
    if user_data[user_id]["credits"] <= 0:
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
    
    # Reset seen media if all media has been seen
    if len(user_data[user_id]["seen_media"]) >= MAX_MEDIA_ID:
        user_data[user_id]["seen_media"] = []
        save_user_data(user_data)
    
    max_attempts = 15
    for attempt in range(max_attempts):
        try:
            # Get random message ID that hasn't been seen
            available_ids = list(set(range(1, MAX_MEDIA_ID + 1)) - set(user_data[user_id]["seen_media"]))
            if not available_ids:
                user_data[user_id]["seen_media"] = []
                available_ids = list(range(1, MAX_MEDIA_ID + 1))
            
            message_id = random.choice(available_ids)
            
            try:
                # Try to copy the message
                sent_message = await context.bot.copy_message(
                    chat_id=update.effective_chat.id,
                    from_chat_id=PRIVATE_CHANNEL_ID,
                    message_id=message_id
                )
                
                # Mark this ID as seen regardless of outcome
                user_data[user_id]["seen_media"].append(message_id)
                save_user_data(user_data)
                
                # Deduct credit and save
                user_data[user_id]["credits"] -= 1
                save_user_data(user_data)
                
                # Remove searching message
                await searching_msg.delete()
                
                # Send credit status
                if user_data[user_id]["credits"] <= 5:
                    await update.message.reply_text(
                        f"⚠️ Warning: You only have {user_data[user_id]['credits']} credits left!\n"
                        f"Contact admin to buy more: {ADMIN_CONTACT}"
                    )
                else:
                    await update.message.reply_text(
                        f"💰 1 credit used. {user_data[user_id]['credits']} credits remaining"
                    )
                return
                
            except Exception as e:
                if "Message to copy not found" in str(e):
                    # Message doesn't exist, mark as seen and continue
                    user_data[user_id]["seen_media"].append(message_id)
                    save_user_data(user_data)
                    continue
                print(f"Error copying message: {e}")
                continue
                
        except Exception as e:
            print(f"Error in media function: {e}")
            continue
    
    # If we get here, all attempts failed
    try:
        await searching_msg.edit_text("❌ No media found. Please try again.")
    except Exception as e:
        print(f"Error updating search message: {e}")





async def points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    initialize_user(user_id)
    await update.message.reply_text(f"💰 You have {user_data[user_id]['credits']} credits remaining")

async def refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    initialize_user(user_id)
    bot_username = context.bot.username
    referral_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    await update.message.reply_text(
        f"Invite friends with this link:\n{referral_link}\n"
        "You get 5 credits for each successful referral!"
    )

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    initialize_user(user_id)
    await update.message.reply_text(
        f"To purchase more credits, contact the admin:\n{ADMIN_CONTACT}\n"
        "Current rates:\n"
        "100 credits - $5\n"
        "300 credits - $12\n"
        "500 credits - $18"
    )

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    initialize_user(user_id)
    
    help_text = (
        "🔥 How to Use PrmXo Bot:\n\n"
        "1. /media - Get random adult photos/videos\n"
        "• Each media costs 1 credit\n"
        "• You start with 25 free credits\n\n"
        "2. /points - Check your remaining credits\n\n"
        "3. /refer - Get your referral link\n"
        "• Share with friends\n"
        "• Earn 5 credits per referral\n\n"
        "4. /buy - Purchase more credits\n"
        "• Contact admin for packages\n"
        "• Various credit packs available\n\n"
        "⚡ Note: This bot is strictly 18+ only\n"
        "❓ Need help? Contact admin: " + ADMIN_CONTACT
    )
    await update.message.reply_text(help_text)

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id != ADMIN_ID:
        await update.message.reply_text("⚠️ Admin access required!")
        return
    
    help_text = (
        "Admin Commands:\n"
        "Credits Management:\n"
        "/add_credits [user_id] [amount] - Add credits to user\n"
        "/reset_credits [user_id] - Reset user credits to default\n"
        "\nUser Management:\n"
        "/ban or /ben [user_id] - Ban a user\n"
        "/unban [user_id] - Unban a user\n"
        "/user_info [user_id] - View detailed user info\n"
        "/clear_history [user_id] - Clear user's media history\n"
        "/clean_chat [user_id] - Clean recent chat with user\n"
        "/view_users - View list of all users\n"
        "\nMedia Management:\n"
        "/delete_media [message_id] - Delete media from channel\n"
        "/delete_requests - Delete all user suggestions\n"
        "\nBroadcast & Stats:\n"
        "/broadcast - Send message/media to all users\n"
        "/view_stats - Show bot statistics\n"
        "/view_active - Show active users in last 30 days\n"
        "/view_suggestions - View user suggestions"
    )
    await update.message.reply_text(help_text)


async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id != str(ADMIN_ID):  # Convert both to string for comparison
        await update.message.reply_text("⚠️ Admin access required!")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /ban [user_id] or /ben [user_id]")
        return
        
    try:
        target_id = str(context.args[0])
        initialize_user(target_id)  # Initialize user if not exists
            
        if user_data[target_id].get("banned", False):
            await update.message.reply_text("❌ User is already banned!")
            return
            
        user_data[target_id]["banned"] = True
        save_user_data(user_data)
        
        # Send confirmation with more details
        await update.message.reply_text(
            f"✅ User {target_id} has been banned\n"
            f"Use /unban {target_id} to unban"
        )
        
        # Notify user
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text="⚠️ You have been banned from using this bot. Contact admin for more information."
            )
        except Exception:
            await update.message.reply_text("Note: Could not notify user about ban (user might have blocked the bot)")
            
    except Exception as e:
        await update.message.reply_text(f"❌ Error banning user: {str(e)}")


async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id != str(ADMIN_ID):  # Convert both to string for comparison
        await update.message.reply_text("⚠️ Admin access required!")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /unban [user_id]")
        return
        
    try:
        target_id = str(context.args[0])
        if target_id not in user_data:
            initialize_user(target_id)  # Initialize if user doesn't exist
            
        if not user_data[target_id].get("banned", False):
            await update.message.reply_text("❌ User is not banned!")
            return
            
        user_data[target_id]["banned"] = False
        save_user_data(user_data)
        await update.message.reply_text(f"✅ User {target_id} has been unbanned")
        
        # Notify user
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text="✅ You have been unbanned. You can now use the bot again."
            )
        except Exception as e:
            await update.message.reply_text(f"Note: Could not notify user (they might have blocked the bot)")
            
    except Exception as e:
        await update.message.reply_text(f"❌ Error unbanning user: {str(e)}")


async def delete_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id != str(ADMIN_ID):  # Convert both to string for comparison
        await update.message.reply_text("⚠️ Admin access required!")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /delete_media [message_id]")
        return
        
    try:
        message_id = int(context.args[0])
        
        # First verify the message exists
        try:
            # Try to delete the message first
            await context.bot.delete_message(chat_id=PRIVATE_CHANNEL_ID, message_id=message_id)
            
            # If deletion successful, remove from users' history
            modified = False
            for uid in user_data:
                if "seen_media" in user_data[uid] and message_id in user_data[uid]["seen_media"]:
                    user_data[uid]["seen_media"].remove(message_id)
                    modified = True
            
            if modified:
                save_user_data(user_data)
            
            await update.message.reply_text(f"✅ Media with ID {message_id} deleted successfully")
            
        except Exception as e:
            if "Message to delete not found" in str(e):
                await update.message.reply_text("❌ Message not found in channel!")
            else:
                await update.message.reply_text(f"❌ Error deleting message: {str(e)}")
            return
            
    except ValueError:
        await update.message.reply_text("❌ Invalid message ID! Must be a number.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def user_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id != str(ADMIN_ID):  # Convert both to string for comparison
        await update.message.reply_text("⚠️ Admin access required!")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /user_info [user_id]")
        return
        
    try:
        target_id = str(context.args[0])
        if target_id not in user_data:
            await update.message.reply_text("❌ User not found in database!")
            return
            
        user = user_data[target_id]
        
        # Get user's Telegram info
        try:
            chat = await context.bot.get_chat(target_id)
            username = chat.username or "Not set"
            first_name = chat.first_name or "Not set"
            last_name = chat.last_name or "Not set"
        except Exception:
            username = "Unknown"
            first_name = "Unknown"
            last_name = "Unknown"
        
        info = (
            f"👤 User Info for {target_id}:\n\n"
            f"Username: @{username}\n"
            f"First Name: {first_name}\n"
            f"Last Name: {last_name}\n"
            f"Credits: {user.get('credits', 0)}\n"
            f"Referrals: {len(user.get('referrals', []))}\n"
            f"Banned: {'Yes ❌' if user.get('banned', False) else 'No ✅'}\n"
            f"Join Date: {user.get('join_date', 'Unknown')}\n"
            f"Media Viewed: {len(user.get('seen_media', []))}\n\n"
            f"Recent Credit History:\n"
        )
        
        # Add credit history
        if "credit_history" in user and user["credit_history"]:
            for entry in user["credit_history"][-5:]:  # Show last 5 entries
                info += f"• {entry['amount']} credits ({entry['type']}) on {entry['date']}\n"
        else:
            info += "No credit history available"
        
        await update.message.reply_text(info)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error getting user info: {str(e)}")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not validate_admin_command(update, "broadcast", context.args):
        await update.message.reply_text(
            "Usage:\n"
            "1. Reply to a message/media with /broadcast to send that content\n"
            "2. Use /broadcast [text] to send a text message"
        )
        return
    
    status_msg = await update.message.reply_text("📊 Preparing broadcast...")
    
    # Get active users (users who have used the bot in the last 30 days)
    active_users = []
    thirty_days_ago = datetime.datetime.now() - datetime.timedelta(days=30)
    
    for uid in user_data:
        try:
            if not user_data[uid].get("banned", False):  # Skip banned users
                join_date = datetime.datetime.strptime(user_data[uid]["join_date"], "%Y-%m-%d %H:%M:%S.%f")
                if join_date > thirty_days_ago:
                    active_users.append(uid)
        except Exception:
            continue
    
    total_users = len(active_users)
    if total_users == 0:
        await status_msg.edit_text("❌ No active users found!")
        return
    
    sent = failed = 0
    message = update.message.reply_to_message or update.message
    broadcast_text = ' '.join(context.args) if context.args else None
    
    start_time = datetime.datetime.now()
    
    for i, uid in enumerate(active_users, 1):
        try:
            if broadcast_text is not None:
                await context.bot.send_message(chat_id=uid, text=broadcast_text)
            else:
                await message.copy(chat_id=uid)
            sent += 1
            
            if i % 5 == 0:  # Update status more frequently
                elapsed = (datetime.datetime.now() - start_time).total_seconds()
                speed = i / elapsed if elapsed > 0 else 0
                eta = (total_users - i) / speed if speed > 0 else 0
                
                await status_msg.edit_text(
                    f"📤 Broadcasting: {i}/{total_users} users\n"
                    f"✅ Sent: {sent} | ❌ Failed: {failed}\n"
                    f"⚡️ Speed: {speed:.1f} msg/sec\n"
                    f"⏱ ETA: {int(eta/60)}m {int(eta%60)}s"
                )
                
        except Exception as e:
            failed += 1
            print(f"Failed to send to {uid}: {e}")
    
    # Final status update
    duration = (datetime.datetime.now() - start_time).total_seconds()
    await status_msg.edit_text(
        f"📤 Broadcast completed in {int(duration)}s!\n"
        f"✅ Successful: {sent}\n"
        f"❌ Failed: {failed}\n"
        f"📊 Success rate: {(sent/total_users*100):.1f}%"
    )

def validate_admin_command(update: Update, command: str, args: list) -> bool:
    user_id = str(update.effective_user.id)
    if user_id != ADMIN_ID:
        return False
    
    if command in ADMIN_COMMANDS:
        required_args = ADMIN_COMMANDS[command]
        if required_args > 0 and (not args or len(args) < required_args):
            return False
    return True

async def add_credits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not validate_admin_command(update, "add_credits", context.args):
        await update.message.reply_text("⚠️ Invalid command usage. Format: /add_credits [user_id] [amount]")
        return
    
    try:
        target_id = str(context.args[0])
        amount = int(context.args[1])
        
        if amount <= 0:
            await update.message.reply_text("❌ Amount must be positive!")
            return
            
        initialize_user(target_id)
        
        # Add transaction record
        user_data[target_id]["credits"] += amount
        user_data[target_id]["credit_history"].append({
            "amount": amount,
            "date": str(datetime.datetime.now()),
            "type": "admin_add",
            "admin": str(update.effective_user.id)
        })
        save_user_data(user_data)
        
        # Notify user
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text=f"💰 {amount} credits have been added to your account by admin!"
            )
        except Exception:
            pass
            
        await update.message.reply_text(
            f"✅ Added {amount} credits to user {target_id}\n"
            f"New balance: {user_data[target_id]['credits']} credits"
        )
    except ValueError:
        await update.message.reply_text("❌ Invalid amount specified!")

async def reset_credits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not validate_admin_command(update, "reset_credits", context.args):
        await update.message.reply_text("Usage: /reset_credits [user_id]")
        return
    
    try:
        target_id = str(context.args[0])
        if target_id not in user_data:
            await update.message.reply_text("❌ User not found!")
            return
            
        old_credits = user_data[target_id]["credits"]
        user_data[target_id]["credits"] = DEFAULT_CREDITS
        user_data[target_id]["credit_history"].append({
            "amount": DEFAULT_CREDITS - old_credits,
            "date": str(datetime.datetime.now()),
            "type": "admin_reset",
            "admin": str(update.effective_user.id)
        })
        save_user_data(user_data)
        
        await update.message.reply_text(
            f"✅ Reset credits for user {target_id}\n"
            f"Old balance: {old_credits}\n"
            f"New balance: {DEFAULT_CREDITS}"
        )
        
        # Notify user
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text=f"Your credits have been reset to {DEFAULT_CREDITS} by admin."
            )
        except Exception:
            pass
            
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def clean_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not validate_admin_command(update, "clean_chat", context.args):
        await update.message.reply_text("Usage: /clean_chat [user_id]")
        return
    
    try:
        target_id = str(context.args[0])
        if target_id not in user_data:
            await update.message.reply_text("❌ User not found!")
            return
        
        # Delete recent messages
        try:
            # Get chat info
            chat = await context.bot.get_chat(target_id)
            
            # Try to delete messages one by one
            deleted = 0
            for i in range(1, 101):  # Try to delete last 100 messages
                try:
                    # Try to delete message
                    await context.bot.delete_message(chat_id=target_id, message_id=chat.id + i)
                    deleted += 1
                except Exception:
                    continue
            
            if deleted > 0:
                await update.message.reply_text(f"✅ Cleaned {deleted} messages from chat with user {target_id}")
            else:
                await update.message.reply_text("No messages could be deleted. They might be too old or already deleted.")
                
        except Exception as e:
            await update.message.reply_text(f"❌ Error cleaning chat: {str(e)}")
            
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def delete_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not validate_admin_command(update, "delete_requests", []):
        await update.message.reply_text("⚠️ Admin access required!")
        return
    
    deleted = 0
    for uid in user_data:
        if "suggestions" in user_data[uid]:
            deleted += len(user_data[uid]["suggestions"])
            user_data[uid]["suggestions"] = []
            user_data[uid]["last_suggestion"] = None
    
    save_user_data(user_data)
    await update.message.reply_text(f"✅ Deleted {deleted} suggestions from all users")

async def view_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not validate_admin_command(update, "view_users", []):
        await update.message.reply_text("⚠️ Admin access required!")
        return
    
    users_list = []
    for uid in user_data:
        try:
            chat = await context.bot.get_chat(uid)
            username = chat.username or "No username"
            name = chat.first_name or "Unknown"
            users_list.append(f"ID: {uid}\nUsername: @{username}\nName: {name}\n")
        except Exception:
            users_list.append(f"ID: {uid}\nUsername: Unknown\nName: Unknown\n")
    
    if not users_list:
        await update.message.reply_text("No users found!")
        return
    
    # Split into chunks of 10 users each
    chunks = [users_list[i:i + 10] for i in range(0, len(users_list), 10)]
    
    for i, chunk in enumerate(chunks):
        msg = f"👥 Users List (Page {i+1}/{len(chunks)}):\n\n"
        msg += "\n".join(chunk)
        await update.message.reply_text(msg)

async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not validate_admin_command(update, "clear_history", context.args):
        await update.message.reply_text("Usage: /clear_history [user_id]")
        return
    
    try:
        target_id = str(context.args[0])
        if target_id not in user_data:
            await update.message.reply_text("❌ User not found!")
            return
            
        old_count = len(user_data[target_id]["seen_media"])
        user_data[target_id]["seen_media"] = []
        save_user_data(user_data)
        
        await update.message.reply_text(
            f"✅ Cleared media history for user {target_id}\n"
            f"Removed {old_count} entries"
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def view_active(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not validate_admin_command(update, "view_active", context.args):
        await update.message.reply_text("⚠️ Admin access required!")
        return
    
    thirty_days_ago = datetime.datetime.now() - datetime.timedelta(days=30)
    active_users = []
    
    for uid, data in user_data.items():
        try:
            join_date = datetime.datetime.strptime(data["join_date"], "%Y-%m-%d %H:%M:%S.%f")
            if join_date > thirty_days_ago:
                active_users.append({
                    "id": uid,
                    "credits": data["credits"],
                    "media_count": len(data["seen_media"]),
                    "join_date": join_date
                })
        except Exception:
            continue
    
    if not active_users:
        await update.message.reply_text("No active users found in the last 30 days!")
        return
    
    # Sort by media count
    active_users.sort(key=lambda x: x["media_count"], reverse=True)
    
    msg = "👥 Active Users (Last 30 Days):\n\n"
    for i, user in enumerate(active_users[:10], 1):
        msg += (
            f"{i}. User ID: {user['id']}\n"
            f"   Credits: {user['credits']}\n"
            f"   Media Viewed: {user['media_count']}\n"
            f"   Joined: {user['join_date'].strftime('%Y-%m-%d')}\n\n"
        )
    
    msg += f"\nTotal Active Users: {len(active_users)}"
    await update.message.reply_text(msg)

async def view_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    initialize_user(user_id)
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("⚠️ Admin access required!")
        return
    
    total_users = len(user_data)
    total_credits = sum(data["credits"] for data in user_data.values())
    total_refs = sum(len(data["referrals"]) for data in user_data.values())
    
    stats = (
        "📊 Bot Statistics:\n"
        f"• Total users: {total_users}\n"
        f"• Total credits in circulation: {total_credits}\n"
        f"• Total referrals made: {total_refs}"
    )
    await update.message.reply_text(stats)

async def suggest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    initialize_user(user_id)
    
    if not context.args:
        await update.message.reply_text("Usage: /suggest [your suggestion]")
        return
        
    # Check cooldown
    last_suggestion = user_data[user_id].get("last_suggestion")
    if last_suggestion:
        last_time = datetime.datetime.fromisoformat(last_suggestion)
        if (datetime.datetime.now() - last_time).total_seconds() < SUGGESTION_COOLDOWN:
            remaining = int(SUGGESTION_COOLDOWN - (datetime.datetime.now() - last_time).total_seconds())
            await update.message.reply_text(f"Please wait {remaining//60} minutes before making another suggestion.")
            return
    
    suggestion = ' '.join(context.args)
    user_data[user_id]["suggestions"].append({
        "text": suggestion,
        "date": str(datetime.datetime.now()),
        "status": "pending"
    })
    user_data[user_id]["last_suggestion"] = str(datetime.datetime.now())
    save_user_data(user_data)
    
    # Notify admin
    try:
        admin_msg = (
            f"📝 New Suggestion:\n"
            f"From: {update.effective_user.username or user_id}\n"
            f"Text: {suggestion}"
        )
        await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg)
    except Exception:
        pass
    
    await update.message.reply_text("✅ Thank you for your suggestion! It has been sent to the admin.")

async def view_suggestions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id != ADMIN_ID:
        await update.message.reply_text("⚠️ Admin access required!")
        return
    
    all_suggestions = []
    for uid, data in user_data.items():
        if "suggestions" in data:
            for suggestion in data["suggestions"]:
                all_suggestions.append({
                    "user_id": uid,
                    "text": suggestion["text"],
                    "date": suggestion["date"],
                    "status": suggestion.get("status", "pending")
                })
    
    if not all_suggestions:
        await update.message.reply_text("No suggestions found!")
        return
    
    # Sort by date, newest first
    all_suggestions.sort(key=lambda x: x["date"], reverse=True)
    
    # Create message with last 10 suggestions
    msg = "📝 Recent Suggestions:\n\n"
    for suggestion in all_suggestions[:10]:
        status_emoji = "⏳" if suggestion["status"] == "pending" else "✅"
        msg += f"{status_emoji} From: {suggestion['user_id']}\n"
        msg += f"Date: {suggestion['date']}\n"
        msg += f"Text: {suggestion['text']}\n\n"
    
    await update.message.reply_text(msg)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    initialize_user(user_id)
    
    text = update.message.text
    if text == "MEDIA":
        await media(update, context)
    elif text == "POINTS":

        await points(update, context)

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
        application = Application.builder().token("791xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxr3k").build()
        
        # Basic user commands
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("media", media))
        application.add_handler(CommandHandler("points", points))
        application.add_handler(CommandHandler("refer", refer))
        application.add_handler(CommandHandler("buy", buy))
        application.add_handler(CommandHandler("suggest", suggest))
        
        # Admin commands
        application.add_handler(CommandHandler("admin", admin))
        application.add_handler(CommandHandler("broadcast", broadcast))
        application.add_handler(CommandHandler("add_credits", add_credits))
        application.add_handler(CommandHandler("view_stats", view_stats))
        application.add_handler(CommandHandler("ban", ban_user))  # Original ban command
        application.add_handler(CommandHandler("ben", ban_user))  # New alias for ban
        application.add_handler(CommandHandler("unban", unban_user))
        application.add_handler(CommandHandler("delete_media", delete_media))
        application.add_handler(CommandHandler("user_info", user_info))
        application.add_handler(CommandHandler("view_suggestions", view_suggestions))
        application.add_handler(CommandHandler("reset_credits", reset_credits))
        application.add_handler(CommandHandler("view_active", view_active))
        application.add_handler(CommandHandler("clear_history", clear_history))
        application.add_handler(CommandHandler("clean_chat", clean_chat))
        application.add_handler(CommandHandler("delete_requests", delete_requests))
        application.add_handler(CommandHandler("view_users", view_users))
        
        # Add help command
        application.add_handler(CommandHandler("help", help))
        
        # Text message handler (must be last)
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

        # Add error handler
        async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            print(f"Exception while handling an update: {context.error}")

        application.add_error_handler(error_handler)
        
        print("Bot is running...")
        application.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        print(f"Critical error: {e}")
    finally:
        if 'application' in locals():
            import asyncio
            asyncio.run(shutdown(application))


if __name__ == "__main__":
    main()
