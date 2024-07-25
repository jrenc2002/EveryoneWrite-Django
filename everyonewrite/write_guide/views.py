import os
import json
import requests
import asyncio
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import ValidationError
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.tmt.v20180321 import tmt_client, models
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from dotenv import load_dotenv

load_dotenv()  # 从.env文件中读取环境变量

# 模拟写作指导函数
def writing_guidance(prompt, model):
    simulate_silicon_flow_model_list = ["Qwen/Qwen2-72B-Instruct", "Qwen/Qwen2-7B-Instruct", "Qwen/Qwen1.5-110B-Chat", "Qwen/Qwen2-57B-A14B-Instruct"]
    openai_model_list = ["gpt-4o"]
    if model in simulate_silicon_flow_model_list:
        return simulate_silicon_flow(prompt, model)
    elif model in openai_model_list:
        return simulate_silicon_flow(prompt, model)

# 硅基流动API模型调用
def simulate_silicon_flow(prompt, model):
    url = "https://api.siliconflow.cn/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "stream": False,
        "max_tokens": 512,
        "temperature": 0.7,
        "top_p": 0.7,
        "top_k": 50,
        "frequency_penalty": 0.5,
        "n": 1
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {os.getenv('SILICON_FLOW_API_KEY')}"
    }

    response = requests.post(url, json=payload, headers=headers)
    return response.json()

# 异步翻译函数
async def translate_text_tencent(text, source_lang, target_lang):
    try:
        cred = credential.Credential(os.getenv('TENCENT_CLOUD_API_KEY'), os.getenv('TENCENT_CLOUD_API_SECRET'))
        http_profile = HttpProfile(endpoint="tmt.tencentcloudapi.com")
        client_profile = ClientProfile(httpProfile=http_profile)
        client = tmt_client.TmtClient(cred, "ap-beijing", client_profile)

        req = models.TextTranslateRequest()
        params = {
            "SourceText": text,
            "Source": source_lang,
            "Target": target_lang,
            "ProjectId": 100016275430
        }
        req.from_json_string(json.dumps(params))

        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, client.TextTranslate, req)
        resp_dict = json.loads(resp.to_json_string())
        return {
            "TargetText": resp_dict.get("TargetText"),
            "Source": source_lang,
            "Target": target_lang,
            "RequestId": resp_dict.get("RequestId")
        }
    except TencentCloudSDKException as err:
        return {"error": "API request failed", "details": str(err)}
    except Exception as e:
        return {"error": "Internal server error", "details": str(e)}

# 模型选择中间层函数
def select_model(user_id, token, model_choice):
    if model_choice == "model_1":
        return "selected_model_1"
    elif model_choice == "model_2":
        return "selected_model_2"
    else:
        return "default_model"

# 合成writing_guidance的prompt
def compose_prompt_for_writing_guidance(user_input, native_language, learning_language):
    return f"User input: {user_input}, Native language: {native_language}, Learning language: {learning_language}"

# 合成translated_writing_guidance的prompt
def compose_prompt_for_translated_writing_guidance(translated_text, native_language, learning_language):
    return f"Translated text: {translated_text}, Native language: {native_language}, Learning language: {learning_language}"

class AIWritingAssistant(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    async def post(self, request):
        try:
            data = request.data
            user_id = data.get('user_id')
            token = data.get('token')
            user_input = data.get('user_input')
            native_language = data.get('native_language')
            learning_language = data.get('learning_language')
            model_choice = data.get('model_choice')
            assist_expression = data.get('assist_expression', None)

            if not all([user_id, token, user_input, native_language, learning_language, model_choice]):
                raise ValidationError("Missing required fields")

            # 选择模型
            selected_model = select_model(user_id, token, model_choice)

            # 根据是否有辅助表达来合成不同的prompt
            if not assist_expression:
                prompt = compose_prompt_for_writing_guidance(user_input, native_language, learning_language)
                result = writing_guidance(prompt, selected_model)
            else:
                translation = await translate_text_tencent(assist_expression, native_language, learning_language)
                if "error" in translation:
                    return Response(translation, status=500)
                translated_text = translation.get("TargetText")
                prompt = compose_prompt_for_translated_writing_guidance(translated_text, native_language, learning_language)
                result = writing_guidance(prompt, selected_model)

            return Response(result)
        except ValidationError as e:
            return Response({"error": str(e)}, status=400)
        except json.JSONDecodeError:
            return Response({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            return Response({"error": "Internal server error", "details": str(e)}, status=500)
