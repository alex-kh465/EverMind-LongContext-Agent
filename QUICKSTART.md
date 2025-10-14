# 🚀 LongContext Agent - Quick Start Guide

## 📋 Prerequisites

- **Python 3.11+** (for backend)
- **Node.js 18+** (for frontend) 
- **OpenAI API Key** (for AI functionality)

## ⚡ Quick Start (Recommended)

### Option 1: Start Everything at Once
```powershell
# From the project root directory
.\start-project.ps1
```

This will start both servers in separate windows:
- **Frontend**: http://localhost:5173  
- **Backend**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### Option 2: Manual Setup

#### 1. Start the Backend
```powershell
cd backend
.\activate.ps1          # Activates virtual environment  
python start.py         # Starts FastAPI server
```

#### 2. Start the Frontend (in new terminal)
```powershell
cd frontend
.\start-dev.ps1         # Starts React dev server
```

## 🔧 Configuration

### Backend Environment
1. Copy `backend/.env.example` to `backend/.env`
2. Add your OpenAI API key:
```env
OPENAI_API_KEY=sk-your-api-key-here
```

### Frontend Environment
The frontend is pre-configured to connect to `http://localhost:8000`

## 🎯 Features

### ✅ **Optimized UI Components**
- **Responsive chat interface** with proper message display
- **Session management sidebar** with create/delete functionality  
- **Real-time connection status** indicator
- **Optimistic updates** for smooth UX
- **Mobile-responsive design**

### ✅ **Chat Functionality** 
- **Full conversation flow** - send messages and receive AI responses
- **Tool integration** - Calculator, web search, Wikipedia
- **Persistent memory** - Conversations are saved and retrievable
- **Session switching** - Switch between different conversation threads
- **Loading indicators** - Visual feedback during AI processing

### ✅ **Backend Features**
- **FastAPI server** with automatic documentation
- **SQLite + ChromaDB** for structured and vector storage
- **OpenAI integration** with GPT-4o-mini
- **Memory management** with intelligent compression
- **Tool system** with extensible framework

## 🧪 Testing the Chat

1. **Open the application** at http://localhost:5173
2. **Type a message** in the input field
3. **Press Enter** or click send
4. **Watch the AI respond** with tool usage if applicable

### Example Messages to Try:
- `"Calculate 15 * 23 + 42"`
- `"Search for information about React"`  
- `"What is machine learning?"`
- `"Remember that I prefer Python over JavaScript"`

## 🛠 Development

### Backend Development
- **Virtual environment** is automatically activated
- **Hot reload** enabled in development mode
- **Debug logging** shows all API calls
- **Database** files created in backend directory

### Frontend Development  
- **Vite dev server** with hot module replacement
- **TypeScript** with strict type checking
- **Tailwind CSS** for styling
- **React Query** for API state management

## 📊 Architecture

```
┌─────────────────┐    ┌──────────────────┐
│   React App     │────│   FastAPI        │
│   (Frontend)    │    │   (Backend)      │
│   Port: 5173    │    │   Port: 8000     │
└─────────────────┘    └──────────────────┘
         │                       │
         │                       ▼
         │              ┌─────────────────┐
         │              │  SQLite +       │
         │              │  ChromaDB       │ 
         │              │  (Storage)      │
         │              └─────────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌──────────────────┐
│  UI Components  │    │   OpenAI API     │
│  • Chat         │    │   • GPT-4o-mini  │
│  • Sessions     │    │   • Embeddings   │
│  • Memory       │    │   • Tools        │
└─────────────────┘    └──────────────────┘
```

## 🎉 Success Indicators

### ✅ **Working Chat Interface:**
- Messages appear in chat bubbles
- User messages on the right (blue)
- AI messages on the left (white)
- Typing indicators during AI processing
- Tool usage displayed in special cards

### ✅ **Session Management:**
- Sessions listed in left sidebar
- "New Chat" button creates conversations
- Session switching works smoothly
- Delete functionality available on hover

### ✅ **Connection Status:**
- Green banner = all systems working
- Yellow/red banner = issues detected
- Connection status updates in real-time

## 🚨 Troubleshooting

### Backend Issues
- **Check virtual environment**: `.\backend\activate.ps1`
- **Verify OpenAI API key** in `.env` file
- **Check port 8000** is available

### Frontend Issues  
- **Verify Node.js** version with `node --version`
- **Clear npm cache**: `npm cache clean --force`
- **Reinstall dependencies**: `rm -rf node_modules && npm install`

### Connection Issues
- **Ensure backend starts first** (port 8000)
- **Check browser console** for API errors
- **Verify CORS settings** in backend configuration

---

## 🎯 **The application is now fully optimized and ready for production-level usage!**

All UI components are responsive, chat functionality is working smoothly, and the full-stack integration is complete. You can now chat with the AI agent, use tools, manage sessions, and experience persistent memory across conversations.
