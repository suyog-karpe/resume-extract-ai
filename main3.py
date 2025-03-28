import json
import os
import uuid
import requests
import re
import fitz  # pymupdf
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from fastapi import FastAPI, HTTPException, File, UploadFile
from pydantic import BaseModel
from tempfile import gettempdir
import ollama
from docx import Document
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Use system's temp directory
TEMP_DIR = gettempdir()

# Store extracted data temporarily
extraction_data_storage = {}

class ConfirmationRequest(BaseModel):
    extraction_id: str
    confirm: bool  # True for yes, False for no

class SaveFullJsonRequest(BaseModel):
    extraction_id: str
    first_name: str
    last_name: str

def safe_get(data, *keys, default=None):
    """Safely retrieve nested values from a dictionary."""
    for key in keys:
        if isinstance(data, dict) and key in data:
            data = data[key]
        else:
            return default
    return data if data is not None else default

def download_file(file_url: str, save_path: str) -> bool:
    """Download a file from a URL and save it locally."""
    try:
        response = requests.get(file_url, stream=True)
        response.raise_for_status()
        with open(save_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        return True
    except Exception as e:
        print(f"Download failed: {e}")
        return False

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF using pymupdf4llm (pymupdf)."""
    try:
        doc = fitz.open(pdf_path)  # Open PDF
        text = "\n".join([page.get_text("text") for page in doc])  # Extract text from pages
        return text.strip()
    except Exception as e:
        raise RuntimeError(f"PDF text extraction failed: {str(e)}")

def extract_text_from_docx(docx_path: str) -> str:
    """Extract text from a DOCX file."""
    try:
        doc = Document(docx_path)
        return "\n".join([para.text for para in doc.paragraphs])
    except Exception as e:
        raise RuntimeError(f"DOCX text extraction failed: {str(e)}")

def format_resume_prompt(resume_text: str) -> str:
    prompt = f'''Extract the following information from the resume in **precise JSON format**:
- **Primary skills MUST be directly related to current designation**
- **Secondary skills are additional technical/professional skills**
- **Current designation should be the most recent job title**
- **Skills should be split into primary (role-specific) and secondary**

Required JSON Structure:
{{
  "current_designation": "string",
  "skills": {{
    "primary_skills": ["string (must relate to current designation)"],
    "secondary_skills": ["string (other skills)"]
  }},
  "education": [{{"institution": "string", "degree": "string"}}],
  "total_experience": {{"years": "string"}},
  "full_name": "string",
  "contact_info": {{
    "email": "string",
    "phone": ["string"],
    "linkedin_url": "string"
  }},
  "address": {{
    "city": "string",
    "state": "string",
    "country": "string"
  }}
}}

Resume Text:
{resume_text}
'''
    return prompt

def process_with_ai(resume_text: str) -> Dict[str, Any]:
    """Get structured data from AI model."""
    try:
        response = ollama.chat(
            model='qwen2.5:0.5b',
            messages=[{'role': 'user', 'content': format_resume_prompt(resume_text)}],
            format='json',
            stream=False
        )
        json_str = response['message']['content'].strip()
        json_str = re.sub(r'^```json\s*|\s*```$', '', json_str, flags=re.MULTILINE)
        data = json.loads(json_str)

        if 'education' in data and isinstance(data['education'], dict):
            data['education'] = [data['education']]

        data['extraction_id'] = str(uuid.uuid4())
        data['processing_date'] = datetime.now().isoformat()

        return data
    except Exception as e:
        raise RuntimeError(f"AI processing failed: {str(e)}")

def calculate_extraction_accuracy(extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate extraction accuracy metrics."""
    expected_fields = [
        "full_name", 
        "current_designation", 
        "contact_info.email", 
        "contact_info.phone", 
        "contact_info.linkedin_url",
        "address", 
        "skills.primary_skills", 
        "skills.secondary_skills", 
        "total_experience.years", 
        "education"
    ]
    
    filled_fields = 0
    empty_fields = 0
    field_status = {}
    
    for field in expected_fields:
        parts = field.split('.')
        if len(parts) == 1:
            value = extracted_data.get(parts[0], None)
        elif len(parts) == 2:
            parent = extracted_data.get(parts[0], {})
            value = parent.get(parts[1], None) if isinstance(parent, dict) else None
        else:
            value = None
            
        # Check if field is empty
        is_empty = (
            value is None or 
            value == "" or 
            value == [] or 
            value == {} or 
            (isinstance(value, List) and all(not item for item in value))
        )
        
        field_status[field] = "empty" if is_empty else "filled"
        
        if is_empty:
            empty_fields += 1
        else:
            filled_fields += 1
    
    total_fields = len(expected_fields)
    
    return {
        "filled_fields": filled_fields,
        "empty_fields": empty_fields,
        "total_fields": total_fields,
        "extraction_rate": round(filled_fields / total_fields * 100, 2),
        "field_status": field_status
    }

@app.post("/extract-resume-file/")
async def extract_resume_from_file(file: UploadFile = File(...)):
    """Extract resume data from an uploaded PDF or DOCX file."""
    tmp_file_path = None
    try:
        # Create temp file with original extension
        filename = file.filename
        tmp_file_path = os.path.join(TEMP_DIR, filename)

        # Save uploaded file
        with open(tmp_file_path, "wb") as buffer:
            buffer.write(await file.read())

        # Extract text
        resume_text = ""
        if tmp_file_path.lower().endswith(".pdf"):
            resume_text = extract_text_from_pdf(tmp_file_path)
        elif tmp_file_path.lower().endswith(".docx"):
            resume_text = extract_text_from_docx(tmp_file_path)
        else:
            raise HTTPException(400, "Unsupported file format. Only PDF and DOCX are allowed.")

        if not resume_text:
            raise HTTPException(500, "Failed to extract text from resume")

        # Process with AI
        json_data = process_with_ai(resume_text)
        extraction_id = json_data["extraction_id"]
        extraction_data_storage[extraction_id] = json_data
        
        # Calculate accuracy metrics
        accuracy_metrics = calculate_extraction_accuracy(json_data)

        # Extract structured data for response (same as previous URL-based implementation)
        full_name = safe_get(json_data, 'full_name', default='')
        names = full_name.split() if full_name else [""]

        contact_info = safe_get(json_data, 'contact_info', default={})
        phone_list = safe_get(contact_info, 'phone', default=[]) or safe_get(json_data, 'phone', default=[])
        phone_number = phone_list[0] if isinstance(phone_list, list) and phone_list else ""
        email = safe_get(contact_info, 'email', default="") or safe_get(json_data, 'email', default="")
        linkedin_url = safe_get(contact_info, 'linkedin_url', default="")

        address_info = safe_get(json_data, 'address', default={})
        address = ", ".join(filter(None, [
            safe_get(address_info, 'city', default=''),
            safe_get(address_info, 'state', default=''),
            safe_get(address_info, 'country', default='')
        ]))

        current_designation = safe_get(json_data, 'current_designation', default='')

        skills_data = safe_get(json_data, 'skills', default={})
        primary_skills = list(set(safe_get(skills_data, 'primary_skills', default=[])))
        secondary_skills = list(set(safe_get(skills_data, 'secondary_skills', default=[])))

        total_experience = safe_get(json_data, 'total_experience', 'years', default="") or safe_get(json_data, 'total_experience', default="")

        extracted_info = {
            "first_name": names[0] if len(names) > 0 else "",
            "last_name": " ".join(names[1:]) if len(names) > 1 else "",
            "current_designation": current_designation,
            "mobile_number": phone_number,
            "email": email,
            "address": address,
            "linkedin_url": linkedin_url,
            "skills": {
                "primary": primary_skills,
                "secondary": secondary_skills
            },
            "total_experience": total_experience,
            "education": safe_get(json_data, 'education', default=[]),
            "extraction_id": extraction_id,
            "accuracy_metrics": accuracy_metrics
        }

        return JSONResponse(content=extracted_info)
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        if tmp_file_path and os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)



