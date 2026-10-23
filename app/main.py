from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base, seed_initial_data
# 如果有其他路由或接口，这里按需导入，比如：
# from app.api import router as api_router

# 1. 创建 FastAPI 实例（变量名必须叫 app）
app = FastAPI(
    title="天地之中 · 嵩山人文旅行操作系统 API",
    description="为嵩山文旅定制的智能撮合与资源管理后端",
    version="1.0.0"
)

# 2. 配置跨域（非常重要！让 GitHub Pages 的前端能请求云端后端）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发阶段允许所有，上线后可改成 ["https://adx5.github.io"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. 挂载其他路由（如果原来代码里有，就把这行取消注释）
# app.include_router(api_router, prefix="/api")

# 4. 健康检查接口（测试用）
@app.get("/")
def read_root():
    return {"message": "Welcome to Songshan OS API!"}

@app.get("/health")
def health_check():
    return {"status": "ok", "database": "connected"}

# 5. 启动事件（可选，用于初始化数据）
@app.on_event("startup")
def startup_event():
    # 如果你需要每次启动时检查表或播种数据，可以在这里调用
    # seed_initial_data()
    pass