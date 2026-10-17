"""Local launcher disables raw-path server access logs; bounded app logs remain."""
import uvicorn
from app.api.config import load_config
from app.main import create_app


def main():
    config = load_config()
    uvicorn.run(create_app(config), host=config.api_host, port=config.api_port, access_log=False)


if __name__ == '__main__':
    main()
