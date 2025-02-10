from django.shortcuts import render
import requests
import logging
import json
import os
import time
from urllib.parse import urljoin
from requests.exceptions import RequestException
from django.contrib.auth import logout
from bs4 import BeautifulSoup
import random
from accounts.forms import RegisterForm,CourierForm,SendresetcodeForm
# from accounts.models import
from django.core.paginator import Paginator


def home_view(request):
   return render(request,'index.html',)


def login_view(request):
    form = RegisterForm()
    return render(request,'forms/login.html',{'form':form})


def signup_view(request):
    form = RegisterForm()
    return render(request, 'forms/signup.html', {'form': form})


def contact_view(request):
    return render(request,'contact.html')   


def track_view(request):
    return render(request,'track_item.html')  

def parkage_delivery(request):
    form = CourierForm()
    return render(request,'parkage_delivery.html',{'form':form})  


def send_pass(request):
    form = SendresetcodeForm()
    return render(request,'forms/send_pass.html',{'form':form})


def profile(request):
    return render(request,'profile.html')