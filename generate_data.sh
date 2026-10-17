#!/bin/bash

TOKEN=$(curl -s -X POST http://127.0.0.1:8000/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"secret123"}' \
  | python -c "import sys, json; print(json.load(sys.stdin)['token'])")

echo "TOKEN = ${TOKEN:0:30}..."
echo

for i in $(seq 1 5); do
  echo "=== Round $i ==="
  RESP=$(curl -s -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/new-game)
  GID=$(echo "$RESP" | python -c "import sys, json; print(json.load(sys.stdin)['game_id'])")
  NUMS=$(echo "$RESP" | python -c "import sys, json; print(' '.join(str(x) for x in json.load(sys.stdin)['numbers']))")
  echo "game_id = $GID"
  echo "numbers = [$NUMS]"

  EXPR=$(python solve.py $NUMS)
  echo "solution = $EXPR"

  curl -s -X POST http://127.0.0.1:8000/check \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d "{\"game_id\":\"$GID\",\"expression\":\"$EXPR\"}" | python -m json.tool

  echo
done

echo "=== 我的统计 ==="
curl -s -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/my-stats | python -m json.tool
