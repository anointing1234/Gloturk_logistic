from django.urls import path,include,re_path
from django.conf import settings
from django.conf.urls.static import static
from . import views
from django.views.static import serve 


urlpatterns = [ 
    path('register/',views.register,name='register'), 
    path('login_Account/',views.login_Account,name='login_Account'), 
    path('logout_view/',views.logout_view,name='logout_view'), 
    path('courier_form/',views.courier_form,name='courier_form'), 
    path('insert-courier/', views.insert_courier, name='insert_courier'),   
    path('track/',views.track_package, name='track_package'),   
    path('transactions/', views.transaction_history, name='transactions'),   
    path('sendmail_view/',views.send_reset_code_view,name='sendmail_view'),
    path('reset_password/',views.reset_password_view, name='reset_password'),    
    path('contact_send/',views.contact_send,name='contact_send'),           
    re_path(r'^media/(?P<path>.*)$', serve,{'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', serve,{'document_root': settings.STATIC_ROOT}),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)



 

