from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *
from langchain_openai import ChatOpenAI
import tempfile, os, datetime, time, traceback

app = Flask(__name__)
static_tmp_path = os.path.join(os.path.dirname(__file__), 'static', 'tmp')

# Channel Access Token
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
# Channel Secret
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

# NVIDIA API Key initialization
os.environ['NVIDIA_API_KEY'] = os.getenv('NVIDIA_API_KEY')
llm = ChatOpenAI(
    model="meta/llama3-70b-instruct",
    openai_api_key=os.environ["NVIDIA_API_KEY"],
    openai_api_base="https://integrate.api.nvidia.com/v1",
    temperature=0.5,
    max_tokens=1024,
    model_kwargs={"top_p": 1},
)

def GPT_response(text):
    try:
        response = llm.invoke(text)
        answer = response['choices'][0]['text'].replace('。', '')
        return answer
    except Exception as e:
        print(traceback.format_exc())
        return "Error in generating response"

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text
    try:
        GPT_answer = GPT_response(msg)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(GPT_answer))
    except Exception as e:
        print(traceback.format_exc())
        line_bot_api.reply_message(event.reply_token, TextSendMessage('你所使用的OPENAI API key額度可能已經超過，請於後台Log內確認錯誤訊息'))

@handler.add(PostbackEvent)
def handle_postback(event):
    print(event.postback.data)

@handler.add(MemberJoinedEvent)
def welcome(event):
    uid = event.joined.members[0].user_id
    gid = event.source.group_id
    profile = line_bot_api.get_group_member_profile(gid, uid)
    name = profile.display_name
    message = TextSendMessage(text=f'{name}歡迎加入')
    line_bot_api.reply_message(event.reply_token, message)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
