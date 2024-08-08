# authentication.py

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import exceptions
from django.utils.translation import gettext_lazy as _
from write_guide.models import UtoolsUser
from rest_framework_simplejwt.tokens import RefreshToken
# authentication.py

class CustomJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        """
        自定义get_user方法，通过utool_id进行用户认证。
        """
        try:
            # 从JWT中获取utool_id
            utool_id = validated_token.get('utool_id')
            if not utool_id:
                raise exceptions.AuthenticationFailed(_('UtoolsUser ID not found in token'))

            # 查找对应的UtoolsUser
            utools_user = UtoolsUser.objects.get(utool_id=utool_id)

            # Debug: 打印找到的UtoolsUser对象
            print(f"Authenticated UtoolsUser: {utools_user}")
            
            # 返回找到的UtoolsUser对象
            return utools_user
        except UtoolsUser.DoesNotExist:
            raise exceptions.AuthenticationFailed(_('UtoolsUser not found'), code='utools_user_not_found')
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            raise



from rest_framework_simplejwt.tokens import RefreshToken


def generate_jwt_for_utools_user(utools_user):
    """
    为UtoolsUser生成JWT，确保将utool_id包含在内。
    """
    # 创建刷新token
    refresh = RefreshToken()

    # 添加自定义的utool_id到token的payload中
    refresh['utool_id'] = utools_user.utool_id
    print(refresh)

    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }
