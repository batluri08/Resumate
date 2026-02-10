# RestlessResume 🚀

An AI-powered resume optimization tool that automatically tailors your resume to match job descriptions while preserving your original formatting.

## Features

- **One-time Upload**: Upload your resume once (PDF or DOCX format)
- **Smart Optimization**: AI analyzes the job description and tailors your resume content
- **Format Preservation**: Your resume layout, fonts, and styling stay intact
- **Instant Download**: Get your optimized resume ready to submit

## Quick Start

### Prerequisites

- Python 3.10+
- OpenAI API key

### Setup

1. **Create and activate virtual environment:**
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   ```bash
   # Copy the example env file
   copy .env.example .env   # Windows
   cp .env.example .env     # macOS/Linux

   # Edit .env and add your OpenAI API key
   OPENAI_API_KEY=sk-your-api-key-here
   ```

4. **Run the application:**
   ```bash
   uvicorn app.main:app --reload
   ```

5. **Open your browser:**
   Navigate to [http://localhost:8000](http://localhost:8000)

## How It Works

1. **Upload** your master resume (PDF or DOCX)
2. **Paste** the job description you're targeting
3. **Click Optimize** and wait for AI magic ✨
4. **Download** your tailored resume

## Project Structure

```
RestlessResume/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── routers/
│   │   └── resume.py        # API endpoints
│   ├── services/
│   │   ├── document_parser.py   # PDF/DOCX parsing
│   │   ├── ai_optimizer.py      # OpenAI integration
│   │   └── document_writer.py   # Format-preserving writer
│   └── templates/
│       └── index.html       # Frontend UI
├── static/
│   ├── css/style.css
│   └── js/app.js
├── uploads/                 # Temporary file storage
├── requirements.txt
├── .env.example
└── README.md
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Redirect to main page |
| `/resume` | GET | Main application page |
| `/resume/upload` | POST | Upload a resume file |
| `/resume/optimize` | POST | Optimize resume for job |
| `/resume/download/{id}` | GET | Download optimized resume |
| `/resume/cleanup/{id}` | DELETE | Clean up session |

## Technology Stack

- **Backend**: FastAPI (Python)
- **AI**: OpenAI GPT-4o
- **Document Processing**: python-docx, PyPDF2
- **Frontend**: Vanilla HTML/CSS/JavaScript

## Notes

- PDF uploads are converted to DOCX for output (PDF modification is complex)
- Files are stored temporarily and can be cleaned up via the API
- The AI preserves your truthful information—it never fabricates experience

## License

MIT License - Feel free to use and modify for your job search!

---

Made with ❤️ for job seekers everywhere
