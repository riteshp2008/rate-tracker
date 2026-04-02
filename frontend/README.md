# NextJS Frontend

This is the optional bonus frontend for Rate-Tracker, built with Next.js 14.

## Features

✅ **Rate Comparison Table**

- Display latest rates per provider
- Sortable by rate value and effective date
- Responsive design (works on 375px+ screens)

✅ **30-Day Historical Chart**

- Line chart showing rate trends
- Min/Max/Average statistics
- Interactive tooltips

✅ **Auto-Refresh**

- Automatically refreshes every 60 seconds
- Manual refresh button
- Last updated timestamp

✅ **Loading & Error States**

- Visible loading spinners during data fetch
- Clear error messages if API is unavailable
- Graceful fallbacks

✅ **Responsive Design**

- Mobile-first approach
- Works on tablets and desktops
- Tailwind CSS styling

## Setup

### Prerequisites

- Node.js 18+ with npm/yarn
- Rate-Tracker backend running (http://localhost:8000/api)

### Installation

```bash
cd frontend
npm install
# or
yarn install
```

### Configuration

Create a `.env.local` file:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

### Development

```bash
npm run dev
# or
yarn dev
```

Visit: http://localhost:3000

### Building

```bash
npm run build
npm start
```

### Docker

The frontend runs as a service in `docker-compose.yml`:

```bash
make up                    # Start all services including frontend
docker-compose logs frontend  # View logs
```

## API Connection

The frontend connects to Django backend using the axios HTTP client (`lib/api.ts`).

**Required Endpoints:**

- `GET /api/rates/latest` - Latest rates
- `GET /api/rates/history` - Historical rates
- `GET /api/rates/providers` - Provider list
- `GET /api/rates/types` - Rate type list

If the backend is unavailable, the dashboard shows an error message.

## Architecture

```
frontend/
├── app/              # Next.js 14 app router
│   ├── layout.tsx   # Root layout
│   ├── page.tsx     # Dashboard page
│   └── globals.css  # Global styles
├── components/      # React components
│   ├── RateTable.tsx        # Sortable rate table
│   ├── RateHistoryChart.tsx # Recharts line chart
│   └── ui.tsx              # UI utilities
├── lib/
│   └── api.ts       # API client
├── package.json
├── tsconfig.json
├── tailwind.config.ts
└── next.config.js
```

## Component Breakdown

### RateComparisonTable

- Displays latest rates in sortable table
- Click column headers to sort
- Highlights rates in green
- Mobile responsive with horizontal scroll

### RateHistoryChart

- Renders historical rate trends
- Shows min/avg/max statistics
- Interactive tooltip on hover
- Empty state handling

### Dashboard (page.tsx)

- Main entry point
- Fetches rates and metadata
- Manages auto-refresh (60s interval)
- Error boundary and loading states

## Styling

Uses **Tailwind CSS** for styling:

- Responsive breakpoints: `sm:` (640px), `md:` (768px), `lg:` (1024px)
- Custom components in `globals.css`
- Mobile-first design (works at 375px)

## Performance

- Static exports possible: `npm run build && npm run export`
- ISR (Incremental Static Regeneration) ready
- Image optimization with `next/image`
- API response caching via HTTP headers

## Troubleshooting

**"Failed to fetch rates" error:**

- Ensure Django backend is running on http://localhost:8000
- Check CORS settings in Django (`CORS_ALLOWED_ORIGINS`)
- Verify API endpoints are accessible

**Styles not loading:**

```bash
rm -rf .next node_modules
npm install
npm run build
```

**Auto-refresh not working:**

- Check browser console for errors
- Verify API is returning data
- Check network tab for 429 rate limits

## Future Enhancements

- [ ] Provider-specific history filter
- [ ] Export rates to CSV
- [ ] Dark mode theme
- [ ] Real-time WebSocket updates
- [ ] Time range picker for chart
- [ ] Administrative dashboard
- [ ] Rate comparison overlay
