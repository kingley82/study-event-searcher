from django import forms
from django.contrib.auth import authenticate
from .models import *
from django.forms.widgets import ClearableFileInput
from django.utils import timezone
import string
from .curse import censor_text
import datetime
from zoneinfo import ZoneInfo
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile

SLAVIC_LETTERS = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдеёжзийклмнопрстуфхцчшщъыьэюяҐґЄєІіЇїЎўЈјЉљЊњЋћЂђЏџЃѓЅѕЌќ"

class RegisterForm(forms.ModelForm):
    password1 = forms.CharField(widget=forms.PasswordInput, label="Пароль")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Повторите пароль")

    class Meta:
        model = User
        fields = ["login", "name", "birthday"]
        widgets = {
            "birthday": forms.DateInput(attrs={
                "type": "date",
                "class": "form-input"
            }),
        }
        labels = {
            'login': 'Логин',
            'name': 'ФИО',
            'birthday': 'Дата рождения'
        }
        error_messages = {
            "login": {
                "unique": "Этот логин уже используется, придумайте другой."
            }
        }

    def clean(self):
        cleaned_data = super().clean()

        login = cleaned_data.get("login")
        if login:
            login = login.strip()
            if len(login) < 4: self.add_error("login", "Логин слишком короткий")
            for i in login:
                if i not in string.ascii_letters + string.digits + string.punctuation:
                    self.add_error("login", "Логин может содержать только латинские буквы, цифры и специальные символы")
                    break
        
        name = cleaned_data.get("name")
        if name:
            name = name.strip()
            if name == "": self.add_error("name", "Заполните это поле")
            else:
                length = len(name.split())
                if length == 1: self.add_error("name", "Введите корректное ФИО")
                if length > 3: self.add_error("name", "Введите корректное ФИО. Если одна из его частей составная, используйте '-'")
            if name != censor_text(name): self.add_error("name", "ФИО содержит неприемлимые выражения")
            for i in name:
                if i not in SLAVIC_LETTERS+"- ": 
                    self.add_error("name", "Пожалуйста, используйте только кириллические символы")
                    break
            name = " ".join(name.split())
            cleaned_data['name'] = name
            self.instance.name = name

        p1 = cleaned_data.get("password1").strip()
        p2 = cleaned_data.get("password2").strip()

        has_letters = False
        has_numbers = False
        has_special = False

        if p1 and p2:
            if len(p1) < 8: self.add_error("password1", "Длина пароля должна быть не менее 8 символов")
            for i in p1:
                if i in string.ascii_letters: has_letters = True
                elif i in string.digits: has_numbers = True
                elif i in string.punctuation: has_special = True
                else:
                    self.add_error("password1", "Пароль содержит недопустимые символы")
                    break
            if sum([has_letters, has_numbers, has_special]) != 3:
                self.add_error("password1", "Пароль должен содержать хотя-бы одну букву латинского алфавита, одну цифру и один специальный символ")
            if p1 != p2:
                self.add_error("password2", "Пароли не совпадают")
        
        birthday = cleaned_data.get("birthday")
        if birthday.year < 1926: self.add_error("birthday", "Вы уже довольно стары, посидите дома")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])

        if commit:
            user.save()

        return user


class LoginForm(forms.Form):
    login = forms.CharField(max_length=72, label="Логин")
    password = forms.CharField(widget=forms.PasswordInput, label='Пароль')

    def clean(self):
        cleaned_data = super().clean()

        login = cleaned_data.get("login")
        password = cleaned_data.get("password")

        user = authenticate(login=login, password=password)

        if user is None:
            self.add_error("password", "Логин или пароль неверные")

        cleaned_data["user"] = user
        return cleaned_data
    
class CustomFileInput(ClearableFileInput):
    template_name = "widgets/custom_file_input.html"

class ProfileEditForm(forms.ModelForm):
    avatar = forms.ImageField(
        required=False,
        widget=CustomFileInput(),
        label="Аватар"
    )

    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-input"}),
        required=False,
        label="Старый пароль"
    )

    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-input"}),
        required=False,
        label="Новый пароль",
    )    

    class Meta:
        model = User
        fields = ["login", "name", "avatar", "tg_account", "max_account", "vk_account", "whatsapp_account", "insta_account"]

        widgets = {
            "login": forms.TextInput(attrs={"class": "form-input"}),
            "name": forms.TextInput(attrs={"class": "form-input"}),
            "tg_account": forms.TextInput(attrs={"placeholder": "https://t.me/", "class": "form-input"}),
            "max_account": forms.TextInput(attrs={"placeholder": "https://max.ru/", "class": "form-input"}),
            "vk_account": forms.TextInput(attrs={"placeholder": "https://vk.ru/", "class": "form-input"}),
            "whatsapp_account": forms.TextInput(attrs={"placeholder": "https://wa.me/ или https://chat.whatsapp.com/", "class": "form-input"}),
            "insta_account": forms.TextInput(attrs={"placeholder": "https://www.instagram.com/", "class": "form-input"})
        }
        labels = {
            "login": "Логин",
            "name": "Имя пользователя",
            "tg_account": "Ваш Telegram",
            "max_account": "Ваш MAX",
            "vk_account": "Ваш ВКонтакте",
            "whatsapp_account": "Ваш WhatsApp*",
            "insta_account": "Ваш Instagram*"
        }

    def clean_login(self):
        login = self.cleaned_data["login"]

        if User.objects.exclude(id=self.instance.id).filter(login=login).exists():
            raise forms.ValidationError("Этот логин уже занят")

        return login

    def clean(self):
        cleaned_data = super().clean()

        old_password = cleaned_data.get("old_password")
        new_password = cleaned_data.get("new_password")

        if new_password:
            if not old_password:
                self.add_error("old_password", "Введите старый пароль")

            elif not self.instance.check_password(old_password):
                self.add_error("old_password", "Старый пароль неверный")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)

        new_password = self.cleaned_data.get("new_password")

        if new_password:
            user.set_password(new_password)

        if commit:
            user.save()

        return user
    
