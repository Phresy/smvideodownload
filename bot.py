import os
import time
import logging
import yt_dlp
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.request import HTTPXRequest

# Load environment variables from .env file (local development)
load_dotenv()

# Get token from environment variable (SECURE - no hardcoding)
TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    raise ValueError("❌ No BOT_TOKEN found! Please set BOT_TOKEN in environment variables or .env file")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

os.makedirs("downloads", exist_ok=True)

def get_ydl_opts(url):
    """Get platform-specific yt-dlp options"""
    
    # Common options for all platforms
    base_opts = {
        'outtmpl': 'downloads/%(title)s_%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': False,
        'extract_flat': False,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    }
    
    # YouTube-specific options - FIXED: single format, no merging needed
    if 'youtube.com' in url or 'youtu.be' in url:
        base_opts.update({
            'format': 'best[ext=mp4]',  # Downloads single best mp4 format (no ffmpeg needed)
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
            }
        })
    
    # TikTok-specific options
    elif 'tiktok.com' in url:
        base_opts.update({
            'format': 'best[ext=mp4]',
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }
        })
    
    # Instagram-specific options
    elif 'instagram.com' in url:
        base_opts.update({
            'format': 'best[ext=mp4]',
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
        })
    
    # X/Twitter-specific options
    elif 'twitter.com' in url or 'x.com' in url:
        base_opts.update({
            'format': 'best[ext=mp4]',
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
        })
    
    return base_opts

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎥 Send me a video link from:\n✅ YouTube\n✅ TikTok\n✅ Instagram\n✅ X (Twitter)\n\nI'll download and send it back!"
    )

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    chat_id = update.effective_chat.id
    
    msg = await update.message.reply_text("⬇️ Downloading video... Please wait.")
    
    try:
        # Get platform-specific options
        ydl_opts = get_ydl_opts(url)
        
        # Download the video
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            # Handle different extensions
            if not os.path.exists(filename):
                # Try common extensions
                for ext in ['.mp4', '.webm', '.mkv']:
                    test_file = filename.rsplit('.', 1)[0] + ext
                    if os.path.exists(test_file):
                        filename = test_file
                        break
                
                # Search in downloads folder if still not found
                if not os.path.exists(filename):
                    for file in os.listdir('downloads'):
                        if info.get('id', '') in file or info.get('title', '')[:30] in file:
                            filename = os.path.join('downloads', file)
                            break
        
        # Check if file exists
        if not os.path.exists(filename):
            await msg.edit_text("❌ Could not find downloaded file. Please try again.")
            return
        
        # Check file size
        file_size = os.path.getsize(filename) / (1024 * 1024)
        if file_size > 49:
            await msg.edit_text(f"⚠️ Video is {file_size:.1f}MB, but Telegram limit is 50MB.\nTry a shorter video or send me a different link.")
            os.remove(filename)
            return
        
        # Send the video
        with open(filename, 'rb') as video_file:
            await context.bot.send_video(
                chat_id=chat_id, 
                video=video_file, 
                caption=f"✅ {info.get('title', 'Video')[:50]}",
                supports_streaming=True
            )
        
        # Cleanup
        os.remove(filename)
        await msg.delete()
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Download error for {url}: {error_msg}")
        
        # Give more helpful error messages
        if 'tiktok' in url.lower():
            await msg.edit_text("❌ Failed to download TikTok video. Try using a different link or check if the video is public.")
        elif 'instagram' in url.lower():
            await msg.edit_text("❌ Failed to download Instagram video. Instagram has strict limits - try a public account video.")
        elif 'youtube' in url.lower():
            await msg.edit_text("❌ Failed to download YouTube video. Try a shorter video or a different link.")
        else:
            await msg.edit_text(f"❌ Error: {error_msg[:100]}")

def main():
    req = HTTPXRequest(
        connect_timeout=60,
        read_timeout=120,
        write_timeout=60,
    )
    
    app = Application.builder().token(TOKEN).request(req).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))
    
    print("✅ Bot is running! Press Ctrl+C to stop.")
    print("📌 Send any video link to test (YouTube, TikTok, Instagram, X)")
    app.run_polling()

if __name__ == "__main__":
    main()