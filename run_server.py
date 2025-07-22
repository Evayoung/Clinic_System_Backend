import uvicorn

if __name__ == "__main__":
    uvicorn.run("app_package.main:app", host="127.0.0.1", port=8006, reload=True)
    # uvicorn.run("app_package.main:app", host="0.0.0.0", port=10000)