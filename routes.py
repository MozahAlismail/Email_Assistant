import os
from dotenv import load_dotenv
import requests

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio.session import AsyncSession
from schemas import EmailRequest, EmailResponse
from schemas import EmailLogCreate, EmailLogRead
from database import get_session
from crud import crud_email_logs

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")
if not HF_TOKEN:
    raise ValueError("HF_TOKEN environment variable is not set")

# Simple Hugging Face API setup
HF_API_URL = "https://huggingface.co/meta-llama/Llama-2-7b-chat-hf"
HF_HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"}

def query_huggingface(payload):
    response = requests.post(HF_API_URL, headers=HF_HEADERS, json=payload)
    
    if response.status_code == 503:
        raise HTTPException(status_code=503, detail="Model is loading, please wait a few minutes")
    elif response.status_code == 401:
        raise HTTPException(status_code=401, detail="Invalid HF token or no Llama2 access")
    elif response.status_code == 404:
        raise HTTPException(status_code=404, detail="Llama2 model not found")
    elif response.status_code != 200:
        raise HTTPException(status_code=500, detail=f"API error: {response.text}")
    
    return response.json()

# Email router
email_router = APIRouter()

@email_router.post("/", response_model=EmailResponse)
async def generate_email(request: EmailRequest, db: AsyncSession = Depends(get_session)):
    try:
        # Proper Llama2 Chat Format
        system_message = "You are a professional email assistant. Write clear, appropriate emails based on user requests."
        
        user_message = f"""Write an email with these details:
- Request: {request.user_input}
- Reply to: {request.reply_to if request.reply_to else 'N/A'}
- Context: {request.context if request.context else 'N/A'}
- Tone: {request.tone if request.tone else 'professional'}

Write only the email content:"""

        # Llama2 Chat Template
        llama_prompt = f"<s>[INST] <<SYS>>\n{system_message}\n<</SYS>>\n\n{user_message} [/INST]"
        
        # Optimized Llama2 Parameters
        payload = {
            "inputs": llama_prompt,
            "parameters": {
                "max_new_tokens": min(request.length or 300, 500),
                "temperature": 0.7,
                "top_p": 0.9,
                "do_sample": True,
                "return_full_text": False,
                "repetition_penalty": 1.1
            }
        }
        
        response = query_huggingface(payload)
        
        # Extract and clean response
        if isinstance(response, list) and len(response) > 0:
            generated_email = response[0]["generated_text"]
        else:
            generated_email = response["generated_text"]
            
        # Clean Llama2 tokens
        generated_email = generated_email.replace("</s>", "").strip()
        
        # Save to database
        log_entry = EmailLogCreate(
            user_input=request.user_input,
            reply_to=request.reply_to,
            context=request.context,
            length=request.length,
            tone=request.tone,
            generated_email=generated_email
        )
        await crud_email_logs.create(db, log_entry)
        
        return EmailResponse(generated_email=generated_email)
        
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