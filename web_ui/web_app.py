import os
import sys
import logging
import asyncio
from typing import List, Optional, Dict
from pydantic import BaseModel
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import nest_asyncio
nest_asyncio.apply()

# Add root project path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
sys.path.insert(0, root_dir)

from scanner_service import ScannerService
from services.ai_analysis_service import get_ai_service

# Logging Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WebUI")

# FastAPI App
app = FastAPI(title="Option Scanner Pro", version="2.0.0")

# Setup Templates & Static
templates = Jinja2Templates(directory=os.path.join(current_dir, "templates"))
# app.mount("/static", StaticFiles(directory=os.path.join(current_dir, "static")), name="static") 

# Global Service Instances
scanner_service = ScannerService()
ai_service = get_ai_service()

@app.on_event("startup")
async def startup_event():
    logger.info("Web UI Starting Up...")
    # NOTE: We do not auto-start scanner, user must click 'Start'

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Web UI Shutting Down...")
    scanner_service.stop()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/status")
async def get_status():
    return {
        "running": scanner_service.running, 
        "connected": scanner_service.is_connected,
        "opportunities_count": len(scanner_service.latest_opportunities),
        "last_scan_time": scanner_service.last_scan_time.isoformat() if scanner_service.last_scan_time else None,
        "status_message": scanner_service.status_message
    }

class StartRequest(BaseModel):
    selected_strategies: List[str] = []

@app.post("/api/start")
async def start_scanner(request: StartRequest):
    if not scanner_service.running:
        # Clear previous results before starting
        scanner_service.clear_opportunities()
        # Run in background so we don't block the response
        asyncio.create_task(scanner_service.start(request.selected_strategies))
        return {"status": "started", "message": f"Scanner started with strategies: {request.selected_strategies}"}
    return {"status": "already_running", "message": "Scanner is already running"}

@app.post("/api/stop")
async def stop_scanner():
    if scanner_service.running:
        await scanner_service.stop()
        return {"status": "stopped", "message": "Scanner stopped"}
    return {"status": "not_running", "message": "Scanner is not running"}

@app.get("/api/results")
async def get_results():
    return {"opportunities": scanner_service.latest_opportunities}

@app.get("/api/report/{ticker}")
async def get_ai_report(ticker: str):
    """
    Generate AI Report for a specific ticker found in opportunities.
    """
    # Find the opportunity data from cache
    opp = next((o for o in scanner_service.latest_opportunities if o['ticker'] == ticker), None)
    
    if not opp:
        return JSONResponse(status_code=404, content={"message": "Ticker not found in current opportunities"})
        
    try:
        # Trigger Deep Analysis (32 Modules)
        # This will update status_message for UI feedback
        # Note: This might take time (10-20s), so UI should show a spinner.
        deep_analysis_result = await scanner_service.run_deep_analysis(ticker, setup_info=opp)
        
        # Determine setup data for AI
        # We merge deep_analysis result with the original opportunity data
        # actually generate_analysis can handle the dict.
        # But we should probably pass the deep_analysis_result which contains everything?
        # deep_analysis_result has 'moduleX': ... 
        # It doesn't necessarily have 'score' from scanner (unless we add it).
        # Let's add scanner context to deep result.
        deep_analysis_result['scanner_context'] = opp
        
        report = await ai_service.generate_analysis_async(ticker, deep_analysis_result)
        return {"ticker": ticker, "report": report}
    except Exception as e:
        logger.error(f"AI Report Error: {e}")
        return JSONResponse(status_code=500, content={"message": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
