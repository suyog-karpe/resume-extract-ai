import streamlit as st
import requests
import tempfile
import os
import json

st.title("Resume Information Extractor")

# Initialize session state
if 'autofill_data' not in st.session_state:
    st.session_state.autofill_data = {}
if 'extraction_id' not in st.session_state:
    st.session_state.extraction_id = None
if 'extraction_data' not in st.session_state:
    st.session_state.extraction_data = None

def save_resume_json(form_data):
    """
    Save form data as a JSON file in the same directory as the script.
    Generates a filename based on first name and last name with timestamp.
    """
    try:
        # Get the directory of the current script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Create a 'resumes' subdirectory if it doesn't exist
        resume_dir = os.path.join(script_dir, 'resumes')
        os.makedirs(resume_dir, exist_ok=True)
        
        # Generate filename with timestamp to avoid overwriting
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{form_data['first_name']}_{form_data['last_name']}_{timestamp}.json"
        
        # Full path for the JSON file
        file_path = os.path.join(resume_dir, filename)
        
        # Save the JSON file
        with open(file_path, 'w') as f:
            json.dump(form_data, f, indent=4)
        
        return file_path
    except Exception as e:
        st.error(f"Error saving JSON: {e}")
        return None

# File upload section
st.subheader("Upload Resume")
uploaded_file = st.file_uploader("Choose a PDF or DOCX file", 
                                 type=['pdf', 'docx'], 
                                 help="Upload your resume in PDF or DOCX format")

if st.button("Extract Information") and uploaded_file:
    try:
        # Save uploaded file to a temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as temp_file:
            temp_file.write(uploaded_file.getvalue())
            temp_file_path = temp_file.name
        
        # Open the file in read-binary mode to upload
        with open(temp_file_path, 'rb') as file:
            files = {'file': (uploaded_file.name, file, 'multipart/form-data')}
            
            # Call extract-resume-file API
            response = requests.post(
                "http://localhost:8000/extract-resume-file/", 
                files=files
            )
        
        # Remove the temporary file
        os.unlink(temp_file_path)
        
        if response.status_code == 200:
            data = response.json()
            
            # Store extraction data in session state
            st.session_state.extraction_data = data
            st.session_state.extraction_id = data['extraction_id']
            
            # Display accuracy metrics
            st.success(f"Extraction Rate: {data['accuracy_metrics']['extraction_rate']}%")
            
            with st.expander("Extraction Details"):
                st.write(f"Filled Fields: {data['accuracy_metrics']['filled_fields']}/{data['accuracy_metrics']['total_fields']}")
                st.write(f"Empty Fields: {data['accuracy_metrics']['empty_fields']}/{data['accuracy_metrics']['total_fields']}")
                
                # Display field status
                st.subheader("Field Status")
                status_df = {"Field": [], "Status": []}
                for field, status in data['accuracy_metrics']['field_status'].items():
                    status_df["Field"].append(field)
                    status_df["Status"].append(status)
                st.dataframe(status_df)
            
            # Accuracy confirmation buttons
            col1, col2 = st.columns(2)
            with col1:
                st.button("Accept AI Results", on_click=lambda: confirm_extraction(True))
            with col2:
                st.button("Reject Extraction Results", on_click=lambda: confirm_extraction(False))
        else:
            st.error(f"Error processing resume: {response.text}")
    
    except Exception as e:
        st.error(f"Error: {str(e)}")

