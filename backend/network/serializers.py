from rest_framework import serializers
from .models import Changeset, Node, Link, NodeVersion, LinkVersion
from django.contrib.auth import get_user_model

User = get_user_model()

class NodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Node
        fields = '__all__'

class LinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Link
        fields = '__all__'

class NodeVersionSerializer(serializers.ModelSerializer):
    node_id = serializers.IntegerField(source='node.id', read_only=True)
    changeset_id = serializers.IntegerField(source='changeset.id', read_only=True)

    class Meta:
        model = NodeVersion
        fields = [
            'id',
            'node_id',
            'version',
            'geometry',
            'attributes',
            'changeset_id',
            'created_at',
        ]

class LinkVersionSerializer(serializers.ModelSerializer):
    link_id = serializers.IntegerField(source='link.id', read_only=True)
    from_node = serializers.IntegerField(source='from_node.id', read_only=True)
    to_node = serializers.IntegerField(source='to_node.id', read_only=True)
    changeset_id = serializers.IntegerField(source='changeset.id', read_only=True)

    class Meta:
        model = LinkVersion
        fields = [
            'id',
            'link_id',
            'version',
            'from_node',
            'to_node',
            'geometry',
            'attributes',
            'changeset_id',
            'created_at',
        ]

class ChangesetSerializer(serializers.ModelSerializer):
    depends_on = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = Changeset
        fields = ['id', 'comment', 'pid', 'created_at', 'user', 'editor', 'auth_area', 'is_base_network', 'base_network', 'depends_on']

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username', 'full_name', 'organization', 'email')
        read_only_fields = ('username', 'full_name', 'organization', 'email')

class CustomUserSignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'password')

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password']
        )
        return user
