run:
    dotenv run -- fastapi dev yourss/main.py

run-redis:
    docker run --rm -ti  -p 6379:6379 redis
    
test:
    pytest tests/
