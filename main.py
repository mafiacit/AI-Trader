import os
import logging
from app import app  # noqa: F401
# Import the simplified Telegram bot instead
import telegram_bot_simple as telegram_bot
import threading

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                  format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def start_web_app():
    """Start the Flask web app for development and admin purposes."""
    logger.info("Starting Flask web app on port 5000")
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

def start_telegram_bot():
    """Start the Telegram bot."""
    logger.info("Starting Telegram bot")
    telegram_bot.main()

if __name__ == "__main__":
    # Check if we have a Telegram token
    if os.environ.get("TELEGRAM_TOKEN"):
        logger.info("TELEGRAM_TOKEN found, starting both web app and Telegram bot")
        # Start web app in a separate thread
        web_thread = threading.Thread(target=start_web_app)
        web_thread.daemon = True
        web_thread.start()
        
        # Start the Telegram bot in the main thread
        start_telegram_bot()
    else:
        logger.warning("No TELEGRAM_TOKEN found. Starting only the web app. Set TELEGRAM_TOKEN to enable the bot.")
        # Start only the web app in the main thread
        start_web_app()
