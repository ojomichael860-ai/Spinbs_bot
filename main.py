import os
import asyncio
import threading
import json
import http.client
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- Web Server for Render Health Checks ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Spinbot Paraphrasing Engine Active!")

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()

def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    print(f"Health check server running on port {port}")
    server.serve_forever()

# --- Spinbot Paraphrasing Core Logic ---
def spin_text_engine(text: str) -> str:
    """Uses a serverless edge endpoint to spin and paraphrase text efficiently."""
    try:
        conn = http.client.HTTPSConnection("open-api.no-api.workers.dev")
        payload = json.dumps({
            "prompt": f"Paraphrase and rewrite the following text to make it unique, engaging, and completely different while preserving its original meaning. Return only the rewritten text without adding generic introductions, conversational filler, or commentary: '{text}'"
        })
        headers = {'Content-Type': 'application/json'}
        conn.request("POST", "/v1/chat/completions", payload, headers)
        res = conn.getresponse()
        data = res.read().decode("utf-8")
        parsed = json.loads(data)
        return parsed["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Spinbot Core Exception: {e}")
        return ""

# --- Bot Event Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔄 **Welcome to the Spinbot Content Rewriter!**\n\n"
        "Send me any text, paragraph, or article snippet, and I will instantly paraphrase "
        "and rewrite it to give you a unique, plagiarism-free variation.\n\n"
        "👉 **Paste your text below to spin it instantly:**",
        parse_mode="Markdown"
    )

async def handle_text_spinning(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    
    if not user_text.strip() or len(user_text) < 5:
        await update.message.reply_text("⚠️ *Please provide a longer text block to paraphrase effectively.*", parse_mode="Markdown")
        return

    # Trigger 'typing' indicator to keep user engaged during API loop
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    # Process text rewrite
    spun_result = spin_text_engine(user_text)
    
    if not spun_result:
        await update.message.reply_text("❌ *An error occurred while rewriting your text. Please try again later.*", parse_mode="Markdown")
        return

    # Format the message layout so users can tap to copy instantly
    response_text = (
        f"📝 **Your Unique Spun Content:**\n\n"
        f"`{spun_result}`\n\n"
        f"💡 *Tip: Tap the text box above to copy the new content directly to your clipboard.*"
    )
    
    await update.message.reply_text(response_text, parse_mode="Markdown")

async def main():
    TOKEN = os.environ.get("TELEGRAM_TOKEN")
    if not TOKEN:
        raise ValueError("Missing TELEGRAM_TOKEN environment target variable.")

    # Start the mandatory web server background port routing for Render checks
    threading.Thread(target=run_health_server, daemon=True).start()

    # Build the Application framework mapping sequences
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_spinning))
    
    print("Spinbot engine processing active and polling...")
    
    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        while True:
            await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
