import os
from dotenv import load_dotenv
import requests
import json

from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.ext.asyncio.session import AsyncSession
from schemas import EmailRequest, EmailResponse
from schemas import EmailLogCreate, EmailLogRead
from database import get_session

from crud import crud_email_logs

# Load environment variables from .env file (if it exists)
load_dotenv()

# Get Hugging Face token from environment variables
HF_TOKEN = os.getenv("HF_TOKEN")

if not HF_TOKEN:
    raise ValueError("HF_TOKEN environment variable is not set")

# Hugging Face Inference API configuration
HF_API_URL = "https://api-inference.huggingface.co/models/meta-llama/Llama-2-7b-chat-hf"
HF_HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"}

def query_huggingface(payload):
    """Query Hugging Face Inference API"""
    response = requests.post(HF_API_URL, headers=HF_HEADERS, json=payload)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Hugging Face API error: {response.text}")
    return response.json()

# ------- email -------
email_router = APIRouter()

@email_router.post("/", response_model=EmailResponse)
async def generate_email(
    request: EmailRequest, #This references the schema with the same name
    #request is the name of the instance that is running when using the endpoint
    #The inputs filled by the user to call the API are referenced by using request.NAME_OF_INPUT
    #for example, to reference the context, you would use request.context
    db: AsyncSession = Depends(get_session)
):
    try:
        # Create the prompt for Llama2
        system_prompt = "You are a helpful email assistant. You get a prompt to write an email, you reply with the email and nothing else."
        
        user_prompt = f"""Write an email based on the following input:
- User Input: {request.user_input}
- Reply To: {request.reply_to if request.reply_to else 'N/A'}
- Context: {request.context if request.context else 'N/A'}
- Length: {request.length if request.length else 'N/A'} characters
- Tone: {request.tone if request.tone else 'N/A'}

Email:"""

        # Format prompt for Llama2 chat template
        full_prompt = f"<s>[INST] <<SYS>>\n{system_prompt}\n<</SYS>>\n\n{user_prompt} [/INST]"
        
        # Prepare payload for Hugging Face API
        payload = {
            "inputs": full_prompt,
            "parameters": {
                "max_new_tokens": request.length if request.length and request.length <= 1000 else 500,
                "temperature": 0.7,
                "top_p": 0.95,
                "do_sample": True,
                "return_full_text": False
            }
        }
        
        # Query Hugging Face API
        hf_response = query_huggingface(payload)
        
        # Extract generated text
        if isinstance(hf_response, list) and len(hf_response) > 0:
            generated_email = hf_response[0].get("generated_text", "").strip()
        else:
            raise HTTPException(status_code=500, detail="Unexpected response format from Hugging Face")
        
        # Clean up the response (remove any system tokens)
        generated_email = generated_email.replace("</s>", "").strip()

        #Stocking the results in EmailLogCreate format
        log_entry = EmailLogCreate(
            user_input=request.user_input,
            reply_to=request.reply_to,
            context=request.context,
            length=request.length,
            tone=request.tone,
            generated_email=generated_email,
        )
        #Use CRUD to write in the database
        await crud_email_logs.create(db, log_entry)

        #Using EmailResponse Schema to return the generated email
        return EmailResponse(generated_email=generated_email)

    #Exception handling
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ------- logs -------
log_router = APIRouter()

#endpoint to get all logs
@log_router.get("/")
async def read_logs(db: AsyncSession = Depends(get_session)):
    logs = await crud_email_logs.get_multi(db)
    return logs


#endpoint to get specific logs
@log_router.get("/{log_id}", response_model=EmailLogRead)
async def read_log(log_id: int, db: AsyncSession = Depends(get_session)):
    log = await crud_email_logs.get(db, id=log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    return log