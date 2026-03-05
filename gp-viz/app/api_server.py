import os

import uvicorn

from app.api import create_app


def main() -> None:
    app = create_app()
    host = os.getenv("GP_API_HOST", "0.0.0.0")
    port = int(os.getenv("GP_API_PORT", "8080"))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
