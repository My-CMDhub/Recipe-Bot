# 🍽️ WhatsApp Recipe Bot

> **Automated daily dinner recipe suggestions via WhatsApp**  
> Built with Flask, WhatsApp Cloud API, and Supabase. Features AI-powered grocery predictions and receipt processing.

---

## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Quick Start](#-quick-start)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Deployment](#-deployment)
- [API Reference](#-api-reference)
- [Project Structure](#-project-structure)
- [Contributing](#-contributing)

---

## ✨ Features

### 🎯 Core Features

- **🍽️ Daily Recipe Suggestions** - Automated recipe delivery at configured time (default: 22:00 AEST)
- **🔄 Alternative Recipes** - Get different suggestions by replying "not today"
- **📋 Full Recipe List** - View all available recipes anytime
- **👋 Smart Conversations** - Natural greeting and farewell handling
- **🔄 Auto Reset** - Daily recipe history resets at midnight automatically

### 🤖 Advanced Features

- **🛒 AI Grocery Predictions** - Get personalized shopping lists based on purchase history
- **📸 Receipt Processing** - Upload receipts via WhatsApp for automatic item extraction
- **📊 Feedback System** - Submit receipts to improve prediction accuracy
- **🧠 Learning Engine** - AI learns from your shopping patterns over time
- **⏰ Smart Scheduling** - Robust scheduler for production environments

### 🛡️ Reliability Features

- **🔄 Duplicate Prevention** - Idempotency for webhooks and images
- **📊 Status Filtering** - Automatically ignores WhatsApp status updates
- **⚡ Fast Responses** - Always returns 200 OK quickly to prevent retries
- **🔍 Health Monitoring** - Built-in health check endpoint with scheduler status

---

## 🏗️ Architecture

```
┌─────────────────┐
│  WhatsApp User  │
└────────┬────────┘
         │
         │ Messages/Images
         ▼
┌─────────────────────────────────────┐
│         Flask Application           │
│  ┌───────────────────────────────┐  │
│  │   Webhook Handler             │  │ ← Receives messages
│  │   - Duplicate prevention      │  │
│  │   - Status filtering          │  │
│  └───────────────────────────────┘  │
│  ┌───────────────────────────────┐  │
│  │   Message Processor           │  │ ← Routes messages
│  │   - Text messages             │  │
│  │   - Image receipts            │  │
│  └───────────────────────────────┘  │
│  ┌───────────────────────────────┐  │
│  │   Scheduler (APScheduler)     │  │ ← Daily automation
│  │   - Recipe sending            │  │
│  │   - History reset             │  │
│  └───────────────────────────────┘  │
└────────┬────────────────────────────┘
         │
         ├─── WhatsApp Cloud API (Send messages)
         │
         └─── Supabase (Database)
              ├── Recipes
              ├── Receipts
              ├── Predictions
              └── Feedback
```

---

## 🚀 Quick Start

### Prerequisites

- **Python** 3.11+
- **Meta Developer Account** with WhatsApp Cloud API access
- **Supabase** account (free tier works)
- **WhatsApp** test number or verified business number.

### 1-Minute Setup

```bash
# Clone and setup
git clone <repository-url>
cd Daily-Automation
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Run locally
python app.py
```

---

## 📦 Installation

### Step 1: Clone Repository

```bash
git clone <repository-url>
cd Daily-Automation
```

### Step 2: Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Mac/Linux
# OR
venv\Scripts\activate     # On Windows
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Database Setup

1. **Create Supabase Project**
   - Go to [supabase.com](https://supabase.com)
   - Create a new project
   - Note your project URL and anon key

2. **Run Database Migrations**
   - Open Supabase SQL Editor
   - Run `utils/db_migrations/grocery_schema.sql`
   - This creates all necessary tables

3. **Seed Initial Recipes**
   - After starting the app, make a POST request to `/seed-recipes` endpoint

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the root directory:

```env
# WhatsApp Configuration
WHATSAPP_TOKEN=your_access_token_here
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_VERIFY_TOKEN=your_custom_verify_token (anything you would like)

# Recipients (comma-separated for multiple numbers)
RECIPIENT_PHONE_NUMBER=1234567890,9876543210

# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_anon_key_here

# Scheduling
RECIPE_SEND_TIME=00:00  # Format: HH:MM (24-hour)

# Optional
DEBUG=False             # Set to True for development
PORT=5001              # Default port (Heroku sets this automatically)
MIN_RECEIPTS_NEEDED=25  # Minimum receipts for grocery predictions
```

### Variable Descriptions

| Variable | Required | Description |
|----------|----------|-------------|
| `WHATSAPP_TOKEN` | ✅ Yes | WhatsApp Cloud API access token |
| `WHATSAPP_PHONE_NUMBER_ID` | ✅ Yes | Your WhatsApp phone number ID |
| `WHATSAPP_VERIFY_TOKEN` | ✅ Yes | Custom token for webhook verification |
| `RECIPIENT_PHONE_NUMBER` | ✅ Yes | Phone number(s) without +, comma-separated |
| `SUPABASE_URL` | ✅ Yes | Your Supabase project URL |
| `SUPABASE_KEY` | ✅ Yes | Supabase anon/public key |
| `RECIPE_SEND_TIME` | ❌ No | Time to send recipes (default: `22:00`) |
| `DEBUG` | ❌ No | Enable debug mode (default: `False`) |
| `PORT` | ❌ No | Server port (default: `5001`) |
| `MIN_RECEIPTS_NEEDED` | ❌ No | Min receipts for predictions (default: `25`) |

---

## 🚢 Deployment

### General Deployment Steps

1. **Choose a hosting platform** (e.g., Heroku, Railway, Render, AWS, etc.)

2. **Set environment variables** on your hosting platform:
   - `WHATSAPP_TOKEN`
   - `WHATSAPP_PHONE_NUMBER_ID`
   - `WHATSAPP_VERIFY_TOKEN`
   - `RECIPIENT_PHONE_NUMBER`
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `RECIPE_SEND_TIME` (optional, default: `22:00`)
   - `DEBUG` (optional, default: `False`)

3. **Configure webhook URL** in Meta Developer Dashboard:
   - Go to [Meta for Developers](https://developers.facebook.com)
   - Navigate to your WhatsApp app
   - Set webhook URL to: `https://your-domain.com/webhook`
   - Set verify token (same as `WHATSAPP_VERIFY_TOKEN`)
   - Subscribe to `messages` events

4. **Deploy your application** using your platform's deployment method

---

## 📡 API Reference

### Health Check

```http
GET /health
```

**Response:**
```json
{
  "status": "ok",
  "message": "WhatsApp Recipe Bot is running!",
  "scheduler": {
    "running": true,
    "jobs_count": 3
  },
  "jobs": [
    {
      "id": "daily_recipe",
      "name": "Send daily recipe suggestion",
      "next_run": "2025-11-27 22:00:00 AEDT"
    }
  ]
}
```

### Webhook Endpoints

#### Verification (GET)

```http
GET /webhook?hub.mode=subscribe&hub.verify_token=YOUR_TOKEN&hub.challenge=CHALLENGE
```

Used by WhatsApp to verify webhook ownership.

#### Message Handler (POST)

```http
POST /webhook
Content-Type: application/json
```

Receives incoming WhatsApp messages and processes them automatically.

### Admin Endpoints (Debug Mode Only)

#### Seed Recipes

```http
POST /seed-recipes
```

Seeds initial recipes into the database.

#### Test Scheduler

```http
POST /test-scheduler
```

Manually triggers the daily recipe function (for testing).

#### Test Recipe Send

```http
POST /test-recipe
Content-Type: application/json

{
  "phone_number": "1234567890"
}
```

Sends a test recipe to specified number.

---

## 📁 Project Structure

```
Daily-Automation/
│
├── app.py                      # Main Flask application & routes
├── Procfile                    # Process configuration (for platforms that support it)
├── requirements.txt            # Python dependencies
├── runtime.txt                 # Python version specification
│
├── config/
│   └── supabase_config.py     # Supabase client setup
│
├── handlers/
│   ├── whatsapp_hanlder.py    # WhatsApp API functions (send messages)
│   ├── webhook_handler.py     # Webhook processing & message routing
│   ├── image_handler.py        # Receipt image processing & OCR
│   ├── prediction_handler.py   # AI grocery prediction generation
│   └── feedback_handler.py    # Feedback processing & accuracy calculation
│
├── utils/
│   ├── scheduler_utils.py      # APScheduler setup & job definitions
│   ├── recipe_utils.py         # Recipe selection & history management
│   ├── receipt_storage.py      # Receipt CRUD operations
│   ├── grocery_prediction_utils.py  # Prediction data processing
│   ├── session_manager.py     # Feedback session management
│   └── prompt_tracking.py     # LLM prompt metrics tracking
│
└── utils/db_migrations/
    ├── grocery_schema.sql      # Main database schema
    └── prompt_metrics_schema.sql  # Metrics tracking schema
```

---

## 🎯 Usage Examples

### User Interactions

**Get Daily Recipe:**
```
User: (waits for 22:00)
Bot: 🍽️ Daily Recipe Suggestion
     Tomorrows's  dinner idea: Pasta Carbonara
     Reply 'not today' if you'd like a different suggestion!
```

**Request Alternative:**
```
User: not today
Bot: 🔄 Alternative Suggestion
     How about: Chicken Curry?
```

**Get Grocery Prediction:**
```
User: grocery
Bot: 🛒 Shopping List
     When: Dec 1 - Dec 5
     Items:
     1. Milk
     2. Bread
     3. Eggs
     ...
```

**Submit Receipt:**
```
User: (sends receipt image)
Bot: 📸 Receipt received, processing...
     ✅ Receipt processed successfully! Found 15 items from Coles.
```

---

## 📝 Notes

- **Timezone:** Uses `Australia/Sydney` (handles daylight saving automatically)
- **Scheduler:** Uses APScheduler with `daemon=False` for production compatibility
- **Test Mode:** Test endpoints only available when `DEBUG=True`
- **WhatsApp Limits:** Test numbers have 24-hour messaging window

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is private and proprietary.

---

## 🙏 Acknowledgments

- Built with [Flask](https://flask.palletsprojects.com/)
- Uses [WhatsApp Cloud API](https://developers.facebook.com/docs/whatsapp)
- Database powered by [Supabase](https://supabase.com)
- Scheduling with [APScheduler](https://apscheduler.readthedocs.io/)

---

**Made with ❤️ by @DHRUV PATEL for fun and learning**