@app.post("/save-full-json/")
async def save_full_json(request: SaveFullJsonRequest):
    """
    Save the full JSON data after manual confirmation and potential edits
    """
    try:
        # Retrieve the original extraction data
        if request.extraction_id not in extraction_data_storage:
            raise HTTPException(404, "Extraction data not found")
        
        # Get the original extracted data
        original_data = extraction_data_storage[request.extraction_id]
        
        # Prepare save directory
        save_dir = os.path.join(os.path.dirname(__file__), 'saved_resumes')
        os.makedirs(save_dir, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{request.first_name}_{request.last_name}_{timestamp}.json"
        filepath = os.path.join(save_dir, filename)
        
        # Additional metadata
        full_save_data = {
            "original_extraction": original_data,
            "confirmation_details": {
                "first_name": request.first_name,
                "last_name": request.last_name,
                "confirmation_timestamp": datetime.now().isoformat()
            }
        }
        
        # Save JSON file
        with open(filepath, 'w') as f:
            json.dump(full_save_data, f, indent=4)
        
        # Optional: Clean up the temporary storage
        del extraction_data_storage[request.extraction_id]
        
        return {
            "message": "JSON saved successfully",
            "filepath": filepath
        }
    
    except Exception as e:
        raise HTTPException(500, f"Error saving JSON: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)