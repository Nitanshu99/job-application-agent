#!/bin/bash

echo "🔍 Verifying Job Application System Status..."
echo ""

# 1. Check if services are responding
echo "🌐 Testing service connectivity..."

# Test frontend
echo -n "Frontend (http://localhost:3000): "
if curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 | grep -q "200\|404\|302"; then
    echo "✅ Responding"
else
    echo "❌ Not responding"
fi

# Test backend API docs
echo -n "Backend API Docs (http://localhost:8000/docs): "
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs | grep -q "200"; then
    echo "✅ Responding"
else
    echo "❌ Not responding"
fi

# Test backend health endpoint
echo -n "Backend Health (http://localhost:8000/health): "
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health | grep -q "200"; then
    echo "✅ Healthy"
else
    echo "⚠️  May need health endpoint setup"
fi

# Test backend root
echo -n "Backend Root (http://localhost:8000): "
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000 | grep -q "200\|404\|422"; then
    echo "✅ Responding"
else
    echo "❌ Not responding"
fi

echo ""

# 2. Check process status
echo "🔧 Process Status..."
echo "Backend PID: $(ps aux | grep '[u]vicorn' | awk '{print $2}' | head -1 || echo 'Not found')"
echo "Frontend PID: $(ps aux | grep '[n]ode.*next' | awk '{print $2}' | head -1 || echo 'Not found')"

echo ""

# 3. Check recent logs for errors
echo "📋 Recent Backend Logs (last 10 lines)..."
if [ -f "app.log" ]; then
    tail -10 app.log | grep -E "(ERROR|CRITICAL|Exception)" || echo "No recent errors found"
else
    echo "No app.log found"
fi

echo ""
echo "📋 Recent Frontend Logs (last 5 lines)..."
if [ -f "frontend.log" ]; then
    tail -5 frontend.log
else
    echo "No frontend.log found"
fi

echo ""

# 4. Test API endpoint
echo "🧪 Testing API endpoint..."
api_response=$(curl -s http://localhost:8000/api/v1/auth/login 2>/dev/null || echo "Connection failed")
if echo "$api_response" | grep -q "404"; then
    echo "⚠️  Login endpoint returning 404 - may need route setup"
elif echo "$api_response" | grep -q "422\|405"; then
    echo "✅ Login endpoint exists (returned method/validation error - normal)"
elif echo "$api_response" | grep -q "Connection failed"; then
    echo "❌ Cannot connect to backend"
else
    echo "✅ API responding"
fi

echo ""

# 5. Check environment file
echo "📄 Environment Configuration..."
if [ -f ".env" ]; then
    echo "✅ .env file exists"
    echo "Environment variables:"
    grep -E "^[A-Z]" .env | head -5 | sed 's/=.*/=***/' || echo "No environment variables found"
else
    echo "⚠️  No .env file found - may need configuration"
fi

echo ""

# 6. Check Docker services (database, redis)
echo "🐳 Docker Services Status..."
if command -v docker &> /dev/null; then
    if docker ps | grep -q "postgres\|redis"; then
        echo "✅ Database/Redis containers running:"
        docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(postgres|redis)"
    else
        echo "⚠️  Database/Redis containers not running"
        echo "This may cause issues with user authentication and data storage"
        echo ""
        echo "To start them:"
        echo "docker-compose up -d db redis"
    fi
else
    echo "⚠️  Docker not found"
fi

echo ""
echo "🎯 Summary:"
echo ""

# Overall status
if curl -s http://localhost:3000 >/dev/null && curl -s http://localhost:8000 >/dev/null; then
    echo "🎉 SUCCESS! Your Job Application System is running!"
    echo ""
    echo "🌐 Access your system:"
    echo "   📱 Frontend UI: http://localhost:3000"
    echo "   📚 API Documentation: http://localhost:8000/docs"
    echo "   🔧 API Root: http://localhost:8000"
    echo ""
    echo "🚀 Next Steps:"
    echo "1. Open http://localhost:3000 in your browser"
    echo "2. Create an account or login"
    echo "3. Set up your profile and job preferences"
    echo "4. Start using the AI-powered job automation!"
    echo ""
    if ! docker ps | grep -q "postgres\|redis"; then
        echo "⚠️  Recommendation: Start database services for full functionality:"
        echo "   docker-compose up -d db redis"
    fi
else
    echo "❌ System not fully responsive"
    echo ""
    echo "🛠️  Troubleshooting steps:"
    echo "1. Check logs: tail -f app.log"
    echo "2. Restart: bash project_manager.sh stop && bash project_manager.sh run"
    echo "3. Check if ports 3000 and 8000 are available"
fi