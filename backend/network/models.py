from django.contrib.gis.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.contrib.auth import get_user_model

class CustomUserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError("The Username must be set")
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(username, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    id = models.AutoField(primary_key=True, editable=False)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(blank=True)
    organization = models.CharField(max_length=10)
    full_name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    
    auth_area = models.CharField(max_length=20)

    objects = CustomUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.username

class Node(models.Model):
    id = models.AutoField(primary_key=True, editable=False)

    def __str__(self):
        return str(self.id)

class NodeVersion(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    node = models.ForeignKey(Node, on_delete=models.CASCADE, related_name='versions')
    version = models.IntegerField()
    active = models.BooleanField(default=True, null=True)
    geometry = models.PointField(srid=3735)
    attributes = models.JSONField(blank=True, default=dict)

    changeset = models.ForeignKey("Changeset", on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('node', 'version')

    def __str__(self):
        return f"NodeVersion {self.node} v{self.version}"


class Link(models.Model):
    id = models.AutoField(primary_key=True, editable=False)

    def __str__(self):
        return str(self.id)

class LinkVersion(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    link = models.ForeignKey(Link, on_delete=models.CASCADE, related_name='versions')
    version = models.IntegerField()
    active = models.BooleanField(default=True, null=True)

    f_node = models.ForeignKey(Node, on_delete=models.PROTECT, related_name='outgoing_links')
    t_node = models.ForeignKey(Node, on_delete=models.PROTECT, related_name='incoming_links')

    geometry = models.LineStringField(srid=3735)
    attributes = models.JSONField(blank=True, default=dict)

    changeset = models.ForeignKey("Changeset", on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('link', 'version')

    def __str__(self):
        return f"LinkVersion {self.link} v{self.version}"

class Changeset(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    user = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True, blank=True)
    comment = models.TextField(blank=True)
    pid = models.CharField(max_length=100, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    editor = models.CharField(max_length=100, blank=True)
    
    auth_area = models.CharField(max_length=20)
    is_base_network = models.BooleanField(default=False)
    base_network = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        related_name='descendants',
        null=True, 
        blank=True
    )
    depends_on = models.ManyToManyField('self', symmetrical=False, blank=True, related_name='required_by')

    def __str__(self):
        return f"Changeset {self.id} ({self.pid or 'No project name'})"