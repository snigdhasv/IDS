#!/bin/bash

# IDS Dashboard - Setup Script
# Creates a Next.js dashboard with Grafana-style theme

set -e

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                                                               ║"
echo "║         IDS Real-time Dashboard Setup                        ║"
echo "║         Grafana-inspired Next.js App                         ║"
echo "║                                                               ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo

# Check if we're in IDS directory
if [[ ! -f "run_realtime_engine.sh" ]]; then
    echo "❌ Error: Run this script from /home/s-ujay/Programming/IDS"
    exit 1
fi

echo "[1/5] Creating Next.js app..."
npx create-next-app@latest ids-dashboard \
    --typescript \
    --tailwind \
    --app \
    --no-src-dir \
    --import-alias "@/*" \
    --use-npm

cd ids-dashboard

echo "[2/5] Installing dependencies..."
npm install recharts lucide-react date-fns

echo "[3/5] Creating dashboard components..."
# Will create the actual components in the next step

echo "[4/5] Setting up API routes..."
# Will create API routes to parse logs

echo "[5/5] Configuration..."
cat > README.md << 'EOF'
# IDS Real-time Dashboard

Grafana-inspired dashboard for monitoring the Ensemble IDS.

## Start Development Server

\`\`\`bash
npm run dev
\`\`\`

Then open http://localhost:3000

## Features

- Real-time attack feed
- Traffic statistics (benign vs attacks)
- Model ensemble agreement visualization
- Confidence score trends
- Dark Grafana-style theme

## API Endpoints

- GET /api/stats - Current statistics
- GET /api/predictions - Recent predictions
- GET /api/live - Live feed (SSE)
EOF

echo "✅ Dashboard created in: ids-dashboard/"
echo
echo "To start the dashboard:"
echo "  cd ids-dashboard"
echo "  npm run dev"
echo
echo "Then open: http://localhost:3000"
