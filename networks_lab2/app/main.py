from fastapi import FastAPI, Depends, Response, Request
from fastapi.responses import HTMLResponse, FileResponse
import redis

app = FastAPI()
r = redis.Redis(host="redis")
r.set("zInIu", "1004890")
r.set("jUnYi", "1004891")
r.set("lInGaO", "1004892")


def get_redis_client():
    return redis.Redis(host="redis")


@app.get("/", response_class=HTMLResponse)
async def read_root():
    html_content = """
        <html>
            <head>
                <title>students</title>
            </head>
            <body>
                <h1>change query params to get some students...</h1>
                <a href="/students">students</a>
            </body>
        </html>
        """
    return html_content


@app.get("/students")
async def get_students(sort: int = 0, limit: int = -1, in_r: redis.Redis = Depends(get_redis_client)):
    # sort: 1=asc
    result = {}
    for key in in_r.keys():
        result[key] = in_r.get(key)
    if sort == 1:
        result = sorted(result.items(), key=lambda i: i[1])
    else:
        result = sorted(result.items(), key=lambda i: i[1], reverse=True)
    if limit < 0:
        return result
    else:
        return result[:limit]


@app.get("/students/{student_id}", status_code=200)
async def get_students_by_id(response: Response, student_id: str, in_r: redis.Redis = Depends(get_redis_client)):
    # sort: 1=asc
    for key in in_r.keys():
        val = in_r.get(key)
        if student_id == val.decode():
            return {key: val}
    response.status_code = 404
    return "this student does not exist"


@app.post("/students")
async def create_student(student: dict, in_r: redis.Redis = Depends(get_redis_client)):
    in_r.set(student["name"], student["id"])


@app.delete("/students/{student_id}")
async def delete_student(response: Response, student_id: str, in_r: redis.Redis = Depends(get_redis_client)):
    for key in in_r.keys():
        val = in_r.get(key)
        if student_id == val.decode():
            in_r.delete(key)
            return
    response.status_code = 404
    return "this student does not exist"


# challenge
# Have a route in your application that returns a content type
# that is not plaintext

# Some form of authorization through inspecting the request headers
@app.get("/image")
async def main(request: Request, response: Response):
    if request.headers["my-passcode"] != "iLoveCuteCats":
        response.status_code=403
        return
    return FileResponse("cat.jpg")

