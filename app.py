from fastapi import FastAPI, Request, HTTPException, Depends
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import httpx
from anthropic import Anthropic
from typing import List
import random
from urllib.parse import urlparse
import yt_dlp
import jwt
from jwt import DecodeError, decode
from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordBearer
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import re
from dotenv import load_dotenv
import os


load_dotenv()  # Load environment variables from .env file

key = os.getenv("API_KEY")
client = Anthropic(api_key=key)
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
security = HTTPBearer()
device_id_pattern = re.compile(r'^[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}[0-9A-Z]+$')

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

class Message(BaseModel):
    role: str
    content: str

class DeviceIDRequest(BaseModel):
    device_id: str

async def get_current_device(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        device_id = payload.get("device_id")
        
        if device_id is None:
            raise HTTPException(status_code=401, detail="Invalid JWT: Device ID not found")
        return device_id
    except DecodeError:
        raise HTTPException(status_code=401, detail="Invalid JWT")

@app.get("/protected_endpoint")
async def protected_endpoint(token: str = Depends(get_current_device)):
    return {"message": f"Access granted for device {token}"}

@app.post("/gpt/knowledgeBase")
async def knowledgeResponse(conversation: List[Message]):
    print(conversation)

    completion = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=1000,
            messages=conversation)
    


    claude_response = completion.content[0].text
    return claude_response

@app.post("/heartbeat")
async def get_token(request: DeviceIDRequest):
    device_id = request.device_id
    print(device_id)
    if not device_id_pattern.match(device_id):
        raise HTTPException(status_code=400, detail="Invalid device ID format")

    expiration = datetime.utcnow() + timedelta(hours=1)
    token = jwt.encode({"device_id": device_id, "exp": expiration}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token}

@app.get("/getAudioSize")
async def get_audio_size(link: str, bitrate: int = 190):
    try:
        parsed_url = urlparse(link)
        domain = parsed_url.netloc

        ydl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'playlistend': 1,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(link, download=False)
            duration = info_dict.get('duration', 0)  # Duration in seconds
            video_title = info_dict.get('title', 'Unknown')  # Video title

        file_size_bytes = (duration * bitrate * 1000) / 8  # bitrate is converted from kbps to bps

        file_size_mb = file_size_bytes / (1024 * 1024)
        file_size_mb = round(file_size_mb, 2)

        return {"status": "success", "file_size_mb": file_size_mb, "duration_seconds": duration, "video_title": video_title}
    
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@app.post('/gpt/flourish')
async def getFleurResponse(conversation: List[Message], token: str = Depends(get_current_device)):
    print(token)
    print({"message": f"Access granted for device {token}"})
    
    print(conversation)
    completion = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=300,
            system=conversation[0].content,
            messages=conversation[1:])

    claude_response = completion.content[0].text
    return claude_response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4242)
