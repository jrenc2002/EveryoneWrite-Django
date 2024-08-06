from django.db import models
from django.utils import timezone
import uuid
from transformers import AutoTokenizer

class UtoolsUser(models.Model):
    """
    用户模型，用于存储用户的基本信息和状态。
    """
    utool_id = models.CharField(max_length=255, unique=True)  # utoolID，唯一标识
    registration_time = models.DateTimeField(default=timezone.now)  # 注册时间，默认当前时间
    token_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)  # 用户的token余额
    update_time = models.DateTimeField(auto_now=True)  # 更新时间，每次记录更新时自动更改
    delete_time = models.DateTimeField(null=True, blank=True)  # 删除时间，可为空



    class Meta:
        # 数据库中的表名为 `utools_user`，遵循通常的Django约定。
        db_table = 'utools_user'
        verbose_name = '用户'
        verbose_name_plural = '用户'

    def is_deleted(self):
        """
        检查用户是否被标记为删除。
        """
        return self.delete_time is not None



class Order(models.Model):
    """
    订单模型，用于管理用户的订单信息。
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('unpaid', 'Unpaid'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('paid', 'Paid'),
        ('unpaid', 'Unpaid'),
        ('refunded', 'Refunded'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('credit_card', 'Credit Card'),
        ('paypal', 'PayPal'),
        ('bank_transfer', 'Bank Transfer'),
        ('wechat', 'WeChat Pay'),  # 新增微信支付选项
    ]

    CURRENCY_CHOICES = [
        ('USD', 'US Dollar'),
        ('CNY', 'Chinese Yuan Renminbi'),  # 新增人民币选项
        ('EUR', 'Euro'),
    ]

    order_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)  # 订单ID，UUID类型
    user = models.ForeignKey(UtoolsUser, on_delete=models.CASCADE)  # 外键，关联到用户
    utools_order_id = models.CharField(max_length=50, unique=True, null=True, blank=True)  # uTools 订单号，确保唯一
    goods_id = models.CharField(max_length=50, null=True, blank=True)  # 商品ID
    attach = models.TextField(blank=True, null=True)  # 附加数据
    body = models.CharField(max_length=255)  # 支付内容
    order_status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='unpaid')  # 订单状态
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # 订单金额（元）
    pay_fee = models.IntegerField()  # 支付金额（分）
    created_at = models.DateTimeField(auto_now_add=True)  # 创建时间，记录创建时自动设置
    paid_at = models.DateTimeField(null=True, blank=True)  # 用户支付时间
    updated_at = models.DateTimeField(auto_now=True)  # 更新时间，记录更新时自动设置
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default='unpaid')  # 支付状态
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='wechat')  # 支付方式，默认微信支付
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='CNY')  # 货币类型，默认人民币
    description = models.TextField(blank=True, null=True)  # 订单描述或备注信息
    token_added = models.IntegerField(default=0)  # 订单完成后增加的token数量


    def __str__(self):
        """
        返回订单的字符串表示，包括订单ID和用户信息。
        """
        return f"Order {self.order_id} for User {self.user.username}"

    class Meta:
        db_table = 'orders'
        verbose_name = '订单'
        verbose_name_plural = '订单'
class WritingTask(models.Model):
    """
    写作任务模型，用于管理用户的写作任务信息和状态。
    """
    TASK_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    MODEL_CHOICES = [
        ('bert', 'BERT'),
        ('gpt-3.5-turbo', 'GPT-3.5-Turbo'),
    ]

    task_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)  # 任务ID，UUID类型
    user = models.ForeignKey(UtoolsUser, on_delete=models.CASCADE)  # 外键，关联到用户
    source_language = models.CharField(max_length=100)  # 源语言
    target_language = models.CharField(max_length=100)  # 学习语言
    model_type = models.CharField(max_length=50, choices=MODEL_CHOICES, default='bert')  # 模型类型，确保默认值存在于选择列表中
    ai_understanding_content = models.TextField()  # 源语言辅助AI理解的内容
    user_attempt_content = models.TextField()  # 用户输入的尝试写作内容
    ai_guidance_content = models.TextField(blank=True, null=True)  # AI返回的写作指导内容
    created_at = models.DateTimeField(auto_now_add=True)  # 创建时间，记录创建时自动设置
    token_spent = models.IntegerField(default=0)  # Token花费的数量
    task_quota = models.IntegerField(default=0)  # 任务额度
    status = models.CharField(max_length=10, choices=TASK_STATUS_CHOICES, default='pending')  # 任务状态
    description = models.TextField(blank=True, null=True)  # 任务描述或备注信息

    def __str__(self):
        """
        返回任务的字符串表示，包括任务ID和用户信息。
        """
        return f"Task {self.task_id} for User {self.user.username} using {self.model_type}"

    def calculate_token_cost(self):
        """
        计算任务的Token花费，使用Hugging Face Transformers根据模型类型计算多语言的token数量。
        """
        # 根据模型类型选择合适的tokenizer
        tokenizer = AutoTokenizer.from_pretrained(self.model_type)

        # 使用tokenizer编码用户的尝试写作内容
        tokens = tokenizer.encode(self.user_attempt_content, add_special_tokens=True)

        # 计算token数量
        num_tokens = len(tokens)

        # 设置基础token消耗和额外消耗
        base_cost = 10  # 基础Token消耗
        additional_cost = num_tokens  # 每个token消耗一个单位

        # 返回总消耗
        return base_cost + additional_cost

    def save(self, *args, **kwargs):
        """
        保存任务时计算token花费并更新字段。
        """
        # 调用token计算方法
        self.token_spent = self.calculate_token_cost()

        # 保存实例
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'writing_tasks'
        verbose_name = '写作任务'
        verbose_name_plural = '写作任务'

