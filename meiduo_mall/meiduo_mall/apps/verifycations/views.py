from django.shortcuts import render
from django.views import View
from meiduo_mall.libs.captcha.captcha import captcha
from django_redis import get_redis_connection
from . import constants
from django.http import JsonResponse, HttpResponse
from meiduo_mall.utils.response_code import RETCODE
import random
import time
from celery_tasks.sms.tasks import send_sms


class ImageCodeView(View):
    def get(self, request, uuid):
        # 接收
        # 验证
        # 处理：
        # 1.生成图片的文本、数据
        text, code, image = captcha.generate_captcha()

        # 2.保存图片文本，用于后续与用户输入值对比
        redis_cli = get_redis_connection('image_code')
        redis_cli.setex(uuid, constants.IMAGE_CODE_EXPIRES, code)

        # 响应：输出图片数据
        return HttpResponse(image, content_type='image/png')


class SmsCodeView(View):
    def get(self, request, mobile):
        # 接收
        uuid = request.GET.get('image_code_id')
        image_code = request.GET.get('image_code')

        # 验证
        # 连接redis
        redis_cli1 = get_redis_connection('sms_code')

        # 0.是否60秒内
        if redis_cli1.get(mobile + '_flag') is not None:
            return JsonResponse({'code': RETCODE.SMSCODERR, 'errmsg': '发送短信太频繁，请稍候再发'})

        # 1.非空
        if not all([uuid, image_code]):
            return JsonResponse({'code': RETCODE.IMAGECODEERR, 'errmsg': '图形验证码已过期，点击图片换一个'})

        # 2.图形验证码是否正确
        # 2.1从redis中读取之前保存的图形验证码文本
        redis_cli = get_redis_connection('image_code')
        image_code_redis = redis_cli.get(uuid)

        # 2.2如果redis中的数据过期则提示
        if image_code_redis is None:
            return JsonResponse({'code': RETCODE.IMAGECODEERR, 'errmsg': '图形验证码已过期，点击图片换一个'})

        # 2.3立即删除redis中图形验证码，表示这个值不能使用第二次
        redis_cli.delete(uuid)

        # 2.3对比图形验证码：不区分大小写
        if image_code_redis.decode().lower() != image_code.lower():
            return JsonResponse({'code': RETCODE.IMAGECODEERR, 'errmsg': '图形验证码错误'})

        # 处理
        # 1.生成随机6位数
        sms_code = '%06d' % random.randint(0, 999999)

        # 2.存入redis
        # redis_cli.setex(mobile, constants.SMS_CODE_EXPIRES, sms_code)
        redis_pl = redis_cli1.pipeline()
        redis_pl.setex(mobile, constants.SMS_CODE_EXPIRES, sms_code)
        redis_pl.setex(mobile + '_flag', constants.SMS_CODE_FLAG, 1)
        redis_pl.execute()
        # redis_cli.setex(mobile, constants.SMS_CODE_EXPIRES, sms_code)
        # redis_cli.setex(mobile + '_flag', constants.SMS_CODE_FLAG, 1)


        # 3.发短信
        # ccp = CCP()
        # ccp.send_template_sms(mobile, [sms_code, constants.SMS_CODE_EXPIRES / 60], 1)
        # print(sms_code)
        # 通过delay调用，可以将任务加到队列中，交给celery去执行
        send_sms.delay(mobile, sms_code)
        # time.sleep(1)
        # print(redis_cli.get(mobile))

        # 响应
        return JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})