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

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")
if not HF_TOKEN:
    raise ValueError("HF_TOKEN environment variable is not set")

# Simple Hugging Face API setup
HF_API_URL = "https://api-inference.huggingface.co/models/meta-llama/Llama-2-7b-chat-hf"
HF_HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"}

# Debug logging
print(f"🔑 HF_TOKEN (first 10 chars): {HF_TOKEN[:10]}...")
print(f"🌐 API URL: {HF_API_URL}")

def query_huggingface(payload):
    print(f"📤 Sending request to: {HF_API_URL}")
    print(f"📋 Headers: Authorization: Bearer {HF_TOKEN[:10]}...")
    print(f"📝 Payload: {json.dumps(payload, indent=2)}")
    
    response = requests.post(HF_API_URL, headers=HF_HEADERS, json=payload)
    
    print(f"📨 Response Status Code: {response.status_code}")
    print(f"📄 Response Headers: {dict(response.headers)}")
    print(f"📃 Response Text: {response.text[:500]}...")  # First 500 chars
    
    if response.status_code == 503:
        print("⏳ Model is loading...")
        raise HTTPException(status_code=503, detail="Model is loading, please wait a few minutes")
    elif response.status_code == 401:
        print("🚫 Authentication failed")
        raise HTTPException(status_code=401, detail="Invalid HF token or no Llama2 access")
    elif response.status_code == 404:
        print("❌ Model not found")
        raise HTTPException(status_code=404, detail="Llama2 model not found")
    elif response.status_code != 200:
        print(f"💥 Unexpected error: {response.status_code}")
        raise HTTPException(status_code=500, detail=f"API error: {response.text}")
    
    print("✅ Request successful!")
    return response.json()

# Email router
email_router = APIRouter()

@email_router.post("/", response_model=EmailResponse)
async def generate_email(request: EmailRequest, db: AsyncSession = Depends(get_session)):
    try:
        print(f"🎯 Starting email generation for: {request.user_input}")
        
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
        
        print(f"📝 Generated prompt (first 200 chars): {llama_prompt[:200]}...")
        
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
        
        print("🚀 Calling Hugging Face API...")
        response = query_huggingface(payload)
        print(f"📥 Received response: {response}")
        
        # Extract and clean response
        if isinstance(response, list) and len(response) > 0:
            generated_email = response[0]["generated_text"]
            print(f"📧 Extracted from list: {generated_email[:100]}...")
        else:
            generated_email = response["generated_text"]
            print(f"📧 Extracted from dict: {generated_email[:100]}...")
            
        # Clean Llama2 tokens
        generated_email = generated_email.replace("</s>", "").strip()
        print(f"🧹 Cleaned email: {generated_email[:100]}...")

        # Save to database
        print("💾 Saving to database...")
        log_entry = EmailLogCreate(
            user_input=request.user_input,
            reply_to=request.reply_to,
            context=request.context,
            length=request.length,
            tone=request.tone,
            generated_email=generated_email
        )
        await crud_email_logs.create(db, log_entry)
        print("✅ Successfully saved to database")
        
        return EmailResponse(generated_email=generated_email)
        
    except Exception as e:
        print(f"❌ Error occurred: {str(e)}")
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