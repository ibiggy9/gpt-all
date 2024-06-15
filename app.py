from fastapi import FastAPI, Request, HTTPException, Depends
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import httpx
from openai import OpenAI
from typing import List
import random
from urllib.parse import urlparse
from fastapi import FastAPI, Request, HTTPException, Depends
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp
from urllib.parse import urlparse
import jwt
from jwt import  DecodeError, decode
from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordBearer
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import re


key = "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"
client=OpenAI(api_key=key)
SECRET_KEY = 'ASDGRTHHK@#K$%@#@!#%235283yhth7io1234hf783421g@$G$Y@45g7h24589gh5b2g@F!@#$F1f!Uf!YU(@UF(#H!H#K!FY(#(!&THFK!H@#$GH!THQEWKTQESTUGQERGHQJRGFB@J))))'
ALGORITHM='HS256'
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
    role:str
    content:str

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
    completion = client.chat.completions.create(
        model="gpt-4-1106-preview",
        messages=conversation
    )
    return completion.choices[0].message


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
        # Extract video information
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

        # Calculate file size in bytes
        file_size_bytes = (duration * bitrate * 1000) / 8  # bitrate is converted from kbps to bps

        # Convert file size to megabytes for a more human-readable format
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
    completion = client.chat.completions.create(
        model="gpt-4-1106-preview",
        messages=conversation
    )
    return completion


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4242)


