import sys
import os
import requests
from pathlib import Path
from fastapi import FastAPI, HTTPException, Depends, File, UploadFile
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.database import SessionLocal, Resource, Lead, Event

app = FastAPI(title="天地之中 · 嵩山人文志 API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

ADMIN_PASSWORD = "xinghuo2026"


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ================= 数据模型 =================
class ResourceCreate(BaseModel):
    title: str
    category: str
    tag: Optional[str] = ""
    duration: Optional[str] = ""
    price: Optional[int] = 0
    img: Optional[str] = ""
    desc: Optional[str] = ""
    keywords: Optional[str] = ""


class LeadCreate(BaseModel):
    resource_name: str
    message: str


class EventCreate(BaseModel):
    title: str
    date_str: str
    location: str
    summary: Optional[str] = ""
    content: Optional[str] = ""
    images: Optional[str] = ""
    media_links: Optional[str] = ""


class LoginRequest(BaseModel):
    password: str


# ================= 接口 =================
@app.post("/api/admin/login")
def admin_login(req: LoginRequest):
    if req.password == ADMIN_PASSWORD: return {"token": ADMIN_PASSWORD}
    raise HTTPException(status_code=401, detail="密码错误")


@app.post("/api/resources")
def create_resource(resource: ResourceCreate, db: Session = Depends(get_db)):
    db_resource = Resource(**resource.model_dump())
    db.add(db_resource);
    db.commit();
    db.refresh(db_resource)
    return {"message": "发布成功", "id": db_resource.id}


@app.get("/api/resources")
def get_resources(db: Session = Depends(get_db)):
    res = db.query(Resource).order_by(Resource.id.desc()).all()
    return {"resources": [
        {"id": r.id, "title": r.title, "category": r.category, "tag": r.tag, "duration": r.duration, "price": r.price,
         "img": r.img, "desc": r.desc, "keywords": r.keywords} for r in res]}


@app.put("/api/resources/{id}")
def update_resource(id: int, resource: ResourceCreate, db: Session = Depends(get_db)):
    db_res = db.query(Resource).filter(Resource.id == id).first()
    if not db_res: raise HTTPException(status_code=404)
    for k, v in resource.model_dump().items(): setattr(db_res, k, v)
    db.commit();
    return {"message": "更新成功"}


@app.delete("/api/resources/{id}")
def delete_resource(id: int, db: Session = Depends(get_db)):
    db.query(Resource).filter(Resource.id == id).delete();
    db.commit()
    return {"message": "删除成功"}


@app.get("/api/events")
def get_events(db: Session = Depends(get_db)):
    return db.query(Event).order_by(Event.created_at.desc()).all()


@app.post("/api/events")
def create_event(event: EventCreate, db: Session = Depends(get_db)):
    db_event = Event(**event.model_dump())
    db.add(db_event);
    db.commit();
    db.refresh(db_event)
    return {"message": "发布成功", "id": db_event.id}


@app.put("/api/events/{id}")
def update_event(id: int, event: EventCreate, db: Session = Depends(get_db)):
    db_event = db.query(Event).filter(Event.id == id).first()
    if not db_event: raise HTTPException(status_code=404)
    for k, v in event.model_dump().items(): setattr(db_event, k, v)
    db.commit();
    return {"message": "更新成功"}


@app.delete("/api/events/{id}")
def delete_event(id: int, db: Session = Depends(get_db)):
    db.query(Event).filter(Event.id == id).delete();
    db.commit()
    return {"message": "删除成功"}


@app.post("/api/leads")
def create_lead(lead: LeadCreate, db: Session = Depends(get_db)):
    db_lead = Lead(**lead.model_dump())
    db.add(db_lead);
    db.commit()
    return {"message": "提交成功"}


@app.get("/api/leads")
def get_leads(db: Session = Depends(get_db)):
    return {"leads": db.query(Lead).order_by(Lead.id.desc()).all()}


@app.get("/api/admin/stats")
def get_admin_stats(db: Session = Depends(get_db)):
    return {"total_resources": db.query(Resource).count(), "total_leads": db.query(Lead).count(),
            "total_events": db.query(Event).count()}


BEEIMG_TOKEN = os.getenv("BEEIMG_TOKEN", "")
BEEIMG_API_URL = "https://www.beeimg.cn/api/v2/upload"


@app.post("/api/admin/upload")
async def upload_image(file: UploadFile = File(...)):
    if not file.content_type.startswith('image/'): raise HTTPException(status_code=400, detail="只允许图片")
    if not BEEIMG_TOKEN: raise HTTPException(status_code=500, detail="云端未配置 BEEIMG_TOKEN，请检查环境变量")

    file_content = await file.read()
    headers = {"Authorization": f"Bearer {BEEIMG_TOKEN}", "Accept": "application/json"}
    data = {"storage_id": 17}
    files = {"file": (file.filename, file_content, file.content_type)}

    try:
        response = requests.post(BEEIMG_API_URL, files=files, data=data, headers=headers, timeout=30)
        res_json = response.json()
        if response.status_code == 200 and res_json.get("status") == "success":
            return {"url": res_json["data"]["public_url"]}
        else:
            raise HTTPException(status_code=500, detail=f"图床报错: {res_json.get('message')}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"连接图床失败: {str(e)}")


@app.get("/")
def root(): return {"message": "API OK"}