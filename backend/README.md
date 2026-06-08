# 🏛️ FinSight AI - Secure Read-Only Portfolio Intelligence Platform

> **Institution-grade portfolio analytics dashboard** for secure portfolio visualization, AI-powered insights, and real-time market data.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.14.3](https://img.shields.io/badge/Python-3.14.3-blue)](https://www.python.org/)
[![Node.js 18+](https://img.shields.io/badge/Node.js-18%2B-green)](https://nodejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-green)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-15-black)](https://nextjs.org/)

---

## 🎯 Quick Start

### ⚡ Fastest Way (Docker Compose)

```bash
# 1. Clone and setup
git clone <repo-url>
cd Finsight_ai
cp .env.example .env

# 2. Start everything
docker-compose up --build

# 3. Open in browser
# Frontend: http://localhost:3000
# API Docs: http://localhost:8000/docs
```

### 📜 Manual Setup

```bash
# Generated keys (save to .env)
python -c "import secrets; print(f'SECRET_KEY={secrets.token_urlsafe(64)}')"
python -c "from cryptography.fernet import Fernet; print(f'ENCRYPTION_KEY={Fernet.generate_key().decode()}')"

# Backend
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend && npm install && npm run dev
```

See [SETUP.md](SETUP.md) for detailed instructions.

---

## 🔒 Security First

FinSight AI is **100% READ-ONLY**:
- ✅ No trade execution
- ✅ No order placement
- ✅ No fund transfers
- ✅ No credential storage
- ✅ Encrypted broker tokens
- ✅ JWT authentication
- ✅ Audit logging

---

## ✨ Features

### 📊 Portfolio Analytics
- **Unified Dashboard** — Aggregate from Zerodha, Angel One, Binance
- **Real-time Streaming** — WebSocket live price updates
- **P&L Tracking** — Day change, total P&L, historical performance
- **Sector Allocation** — Visual breakdown by sector
- **Risk Analysis** — Portfolio diversification & exposure metrics

### 🤖 ML-Powered Insights
- **Volatility Prediction** — XGBoost-based scoring
- **Trend Detection** — RandomForest pattern recognition
- **Risk Scoring** — Comprehensive portfolio risk analysis
- *Educational & analytical only - no buy/sell recommendations*

### 🎨 Premium UI/UX
- Modern fintech design with glassmorphism
- TradingView interactive charts
- Responsive (desktop & mobile)
- Dark mode with smooth animations
- Institution-grade usability

### 🔌 Integrations
| Broker | Status | Methods | Auth |
|--------|--------|---------|------|
| **Zerodha** | ✅ Live | Holdings, Positions, Funds | OAuth |
| **Angel One** | ✅ Live | Holdings, Positions, Funds | TOTP |
| **Binance** | ✅ Live | Holdings, Positions (Spot) | API Key |

---

## 🛠️ Tech Stack

```
Frontend          Backend           Database        Infrastructure
├─ Next.js 15     ├─ FastAPI        ├─ PostgreSQL   ├─ Docker
├─ React 19       ├─ Python 3.14.3  ├─ Redis        ├─ Docker Compose
├─ TypeScript     ├─ SQLAlchemy     ├─ Celery       └─ (Deploy to
├─ Tailwind CSS   ├─ Pydantic       └─ Alembic      Vercel/Railway/AWS)
├─ shadcn/ui      └─ JWT + OAuth2
├─ Zustand        
└─ Recharts/TradingView Charts
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│           Frontend (Next.js + React)            │
│  Dashboard | Holdings | Analytics | Profile     │
└────────────────────┬────────────────────────────┘
                     │ HTTPS + JWT
┌────────────────────▼────────────────────────────┐
│           FastAPI Backend (Python)              │
│  ├─ Auth Service                                │
│  ├─ Broker Integration                          │
│  ├─ Portfolio Aggregation                       │
│  ├─ ML Analytics                                │
│  └─ WebSocket Service                           │
└────────────┬──────────────────┬─────────────────┘
             │                  │
         ┌───▼────┐         ┌───▼────┐
         │PostgreSQL         │ Redis  │
         │ Database          │ Cache  │
         └────────┘          └────────┘
```

---

## 📱 Core Pages

| Page | Purpose |
|------|---------|
| **Login/Register** | JWT authentication with email/password |
| **Dashboard** | Portfolio overview, P&L, quick stats |
| **Holdings** | All positions, sector breakdown, filters |
| **Analytics** | Risk metrics, performance, ML predictions |
| **Profile** | User settings, connected brokers |

---

## 💾 Database Schema

```sql
users              -- User accounts & profiles
broker_connections -- Connected broker accounts (encrypted tokens)
holdings           -- Long-term equity positions
positions          -- Intraday/trading positions
predictions        -- ML model outputs
portfolio_snapshots-- Historical value snapshots
audit_logs         -- Security audit trail
```

---

## 🔐 Security Features

- ✅ **JWT Authentication** with 30-min token expiry
- ✅ **Fernet Encryption** for broker access tokens at rest
- ✅ **OAuth 2.0** for broker account linking
- ✅ **Rate Limiting** to prevent abuse
- ✅ **CORS Protection** with strict origins
- ✅ **Secure Headers** (CSP, X-Frame-Options, etc.)
- ✅ **Audit Logging** for all sensitive operations
- ✅ **Role-Based Access Control** (user, admin)
- ✅ **Environment-Based Secrets** (never in code)
- ✅ **HTTPS Only** in production

---

## 📚 API Endpoints

### Authentication
```
POST   /auth/register          Sign up
POST   /auth/login             Login
POST   /auth/refresh           Refresh token
GET    /auth/me                Get profile
```

### Broker Integration
```
GET    /broker/brokers         List brokers
POST   /broker/connect/:broker Start OAuth
GET    /broker/callback/:broker OAuth callback
GET    /broker/connections     List connected
POST   /broker/disconnect/:id  Disconnect
```

### Portfolio
```
GET    /portfolio/summary      Overview
GET    /portfolio/holdings     All holdings
GET    /portfolio/positions    Open positions
GET    /portfolio/history      Value history
```

### Analytics
```
GET    /analytics/sector-allocation   Sectors
GET    /analytics/risk-metrics        Risk exposure
GET    /analytics/performance         Performance
GET    /analytics/predictions         ML predictions
```

### Real-time
```
WS     /ws                     Live prices
```

✅ **Full API docs available at `/docs` (Swagger UI)**

---

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest                  # All tests
pytest tests/test_auth.py  # Specific file
pytest --cov=app       # With coverage
```

### Frontend Tests
```bash
cd frontend
npm test               # Run tests
npm run lint          # Lint code
```

---

## 📖 Development Guide

### Project Structure
```
finsight-ai/
├── backend/
│   ├── app/
│   │   ├── core/          Config, DB, security
│   │   ├── models/        ORM (SQLAlchemy)
│   │   ├── routers/       API routes
│   │   ├── services/      Business logic
│   │   ├── schemas/       Validation (Pydantic)
│   │   ├── integrations/  Broker clients
│   │   ├── ml/            ML models
│   │   └── tasks/         Celery jobs
│   ├── tests/
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── app/           Pages
│   │   ├── components/    React components
│   │   ├── lib/           Utilities
│   │   ├── stores/        State (Zustand)
│   │   └── types/         TypeScript types
│   └── package.json
│
├── docker-compose.yml
├── .env                    Environment (don't commit!)
├── SETUP.md               Detailed setup
└── README.md              This file
```

### Adding a Broker

1. Create `backend/app/integrations/yourbroker.py`
2. Inherit from `BaseBroker`
3. Implement 4 read-only methods:

```python
from app.integrations.base import BaseBroker

class YourBrokerClient(BaseBroker):
    async def get_holdings(self) -> list[dict]:
        """Fetch holdings"""
        pass
    
    async def get_positions(self) -> list[dict]:
        """Fetch positions"""
        pass
    
    async def get_funds(self) -> dict:
        """Fetch available funds"""
        pass
    
    async def get_profile(self) -> dict:
        """Fetch account profile"""
        pass
```

---

## 🚀 Deployment

### Frontend (Vercel)
```bash
# Connect GitHub repo to Vercel
# Environment variables:
NEXT_PUBLIC_API_URL=https://api.yourapp.com/api/v1
NEXT_PUBLIC_WS_URL=wss://api.yourapp.com/api/v1/ws
```

### Backend (Render Free Tier)
```bash
# Push code, set environment variables:
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
SECRET_KEY=...
ENCRYPTION_KEY=...

# Render will provide PORT automatically; the backend listens on it.
```

### Database (Neon/Supabase)
```bash
# Create PostgreSQL instance
# Update DATABASE_URL
```

---

## 🐛 Troubleshooting

### Backend won't start
```bash
# Check PostgreSQL
psql -U postgres -d finsight_db -c "SELECT 1"

# Check Redis
redis-cli ping

# View logs
tail -f docker-compose logs backend
```

### Frontend won't build
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install && npm run build
```

### WebSocket fails to connect
- Verify backend is running
- Check `NEXT_PUBLIC_WS_URL` in frontend
- Test with: `wscat -c ws://localhost:8000/api/v1/ws`

---

## 📄 Environment Variables

### Database
```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/finsight_db
POSTGRES_USER=finsight
POSTGRES_PASSWORD=secure_password
POSTGRES_DB=finsight_db
```

### Redis & Celery
```env
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

### Security
```env
SECRET_KEY=<64+ char random string>
ENCRYPTION_KEY=<Fernet key>
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

### Broker APIs (optional - uses simulator if empty)
```env
KITE_API_KEY=your_key
KITE_API_SECRET=your_secret
ANGEL_API_KEY=your_key
ANGEL_CLIENT_ID=your_id
BINANCE_API_KEY=your_key
BINANCE_API_SECRET=your_secret
```

### Frontend
```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost:8000/api/v1/ws
```

---

## 📜 Important: Legal & Compliance

**This is a portfolio analytics platform ONLY:**
- ❌ No trade execution
- ❌ No order placement
- ❌ No fund transfers
- ❌ No investment advice
- ✅ Read-only visualization & analysis

Always comply with broker API terms and local laws.

---

## 📄 License

MIT License - see [LICENSE](LICENSE)

---

## 🤝 Support

- 📖 **Documentation**: [SETUP.md](SETUP.md)
- 🐛 **Issues**: GitHub Issues
- 💬 **Discussions**: GitHub Discussions
- 📧 **Email**: support@example.com

---

## 🎖️ Acknowledgments

- Powered by FastAPI & Next.js
- Charts: TradingView, Recharts
- UI: shadcn/ui & Radix UI
- Auth: python-jose, cryptography
- ML: XGBoost, scikit-learn

---

**Made with ❤️ for portfolio analytics enthusiasts**

🚀 **Ready to start?** Run `./setup.sh` or see [SETUP.md](SETUP.md)
