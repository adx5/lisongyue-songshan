import sys
import traceback
import os
import requests
from pathlib import Path
from fastapi import FastAPI, HTTPException, Depends, Header, File, UploadFile
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 🌟 增加了 Event 的导入
from app.database import SessionLocal, Resource, Lead, VipClient, Event

app = FastAPI(
    title="天地之中 · 嵩山人文志 API",
    description="为嵩山文旅定制的智能撮合与资源管理后端",
    version="1.0.0"
)

# 允许前端跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

ADMIN_PASSWORD = "xinghuo2026" # 后台登录密码

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ================= 模型定义 =================
class ResourceCreate(BaseModel):
    title: str
    category: str
    tag: Optional[str] = ""
    duration: Optional[str] = ""
    price: Optional[int] = 0
    img: Optional[str] = ""
    desc: Optional[str] = ""
    keywords: Optional[str] = ""

class ResourceUpdate(BaseModel):
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

class LeadUpdate(BaseModel):
    client_name: Optional[str] = ""
    contact_info: Optional[str] = ""
    address: Optional[str] = ""
    message: Optional[str] = ""

class LoginRequest(BaseModel):
    password: str

class VipClientCreate(BaseModel):
    title: str
    banner_url: str
    slogan: str = ""
    intro: str = ""
    gallery_urls: str = ""
    cases: str = ""
    phone: str = ""
    wechat: str = ""
    ext_link: str = ""
    sort_order: int = 0
    theme: str = "warm"

class MatchRequest(BaseModel):
    requirement: str

class BatchIds(BaseModel):
    ids: List[int]

# 🌟 新增：会议模型定义
class EventCreate(BaseModel):
    title: str
    date_str: str
    location: str
    summary: Optional[str] = ""
    content: Optional[str] = ""
    images: Optional[str] = ""

class EventUpdate(BaseModel):
    title: str
    date_str: str
    location: str
    summary: Optional[str] = ""
    content: Optional[str] = ""
    images: Optional[str] = ""


# ================= 后台登录 =================
@app.post("/api/admin/login")
def admin_login(req: LoginRequest):
    if req.password == ADMIN_PASSWORD: return {"token": ADMIN_PASSWORD}
    raise HTTPException(status_code=401, detail="密码错误")

# ================= 生态资源接口 =================
@app.post("/api/resources")
def create_resource(resource: ResourceCreate, db: Session = Depends(get_db)):
    db_resource = Resource(**resource.model_dump())
    db.add(db_resource)
    db.commit()
    db.refresh(db_resource)
    return {"message": "发布成功", "id": db_resource.id}

@app.get("/api/resources")
def get_resources(db: Session = Depends(get_db)):
    resources = db.query(Resource).order_by(Resource.id.desc()).all()
    return {"resources": [
        {"id": r.id, "title": r.title, "category": r.category, "tag": r.tag,
         "duration": r.duration, "price": r.price, "img": r.img,
         "desc": r.desc, "keywords": r.keywords} for r in resources]}

@app.put("/api/resources/{resource_id}")
def update_resource(resource_id: int, resource: ResourceUpdate, db: Session = Depends(get_db)):
    db_resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if not db_resource: raise HTTPException(status_code=404, detail="资源不存在")
    for k, v in resource.model_dump().items(): setattr(db_resource, k, v)
    db.commit()
    return {"message": "更新成功"}

@app.delete("/api/resources/{resource_id}")
def delete_resource(resource_id: int, db: Session = Depends(get_db)):
    db.query(Resource).filter(Resource.id == resource_id).delete()
    db.commit()
    return {"message": "删除成功"}

# ================= 🌟 会议管理接口 =================
@app.get("/api/events")
def get_events(db: Session = Depends(get_db)):
    # 按创建时间倒序排列，最新会议在最前
    events = db.query(Event).order_by(Event.created_at.desc()).all()
    return events

