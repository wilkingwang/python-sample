from fastapi import FastAPI
import uvicorn

app = FastAPI()

fake_itme_db = [{"item_name": "Foo"}, {"item_name": "Bar"}, {"item_name": "Baz"}]

# Hello World
@app.get("/")
async def root():
    return {"message": "Hello World"}


# 路径参数
@app.get("/items/{item_id}")
async def read_item(item_id: int):
    return {"item_id": item_id}

# 查询参数
@app.get("/items")
async def read_item(skip: int = 0, limit: int = 10):
    return fake_itme_db[skip : skip + limit]


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)