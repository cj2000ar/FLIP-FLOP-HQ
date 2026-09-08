# Alpaca Market Data Setup

## Get Credentials

1. Visit https://app.alpaca.markets
2. Sign in (create account if needed)
3. Dashboard → API Keys
4. Copy:
   - API Key
   - API Secret (save securely)

## Configure System

### Windows
```powershell
# Edit credentials file
notepad "C:\ProgramData\FlipFlop\secrets\market-api.env"

# Add:
ALPACA_API_KEY=your_api_key_here
ALPACA_API_SECRET=your_api_secret_here

# Save & restart scheduler
Restart-ScheduledTask -TaskName "FlipFlop-Scheduler"
```

### Linux
```bash
# Edit credentials
sudo nano /etc/flipflop/market-api.env

# Add:
export ALPACA_API_KEY=your_api_key_here
export ALPACA_API_SECRET=your_api_secret_here

# Restart service
sudo systemctl restart flipflop-scheduler
```

## Verify Connection

```bash
curl http://localhost:8000/health

# Should show fresh data age < 5 minutes
```

## Market Data Available

- ES (S&P 500 Futures)
- NQ (Nasdaq Futures)
- MES (Micro E-mini S&P 500)
- MNQ (Micro E-mini Nasdaq)
- AAPL, MSFT, GOOGL (stocks)
- Custom tickers

## SIP vs Standard

- **SIP Data**: $150/month, high-fidelity
- **Standard Data**: $0/month, delayed

This system uses whichever available. Fallback to synthetic if credentials missing.

## Troubleshooting

**"Credentials missing" warning**: API key not set. System uses synthetic data until configured.

**"Authentication failed"**: Wrong credentials. Verify at alpaca.markets/api-keys

**Data gaps**: Market closed (equities) or data not available for ticker
