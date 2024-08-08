from django.urls import include, path
from rest_framework import routers
from tutorial.quickstart import views
from write_guide.views import UserLoginAPIView, BalanceView, AIWritingAssistant, OrderQueryView, CreateOrderAPIView

# 导入drf-yasg相关模块
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions

# 定义Swagger的Schema View
schema_view = get_schema_view(
    openapi.Info(
        title="EveryoneWrite",  # API标题
        default_version='v1',    # API版本
        description="EveryoneWrite的API描述文档",  # API描述
        terms_of_service="https://www.example.com/terms/",  # 服务条款
        contact=openapi.Contact(email="862055705@qq.com"),  # 联系信息
        license=openapi.License(name="BSD License"),  # 许可证信息
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),  # 设置公共访问权限
)

router = routers.DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'groups', views.GroupViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('api/login/', UserLoginAPIView.as_view(), name='user-login'),
    path('api/balance/', BalanceView.as_view(), name='balance'),
    path('api/writing-guidance/', AIWritingAssistant.as_view(), name='writing_guidance'),
    path('api/order-query/', OrderQueryView.as_view(), name='order_query'),
    path('api/create-order/', CreateOrderAPIView.as_view(), name='order_create'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('swagger.yaml/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
]
