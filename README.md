# NeuralGCM Weather API

AI-powered weather prediction API inspired by Google's NeuralGCM research model.

## Features
- 15-day precipitation forecasts
- Extreme weather alerts
- 10+ preset city locations
- API key authentication with tiered rate limits

## Quick Start

```bash
pip install -r requirements.txt
python main.py
```

Open http://localhost:8001

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /forecast/{lat}/{lon}` | Get weather forecast |
| `GET /api/location/{city}` | Forecast for preset city |
| `GET /api/extreme-events` | Extreme weather alerts |
| `POST /api/register?name=YourName` | Get free API key |

## Demo API Key

Use `demo-free-key-2026` for testing (10 req/min)

## Deploy to Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

## Pricing

| Tier | Rate Limit | Price |
|------|-----------|-------|
| Free | 10/min | $0 |
| Starter | 60/min | $29/mo |
| Pro | 300/min | $99/mo |
| Enterprise | 1000/min | $499/mo |