def confirm_extraction(confirm):
    """Handle extraction confirmation"""
    if not st.session_state.extraction_data:
        st.error("No extraction data available")
        return
    
    if confirm:
        # Prepare autofill data
        data = st.session_state.extraction_data
        st.session_state.autofill_data = {
            "first_name": data.get("first_name", ""),
            "last_name": data.get("last_name", ""),
            "mobile": data.get("mobile_number", ""),
            "email": data.get("email", ""),
            "address": data.get("address", ""),
            "linkedin_url": data.get("linkedin_url", ""),
            "designation": data.get("current_designation", ""),
            "total_exp": data.get("total_experience", ""),
            "primary_skills": ", ".join(data.get("skills", {}).get("primary", [])),
            "secondary_skills": ", ".join(data.get("skills", {}).get("secondary", [])),
            "education": ", ".join([f"{edu.get('institution', '')}: {edu.get('degree', '')}" 
                                    for edu in data.get("education", [])])
        }
        st.success("Extraction confirmed. Form will be autofilled.")
    else:
        st.session_state.autofill_data = {}
        st.info("Extraction rejected. Please fill the form manually.")

# Form section
with st.form("candidate_form"):
    st.subheader("Candidate Information")
    
    col1, col2 = st.columns(2)
    with col1:
        first_name = st.text_input("First Name*", 
            value=st.session_state.autofill_data.get("first_name", ""))
    with col2:
        last_name = st.text_input("Last Name*", 
            value=st.session_state.autofill_data.get("last_name", ""))
    
    col3, col4 = st.columns(2)
    with col3:
        mobile = st.text_input("Mobile Number*", 
            value=st.session_state.autofill_data.get("mobile", ""))
    with col4:
        address = st.text_input("Address", 
            value=st.session_state.autofill_data.get("address", ""))
    
    col5, col6 = st.columns(2)
    with col5:
        linkedin_url = st.text_input("LinkedIn URL", 
            value=st.session_state.autofill_data.get("linkedin_url", ""))
    with col6:
        email = st.text_input("Email*", 
            value=st.session_state.autofill_data.get("email", ""))
    
    education = st.text_input("Education*", 
        value=st.session_state.autofill_data.get("education", ""))
    
    col7, col8 = st.columns(2)
    with col7:
        total_exp = st.text_input("Total Experience (years)*", 
            value=st.session_state.autofill_data.get("total_exp", ""))
    with col8:
        designation = st.text_input("Current Designation*", 
            value=st.session_state.autofill_data.get("designation", ""))
    
    col9, col10 = st.columns(2)
    with col9:
        primary_skills = st.text_input("Primary Skills (comma separated)*", 
            value=st.session_state.autofill_data.get("primary_skills", ""))
    with col10:
        secondary_skills = st.text_input("Secondary Skills (comma separated)", 
            value=st.session_state.autofill_data.get("secondary_skills", ""))
    
    submitted = st.form_submit_button("Submit Profile")
    
    if submitted:
        required_fields = [first_name, last_name, mobile, email, education, total_exp, designation, primary_skills]
        if all(required_fields):
            form_data = {
                "first_name": first_name,
                "last_name": last_name,
                "mobile": mobile,
                "address": address,
                "linkedin_url": linkedin_url,
                "email": email,
                "education": education,
                "total_exp": total_exp,
                "designation": designation,
                "primary_skills": primary_skills,
                "secondary_skills": secondary_skills
            }
            
            if st.session_state.extraction_id:
                response = requests.post(
                    "http://localhost:8000/save-full-json/",
                    json={
                        "extraction_id": st.session_state.extraction_id, 
                        "first_name": first_name,
                        "last_name": last_name
                    }
                )
                
                if response.status_code == 200:
                    # Save local JSON file
                    saved_file_path = save_resume_json(form_data)
                    
                    if saved_file_path:
                        st.success(f"Profile saved successfully! JSON saved at: {saved_file_path}")
                    
                    # Reset session states
                    st.session_state.autofill_data = {}
                    st.session_state.extraction_id = None
                    st.session_state.extraction_data = None
                else:
                    st.error(f"Save failed: {response.text}")
            else:
                st.error("No extraction ID found")
        else:
            st.error("Please fill all required fields (marked with *)")

# Optional: Display submitted data
if 'form_data' in locals():
    st.subheader("Submitted Form Data")
    st.json(form_data)