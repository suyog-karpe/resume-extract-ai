## AI-Resume-Extractor

### Overview
AI-Resume-Extract is a FastAPI-based service and a dummy streamlit platform for seamless User experience for extracting structured information from resumes. It supports PDF and DOCX formats, utilizing the Ollama LLM for intelligent data extraction.

### Features
- Upload resumes in PDF/word.
- Extract structured information: name, contact details, education, experience, projects, and skills.
- Uses Ollama (Qwen2.5:0.5B) for text processing.
- Saves extracted data as JSON.
- Provides API endpoints for processing resumes and saving extracted data.

### Installation
#### Prerequisites
- fastapi
- uvicorn
- pydantic
- python-multipart
- ollama
- python-docx
- pymupdf
- requests
- streamlit

#### Setup
```sh
# Clone the repository
git clone https://github.com/suyog-karpe/resume-extract-ai.git

# Create a virtual environment
python -m venv resume
source resume/bin/activate  # On Windows use `venv\Scripts\activate`

# Install dependencies
pip install -r requirements.txt

#Install snap if running on server
sudo snap install ollama

#install model
ollama run qwen2.5:3b  (Can use a bigger model but needs a GPU as Processing time increases exponentially.)
```

### Running the API
```sh
uvicorn main3:app --host 192.168.1.99:8000 --port 8000 --reload
```
### Running the APP
```sh
streamlit run app2.py
```

### API Endpoints
#### Extract Resume from URL
**Endpoint:**
```http
POST /extract-resume-file/
```
**Request Body:**
```file
`  upload file
```
**Response:**
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "mobile_number": "1234567890",
  "email": "john.doe@example.com",
  "address": "New York, USA",
  "Linkedin URL":"https://www.linkedin.com/in/john-doe/",
  "current-designation": "Software Engineer",
  "primary-skills": ["Python", "Machine Learning"],
  "secondary-skills": ["Python", "Machine Learning"],
  "extraction_id": "uuid"
}
```
Skills seperated according to current designation

#### Save Full JSON Data
**Endpoint:**
```http
POST /save-full-json/
```
**Request Body:**
```json
{
  "extraction_id": "uuid",
  "first_name": "John",
  "last_name": "Doe"
}
```
**Response:**
```json
{
  "message": "Full JSON data saved successfully"
}
```

### Project Structure
```
.
├── main.py            # FastAPI application
├── requirements.txt   # Python dependencies
├── README.md          # Documentation
├── app.py/            #streamlit apllication
└── Resume_JSONs/      # Storage for extracted JSON data
```

### Contributing
Contributing for HRMS Platform.

### License
qwen-research
