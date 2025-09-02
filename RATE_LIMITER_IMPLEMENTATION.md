# Rate Limiter Implementation

## Overview

This implementation adds a PostgreSQL-backed rate limiter with query logging to all API endpoints. Users are limited to a **configurable number of requests per time window** (default: 20 requests per 24 hours) and all queries are logged with their results.

## Features

✅ **PostgreSQL Backend**: Uses PostgreSQL database for persistent rate limiting and query history  
✅ **Configurable Rate Limit**: Sliding window rate limiter with configurable time windows (default: 20 requests per 24 hours)  
✅ **Query Logging**: All requests, responses, and errors are logged to database  
✅ **User Email Integration**: All endpoints now require `user_email` field  
✅ **Remaining Requests**: API responses include `remaining_requests` field  
✅ **Error Handling**: Graceful handling of database failures  
✅ **Processing Time Tracking**: Logs response times for performance monitoring  

## Database Schema

### user_rate_limits
```sql
CREATE TABLE user_rate_limits (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) UNIQUE NOT NULL,
    request_count INTEGER NOT NULL DEFAULT 0,
    reset_time TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### query_history
```sql
CREATE TABLE query_history (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    endpoint VARCHAR(100) NOT NULL,
    prompt TEXT NOT NULL,
    result TEXT, -- JSON string of response
    success BOOLEAN NOT NULL DEFAULT TRUE,
    error_message TEXT,
    processing_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## API Changes

### Request Format (All Endpoints)
```json
{
  "prompt": "Compare proposal 1679 and 1680",
  "user_email": "krishna.nitkkr1@gmail.com"
}
```

### Response Format (All Endpoints)
```json
{
  "ids": ["1679", "1680"],
  "links": [],
  "proposals": [...],
  "analysis": "...",
  "remaining_requests": 19
}
```

### Rate Limit Error Response (HTTP 429)
```json
{
  "error": "Rate limit exceeded",
  "message": "You have exceeded the limit of 20 requests per second",
  "remaining_requests": 0
}
```

## Configuration

### Environment Variables (.env)
```bash
# PostgreSQL Configuration
POSTGRES_HOST=onchain-data.cwv6oeo2i03b.us-east-1.rds.amazonaws.com
POSTGRES_PORT=5432
POSTGRES_DATABASE=onchain-data
POSTGRES_USER=pa_postgres
POSTGRES_PASSWORD=subsquare22

# Rate Limiting Configuration
RATE_LIMIT_WINDOW_HOURS=24  # Time window in hours (default: 24 hours)
```

### Dependencies (requirements.txt)
```
asyncpg==0.29.0
sqlalchemy==2.0.23
alembic==1.13.1
```

## Implementation Details

### 1. Database Models (`app/models/database_models.py`)
- `UserRateLimit`: Tracks request counts and reset times
- `QueryHistory`: Stores all query logs with metadata

### 2. Database Service (`app/services/database.py`)
- Handles PostgreSQL connections using asyncpg
- Automatic table creation on startup
- Connection pooling and error handling

### 3. Rate Limiter Service (`app/services/rate_limiter.py`)
- Sliding window rate limiting (20 req/sec)
- Query logging with success/failure tracking
- Processing time measurement
- Cleanup functionality for old records

### 4. API Integration (`app/main.py`)
- Database initialization on startup
- Rate limiting middleware for all endpoints
- Automatic query logging
- Error handling and response formatting

## Usage Examples

### Basic Request
```bash
curl -X POST "http://localhost:8000/general-chat" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What are the main features of proposal 1679?",
    "user_email": "user@example.com"
  }'
```

### Response
```json
{
  "ids": ["1679"],
  "links": [],
  "proposals": [...],
  "answer": "Based on the proposal data...",
  "remaining_requests": 19
}
```

### Rate Limit Exceeded
```bash
# After 20 requests in 1 second
HTTP 429 Too Many Requests
{
  "detail": {
    "error": "Rate limit exceeded",
    "message": "You have exceeded the limit of 20 requests per second",
    "remaining_requests": 0
  }
}
```

## Testing

### Rate Limiter Test
```bash
python test_rate_limiter.py
```

### API Test
```bash
# Start the server
uvicorn app.main:app --reload --port 8000

# Test rate limiting
for i in {1..25}; do
  curl -X POST "http://localhost:8000/extract" \
    -H "Content-Type: application/json" \
    -d '{"prompt": "test", "user_email": "test@example.com"}' &
done
```

## Database Monitoring

### Check Rate Limits
```sql
SELECT user_email, request_count, reset_time 
FROM user_rate_limits 
ORDER BY updated_at DESC;
```

### Query Analytics
```sql
SELECT 
    endpoint,
    COUNT(*) as total_requests,
    AVG(processing_time_ms) as avg_response_time,
    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful_requests
FROM query_history 
WHERE created_at > NOW() - INTERVAL '1 hour'
GROUP BY endpoint;
```

### User Activity
```sql
SELECT 
    user_email,
    COUNT(*) as total_queries,
    MIN(created_at) as first_query,
    MAX(created_at) as last_query
FROM query_history 
GROUP BY user_email 
ORDER BY total_queries DESC;
```

## Deployment

### With Gunicorn
```bash
gunicorn app.main:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8002 \
  --access-logfile - \
  --error-logfile -
```

## Security Considerations

1. **Database Credentials**: Store PostgreSQL credentials securely
2. **Email Validation**: Consider adding email format validation
3. **DoS Protection**: Rate limiter helps prevent abuse
4. **Query Logging**: Be mindful of sensitive data in logs
5. **Database Access**: Ensure proper database access controls

## Maintenance

### Cleanup Old Records
The rate limiter includes automatic cleanup functionality:

```python
# Clean up records older than 30 days
await rate_limiter.cleanup_old_records(days_to_keep=30)
```

### Monitor Database Size
- Query history can grow large over time
- Consider implementing log rotation
- Monitor database storage usage

## Error Handling

The implementation includes robust error handling:
- Database connection failures don't break the API
- Rate limiting gracefully degrades if database is unavailable
- Query logging failures don't affect main request processing
- Detailed error logging for debugging

## Performance Considerations

- Database queries are optimized with proper indexes
- Connection pooling for efficient database usage
- Asynchronous operations throughout
- Minimal performance impact on API responses
- Processing time tracking for monitoring

This implementation provides a production-ready rate limiting solution with comprehensive logging and monitoring capabilities.
