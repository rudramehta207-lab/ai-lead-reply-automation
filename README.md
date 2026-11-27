# AI Lead-Reply Automation System

**Live Demo:** [ai-lead-reply-automation.onrender.com](https://ai-lead-reply-automation.onrender.com)  
*(Hosted on Render's free tier — first load may take ~1 minute to wake up. Please use dummy details when testing.)*

A lightweight Python and Flask web application that automatically responds to customer inquiries using the Google Gemini REST API and logs every lead into an Excel-compatible CSV file.

## Features
- **Instant AI Responses:** Uses Google's Gemini REST API (`gemini-3.5-flash-lite`) to generate polite, business-specific replies in seconds.
- **Fault-Tolerant API Calls:** Built-in auto-retry mechanism for temporary `503` service spikes along with timeout and connection error handling.
- **Automated Lead Logging:** Automatically timestamps and saves every inquiry and generated reply to `leads.csv` while displaying recent leads on the web dashboard.
- **Environment Security:** API credentials are isolated in a local `.env` file using `python-dotenv` and excluded from version control via `.gitignore`.

## Tech Stack
- **Backend:** Python, Flask
- **API Integration:** REST API (`requests`), Google Gemini API
- **Data Storage:** CSV (`leads.csv`)
- **Configuration:** `python-dotenv`

## Run Locally

1. Clone the repository:
   ```bash
   git clone [https://github.com/rudramehta207-lab/ai-lead-reply-automation.git](https://github.com/rudramehta207-lab/ai-lead-reply-automation.git)
   cd ai-lead-reply-automation
