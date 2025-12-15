
import os
import uuid
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

# Load environment variables from a local .env file if present
load_dotenv()

from utils.blob_upload import upload_image_to_blob
from utils.vision_ocr import extract_text_from_image_url

APPINSIGHTS_CONNECTION_STRING = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")

tracer_provider = None
if APPINSIGHTS_CONNECTION_STRING:
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.requests import RequestsInstrumentor

    resource = Resource.create({"service.name": "azure-ocr-demo"})
    tracer_provider = TracerProvider(resource=resource)
    exporter = AzureMonitorTraceExporter.from_connection_string(APPINSIGHTS_CONNECTION_STRING)
    tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(tracer_provider)

app = FastAPI(title="Azure OCR Demo", version="1.0.0")

# CORS: widen or restrict as needed; tighten origins for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if tracer_provider:
    FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)
    RequestsInstrumentor().instrument()

@app.get("/", include_in_schema=False)
async def serve_frontend():
    # Serve the static page
    return FileResponse("static/index.html")

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    if not file or not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Veuillez envoyer un fichier image.")

    filename = f"{uuid.uuid4()}{os.path.splitext(file.filename)[1] or '.jpg'}"

    try:
        blob_url = await upload_image_to_blob(file, filename)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Echec upload Blob : {exc}") from exc

    try:
        # Vision SDK is synchronous; run in thread to avoid blocking event loop
        text = await asyncio.to_thread(extract_text_from_image_url, blob_url)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Echec OCR : {exc}") from exc

    return JSONResponse({"blob_url": blob_url, "text": text})
