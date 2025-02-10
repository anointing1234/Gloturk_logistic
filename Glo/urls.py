from django.urls import path,include,re_path
from django.conf import settings
from django.conf.urls.static import static
from . import views
from django.views.static import serve 
from django.conf.urls import handler404, handler500



urlpatterns = [
    path('',views.home_view,name='home_view'),
    path('home_view',views.home_view,name='home_view'),
    path('login_view/',views.login_view,name='login_view'),
    path('track_view/',views.track_view,name='track_view'),
    path('parkage_delivery/',views.parkage_delivery,name='parkage_delivery'),
    path('contact_view/',views.contact_view,name='contact_view'),
    path('signup_view/',views.signup_view,name='signup_view'),
    path('forgot_pass/',views.send_pass,name='forgot_pass'),
    path('profile/',views.profile,name='profile'),
    re_path(r'^media/(?P<path>.*)$', serve,{'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', serve,{'document_root': settings.STATIC_ROOT}),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)



# handler404 = views.custom_404_view
# handler500 = views.custom_500_view
 
 