@app.post("/api/events")
def create_event(event: EventCreate, db: Session = Depends(get_db)):
    db_event = Event(**event.model_dump())
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return {"message": "发布成功", "id": db_event.id}

@app.put("/api/events/{event_id}")
def update_event(event_id: int, event: EventUpdate, db: Session = Depends(get_db)):
    db_event = db.query(Event).filter(Event.id == event_id).first()
    if not db_event: raise HTTPException(status_code=404, detail="会议不存在")
    for k, v in event.model_dump().items(): setattr(db_event, k, v)
    db.commit()
    return {"message": "更新成功"}

@app.delete("/api/events/{event_id}")
def delete_event(event_id: int, db: Session = Depends(get_db)):
    db_event = db.query(Event).filter(Event.id == event_id).first()
    if not db_event: raise HTTPException(status_code=404, detail="会议不存在")
    db.delete(db_event)
    db.commit()
    return {"message": "删除成功"}


# ================= 线索与行囊接口 =================
@app.post("/api/leads")
def create_lead(lead: LeadCreate, db: Session = Depends(get_db)):
    db_lead = Lead(**lead.model_dump())
    db.add(db_lead)
    db.commit()
    return {"message": "提交成功"}

@app.get("/api/leads")
def get_leads(db: Session = Depends(get_db)):
    leads = db.query(Lead).order_by(Lead.id.desc()).all()
    return {"leads": [
        {"id": l.id, "resource_name": l.resource_name, "client_name": l.client_name,
         "contact_info": l.contact_info, "address": l.address or "", "message": l.message} for l in leads]}

@app.put("/api/leads/{lead_id}")
def update_lead(lead_id: int, lead: LeadUpdate, db: Session = Depends(get_db)):
    db_lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not db_lead: raise HTTPException(status_code=404)
    for k, v in lead.model_dump().items(): setattr(db_lead, k, v)
    db.commit()
    return {"message": "线索更新成功"}

# ================= 仪表盘统计 =================
@app.get("/api/admin/stats")
def get_admin_stats(db: Session = Depends(get_db)):
    return {
        "total_resources": db.query(Resource).count(),
        "total_leads": db.query(Lead).count(),
        "total_events": db.query(Event).count() # 改为统计会议数
    }

# ================= AI 匹配（暂时留空壳防报错） =================
@app.post("/api/match")
def match_requirement(req: MatchRequest):
    return {"status": "success", "message": "AI模块升级中", "data": {}}

# ================= 图床上传 =================
BEEIMG_TOKEN = os.getenv("BEEIMG_TOKEN", "")
BEEIMG_API_URL = "https://www.beeimg.cn/api/v2/upload"

@app.post("/api/admin/upload")
async def upload_image(file: UploadFile = File(...)):
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="只允许上传图片文件")
    if not BEEIMG_TOKEN:
        raise HTTPException(status_code=500, detail="后端未配置 BEEIMG_TOKEN")

    file_content = await file.read()
    headers = {
        "Authorization": f"Bearer {BEEIMG_TOKEN}",
        "Accept": "application/json"
    }
    data = { "storage_id": 17 }
    files = {"file": (file.filename, file_content, file.content_type)}

    try:
        response = requests.post(BEEIMG_API_URL, files=files, data=data, headers=headers, timeout=30)
        try:
            res_json = response.json()
        except ValueError:
            raise HTTPException(status_code=500, detail=f"图床返回异常: {response.text}")

        if response.status_code == 200 and res_json.get("status") == "success":
            return {"url": res_json["data"]["public_url"]}
        else:
            error_msg = res_json.get("message", "未知错误")
            raise HTTPException(status_code=500, detail=f"图床报错: {error_msg}")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"连接图床网络异常: {str(e)}")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"系统异常: {str(e)}")


# ================= 健康检查 =================
@app.get("/")
def root(): return {"message": "天地之中 · 嵩山人文志 API 正在运行"}