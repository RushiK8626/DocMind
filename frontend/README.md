# MultiModal Document Intelligence Frontend

This is the frontend client for the MultiModal Document Intelligence platform. Built as a fast, responsive Single Page Application (SPA) using React, Vite, and custom CSS.

## Features

- **Authentication:** Register and log in secure sessions using JWT tokens.
- **Projects Dashboard:** Manage workspace projects to group related documents.
- **Document Management:** Upload PDFs, view document processing pipelines, list documents, and delete files.
- **Document Preview:** High-fidelity document viewer showing parsed layout sections, OCR highlights, and metadata.
- **Agentic Chat Interface:** Engage in dynamic RAG-based conversations with an LLM agent contextually aware of project documents.

## Tech Stack

- **Framework:** React (v19)
- **Routing:** React Router DOM (v7)
- **Icons:** Lucide React
- **Build Tool:** Vite
- **Styling:** Custom Vanilla CSS for premium, responsive layouts and smooth transitions.

## Getting Started

### Prerequisites

Make sure you have Node.js (v18 or higher) and npm installed.

### Setup Instructions

1. **Navigate to the frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Configure Environment Variables (Optional):**
   By default, the application connects to the Flask API at `http://localhost:5000`. You can configure a custom URL by creating a `.env` file or `.env.local` inside the `frontend` folder:
   ```env
   VITE_API_BASE_URL=http://localhost:5000
   ```

4. **Run the Development Server:**
   ```bash
   npm run dev
   ```
   Open your browser and navigate to the address shown in the terminal (usually `http://localhost:5173`).

### Other Scripts

- **Build for Production:**
  ```bash
  npm run build
  ```
- **Preview Production Build:**
  ```bash
  npm run preview
  ```
- **Lint Code:**
  ```bash
  npm run lint
  ```
