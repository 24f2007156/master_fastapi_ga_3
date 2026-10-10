uvicorn main:app --port 8000 &
PID=$!
sleep 1
echo "Preflight allowed origin:"
curl -I -X OPTIONS http://localhost:8000/stats -H "Origin: https://dash-z74j6s.example.com" -H "Access-Control-Request-Method: GET"
echo "Preflight evil origin:"
curl -I -X OPTIONS http://localhost:8000/stats -H "Origin: https://evil.com" -H "Access-Control-Request-Method: GET"
echo "GET stats:"
curl -i "http://localhost:8000/stats?values=1,2,3,4,5" -H "Origin: https://dash-z74j6s.example.com"
kill $PID
