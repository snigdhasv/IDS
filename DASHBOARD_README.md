# IDS Real-time Dashboard - Next.js

A Grafana-inspired real-time dashboard for monitoring the Intrusion Detection System.

## Features

- **Real-time metrics** from ML consumer logs
- **Live attack feed** with confidence scores
- **Traffic statistics** (benign vs attacks)
- **Model ensemble agreement** visualization
- **Dark theme** inspired by Grafana

## Setup

```bash
cd /home/s-ujay/Programming/IDS
npx create-next-app@latest ids-dashboard --typescript --tailwind --app --no-src-dir
cd ids-dashboard
npm install recharts lucide-react
npm run dev
```

## Architecture

```
ML Consumer logs → Backend API → WebSocket → Dashboard UI
```

- Backend: Next.js API routes parse logs
- Frontend: React components with Recharts
- Updates: Real-time via polling or WebSocket

## Start Dashboard

```bash
cd ids-dashboard
npm run dev
```

Then open: http://localhost:3000
