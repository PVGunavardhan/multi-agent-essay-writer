# AI Essay Writer - Deployment Guide

This guide covers deploying the AI Essay Writer to various cloud platforms.

## 🚀 Quick Deploy Options

### Render (Recommended)
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

1. Fork this repository to your GitHub account
2. Connect your GitHub account to Render
3. Create a new Web Service from your forked repository
4. Set environment variables in Render dashboard
5. Deploy!

### Railway
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template)

1. Click the Railway deploy button
2. Connect your GitHub account
3. Set environment variables
4. Deploy automatically

### Heroku
[![Deploy to Heroku](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)

1. Click the Heroku deploy button
2. Set up environment variables
3. Deploy the application

## 📋 Environment Variables Required

For any deployment platform, you'll need these environment variables:

```bash
# Required API Keys
GROQ_API_KEY=your_groq_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here

# OAuth Credentials (at least one required)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret

# Application Security
SECRET_KEY=your_secret_key_here_use_strong_random_string

# Production Settings
DASH_DEBUG=False
OAUTHLIB_INSECURE_TRANSPORT=0
```

## 🔧 Platform-Specific Instructions

### Render Deployment

1. **Fork Repository**: Fork this repo to your GitHub
2. **Create Web Service**: 
   - Go to Render Dashboard → New → Web Service
   - Connect your GitHub repository
   - Choose the forked repository
3. **Configure Service**:
   - **Name**: `ai-essay-writer`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:server`
4. **Environment Variables**: Add all required variables in the Environment tab
5. **Deploy**: Click "Create Web Service"

### Railway Deployment

1. **Connect Repository**: Link your GitHub account
2. **Deploy from GitHub**: Select your forked repository
3. **Environment Variables**: Set in the Variables tab
4. **Domain**: Railway provides a custom domain automatically

### Heroku Deployment

1. **Create App**: `heroku create your-app-name`
2. **Set Environment Variables**:
   ```bash
   heroku config:set GROQ_API_KEY=your_key
   heroku config:set TAVILY_API_KEY=your_key
   # ... set all other variables
   ```
3. **Deploy**: `git push heroku main`

### Vercel Deployment

1. **Install Vercel CLI**: `npm i -g vercel`
2. **Deploy**: `vercel --prod`
3. **Set Environment Variables**: In Vercel dashboard

## 🔐 OAuth Setup for Production

### Google OAuth
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create/select project
3. Enable Google+ API
4. Create OAuth 2.0 credentials
5. Add authorized redirect URI: `https://your-domain.com/login/google/authorized`

### GitHub OAuth
1. Go to GitHub Settings → Developer settings → OAuth Apps
2. Create new OAuth App
3. Set Homepage URL: `https://your-domain.com`
4. Set Authorization callback URL: `https://your-domain.com/login/github/authorized`

## 📦 Database Considerations

### SQLite (Default)
- Works for small to medium traffic
- No additional setup required
- File-based storage

### PostgreSQL (Recommended for Production)
Add to your environment variables:
```bash
DATABASE_URL=postgresql://user:password@host:port/database
```

Update requirements.txt:
```
psycopg2-binary
```

## 🎯 Production Optimizations

### Performance
- Set `DASH_DEBUG=False` in production
- Use PostgreSQL for better performance
- Enable gzip compression
- Use CDN for static assets

### Security
- Use strong SECRET_KEY (32+ random characters)
- Set `OAUTHLIB_INSECURE_TRANSPORT=0` for HTTPS
- Use environment variables for all secrets
- Enable HTTPS/SSL

### Monitoring
- Enable application logs
- Set up error tracking (e.g., Sentry)
- Monitor resource usage
- Set up health checks

## 🔍 Troubleshooting

### Common Issues

1. **OAuth Redirect Mismatch**
   - Ensure redirect URIs in OAuth apps match your domain
   - Use HTTPS in production

2. **Database Connection Issues**
   - Check DATABASE_URL format
   - Ensure database is accessible

3. **Missing Environment Variables**
   - Verify all required variables are set
   - Check for typos in variable names

4. **SSL/HTTPS Issues**
   - Most platforms handle SSL automatically
   - Ensure OAuth settings use HTTPS URLs

### Logs and Debugging

Enable detailed logging:
```bash
# Add to environment variables
LOG_LEVEL=DEBUG
```

## 📞 Support

If you encounter deployment issues:
1. Check the deployment platform's documentation
2. Review application logs
3. Verify environment variables
4. Open an issue in the GitHub repository

## 🚀 Post-Deployment

After successful deployment:
1. Test OAuth login flows
2. Verify essay generation works
3. Check all UI components
4. Test with different user accounts
5. Monitor application performance