# 🔄 System Reset Guide

## 🚨 **What is System Reset?**

The System Reset feature allows you to completely clear all data from your LongContext Agent and start fresh. This is a **destructive operation** that cannot be undone.

## ⚠️ **What Gets Deleted**

When you reset the system, **ALL** of the following data is permanently deleted:

- ✅ **All conversation sessions**
- ✅ **All messages and chat history**
- ✅ **All stored memories**
- ✅ **All performance metrics**
- ✅ **All tool execution history**
- ✅ **Vector database embeddings**
- ✅ **Database auto-increment counters**
- ✅ **Cached embeddings in memory**

## 🎯 **When to Use System Reset**

### **Good Use Cases:**
- 🧪 **Testing**: Starting fresh for development or testing
- 🔄 **Clean Slate**: Removing all previous conversations for privacy
- 🐛 **Troubleshooting**: Clearing corrupted data or resolving issues
- 📊 **Benchmarking**: Starting with clean metrics for evaluation
- 🚀 **Production Deployment**: Clearing test data before going live

### **NOT Recommended For:**
- ❌ Fixing small issues (try restarting the backend first)
- ❌ Clearing just one conversation (use session delete instead)
- ❌ Regular maintenance (not needed)

## 📍 **How to Access Reset**

### **Method 1: Sidebar Settings**
1. Look for the **"Settings"** section in the left sidebar
2. Click the **"Reset System"** button

### **Method 2: Metrics Dashboard**
1. Navigate to the **"Metrics"** page
2. Expand the metrics display
3. Scroll to the **"Danger Zone"** section
4. Click **"Reset System"**

## 🔒 **Safety Features**

### **Confirmation Required:**
- You must type **`DELETE ALL DATA`** exactly (case-sensitive)
- The reset button is disabled until you type it correctly
- Multiple warnings are displayed before proceeding

### **Visual Warnings:**
- 🔴 Red color scheme indicates danger
- ⚠️ Warning icons throughout the interface
- 📝 Detailed list of what will be deleted

### **Process Feedback:**
- 🔄 Loading spinner during reset process
- ✅ Success confirmation when completed
- ❌ Error messages if reset fails

## 🚀 **Reset Process**

### **What Happens:**
1. **Backend Operations:**
   - Clears all database tables (sessions, messages, memories, metrics, tool_calls)
   - Deletes and recreates ChromaDB vector collection
   - Resets SQLite auto-increment counters
   - Vacuums database to reclaim disk space
   - Clears embedding cache

2. **Frontend Operations:**
   - Clears all React Query caches
   - Invalidates all cached data
   - Forces fresh data fetching

### **Timeline:**
- ⚡ **Small datasets**: ~1-2 seconds
- 📊 **Medium datasets**: ~3-5 seconds  
- 🗄️ **Large datasets**: ~5-10 seconds

## ✅ **After Reset**

### **What You Can Do Immediately:**
- Start new conversations
- Use all tools (calculator, web search, Wikipedia)
- View fresh metrics (will be empty initially)
- Create new sessions

### **What to Expect:**
- Empty session list
- No conversation history
- Zero metrics values
- Fresh embedding cache
- Clean database with no previous data

## 🔧 **API Endpoint**

For advanced users or automation:

```bash
POST /system/reset
```

**Response:**
```json
{
  "success": true,
  "message": "System reset completed successfully. All data has been cleared.",
  "timestamp": 1697123456.789
}
```

## ⚠️ **Important Notes**

1. **No Backup**: There is no automatic backup before reset
2. **No Undo**: This action cannot be reversed
3. **Immediate Effect**: Changes take effect immediately
4. **Session Persistence**: Any open browser sessions will see empty data
5. **Server Restart**: Not required after reset

## 🆘 **If Something Goes Wrong**

### **Reset Fails:**
1. Check server logs for detailed error messages
2. Restart the backend server
3. Try the reset operation again
4. If persistently failing, check database file permissions

### **Partial Reset:**
- Some data might remain if reset fails partway
- Safe to retry - the operation is designed to be repeatable
- Check logs to see which step failed

### **Recovery:**
- No built-in recovery mechanism
- You'll need to manually restore from backups if you have them
- Consider exporting important conversations before major resets

## 💡 **Tips**

1. **Before Reset**: Export any important conversations if needed
2. **Development**: Use reset frequently during development for clean testing
3. **Production**: Be extra careful and confirm you really want to delete all data
4. **Monitoring**: Watch the system logs during reset for any issues

---

**Remember: System Reset is a powerful tool that gives you a fresh start, but use it carefully since all data will be permanently lost!** 🚨