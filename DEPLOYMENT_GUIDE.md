# LongContext Agent - Deployment Guide

This guide covers both local development and production deployment of the LongContext Agent.

## Prerequisites

- OpenAI API key
- Git repository (GitHub recommended)
- Render account (for backend)
- Vercel account (for frontend)

## Quick Local Development Setup

### 1. Clone and Setup

```bash
git clone <your-repo-url>
cd longcontext-agent
```

### 2. Backend Setup

```bash
cd backend
pip install -r requirements.txt
cp .env.local .env
# Edit .env and add your OPENAI_API_KEY
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend Setup

```bash
cd frontend
npm install
cp .env.local .env
# Edit .env and set VITE_API_URL=http://localhost:8000
npm run dev
```

## Production Deployment

### Step 1: Deploy Backend to Render

1. **Create Render Account**: Sign up at [render.com](https://render.com)

2. **Connect GitHub**: Link your GitHub repository to Render

3. **Create Web Service**:
   - Click "New +" → "Web Service"
   - Connect your repository
   - Configure the service:
     - **Name**: `longcontext-agent-backend`
     - **Region**: `Oregon (US West)`
     - **Branch**: `main`
     - **Runtime**: `Docker`
     - **Dockerfile Path**: `backend/Dockerfile`

4. **Environment Variables**:
   Add these environment variables in Render dashboard:
   ```
   OPENAI_API_KEY=your_actual_openai_api_key
   OPENAI_MODEL=gpt-4o-mini
   DATABASE_URL=sqlite:///./data/memory.db
   ENVIRONMENT=production
   PORT=10000
   ```

5. **Deploy**: Click "Create Web Service"

6. **Get Backend URL**: After deployment, note the URL (e.g., `https://longcontext-agent-backend.onrender.com`)

### Step 2: Deploy Frontend to Vercel

1. **Create Vercel Account**: Sign up at [vercel.com](https://vercel.com)

2. **Connect GitHub**: Link your GitHub repository

3. **Create New Project**:
   - Click "Add New..." → "Project"
   - Import your repository
   - Configure:
     - **Framework Preset**: `Vite`
     - **Root Directory**: `frontend`
     - **Build Command**: `npm run build`
     - **Output Directory**: `dist`

4. **Environment Variables**:
   Add in Vercel dashboard:
   ```
   VITE_API_URL=https://your-backend-url.onrender.com
   VITE_APP_TITLE=LongContext Agent
   NODE_ENV=production
   ```

5. **Deploy**: Click "Deploy"

### Step 3: Update CORS Settings

After frontend deployment, update backend CORS settings:

1. Go to Render dashboard → Your backend service → Environment
2. Add/update:
   ```
   ALLOWED_ORIGINS=["https://your-frontend-url.vercel.app"]
   ```
3. Redeploy the backend service

## Configuration Files Created

### Backend Files:
- `backend/Dockerfile` - Docker configuration
- `backend/.dockerignore` - Docker ignore rules
- `backend/.env.production` - Production environment template
- `backend/.env.local` - Local environment template
- `backend/start.sh` - Startup script
- `render.yaml` - Render service configuration

### Frontend Files:
- `frontend/vercel.json` - Vercel configuration
- `frontend/.env.production` - Production environment template

## Deployment Checklist

### Pre-deployment:
- [ ] OpenAI API key ready
- [ ] GitHub repository with all code
- [ ] All environment templates configured

### Backend Deployment (Render):
- [ ] Service created and configured
- [ ] Environment variables set
- [ ] Dockerfile builds successfully
- [ ] Health check passes at `/health`
- [ ] Database initializes properly

### Frontend Deployment (Vercel):
- [ ] Project created and configured
- [ ] Environment variables set
- [ ] Build completes successfully
- [ ] Site loads and connects to backend

### Post-deployment:
- [ ] CORS configured for frontend domain
- [ ] End-to-end testing completed
- [ ] Performance monitoring setup
- [ ] Demo URLs documented

## Troubleshooting

### Common Backend Issues:

1. **Build Failures**:
   - Check Dockerfile syntax
   - Verify all dependencies in requirements.txt
   - Check Python version compatibility

2. **Database Errors**:
   - Ensure data directory is created
   - Check database permissions
   - Verify SQLite installation

3. **Environment Variable Issues**:
   - Double-check OpenAI API key
   - Verify all required variables are set
   - Check for typos in variable names

### Common Frontend Issues:

1. **Build Failures**:
   - Check Node.js version (use 18+)
   - Verify all dependencies in package.json
   - Check TypeScript compilation errors

2. **API Connection Issues**:
   - Verify VITE_API_URL is correct
   - Check CORS configuration
   - Test API endpoints directly

3. **Environment Variable Issues**:
   - Ensure variables start with `VITE_`
   - Check Vercel dashboard settings
   - Verify build-time vs runtime variables

## Monitoring and Maintenance

### Health Checks:
- Backend: `https://your-backend-url.onrender.com/health`
- Frontend: Check main page loads

### Performance Monitoring:
- Monitor response times in Render dashboard
- Check error rates and logs
- Monitor OpenAI API usage

### Updates:
- Push code changes to main branch
- Automatic deployments trigger
- Monitor deployment status

## Security Considerations

1. **API Keys**: Never commit API keys to version control
2. **CORS**: Configure restrictive CORS policies
3. **HTTPS**: Both services use HTTPS by default
4. **Rate Limiting**: Implement in production if needed

## Cost Optimization

### Render (Backend):
- Free tier available with limitations
- Upgrade to paid plan for production use
- Monitor resource usage

### Vercel (Frontend):
- Generous free tier
- Pro plan for advanced features
- Monitor bandwidth usage

## Support and Resources

- [Render Documentation](https://render.com/docs)
- [Vercel Documentation](https://vercel.com/docs)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [Vite Deployment](https://vitejs.dev/guide/build.html)

---

**Next Steps**: Follow this guide step-by-step to deploy your LongContext Agent to production!