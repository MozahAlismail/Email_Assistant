import os

from starlette.config import Config
from openai import OpenAI
from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.ext.asyncio.session import AsyncSession
from .schemas import EmailRequest, EmailResponse
from .schemas import EmailLogCreate, EmailLogRead
from .database import get_session

from .crud import crud_email_logs

current_file_dir = os.path.dirname(os.path.realpath(__file__))
env_path = os.path.join(current_file_dir, ".env")

config = Config(env_path)

OPENAI_API_KEY = config("OPENAI_API_KEY")
open_ai_client = OpenAI(api_key=OPENAI_API_KEY)

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

        #System prompt : how the system should behave
        system_prompt = f"""
        You are a helpful email assistant. 
        You get a prompt to write an email,
        you reply with the email and nothing else.
        """
        #prompt : what the model receives as input
        prompt = f"""
        Write an email based on the following input:
        - User Input: {request.user_input}
        - Reply To: {request.reply_to if request.reply_to else 'N/A'}
        - Context: {request.context if request.context else 'N/A'}
        - Length: {request.length if request.length else 'N/A'} characters
        - Tone: {request.tone if request.tone else 'N/A'}
        """
        
        #Getting the response from the model
        response = open_ai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            max_tokens=request.length
        )
        #Get the response
        generated_email = response.choices[0].message.content.strip()

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