class EventCreateForm(forms.ModelForm):
    image = forms.ImageField(
        required=True,
        widget=CustomFileInput()
    )

    class Meta:
        model = Event
        fields = ["name", "desc", "address", "image", "date", "enddate", "explicit", "latitude", "longitude", "timezone"]

        widgets = {
            "desc": forms.Textarea(attrs={"rows": 8, "class": "form-input", "style": "width: 100%;resize:none;"}),
            "name": forms.TextInput(attrs={"class": "form-input"}),

            "address": forms.TextInput(attrs={
                "class": "form-input",
                "readonly": True
            }),

            "date": forms.DateTimeInput(attrs={
                "type": "datetime-local",
                "class": "form-input"
            }),

            "enddate": forms.DateTimeInput(attrs={
                "type": "datetime-local",
                "class": "form-input"
            }),

            "explicit": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "latitude": forms.HiddenInput(),
            "longitude": forms.HiddenInput(),
            "timezone": forms.HiddenInput(attrs={"value": "UTC"}),
        }

        labels = {
            "name": "Название",
            "desc": "Описание",
            "address": "Адрес",
            "image": "Изображение",
            "date": "Дата начала",
            "enddate": "Дата окончания",
            "explicit": "18+ событие?",
        }

    def clean(self):
        cleaned_data = super().clean()

        name = cleaned_data.get("name")
        desc = cleaned_data.get("desc")
        date: datetime.datetime = cleaned_data.get("date")
        enddate = cleaned_data.get("enddate")
        tz = cleaned_data.get("timezone")
        image = cleaned_data.get("image")

        if date and enddate:
            if date.date() < datetime.datetime.now().astimezone(ZoneInfo(tz)).date(): self.add_error("date", "Указанный день уже прошел")
            if enddate < date:
                self.add_error("enddate", "Дата окончания не может быть раньше даты начала")
            # if timezone.is_naive(date):
            #     print(f"NAIVE {date}")
            #     cleaned_data["date"] = timezone.make_aware(date, timezone.get_current_timezone())

            # if timezone.is_naive(enddate):
            #     cleaned_data["enddate"] = timezone.make_aware(enddate, timezone.get_current_timezone())

        if name:
            if name != censor_text(name): self.add_error("name", "Название содержит нецензурные выражения")
        if desc:
            if desc != censor_text(desc): self.add_error("desc", "Описание содержит нецензурные выражения")

        if image:
            img = Image.open(image)
            img = img.convert("RGB")

            width = img.width
            height = img.height
            d_w = 0
            d_h = 0
            coords = (0, 0)
            if img.width / img.height != 16/9:
                d_w = height*(16/9)
                d_h = width*(9/16)
                if d_w > img.width:
                    width = int(d_w)
                    height = int(img.height)
                    print(d_w-img.width, int(d_w-img.width), int(d_w-img.width)//2)
                    coords = (int(d_w-img.width)//2, 0)
                elif d_h > img.height:
                    width = int(img.width)
                    height = int(d_h)
                    coords = (0, int(d_h-img.height)//2)
            print(width, height, d_w, d_h, coords)
            background = Image.new(mode="RGBA", size=(width, height))
            background.paste(img, coords)

            buffer = BytesIO()
            background.save(buffer, format="PNG", quality=100)
            buffer.seek(0)

            image = ContentFile(buffer.read(), name=image.name)
            cleaned_data['image'] = image
            self.instance.image = image

        return cleaned_data

class CommentForm(forms.ModelForm):
    # image = forms.ImageField(
    #     required=False,
    #     label="Фото",
    #     widget=CustomFileInput()
    # )
    class Meta:
        model = Comment
        fields = ["rating", "comment", "image"]

        widgets = {
            "rating": forms.NumberInput(attrs={"type": "range", "min": 1, "max": 5, "step": 1, "class": "rating", "style": "--val: 5", "oninput": "this.style='--val:'+this.value", "value": 5}),
            "comment": forms.Textarea(attrs={"style": "width: 100%; height: 150px;"}),
            "image": CustomFileInput()
        }

        labels = {
            "rating": "Оценка",
            "comment": "Комментарий",
            "image": "Фото"
        }
    
    def clean(self):
        cleaned_data = super().clean()

        comment = cleaned_data.get("comment")
        rating = cleaned_data.get("rating")

        if not comment or comment.strip() == "": self.add_error("comment", "Введите текст отчета")
        if not rating or rating > 5 or rating < 1: self.add_error("rating", "Укажите оценку")

        cleaned_data['comment'] = censor_text(comment)
        self.instance.comment = censor_text(comment)

        return cleaned_data
    
class OrgCommentForm(forms.ModelForm):
    class Meta:
        model = OrgComment
        fields = ["comment", "image"]

        widgets = {
            "comment": forms.Textarea(attrs={"style": "width: 100%; height: 150px;"}),
            "image": CustomFileInput()
        }

        labels = {
            "comment": "Комментарий",
            "image": "Фото"
        }
    
    def clean(self):
        cleaned_data = super().clean()

        comment = cleaned_data.get("comment")

        if not comment or comment.strip() == "": self.add_error("comment", "Введите текст комментария")

        # if comment != censor_text(comment): self.add_error("comment", "Комментарий содержит нецензурные выражения")

        cleaned_data['comment'] = censor_text(comment)
        self.instance.comment = censor_text(comment)

        return cleaned_data