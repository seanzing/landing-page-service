# Claude Context for HubSpot to Duda Integration

## Project Overview

This is a Python Lambda function that automates the creation of SEO-optimized landing pages in Duda when HubSpot deals are marked as "Ready for Published".

**Tech Stack:**
- Python 3.8+
- AWS Lambda
- HubSpot API
- Duda API
- OpenAI API (content generation)
- requests library (HTTP calls)
- pytest (testing)

## Architecture

### Webhook Flow
1. HubSpot sends webhook when deal status changes to "Ready for Published"
2. Lambda receives webhook with contact ID and deal ID
3. Lambda fetches deal details from HubSpot
4. If deal has "Ready for Published" status and Duda site code:
   - Fetches contact location info
   - Generates nearby locations (10 or 50 based on deal type)
   - Uses OpenAI to create SEO-optimized content for each location
   - Creates pages in Duda's Dynamic Content Manager
5. Logs results (can send to DynamoDB or email)

### Key Files

**lambda/** - Core application
- `lambda_function.py` - Main webhook handler (370 lines)
- `content_generator.py` - OpenAI integration for content (392 lines)
- `duda_client.py` - Duda API wrapper (150+ lines)
- `hubspot_client.py` - HubSpot API wrapper (150+ lines)
- `config.py` - Configuration from environment variables

**tests/** - Unit tests
- `test_config.py` - Config system tests
- `test_content_generator.py` - Content generation tests
- `conftest.py` - Pytest configuration

**scripts/** - Utilities
- `deploy.py` - Create Lambda deployment zip
- `local_test.py` - Test locally
- `setup_env.py` - Load .env variables

## Important Code Patterns

### Configuration
All config comes from environment variables via `config.py`:
```python
from config import Config
config = Config()
api_key = config.HUBSPOT_API_KEY
```

### API Clients
Clients are initialized with credentials:
```python
hubspot = HubSpotClient(config.HUBSPOT_API_KEY)
duda = DudaClient(config.DUDA_API_USER, config.DUDA_API_PASS)
content_gen = ContentGenerator(config.OPENAI_API_KEY)
```

### Logging
All events logged for debugging:
```python
logger.info(f"Processing contact {contact_id}")
logger.error(f"Failed to create pages: {str(e)}")
```

### Error Handling
Try/except blocks return structured responses:
```python
return {
    'statusCode': 400,
    'body': json.dumps({'error': 'No Duda site code on deal'})
}
```

## Environment Variables

**Required:**
- `HUBSPOT_API_KEY` - HubSpot private app key (pat-na1-*)
- `DUDA_API_USER` - Duda account username
- `DUDA_API_PASS` - Duda account password
- `OPENAI_API_KEY` - OpenAI API key (sk-proj-*)

**Optional:**
- `CONTENT_LENGTH` - Default: "3-4 sentences"
- `CONTENT_TONE` - Default: "professional"
- `DEFAULT_NUM_PAGES` - Default: 10
- `LOGS_TABLE_NAME` - DynamoDB table for logging
- `NOTIFICATION_EMAIL` - Email for notifications

## Recent Fixes

### Pydantic Dependencies
- Removed pydantic_core dependency issues
- Using openai==0.27.8 (old version without pydantic)
- All code uses legacy `openai.ChatCompletion.create()` API

### Config System
- Created `config.py` that reads from environment variables
- No hardcoded secrets
- Validates required configuration

### Deal ID Prioritization
- **Bug Fixed**: When customer has multiple deals, now uses the deal ID from the webhook instead of fetching first associated deal
- Properly handles "Ready for Published" status check on correct deal
- Contact with deal A, deal B, and deal C → Uses whichever was marked "Ready for Published"

## Testing

Run tests with:
```bash
make test                    # All tests
pytest tests/ -v             # Verbose
pytest tests/test_content_generator.py -v  # Specific test
pytest --cov=lambda tests/   # Coverage report
```

## Deployment

### Local Testing
```bash
python scripts/local_test.py
```

### To Lambda
```bash
make deploy
# Creates lambda-deployment.zip
# Upload to AWS Lambda console
```

Or use AWS CLI:
```bash
aws lambda update-function-code \
  --function-name hubspot-duda-integration \
  --zip-file fileb://lambda-deployment.zip
```

## Code Style

- **Formatting**: Use `black` formatter (`make format`)
- **Linting**: Use `flake8` for code quality (`make lint`)
- **Docstrings**: Google-style docstrings on all functions
- **Type hints**: Add type hints where possible
- **Logging**: Use logger, not print()

## Common Tasks

### Add a New Feature
1. Create feature branch: `git checkout -b feature/description`
2. Edit files in `lambda/`
3. Write tests in `tests/`
4. Run: `make test`
5. Deploy: `make deploy`

### Fix a Bug
1. Check CloudWatch logs for error details
2. Write a test that reproduces the bug
3. Fix the code
4. Verify test passes
5. Deploy

### Optimize Performance
- Cache content generation results to reduce API calls
- Add request batching to reduce API round trips
- Consider async/await for parallel operations
- Profile with CloudWatch metrics

### Add Email Notifications
- Use AWS SES or SendGrid
- Add email config to `config.py`
- Send notification in `lambda_function.py` after page creation

## Known Limitations

1. **OpenAI Rate Limiting**: Generates content sequentially with 0.5s delay
   - Could be optimized with parallel requests
   - Current: ~50 pages = ~25 seconds

2. **Duda Site Code Required**: Must be set on deal to proceed
   - Falls back with error if missing

3. **No Retries on API Failures**: Single attempt per operation
   - Could add exponential backoff for failures

4. **Location Generation**: 60-mile radius approximation
   - OpenAI determines accuracy
   - Could use geolocation library for precision

## Getting Help with Claude Code

Select code and ask Claude to:
- "Explain what this function does"
- "Add error handling for API timeouts"
- "Write unit tests for this module"
- "Optimize this for performance"
- "Add caching to reduce API costs"

Claude can read the full project context and make informed suggestions!

## File Organization Rules

- Keep business logic in `lambda/`
- Keep tests in `tests/` with `test_` prefix
- Keep scripts in `scripts/` for utilities
- Use `config.py` for all settings
- Never commit `.env` file
- Update `requirements.txt` when adding packages

---

**Last Updated**: December 2025  
**Current Version**: Fully functional with multi-deal support and openai 0.27.8
