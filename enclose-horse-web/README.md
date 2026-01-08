# enclose.horse - Solved

A clone of the [enclose.horse](https://enclose.horse) puzzle game that **automatically displays the optimal solution** for any daily puzzle.

## Features

- 🐴 **Automatic Solution Display** - Fetches today's puzzle and shows the optimal wall placement
- 📅 **Past Puzzles** - Navigate to any past puzzle via the date picker or URL parameter
- 🎨 **Authentic Design** - Uses the same Schoolbell font and grass-green theme as the original
- 📱 **Responsive** - Works on desktop and mobile
- ⚡ **Fast** - Solutions are fetched from the enclose.horse API (no solver computation needed)

## How It Works

1. On load, the app fetches today's daily puzzle from `https://enclose.horse/api/daily/{date}`
2. It then fetches the optimal solution from `https://enclose.horse/api/levels/{id}/stats`
3. The puzzle grid is rendered with the optimal walls already placed
4. Navigate between dates using the Previous/Next buttons

## URL Parameters

You can load any date's puzzle by adding a `?date=` parameter:

```
https://your-domain.com/?date=2026-01-04
```

## Local Development

```bash
npm install
npm run dev
```

Visit http://localhost:5173

## Build for Production

```bash
npm run build
```

The built files will be in the `dist` folder.

## Deploy to AWS Amplify

### Option 1: Connect Repository (Recommended)

1. Push this folder to a GitHub/GitLab/Bitbucket repository
2. Go to [AWS Amplify Console](https://console.aws.amazon.com/amplify)
3. Click "New app" → "Host web app"
4. Connect your repository and select the branch
5. Amplify will auto-detect the `amplify.yml` build settings
6. Click "Save and deploy"

### Option 2: Manual Drag & Drop

1. Run `npm run build`
2. Go to [AWS Amplify Console](https://console.aws.amazon.com/amplify)
3. Click "New app" → "Host web app" → "Deploy without Git provider"
4. Drag and drop the `dist` folder
5. Click "Save and deploy"

## Tech Stack

- React 18 + TypeScript
- Vite
- Canvas API for game rendering
- No UI framework (pure CSS matching enclose.horse)

## Credits

- Original game: [enclose.horse](https://enclose.horse) by Shivers
- This is a fan project that uses the enclose.horse public API
