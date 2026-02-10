# RestlessResume - AI-Powered Resume Optimizer

## Project Overview
A Python web application that automatically tailors resumes to job descriptions while preserving original formatting.

## Tech Stack
- **Backend**: Python with FastAPI
- **Frontend**: HTML/CSS/JavaScript
- **Document Processing**: python-docx, PyPDF2
- **AI Integration**: OpenAI API
- **File Handling**: Upload/download with format preservation

## Project Structure
```
RestlessResume/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── routers/
│   │   └── resume.py        # Resume upload and optimization endpoints
│   ├── services/
│   │   ├── document_parser.py   # Parse PDF/DOCX files
│   │   ├── ai_optimizer.py      # OpenAI integration for resume optimization
│   │   └── document_writer.py   # Write optimized resume preserving format
│   └── templates/
│       └── index.html       # Frontend UI
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
├── uploads/                 # Temporary file storage
├── requirements.txt
├── .env.example
└── README.md
```

## Development Guidelines
- Use async/await for FastAPI endpoints
- Preserve document formatting when modifying resumes
- Handle both PDF and DOCX file formats
- Implement proper error handling for file operations
- Keep AI prompts focused on resume optimization best practices

## Running the Project
1. Create virtual environment: `python -m venv venv`
2. Activate: `venv\Scripts\activate` (Windows)
3. Install dependencies: `pip install -r requirements.txt`
4. Set OpenAI API key in `.env` file
5. Run: `uvicorn app.main:app --reload`
