# Multi-Agent ID & Link Extractor API

🧩 A FastAPI-based multi-agent system that extracts custom identifiers (IDs) and URLs from natural language prompts using specialized agents.

## 🎯 Features

- **Multi-Agent Architecture**: Coordinated system with specialized agents
- **LLM Extractor Agent**: Uses Google Gemini to intelligently extract custom IDs
- **Regex Extractor Agent**: Uses regex patterns to extract URLs
- **Coordinator Agent**: Orchestrates agents and aggregates results
- **RESTful API**: Clean FastAPI interface with automatic documentation
- **Comprehensive Testing**: Unit and integration tests included

## 🏗️ Architecture

```
app/
├── agents/                 # Agent implementations
│   ├── base_agent.py      # Base agent class
│   ├── llm_extractor_agent.py    # LLM-based ID extractor
│   └── regex_extractor_agent.py  # Regex-based URL extractor
├── models/                # Pydantic models
│   ├── request_models.py  # API request models
│   └── response_models.py # API response models
├── services/              # Business logic
│   └── coordinator_agent.py      # Main coordinator
└── main.py               # FastAPI application
```

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd clarys-mvp

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your Gemini API key (optional)
GEMINI_API_KEY=your_api_key_here
```

**Note**: The API works without Gemini API key using fallback rule-based ID extraction.

### 3. Run the API

```bash
# Using the run script
python run.py

# Or directly with uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Access the API

- **API Base URL**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## 📡 API Endpoints

### POST `/extract`

Extract IDs and links from a natural language prompt.

**Request Body:**
```json
{
  "prompt": "Compare proposal 1679 and 1680"
}
```

**Response:**
```json
{
  "ids": ["1679", "1680"],
  "links": []
}
```

### POST `/extract-with-proposals`

