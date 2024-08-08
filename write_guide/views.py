from django.utils.decorators import method_decorator
from .authentication import CustomJWTAuthentication
from django.utils import timezone
import requests
import urllib
import hmac
import hashlib
import time
import os
import json
import asyncio
import requests
from asgiref.sync import sync_to_async, async_to_sync
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from asgiref.sync import sync_to_async
# 引入自定义的JWT生成器
from .authentication import generate_jwt_for_utools_user
from .models import UtoolsUser, Order, WritingTask

import urllib.parse
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.tmt.v20180321 import tmt_client, models
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from dotenv import load_dotenv
from rest_framework.exceptions import ValidationError
load_dotenv()  # 从.env文件中读取环境变量

from rest_framework.permissions import IsAuthenticated

# 插件应用 ID 和 secret，可以在开发者插件应用中获得
PLUGIN_ID = "z34ufx63"  # 替换为实际的插件应用 ID
SECRET = "awx7qaX72WPN6L23Ai4GXDkeXDoB3Q1C"  # 替换为实际的 secret



class UserLoginAPIView(APIView):
    """
    用户登录API视图，用于处理用户的登录请求。
    """

    def get_signature(self, params):
        """
        根据uTools的签名方法生成请求签名。
        """
        # 1. 按照键名对数组进行升序排序
        sorted_params = sorted(params.items())

        # 2. 生成 URL-encode 之后的请求字符串
        str_to_sign = urllib.parse.urlencode(sorted_params)

        # 3. 使用 HMAC 方法生成带有密钥的哈希值
        sign = hmac.new(SECRET.encode('utf-8'), str_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()

        return sign

    def get_user_info(self, access_token):
        """
        通过uTools API获取用户信息。
        """
        url = "https://open.u-tools.cn/baseinfo"
        timestamp = int(time.time())

        params = {
            "plugin_id": PLUGIN_ID,
            "access_token": access_token,
            "timestamp": str(timestamp),
        }

        sign = self.get_signature(params)
        params["sign"] = sign

        headers = {
            "Accept": "application/json",
        }

        response = requests.get(url, params=params, headers=headers)

        if response.status_code == 200:
            return response.json().get("resource")
        else:
            return None

    def post(self, request):
        """
        处理用户的登录请求。
        """
        access_token = request.data.get("access_token")
        if not access_token:
            return Response({"message": "Access token is required."}, status=status.HTTP_400_BAD_REQUEST)

        user_info = self.get_user_info(access_token)
        if not user_info:
            return Response({"message": "Failed to authenticate with uTools."}, status=status.HTTP_401_UNAUTHORIZED)

        open_id = user_info.get("open_id")
        nickname = user_info.get("nickname")
        avatar = user_info.get("avatar")
        member = user_info.get("member")

        # 检查用户是否已经注册
        utools_user, created = UtoolsUser.objects.get_or_create(
            utool_id=open_id,
            defaults={"token_balance": 500}  # 新用户默认增加500个token
        )

        if created:
            utools_user.registration_time = timezone.now()
            utools_user.save()

        # 使用自定义JWT生成器生成JWT token
        jwt_token = generate_jwt_for_utools_user(utools_user)

        # 返回用户信息和JWT token
        return Response({
            "message": "Login successful",
            "token": jwt_token,
            "user_info": {
                "avatar": avatar,
                "nickname": nickname,
                "member": member,
                "token_balance": utools_user.token_balance
            }
        }, status=status.HTTP_200_OK)


class BalanceView(APIView):
    """
    余额查询视图，用于返回用户的余额信息。
    """
    authentication_classes = [CustomJWTAuthentication]

    def get(self, request):
        """
        处理余额查询请求。
        """
        # 获取经过身份验证的用户
        user = request.user  # 这是UtoolsUser对象

        # Debug: 打印经过身份验证的用户信息
        print(f"Authenticated User: {user}")

        # 确认user确实是UtoolsUser对象
        if isinstance(user, UtoolsUser):
            # Debug: 打印用户余额
            print(f"UtoolsUser Token Balance: {user.token_balance}")

            balance = user.token_balance
            return Response({"balance": balance}, status=status.HTTP_200_OK)
        else:
            # Debug: UtoolsUser未找到
            print("UtoolsUser not found.")
            return Response({"message": "UtoolsUser not found."}, status=status.HTTP_404_NOT_FOUND)





class AIWritingAssistant(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    async def writing_guidance_async(self, model_name, user_prompt):
        if model_name in ["Qwen/Qwen2-72B-Instruct", "Qwen/Qwen2-57B-A14B-Instruct"]:
            return await self.simulate_silicon_flow(model_name, user_prompt)
        return {"error": "Unsupported model"}

    @sync_to_async
    def simulate_silicon_flow(self, model_name, user_prompt):
        url = "https://api.siliconflow.cn/v1/chat/completions"
        payload = {
            "model": model_name,
            "messages": user_prompt,
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

    @sync_to_async
    def translate_text_tencent(self, text, source_lang, target_lang):
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

            resp = client.TextTranslate(req)
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

    def select_model(self, model_choice):
        return model_choice

    def compose_prompt_for_writing_guidance(self, user_input, native_lang, learning_lang):
        message=[
            {"role": "system", "content": f"你是一个富有经验，能力很强的{learning_lang}写作指导教师，而我是一个母语是{native_lang}的{learning_lang}学习者。"},
            {"role": "user", "content": f"现在请你使用{native_lang}来给我解析一下我的{learning_lang}写作内容-{user_input}，我希望你可以给我写作给予一个中肯的评价，同时可以指出我写作内容的不足或者可以改进的东西，可以给我以清晰的思路简练的语言讲清楚哪些写会好，好在哪里。如果它里面有你认为我可能不会的，值得学习的{learning_lang}固定搭配和语法知识请也一并告诉我。"}
        ]
        return message

    def compose_prompt_for_translated_text(self, translated_text, native_lang, learning_lang):
        message = [
            {"role": "system", "content": f"你是一个富有经验，能力很强的{learning_lang}写作指导教师，而我是一个母语是{native_lang}的{learning_lang}学习者。"},
            {"role": "user", "content": f"现在请你使用{native_lang}来给我讲解范文{translated_text}包含的固定搭配和语法知识。如果它里面有你认为我可能不会的，值得学习的固定搭配和语法知识请也一并告诉我。"}
        ]
        return message

    def compose_prompt_for_translated_writing_guidance(self, translated_text, user_input, native_lang, learning_lang):
        message = [
            {"role": "system", "content": f"你是一个富有经验，能力很强的{learning_lang}写作指导教师，而我是一个母语是{native_lang}的{learning_lang}学习者。"},
            {"role": "user", "content": f"现在请你使用{native_lang}来给我讲解范文{translated_text}包含的固定搭配和语法知识，同时你会根据我写的内容{user_input}和范文{translated_text}的不同来进行写作指导的讲解和更改建议,如果它里面有你认为我可能不会的，值得学习的固定搭配和语法知识请也一并告诉我。"}
        ]
        return message

    @method_decorator(csrf_exempt)
    def post(self, request):
        try:
            data = json.loads(request.body)
            user = request.user
            if not user.is_authenticated:
                return JsonResponse({"message": "User not authenticated."}, status=401)

            assist_expression = data.get('assist_expression', None)
            user_input = data.get('user_input', None)
            native_language = data.get('native_language')
            learning_language = data.get('learning_language')
            model_choice = data.get('model_choice', 'Qwen/Qwen2-72B-Instruct')

            if not all([native_language, learning_language, model_choice]):
                raise ValidationError("Missing required fields")

            selected_model = self.select_model(model_choice)

            if assist_expression and user_input:
                translation = async_to_sync(self.translate_text_tencent)(assist_expression, native_language, learning_language)
                if "error" in translation:
                    return JsonResponse(translation, status=500)
                translated_text = translation.get("TargetText")
                message = self.compose_prompt_for_translated_writing_guidance(translated_text, user_input, native_language, learning_language)
            elif assist_expression and not user_input:
                translation = async_to_sync(self.translate_text_tencent)(assist_expression, native_language, learning_language)
                if "error" in translation:
                    return JsonResponse(translation, status=500)
                translated_text = translation.get("TargetText")
                message = self.compose_prompt_for_translated_text(translated_text, native_language, learning_language)
            elif not assist_expression and user_input:
                message = self.compose_prompt_for_writing_guidance(user_input, native_language, learning_language)
            else:
                return JsonResponse({"error": "Missing both assist_expression and user_input"}, status=400)

            result = async_to_sync(self.writing_guidance_async)(selected_model, message)
            return JsonResponse(result, status=200)
        except ValidationError as e:
            return JsonResponse({"error": str(e)}, status=400)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"error": "Internal server error", "details": str(e)}, status=500)
class OrderQueryView(APIView):
    """
    订单查询视图，返回用户的所有订单信息。
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        orders = Order.objects.filter(user_id=user).values()
        return Response({'orders': list(orders)}, status=200)


class CreateOrderAPIView(APIView):
    """
    创建订单并处理支付的API视图。
    """
    authentication_classes = [CustomJWTAuthentication]

    def get_signature(self, params):
        """
        根据uTools的签名方法生成请求签名。
        """
        sorted_params = sorted(params.items())
        str_to_sign = urllib.parse.urlencode(sorted_params)
        sign = hmac.new(SECRET.encode('utf-8'), str_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
        return sign

    def create_goods(self, title, total_fee):
        """
        通过uTools API动态创建商品。
        """
        url = "https://open.u-tools.cn/goods"
        timestamp = int(time.time())

        params = {
            "plugin_id": PLUGIN_ID,
            "title": title,
            "total_fee": total_fee,
            "timestamp": str(timestamp),
        }

        sign = self.get_signature(params)
        params["sign"] = sign

        headers = {
            "Accept": "application/json",
        }

        response = requests.post(url, json=params, headers=headers)

        if response.status_code == 200:
            return response.json().get("message")
        else:
            return None

    def get_payment_status(self, out_order_id):
        """
        通过uTools API查询订单支付状态。
        """
        url = "https://open.u-tools.cn/payments/record"
        timestamp = int(time.time())

        params = {
            "plugin_id": PLUGIN_ID,
            "out_order_id": out_order_id,
            "timestamp": str(timestamp),
        }

        sign = self.get_signature(params)
        params["sign"] = sign

        headers = {
            "Accept": "application/json",
        }

        response = requests.get(url, params=params, headers=headers)

        if response.status_code == 200:
            return response.json().get("resource")
        else:
            return None

    def post(self, request):
        """
        处理订单创建和支付请求。
        """
        user = request.user  # 经过身份验证的用户
        if not isinstance(user, UtoolsUser):
            return Response({"message": "User not authenticated."}, status=status.HTTP_401_UNAUTHORIZED)

        # 获取前端传来的订单数据
        body = request.data.get("body")
        amount = request.data.get("amount")  # 金额（元）
        total_fee = int(amount * 100)  # 转换为分

        # 创建uTools商品
        goods_id = self.create_goods(title=body, total_fee=total_fee)
        if not goods_id:
            return Response({"message": "Failed to create goods on uTools."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 创建新订单
        order = Order.objects.create(
            user=user,
            body=body,
            amount=amount,
            pay_fee=total_fee,
            goods_id=goods_id,
            order_status='pending',
            payment_status='unpaid',
        )

        # 返回订单ID和支付信息给前端
        return Response({
            "message": "Order created",
            "order_id": order.order_id,
            "amount": amount,
            "pay_fee": total_fee,
            "goods_id": goods_id
        }, status=status.HTTP_201_CREATED)

    def put(self, request):
        """
        处理支付成功后的确认请求。
        """
        order_id = request.data.get("order_id")
        try:
            order = Order.objects.get(order_id=order_id)
        except Order.DoesNotExist:
            return Response({"message": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        payment_status = self.get_payment_status(order.utools_order_id)
        if payment_status and payment_status.get("status") == 10:
            order.payment_status = 'paid'
            order.paid_at = timezone.now()
            order.save()

            # 增加用户token
            user = order.user
            user.token_balance += order.token_added
            user.save()

            return Response({"message": "Payment confirmed and tokens added."}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "Payment not confirmed."}, status=status.HTTP_400_BAD_REQUEST)