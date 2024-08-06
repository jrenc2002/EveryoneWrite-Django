from .authentication import CustomJWTAuthentication
from .models import UtoolsUser, Order, WritingTask
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
import requests
import hmac
import hashlib
import time
import urllib.parse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import status
# 插件应用 ID 和 secret，可以在开发者插件应用中获得
PLUGIN_ID = "z34ufx63"  # 替换为实际的插件应用 ID
SECRET = "awx7qaX72WPN6L23Ai4GXDkeXDoB3Q1C"  # 替换为实际的 secret


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
import requests
import urllib
import hmac
import hashlib
import time

# 引入自定义的JWT生成器
from .authentication import generate_jwt_for_utools_user
from .models import UtoolsUser

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


class ArticleRewriteView(APIView):
    """
    文章改写视图，处理用户的写作请求并提供写作指导。
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        source_language = request.data.get('source_language')
        target_language = request.data.get('target_language')
        user_attempt_content = request.data.get('user_attempt_content')
        ai_understanding_content = request.data.get('ai_understanding_content')

        # 生成写作指导（这里可以集成实际的AI模型逻辑）
        ai_guidance_content = f"Rewritten content from {source_language} to {target_language}"

        # 创建写作任务记录
        writing_task = WritingTask.objects.create(
            user=user,
            source_language=source_language,
            target_language=target_language,
            ai_understanding_content=ai_understanding_content,
            user_attempt_content=user_attempt_content,
            ai_guidance_content=ai_guidance_content,
        )

        return Response({
            'task_id': writing_task.task_id,
            'ai_guidance_content': writing_task.ai_guidance_content,
            'token_spent': writing_task.token_spent
        }, status=200)


class OrderQueryView(APIView):
    """
    订单查询视图，返回用户的所有订单信息。
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        orders = Order.objects.filter(user_id=user).values()
        return Response({'orders': list(orders)}, status=200)


class OrderCreateAndPayView(APIView):
    """
    订单创建和支付视图，处理用户订单创建和支付请求。
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        amount = request.data.get('amount')
        payment_method = request.data.get('payment_method', 'wechat')

        # 创建订单
        order = Order.objects.create(
            user_id=user,
            amount=amount,
            payment_method=payment_method,
            currency='CNY',
        )

        # 模拟支付逻辑
        payment_status = 'success'  # 假设支付成功

        if payment_status == 'success':
            order.payment_status = 'paid'
            order.order_status = 'completed'
            order.token_added = 100  # 假设支付成功后增加100 token
            order.save()

            user.token_balance += order.token_added
            user.save()

            return Response({'status': 'success', 'balance': user.token_balance}, status=200)
        else:
            order.payment_status = 'failed'
            order.save()
            return Response({'status': 'failed'}, status=400)
