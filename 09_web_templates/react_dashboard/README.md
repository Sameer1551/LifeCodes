# react_dashboard

## Purpose
A modern React dashboard application built with Vite. It connects to a Python backend (Flask or FastAPI) to display system status.

## Stack
- **React 18**: UI Library
- **Vite**: Build tool and dev server (replaces Create React App)
- **ESLint**: Code quality

## Project Structure
- `public/`: Static assets
- `src/`: Application source code
  - `components/`: Reusable UI components
  - `App.jsx`: Main application layout
  - `main.jsx`: Entry point
- `vite.config.js`: Proxy configuration for backend API

## Prerequisites
- Node.js (v18 or higher)
- npm or yarn
- Python Backend running (from previous setup steps)

## How to Run

1.  **Install Dependencies**
    ```bash
    npm install
    ```

2.  **Start Development Server**
    ```bash
    npm run dev
    ```
    This starts the frontend on `http://localhost:3000`.

3.  **Backend Connection**
    The `vite.config.js` is configured to proxy `/api` requests to `http://127.0.0.1:8000`.
    Ensure your FastAPI or Flask backend is running on port 8000.

4.  **View in Browser**
    Open `http://localhost:3000`.

## Build for Production
To create a static build for deployment:
```bash
npm run build
