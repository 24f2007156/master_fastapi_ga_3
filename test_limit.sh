uvicorn main:app --port 8000 &
PID=$!
sleep 2
for i in {1..18}; do
  curl -s -i "http://localhost:8000/orders" -H "X-Client-Id: test"
done
kill $PID
