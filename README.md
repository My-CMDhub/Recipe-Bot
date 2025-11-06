# WhatsApp Recipe Bot

Automated daily dinner recipe suggestions via WhatsApp using WhatsApp Cloud API.

## Features

- 🍽️ Daily recipe suggestions at configured time (default: 22:00 Australian time)
- 🔄 Alternative recipe suggestions when user replies "not today"
- 👋 Friendly greeting and farewell responses
- 📋 Full recipe list when all recipes have been sent
- 🔁 Automatic daily reset at midnight

## Setup

### Prerequisites

- Python 3.11+
- Meta Developer Account with WhatsApp Cloud API access
- Supabase account
- WhatsApp test number (or verified business number)

### Installation

1. Clone the repository
2. Create virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Mac/Linux
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables (copy `.env.example` to `.env`):
   ```bash
   cp .env.example .env
   ```

5. Configure `.env` file with your credentials:
   - WhatsApp Cloud API credentials
   - Supabase credentials
   - Recipient phone number
   - Recipe send time (optional, default: 22:00)

6. Set up Supabase database:
   - Run the SQL schema in Supabase SQL Editor
   - Seed initial recipes: `POST /seed-recipes`

## Running Locally

```bash
python app.py
```

The app will run on `http://localhost:5001` (or port specified in PORT env var).

## Deployment

### Heroku

1. Install Heroku CLI
2. Login: `heroku login`
3. Create app: `heroku create your-app-name`
4. Set environment variables:
   ```bash
   heroku config:set WHATSAPP_TOKEN=your_token
   heroku config:set WHATSAPP_PHONE_NUMBER_ID=your_id
   heroku config:set WHATSAPP_VERIFY_TOKEN=your_token
   heroku config:set RECIPIENT_PHONE_NUMBER=your_number
   heroku config:set SUPABASE_URL=your_url
   heroku config:set SUPABASE_KEY=your_key
   heroku config:set RECIPE_SEND_TIME=22:00
   heroku config:set DEBUG=False
   ```

5. Deploy: `git push heroku main`

6. Update WhatsApp webhook URL in Meta Dashboard to your Heroku app URL

### Environment Variables

- `WHATSAPP_TOKEN` - WhatsApp Cloud API access token
- `WHATSAPP_PHONE_NUMBER_ID` - Your WhatsApp phone number ID
- `WHATSAPP_VERIFY_TOKEN` - Webhook verification token
- `RECIPIENT_PHONE_NUMBER` - Phone number to send recipes to (without +)
- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_KEY` - Your Supabase anon key
- `RECIPE_SEND_TIME` - Time to send recipes (HH:MM format, default: 22:00)
- `DEBUG` - Enable debug mode (True/False, default: False)
- `PORT` - Port to run on (default: 5001, Heroku sets this automatically)

## API Endpoints

- `GET /health` - Health check
- `GET /webhook` - Webhook verification (WhatsApp)
- `POST /webhook` - Receive WhatsApp messages
- `POST /seed-recipes` - Seed initial recipes (one-time)
- `POST /test-webhook` - Test webhook (debug mode only)
- `POST /test-recipe` - Test recipe sending (debug mode only)
- `POST /test-scheduler` - Test scheduler (debug mode only)

## Project Structure

```
.
├── app.py                 # Main Flask application
├── config/
│   └── supabase_config.py # Supabase client setup
├── handlers/
│   ├── whatsapp_hanlder.py # WhatsApp API functions
│   └── webhook_handler.py  # Webhook message processing
├── utils/
│   ├── recipe_utils.py      # Recipe selection and history
│   └── scheduler_utils.py  # APScheduler setup
├── requirements.txt        # Python dependencies
├── Procfile               # Heroku process file
└── runtime.txt            # Python version

```

## Notes

- Uses Australia/Sydney timezone (handles daylight saving automatically)
- Test endpoints are only available when `DEBUG=True`
- WhatsApp Cloud API test numbers require 24-hour messaging window
- For production, verify your business in Meta Business Manager

