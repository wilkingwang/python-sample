### 一、FastAPI
#### 1.1、定义装饰器
```python
@app.get("/")
async def root():
    return {"message": "Hello World"}
```
@app.get("/")告诉 FastAPI在它下方的函数负责处理如下访问请求：
- 请求路径为/
- 使用get请求

#### 1.2、路径参数
```python
# 路径参数
@app.get("/items/{item_id}")
async def read_item(item_id: int):
    return {"item_id": item_id}
```
这段代码把路径参数item_id的值传递给路径函数的参数item_id。
使用python标准类型注解，声明路径操作函数中的路径参数类型。类型声明将为函数提供错误检查、代码补全等编辑器支持。如果类型转换出错，接收的返回如下：
```json
{
  "detail": [
    {
      "type": "int_parsing",
      "loc": [
        "path",
        "item_id"
      ],
      "msg": "Input should be a valid integer, unable to parse string as an integer",
      "input": "wang"
    }
  ]
}
```
#### 1.3、

### 二、Uvicorn
#### 2.1、介绍
Uvicorn是一格高性能ASGI服务器，旨在提供高性能的异步请求处理能力。它使用asyncio库实现异步IO操作，支持HTTP/WebSocket协议，可与各种ASGI应用程序框架(FastAPI、Django、Starlette等)配合使用。
#### 2.2、安装
```sh
pip install uvcorn
```
#### 2.3、使用示例
```python
from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}
```
以上代码保存到`main.py`文件中，然后，在命令行中执行以下命令：
```sh
uvcorn main:app --reload
```
这将启动一个名为main的ASGI应用程序，使用uvcorn服务器运行在本地主机的默认8000端口上，并监听根路径`/`的GET请求。在浏览器中访问`http://localhost:8000/`，将看到"{"message":"Hello World"}"
#### 2.4、配置选项
Uvcorn提供了丰富的配置选项，以满足不同需求。可以通过命令行参数或配置文件来配置Uvcorn的行为。以下是常用的配置选项：
- --host：指定主机地址，默认为127.0.0.1
- --port：指定端口号，默认为8000
- --workers：指定工作进程数量，默认为CPU核心数的1倍
- --log-level：指定日志级别，默认为info
- --reload：在代码修改时自动重新加载应用程序
#### 2.5、高级功能
- SLL支持
Uvcorn支持通过SLL加密来提供安全的通信，可以使用`--ssl-keyfile`和`--ssl-certfile`参数来指定SLL密钥文件和证书文件。
```sh
uvconr main:app --ssl-keyfile key.pem --ssl-certfile cert.pem
```

- WebSocket支持
除了支持HTTP请求外，Uvcorn还支持处理WebSocket连接，用于实时通信应用程序。可以在FastAPI中使用`WebSocket`类来处理WebSocket链接。
```python
from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_test()
        await websocket.send_text(f"message test: {data}")
```
- 中间件
Uvcorn支持使用中间件来修改请求和响应，以及执行其他自定义操作。可以通过`--middleware`参数来指定中间件。
```python
from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}
```
- 异步任务

- 自定义错误处理