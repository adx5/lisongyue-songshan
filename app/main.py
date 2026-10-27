import sys
import os
import requests
from pathlib import Path
from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, BackgroundTasks
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


# ================= 飞书通知推送 =================
# ⚠️ 测试完成后，建议在飞书群设置中重置 Webhook，并将其放入环境变量中保护
FEISHU_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/f16b9c94-31bd-405e-b272-3cf06fa156b6"


def send_feishu_notification(title: str, content: str):
    """发送飞书群机器人通知（静默执行，不影响主业务）"""
    if not FEISHU_WEBHOOK:
        return
    try:
        # 采用飞书互动卡片格式，更美观
        payload = {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {
                    "title": {"tag": "plain_text", "content": title},
                    # 主理人申请用绿色，游客定制用蓝色
                    "template": "green" if "主理人" in title else "blue"
                },
                "elements": [
                    {"tag": "div", "text": {"tag": "lark_md", "content": content}},
                    {"tag": "hr"},
                    {"tag": "note", "elements": [{"tag": "plain_text", "content": "来自：天地之中 · 嵩山人文志"}]}
                ]
            }
        }
        requests.post(FEISHU_WEBHOOK, json=payload, timeout=3)
    except Exception as e:
        print(f"❌ 飞书通知发送失败: {e}")


# ================= 接口 =================
@app.post("/api/admin/login")
def admin_login(req: LoginRequest):
    if req.password == ADMIN_PASSWORD: return {"token": ADMIN_PASSWORD}
    raise HTTPException(status_code=401, detail="密码错误")


# 资源接口
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


@app.get("/api/resources/{resource_id}")
def get_resource(resource_id: int, db: Session = Depends(get_db)):
    res = db.query(Resource).filter(Resource.id == resource_id).first()
    if not res: raise HTTPException(status_code=404, detail="资源不存在")
    return {"id": res.id, "title": res.title, "category": res.category, "tag": res.tag, "duration": res.duration,
            "price": res.price, "img": res.img, "desc": res.desc, "keywords": res.keywords}


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


# 会议接口
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


# 🌟 核心更新：线索接口加入飞书后台推送
@app.post("/api/leads")
def create_lead(lead: LeadCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # 1. 存入数据库
    db_lead = Lead(**lead.model_dump())
    db.add(db_lead)
    db.commit()

    # 2. 判断线索类型，组装飞书通知
    if lead.resource_name == '主理人入驻申请':
        title = "🌟 收到新的[主理人入驻申请]"
    else:
        title = "📩 收到新的[定制行囊需求]"

    # 3. 将发送任务扔给后台，不阻塞用户提交响应
    background_tasks.add_task(send_feishu_notification, title, lead.message)

    return {"message": "提交成功"}


@app.get("/api/leads")
def get_leads(db: Session = Depends(get_db)):
    return {"leads": db.query(Lead).order_by(Lead.id.desc()).all()}


@app.get("/api/admin/stats")
def get_admin_stats(db: Session = Depends(get_db)):
    return {"total_resources": db.query(Resource).count(), "total_leads": db.query(Lead).count(),
            "total_events": db.query(Event).count()}


# 图床接口
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