Extract IDs and links from a natural language prompt, fetch detailed proposal information from [Polkadot Polkassembly API](https://polkadot.polkassembly.io/api/v2/ReferendumV2/1679), AND provide AI-powered analysis/comparison.

**Request Body:**
```json
{
  "prompt": "Compare proposal 1679 and 1680",
  "proposal_type": "ReferendumV2",
  "fetch_proposals": true,
  "analyze_proposals": true
}
```

**Response:**
```json
{
  "ids": ["1679", "1680"],
  "links": [],
  "proposals": [
    {
      "id": "1679",
      "title": "CLARYS.AI Beta Product Development",
      "content": "## Why do we need Clarys.AI?...",
      "status": "Deciding",
      "created_at": "2025-07-18T07:26:49.489Z",
      "proposer": "146ZZqm2cMHLf3ju7oc8M9JnPaAktuADAKThagKnXqzjPJbZ",
      "beneficiaries": [...],
      "vote_metrics": {...},
      "timeline": [...],
      "error": null
    }
  ],
  "analysis": "Proposal 1679:\nTitle: CLARYS.AI Beta Product Development\nType: Referendum V2\n...\nComparison:\nCost: Proposal 1679 requests 129K USDC while Proposal 1680...\nImpact on Polkadot: Both proposals contribute to ecosystem growth..."
}
```

### GET `/health`

Health check endpoint.

**Response:**
```json
{
  "status": "healthy"
}
```

## 🧪 Example Usage

The API handles three distinct types of prompts:

### Scenario 1: ID-Only Prompts
Extract standalone identifiers that are not embedded in URLs.

```bash
curl -X POST "http://localhost:8000/extract" \
     -H "Content-Type: application/json" \
     -d '{"prompt": "Compare proposal id 1679 and 1680"}'
```

**Response:**
```json
{
  "ids": ["1679", "1680"],
  "links": []
}
```

### Scenario 2: Link-Only Prompts  
Extract complete URLs without extracting IDs from URL paths.

```bash
curl -X POST "http://localhost:8000/extract" \
     -H "Content-Type: application/json" \
     -d '{"prompt": "Compare https://polkadot.polkassembly.io/referenda/1679 and https://polkadot.polkassembly.io/referenda/1689"}'
```

**Response:**
```json
{
  "ids": [],
  "links": ["https://polkadot.polkassembly.io/referenda/1679", "https://polkadot.polkassembly.io/referenda/1689"]
}
```

### Scenario 3: Mixed Prompts
Extract both standalone IDs and complete URLs appropriately.

```bash
curl -X POST "http://localhost:8000/extract" \
     -H "Content-Type: application/json" \
     -d '{"prompt": "Compare proposal 1679 with https://polkadot.polkassembly.io/referenda/1689"}'
```

**Response:**
```json
{
  "ids": ["1679"],
  "links": ["https://polkadot.polkassembly.io/referenda/1689"]
}
```

### Enhanced Extraction with Proposal Details

Get detailed proposal information for extracted IDs:

```bash
curl -X POST "http://localhost:8000/extract-with-proposals" \
     -H "Content-Type: application/json" \
     -d '{
       "prompt": "Compare proposal 1679 and 1680",
       "proposal_type": "ReferendumV2",
       "fetch_proposals": true,
       "analyze_proposals": true
     }'
```

**Response:**
```json
{
  "ids": ["1679", "1680"],
  "links": [],
  "proposals": [
    {
      "id": "1679",
      "title": "CLARYS.AI Beta Product Development",
      "content": "## Why do we need Clarys.AI?\n\nDo you find OpenGov overwhelming?...",
      "status": "Deciding",
      "created_at": "2025-07-18T07:26:49.489Z",
      "proposer": "146ZZqm2cMHLf3ju7oc8M9JnPaAktuADAKThagKnXqzjPJbZ",
      "error": null
    }
  ],
  "analysis": "Proposal 1679:\nTitle: CLARYS.AI Beta Product Development\nType: Referendum V2\nProposer: 146ZZqm2c...\nReward: 129K USDC\n\nProposal 1680:\nTitle: SubWallet Development\nType: Referendum V2\n...\n\nComparison:\nCost: Proposal 1679 requests 129K USDC while Proposal 1680 requests different amount...\nImpact on Polkadot: Both contribute to ecosystem growth but in different ways..."
}
```

## 🧠 Agent Details

### LLM Extractor Agent
- **Purpose**: Extract custom identifiers using natural language understanding
- **Technology**: Google Gemini 2.5 Flash (with rule-based fallback)
- **Capabilities**: 
  - Understands context to identify custom IDs
  - Handles various ID formats (ID123, USER456, PROD789, etc.)
  - Fallback to regex patterns when LLM is unavailable

### Regex Extractor Agent
- **Purpose**: Extract URLs using pattern matching
- **Technology**: Python regex with comprehensive URL patterns
- **Capabilities**:
  - Extracts HTTP/HTTPS URLs
  - Validates extracted URLs
  - Handles various URL formats

### Coordinator Agent
- **Purpose**: Orchestrate other agents and aggregate results
- **Technology**: Async Python with parallel agent execution
- **Capabilities**:
  - Parallel agent execution for performance
  - Result aggregation and deduplication
  - Error handling and fallback management

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_agents.py

# Run API tests
pytest tests/test_api.py
```

## 🔧 Development

### Project Structure
```
clarys-mvp/
├── app/                   # Main application
│   ├── agents/           # Agent implementations
│   ├── models/           # Pydantic models
│   ├── services/         # Business logic
│   └── main.py          # FastAPI app
├── tests/                # Test suite
├── requirements.txt      # Dependencies
├── .env.example         # Environment template
├── run.py              # Run script
└── README.md           # Documentation
```

### Adding New Agents

1. Create agent class inheriting from `BaseAgent`
2. Implement the `process()` method
3. Add agent to coordinator
4. Write tests

### Environment Variables

- `GEMINI_API_KEY`: Gemini API key (optional)
- `API_HOST`: Server host (default: 0.0.0.0)
- `API_PORT`: Server port (default: 8000)
- `LOG_LEVEL`: Logging level (default: INFO)
- `ENVIRONMENT`: Environment mode (development/production)

## 🚀 Deployment

### Docker (Future Enhancement)
```bash
# Build image
docker build -t multi-agent-extractor .

# Run container
docker run -p 8000:8000 -e GEMINI_API_KEY=your_key multi-agent-extractor
```

### Production Considerations
- Set up proper logging and monitoring
- Configure rate limiting
- Add authentication if needed
- Use environment-specific configurations
- Set up health checks and metrics

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🔮 Future Enhancements

- **Additional Extractors**: Email addresses, phone numbers, dates
- **Custom ID Patterns**: User-configurable ID formats
- **Batch Processing**: Process multiple prompts simultaneously
- **Result Confidence**: Confidence scores for extractions
- **Caching**: Redis-based result caching
- **Metrics**: Detailed extraction metrics and analytics
- **Authentication**: API key-based authentication
- **Rate Limiting**: Request rate limiting and quotas