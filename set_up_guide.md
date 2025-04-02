Accelerator provides voice and text interaction capabilities to help vendors manage their business operations. This system leverages Azure cloud services and AI components to deliver a responsive and intelligent assistant experience.

## Architecture

The Vendor PA system consists of several integrated components:

```
┌─────────────────┐    ┌───────────────┐    ┌────────────────┐
│ Client Interface│    │ Container App │    │   Azure AI     │
│ (Voice/Text)    │───▶│ (FastAPI)     │───▶│   Services     │
└─────────────────┘    └───────────────┘    └────────────────┘
                              │                      │
                              ▼                      ▼
                       ┌──────────────┐     ┌────────────────┐
                       │ Azure Cosmos │     │  Azure Speech  │
                       │     DB       │     │    Service     │
                       └──────────────┘     └────────────────┘
                              │                      │
                              ▼                      ▼
                       ┌──────────────┐     ┌────────────────┐
                       │ Azure Redis  │     │   Azure AI     │
                       │    Cache     │     │    Search      │
                       └──────────────┘     └────────────────┘
```

### Key Components:

- **Bot Agents**: Modular components for handling different interaction types
  - `agent_audio.py` - Processes voice interactions
  - `agent_text.py` - Handles text-based conversations
  - `agent_proxy.py` - Routes requests to appropriate agents
  - `agent_audio_socket.py` - Manages WebSocket connections for real-time audio

- **Data Layer**: Stores and manages application data
  - Cosmos DB - Primary data store for device data, conversations, and transactions
  - Redis Cache - Fast in-memory cache for frequently accessed data and sessions 

- **AI Services**:
  - Azure Speech Service - Speech-to-text and text-to-speech conversions
  - Azure AI Search - Information retrieval capabilities and filter for tools
  - Azure OpenAI - Powers the conversational intelligence

- **Infrastructure**:
  - Azure Container Apps - Hosts the application in containers
  - Azure Application Insights - Monitoring and telemetry
  - Azure Automation Account - Manages operational tasks

## Setup

### Prerequisites

- Azure account with subscription
- Azure CLI installed and configured
- PowerShell 5.1 or later
- Python 3.11 or later
- Docker (for local development)

### Deployment 

#### 1. Deploy resources

```powershell
deploy.ps1 -prefix "vpa-test" -region "South India" -region_openai "South India" -region_speech "centralindia"
```

Parameters:
- `prefix`: Resource name prefix (default: "vpa-12")
- `region`: Primary region for deployment (default: "South India")
- `region_openai`: Region for OpenAI resources (default: "South India")
- `region_speech`: Region for Speech Service (default: "centralindia")

#### 2. Local Development Setup

1. Set up Python environment:
```bash
conda create -n vendorpa python=3.11
conda activate vendorpa
pip install -r bot/requirements.txt
pip install -r server/requirements.txt
```

2. Configure environment variables:
   - Rename .env2 to .env

3. Ingest data
```bash
python -m setup.ingest_data_db
python -m setup.ingest_data_index_langchain
``` 

#### 3. Start Server

```bash
# Build Docker image
docker build -t vendorpa:latest .

# Run Docker container
docker run -d --name vendorpa_container -p 8000:8000 vendorpa:latest

# Or Run server locally
uvicorn server.main:app --reload --port 8000
```

#### 4. Start bot

```bash
# websocket
python -m bot.agent_audio_socket

# amr / http streaming
python -m bot.agent_audio

#text
python -m bot.agent_text
```

## Pretext
Current scenario is built for a device (SoundPod). These devices are POS machines deployed by Fintech companies. Device has multiple models depending on features it supports, cards it accepts, languages it supports etc. The goal is to reduce the call volume for the customer care, where in most of the queries can easily be answered by the SoundPod. For any unresolved, Agent offers option to raise support tickets. This is positioned as merchant/vendor private assistant(vpa).

## Agents

1. **Device Info Agent**
   - Answers queries related to SoundPod
   - Available information 
      - Device info such as model, make, status, features
      - Device rental plans 
   - Sample queries
      - What is name of my device
      - What are features of echobox
      - What is my rental plan

2. **Transaction Agent**
   - Answers queries related to transaction made via SoundPod
   - Available information 
      - Daily collection till now
      - Weekly collection till now
      - Monthly collection till now
      - Last 10 transactions
   - Sample queries
      - What is my collection of the day
      - What is my collection of the week
      - What was my last transaction?
      - And one before that

3. **Notification Agent**
   - Answers queries related reminders, notifications for the Soundpod. Option to add/update/delete notifications. 
   - Available information 
      - Notification details 
   - Sample queries
      - What is schedule for my settlement announcement notification
      - I hear a message every morning at 6. It is very annoying.

4. **Troubleshooting Agent**
   - Answers queries related SoundPod issues
   - Available information 
      - Product manual for all the Soundpod models
      - Common issues and faq to troubleshoot
   - Sample queries
      - My device is not working properly
      - I see a red blinking light on my device
      - There is solid blue light on my device
      - Does my device supoort card transaction 
      - What is schedule for daily settlement

5. **Ledger/Khatabook Agent**
   - Answers queries related offline cash/ledger transactions
   - Available information 
      - Ledger/Khatabook total collection
      - Last 10 transaction with details of associated person/entity 
   - Sample queries
      - Record collection of Rs 250 from Mr Sharma in ledger
      - How much is total collection in Khatabook
      - How much is total collection in khatabook from Mr Sharma
      - When was last collection in Khatabook from Mr Sharma

6. **Support Ticket Agent**
   - Monitors all the conversations and based on context provides option to raise a ticket 
   - Additionally, you have the option to explicitly raise a ticket.  
   - Sample queries
      - Raise ticket for device not charging
      - I want to return my device


## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is proprietary and confidential.

