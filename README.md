# HubSpot to Duda Integration - Local Development

This is a Lambda function that creates SEO-optimized landing pages in Duda when HubSpot deals are marked as "Ready for Published".

## Project Structure

```
hubspot-duda-project/
├── lambda/                 # Lambda deployment package
│   ├── lambda_function.py
│   ├── content_generator.py
│   ├── duda_client.py
│   ├── hubspot_client.py
│   └── config.py
├── tests/                  # Unit tests
│   ├── __init__.py
│   ├── test_content_generator.py
│   ├── test_duda_client.py
│   └── test_hubspot_client.py
├── scripts/                # Utility scripts
│   ├── deploy.py          # Deploy to Lambda
│   ├── local_test.py      # Test locally
│   └── setup_env.py       # Setup environment
├── .env.example            # Example environment variables
├── .gitignore             # Git ignore rules
├── requirements.txt       # Python dependencies
├── requirements-dev.txt   # Development dependencies
├── Makefile              # Common commands
└── README.md             # This file
```

## Setup

1. **Clone and setup:**
   ```bash
   cd hubspot-duda-project
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements-dev.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Run tests:**
   ```bash
   pytest tests/
   ```

4. **Deploy to Lambda:**
   ```bash
   python scripts/deploy.py
   ```

## Environment Variables

Required:
- `HUBSPOT_API_KEY` - HubSpot API key
- `DUDA_API_USER` - Duda API username
- `DUDA_API_PASS` - Duda API password
- `OPENAI_API_KEY` - OpenAI API key

Optional:
- `CONTENT_LENGTH` - Content length (default: "3-4 sentences")
- `CONTENT_TONE` - Content tone (default: "professional")
- `DEFAULT_NUM_PAGES` - Default pages to create (default: 10)
- `LOGS_TABLE_NAME` - DynamoDB logs table (default: "hubspot-duda-logs")
- `NOTIFICATION_EMAIL` - Email for notifications
- `NOTIFICATION_EMAIL_FROM` - From email address

## Development

### Using Claude Code

1. Open project in PyCharm
2. Open Claude Code extension
3. Ask Claude to:
   - Add new features
   - Fix bugs
   - Write tests
   - Improve documentation

### Key Files to Edit

- **lambda/lambda_function.py** - Main webhook handler
- **lambda/content_generator.py** - Content generation logic
- **lambda/duda_client.py** - Duda API client
- **lambda/hubspot_client.py** - HubSpot API client

### Testing Locally

```bash
# Test with mock data
python scripts/local_test.py

# Run specific test
pytest tests/test_content_generator.py -v

# Run with coverage
pytest --cov=lambda tests/
```

## Deployment

### To AWS Lambda

```bash
# Create deployment package
python scripts/deploy.py

# Or manually:
cd lambda
zip -r ../lambda-deployment.zip .
# Upload to Lambda console
```

### Environment Variables in Lambda

Set these in Lambda's Configuration > Environment variables:
```
HUBSPOT_API_KEY=pat-na1-...
DUDA_API_USER=
DUDA_API_PASS=
OPENAI_API_KEY=sk-proj-...
CONTENT_LENGTH=3-4 sentences
CONTENT_TONE=professional
DEFAULT_NUM_PAGES=10
LOGS_TABLE_NAME=hubspot-duda-logs
NOTIFICATION_EMAIL=sean@zing-work.com
NOTIFICATION_EMAIL_FROM=support@zing-work.com
```

## How It Works

1. **Webhook Trigger** - HubSpot sends webhook when deal status = "Ready for Published"
2. **Deal Processing** - Lambda fetches deal details from HubSpot
3. **Content Generation** - OpenAI generates SEO-optimized content for nearby locations
4. **Duda Integration** - Creates pages in Duda's Dynamic Content Manager
5. **Logging** - Records all operations (can be sent to DynamoDB/email)

## Support

For issues or questions, check the logs in CloudWatch or run local tests.
