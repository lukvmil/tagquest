import httpx
from fastapi import FastAPI
from pydantic import BaseModel
from escpos.printer import Win32Raw


app = FastAPI()
printer = Win32Raw("RONGTA 80mm Series Printer")

@app.post("/print")
def print_receipt(from_url: str):
    resp = httpx.get(from_url)
    
    printer.open()
    printer._raw(resp.content)
    printer.close()