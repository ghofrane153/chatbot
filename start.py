import os
import uvicorn

port = int(os.environ.get("PORT", 8001))
uvicorn.run("api.server:app", host="0.0.0.0", port=port)