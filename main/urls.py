from django.contrib import admin
from django.urls import path, include
from .views import *
urlpatterns = [
    # path('', include('main.urls'))
    path('', index, name='index'),
    path('profile/', profile, name='profile'),
    path('profile/<int:id>', profile, name='another_profile'),
    path('profile/edit', profile_edit, name='profile_edit'),
    path('profile/edit/address', profile_edit_address, name="profile_edit_address"),
    path('profile/edit/address/delete', profile_edit_address_delete, name="profile_edit_address_delete"),
    path('profile/edit/address/set', profile_edit_address_set, name="profile_edit_address_set"),
    path('register/', register, name='register'),
    path('login/', login_, name='login'),
    path('logout/', logout_, name='logout'),
    path('event/create', event_create, name='event_create'),
    path('event/<int:id>', view_event, name="event"),
    path('event/<int:id>/cancel', cancel_event, name="cancel_event"),
    path('event/<int:id>/register', event_register, name="event_register"),
    path('event/<int:id>/cancel_register', event_cancel_register, name='event_cancel_register'),
    path('event/<int:id>/org_comment', org_comment, name='org_comment'),
    path('delete_comment/<int:id>', delete_comment, name="delete_comment"),
    path('delete_org_comment/<int:id>', delete_org_comment, name='delete_org_comment'),
    path('search', search, name="search"),
    path('search_user/<str:s>', search_user, name="search_user"),
]
