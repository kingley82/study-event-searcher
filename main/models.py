from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
from django.core.validators import RegexValidator
import datetime

# Create your models here.
class Category(models.Model):
    name = models.CharField(max_length=64)
    def __str__(self):
        return self.name

def user_directory_path() : return "events/"

class UserManager(BaseUserManager):
    def create_user(self, login, password, name, birthday):
        user = self.model(
            login=login,
            name=name,
            birthday=birthday
        )

        user.set_password(password)  # хеширует пароль
        user.save(using=self._db)
        return user

    def create_superuser(self, login, password, name, birthday):
        user = self.create_user(login, password, name, birthday)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

class User(AbstractBaseUser, PermissionsMixin):
    login = models.CharField(max_length=32, unique=True, validators=[RegexValidator(r'^[0-9a-zA-Z_]*$', 'Можно использовать только латинские буквы, цифры и нижнее подчеркивание')])
    name = models.CharField(max_length=72)
    birthday = models.DateField(null=True, blank=True, default=datetime.date.fromtimestamp(946659600))
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True, default="avatars/default.png",)

    tg_account = models.CharField(max_length=48, null=True, blank=True)
    max_account = models.CharField(max_length=48, null=True, blank=True)
    vk_account = models.CharField(max_length=48, null=True, blank=True)
    whatsapp_account = models.CharField(max_length=48, null=True, blank=True)
    insta_account = models.CharField(max_length=48, null=True, blank=True)

    lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    lon = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "login"
    REQUIRED_FIELDS = ["name", "password", "birthday"]

    def __str__(self):
        return self.login + " - " + self.name
    
class Event(models.Model):
    name = models.CharField(max_length=64)
    desc = models.TextField(max_length=2048)
    address = models.CharField(max_length=640)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    image = models.ImageField(upload_to="events/", null=False, blank=False, default="event/default.png",)
    # category = models.ForeignKey(Category, on_delete=models.CASCADE)
    date = models.DateTimeField()
    enddate = models.DateTimeField()
    explicit = models.BooleanField(default=False)
    org = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    timezone = models.CharField(max_length=64)

class UserEventRegister(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    
class Comment(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.SmallIntegerField()
    comment = models.TextField()
    image = models.ImageField(upload_to='comments/', null=True, blank=True)
    time = models.DateTimeField(auto_now_add=True)

class OrgComment(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="summary")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.TextField()
    image = models.ImageField(upload_to='comments/', null=True, blank=True)
    time = models.DateTimeField(auto_now_add=True)