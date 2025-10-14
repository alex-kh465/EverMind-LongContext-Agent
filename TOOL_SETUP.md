# 🔧 Tool Setup and Usage Guide

## 🚀 **Available Tools**

The LongContext Agent now supports **3 powerful tools** that enhance its capabilities:

### ✅ **1. Advanced Calculator**
- **Capabilities**: Mathematical expressions, functions, constants
- **Triggers**: "calculate", "compute", "math", "solve", "+", "-", "*", "/", "="
- **Examples**:
  - "Calculate 15 * 4 + 22"
  - "What is sqrt(144)?"
  - "Compute sin(pi/2)"
  - "Solve 2^8"

### ✅ **2. Web Search (SerpAPI)**
- **Capabilities**: Real-time Google search results, news, knowledge graphs
- **Triggers**: "search", "find", "look up", "what is", "who is", "current", "latest", "news"
- **Examples**:
  - "Search for latest AI developments"
  - "What is the current weather in Tokyo?"
  - "Find recent news about SpaceX"
  - "Look up Python programming tutorials"

### ✅ **3. Wikipedia Search**
- **Capabilities**: Encyclopedia articles, definitions, comprehensive information
- **Triggers**: "wikipedia", "definition", "explain", "tell me about"
- **Examples**:
  - "Tell me about quantum computing"
  - "Wikipedia search for Albert Einstein"
  - "Explain photosynthesis"
  - "Definition of machine learning"

---

## ⚙️ **Setup Instructions**

### **1. Environment Variables**

Add the following to your `backend/.env` file:

```bash
# OpenAI Configuration (Required)
OPENAI_API_KEY=your_openai_api_key_here

# SerpAPI Configuration (Required for Web Search)
SERPAPI_API_KEY=your_serpapi_key_here
```

### **2. Get SerpAPI Key**

1. **Sign up** at [SerpAPI](https://serpapi.com/)
2. **Free tier** includes 100 searches/month
3. **Copy your API key** from the dashboard
4. **Add it** to your `.env` file

### **3. Install Dependencies**

Dependencies are already installed, but if needed:

```bash
cd backend
pip install google-search-results aiohttp
```

---

## 🎯 **How to Use Tools**

### **Calculator Examples:**
```
User: "What is 25 * 4 + 15?"
Agent: Uses calculator → Returns "115"

User: "Calculate the square root of 256"  
Agent: Uses calculator → Returns "16"
```

### **Web Search Examples:**
```
User: "Search for latest news about AI"
Agent: Uses web search → Returns current articles and news

User: "What is the current stock price of Tesla?"
Agent: Uses web search → Returns real-time information
```

### **Wikipedia Examples:**
```
User: "Tell me about the Roman Empire"
Agent: Uses Wikipedia → Returns comprehensive article summary

User: "Explain quantum mechanics"
Agent: Uses Wikipedia → Returns educational content
```

---

## 🔍 **Tool Detection Logic**

The agent automatically detects which tool to use based on keywords:

| Tool | Keywords | Priority |
|------|----------|----------|
| **Calculator** | calculate, compute, math, solve, +, -, *, /, = | High |
| **Web Search** | search, find, look up, what is, who is, current, latest, news | Medium |
| **Wikipedia** | wikipedia, definition, explain, tell me about | Medium |

---

## 📊 **Tool Capabilities**

### **Calculator Features:**
- ✅ Basic arithmetic (`+`, `-`, `*`, `/`)
- ✅ Advanced functions (`sqrt`, `sin`, `cos`, `log`)
- ✅ Constants (`pi`, `e`)
- ✅ Parentheses and order of operations
- ✅ Safe expression evaluation

### **Web Search Features:**
- ✅ Google search results
- ✅ Knowledge graph information
- ✅ News articles
- ✅ Answer boxes
- ✅ Real-time information
- ✅ Safe search options

### **Wikipedia Features:**
- ✅ Article search
- ✅ Content summaries
- ✅ Relevance scoring
- ✅ Multiple article results
- ✅ Thumbnail images
- ✅ Article links

---

## 🚀 **Testing Tools**

### **1. Test Calculator:**
```
"Calculate 2^10"
"What is the area of a circle with radius 5?" 
"Solve 15 * 8 + 32 / 4"
```

### **2. Test Web Search:**
```
"Search for Python tutorials"
"What is the weather in New York?"
"Find latest tech news"
```

### **3. Test Wikipedia:**
```
"Tell me about artificial intelligence"
"Explain photosynthesis" 
"Wikipedia Marie Curie"
```

---

## ⚠️ **Troubleshooting**

### **Common Issues:**

1. **"SERPAPI_API_KEY not configured"**
   - Add your SerpAPI key to `.env` file
   - Restart the backend server

2. **"google-search-results package not installed"**
   - Run: `pip install google-search-results`

3. **Tools not triggering**
   - Check keyword triggers above
   - Try more explicit commands
   - Restart backend if needed

4. **Wikipedia searches failing**
   - Check internet connection
   - Try different search terms
   - Wikipedia API may be temporarily down

---

## 📈 **Performance Notes**

- **Calculator**: ~1-5ms (instant)
- **Web Search**: ~500-2000ms (depends on API)
- **Wikipedia**: ~300-1000ms (depends on article size)

Tools are executed in parallel with context retrieval for optimal performance!

---

## 🔮 **Future Tools**

Planned additions:
- 📧 **Email Tool** (send/read emails)
- 📅 **Calendar Tool** (schedule management)
- 🌤️ **Weather Tool** (detailed forecasts)
- 📊 **Data Analysis Tool** (CSV/JSON processing)
- 🔗 **URL Scraper Tool** (extract webpage content)

Ready to use all these powerful tools in your conversations! 🎉