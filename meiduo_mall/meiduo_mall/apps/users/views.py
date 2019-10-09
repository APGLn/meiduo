from django.shortcuts import render, redirect
from django.views import View
from django.http import HttpResponseForbidden, JsonResponse
import re
from .models import User
from django.contrib.auth import login
from meiduo_mall.utils.response_code import RETCODE
from django_redis import get_redis_connection


# Create your views here.

class RegisterView(View):
    def get(self, request):
        return render(request, 'register.html')

    def post(self, request):
        # 接收
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        password2 = request.POST.get('cpwd')
        mobile = request.POST.get('phone')
        sms_code = request.POST.get('msg_code')
        allow = request.POST.get('allow')

        #  验证
        if not all([username, password, password2, mobile, sms_code, allow]):
            return HttpResponseForbidden('填写数据不完整')

        if not re.match('^[a-zA-Z0-9_-]{5,20}$', username):
            return HttpResponseForbidden('用户名为5到20个字符')

        if User.objects.filter(username=username).count()>0:
            return HttpResponseForbidden('用户名已经存在')

        if not re.match('^[0-9A-Za-z]{8,20}$', password):
            return HttpResponseForbidden('密码为8-20位')

        if password!=password2:
            return HttpResponseForbidden('密码不一致')

        if not re.match('^1[3456789]\d{9}$', mobile):
            return HttpResponseForbidden('手机格式错误')

        if User.objects.filter(mobile=mobile).count() > 0:
            return HttpResponseForbidden('手机号存在')

        #  2.短信验证
        # 1.读取redis中的短信验证码
        redis_cli = get_redis_connection('sms_code')
        sms_code_redis = redis_cli.get(mobile)
        # 2.判断是否过期
        if sms_code_redis is None:
            print(sms_code_redis)
            return HttpResponseForbidden('短信验证码已经过期')
        # 3.删除短信验证码，不可以使用第二次
        redis_cli.delete(mobile)
        redis_cli.delete(mobile + '_flag')
        # 4.判断是否正确
        if sms_code_redis.decode() != sms_code:
            return HttpResponseForbidden('短信验证码错误')


        #  处理
        # 1.创建用户对象
        user = User.objects.create_user(
            username=username,
            password=password,
            mobile=mobile
        )
        # 2.状态保持
        login(request, user)

        # 响应
        return redirect('/')


class UsernameCountView(View):
    def get(self, request, username):
        # 接收：通过路由在路径中提取
        # 验证：路由的正则表达式
        # 处理：判断用户名是否存在
        count = User.objects.filter(username=username).count()
        # 响应：提示是否存在
        return JsonResponse({
            'count': count,
            'code': RETCODE.OK,
            'errmsg': 'OK'
        })


class MobileCountView(View):
    def get(self, request, mobile):
        # 接收
        # 验证
        # 处理：判断手机号是否存在
        count = User.objects.filter(mobile=mobile).count()
        # 响应：提示是否存在
        return JsonResponse({
            'count': count,
            'code': RETCODE.OK,
            'errmsg': "OK"
        })