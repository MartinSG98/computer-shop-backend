"""AWS Lambda entry point.

Wraps the FastAPI app with Mangum so API Gateway events are translated to
ASGI. Set the Lambda handler to `app.lambda_handler.handler`.
"""

from mangum import Mangum

from app.main import app

handler = Mangum(app)
