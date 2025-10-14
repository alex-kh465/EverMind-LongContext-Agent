# 🚀 LongContext Agent

A production-grade agentic framework that enables large-context reasoning for LLM-based systems with resilient multi-turn memory capabilities.

## 🧩 Overview

LongContext Agent retains, compresses, and reuses relevant context across long interactions and tool calls, preventing context rotting even when the total memory exceeds model limits.

## 🏗️ Architecture

```
longcontext-agent/
├── frontend/          # React + Tailwind + Vite (Vercel)
├── backend/           # FastAPI + Python (Render)
├── shared/            # Common schemas and constants
├── tools/             # Tool integrations (calculator, web search)
├── tests/             # Test suites
└── docs/              # Documentation
```

## 🎯 Core Features

- **Context Persistence**: Hybrid memory storage (SQLite + vector DB)
- **Smart Summarization**: GPT-4o-mini powered compression
- **Adaptive Context Loading**: Relevance-based memory retrieval
- **Tool Integration**: Extensible tool framework
- **Multi-Turn Reasoning**: Continuous session support
- **Real-time Visualization**: Memory metrics and analytics

## 📊 Evaluation Metrics

| Metric | Target | Description |
|--------|--------|-------------|
| Context Retention Accuracy | ≥85% | Relevant context recalled correctly |
| Compression Ratio | ≥2× | Token reduction efficiency |
| Retrieval Precision | ≥80% | Relevant memory retrieval accuracy |
| Response Latency | ≤3s | Average response time |
| Memory Growth | Linear | Efficient memory scaling |

## 🚀 Quick Start

### Backend Setup
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

## 🔧 Environment Variables

Create `.env` files in both frontend and backend directories:

**Backend (.env)**
```
OPENAI_API_KEY=your_openai_api_key
DATABASE_URL=sqlite:///./memory.db
ENVIRONMENT=development
```

**Frontend (.env)**
```
VITE_API_URL=http://localhost:8000
VITE_APP_TITLE=LongContext Agent
```

## 🧠 Core Components

- **memory_manager.py**: Context storage and lifecycle management
- **retriever.py**: Hybrid retrieval (vector + keyword search)
- **agent.py**: LLM orchestration and reasoning
- **summarizer.py**: Context compression strategies
- **tools/**: Extensible tool framework

## 🎨 Frontend Components

- **ChatInterface**: Real-time conversation panel
- **MemoryPanel**: Context visualization and metrics
- **MetricsDashboard**: Performance analytics
- **ToolsPanel**: Available tools and outputs

## 📱 Deployment

- **Frontend**: Vercel (automatic deployment from main branch)
- **Backend**: Render (containerized deployment)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.
