import os
from dotenv import load_dotenv
import uvicorn
from app.main import create_app
load_dotenv()
app=create_app()
if __name__=='__main__':
    uvicorn.run(app,host='0.0.0.0',port=int(os.getenv('PORT','8000')),workers=1,ws_max_size=8192)
