"""GitHub App that automatically labels new issues using a trained ML classifier.

Listens for GitHub webhook events, predicts a label from the issue title and
body, applies it to the issue, and leaves a comment asking for feedback.
"""

import os

import aiohttp
import joblib
from aiohttp import web
from gidgethub import aiohttp as gh_aiohttp
from gidgethub import routing
from gidgethub import sansio

MODEL_PATH = "./models/issue_label_classifier.joblib"
BOT_COMMENT = (
    "Greetings 😄, I'm Srini Bot. I predicted a label for this issue. "
    "If it doesn't fit, please correct it. Your feedback helps my creator improve me!"
)

model = joblib.load(MODEL_PATH)
routes = web.RouteTableDef()
router = routing.Router()


def predict_label(title: str, body: str) -> str:
    """Predict an issue label from its title and body text."""
    text = [f"{title} {body}"]
    return model.predict(text)[0]


@router.register("issues", action="opened")
async def issue_opened_event(event, gh, *args, **kwargs):
    """Label a newly opened issue and post a feedback comment."""
    issue = event.data["issue"]
    label = predict_label(issue["title"], issue["body"])

    await gh.post(issue["labels_url"], data=[{"name": label}])
    await gh.post(issue["comments_url"], data={"body": BOT_COMMENT})


@routes.post("/")
async def main(request):
    """Receive and dispatch GitHub webhook events."""
    body = await request.read()

    secret = os.environ.get("GH_SECRET")
    oauth_token = os.environ.get("GH_AUTH")

    event = sansio.Event.from_http(request.headers, body, secret=secret)
    async with aiohttp.ClientSession() as session:
        gh = gh_aiohttp.GitHubAPI(session, "Srinikstudent", oauth_token=oauth_token)
        await router.dispatch(event, gh)
    return web.Response(status=200)


if __name__ == "__main__":
    app = web.Application()
    app.add_routes(routes)

    port = os.environ.get("PORT")
    if port is not None:
        port = int(port)

    web.run_app(app, port=port)
