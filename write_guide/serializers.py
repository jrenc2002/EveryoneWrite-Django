from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'user_id',
            'username',
            'utool_id',
            'default_language',
            'learning_language',
            'registration_time',
            'token_balance',
            'update_time',
            'delete_time',
        ]
