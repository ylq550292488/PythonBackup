import re
import json
import time
# import redis
import base64
import warnings
import pyperclip
import subprocess
import python_socks
from loguru import logger
from appium import webdriver
from telethon import TelegramClient
from random_words import RandomWords
from smsactivate.api import SMSActivateAPI
from telethon.sessions import StringSession
from selenium.common import TimeoutException
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.wait import WebDriverWait
# from utils.config import log_path, api_id, api_hash, account_key, redis_host, redis_port, redis_password
# from utils.tiger_sms import get_tiger_number, get_tiger_sms_code, cancel_tiger_phone

warnings.filterwarnings('ignore')


class telegramXregisterForAppium(object):
    def __init__(self):
        # logger.add(
        #     sink='%s_{time:YYYY_MM_DD}.log' % (log_path / self.__class__.__name__),
        #     encoding='utf8',
        #     format="{time:YYYY-MM-DD HH:mm:ss} | {file} | line:{line} | func:{function} | {level} \n>>>\t{message}\n",
        #     rotation="00:00",
        #     retention="1 days"
        # )
        self.tg_package_name = "org.thunderdog.challegram"
        self.tg_activity_name = "org.thunderdog.challegram.MainActivity"

        self.sms_api = SMSActivateAPI('9c80dc1c9420fbc9A80ddc2cA4f99714')

        # self.redis_client = redis.from_url("redis://{}".format(redis_host), port=redis_port, password=redis_password, encoding='utf-8', decode_responses=True)

        self.phone_redis_key = "tg_spider:register_phone:{}"

        self.rw = RandomWords()

        self.connected_devices = []

    def init_driver(self, package, activated, udid, version, noReset=False):
        """
        初始化
        :return:
        """
        desc = {
            "deviceName": f"{udid}",
            "platformVersion": version,
            "platformName": "Android",
            "appPackage": package,
            "appActivity": activated,
            "udid": udid,
            "unicodeKeyboard": True,
            "resetKeyboard": True,
            "noReset": noReset,
            "autoAcceptAlerts": True,

        }
        driver = webdriver.Remote('127.0.0.1:4723/wd/hub', desc)
        logger.info(f"{udid} :初始化完成")
        return driver

    def production_phone(self):
        """
        获取手机号
        :return:
        """
        "https://sub.paasmi.com/subscribe/280170/B7jWlQRl1fwv"
        while True:
            if self.redis_client.scard(self.phone_redis_key) < 10:
                phone_number_json = self.sms_api.getNumberV2("tg", maxPrice="30", country="12")
                logger.info(phone_number_json)
                phoneNumber = phone_number_json.get('phoneNumber')
                if phoneNumber:
                    self.redis_client.set(self.phone_redis_key.format(phoneNumber), json.dumps(phone_number_json, ensure_ascii=False), nx=True, ex=15 * 60)

    def get_phone(self):
        while True:
            phone_number_json = self.sms_api.getNumberV2("tg", maxPrice="30", country="12")
            logger.info(phone_number_json)
            phoneNumber = phone_number_json.get('phoneNumber')
            if phoneNumber:
                return phone_number_json

    def get_sms_code(self, phone_id):
        """
        获取短信验证码
        :param phone_id:
        :return:
        """
        for _ in range(20):
            sms_code = self.sms_api.getFullSms(phone_id)
            logger.info(sms_code)
            if sms_code != "STATUS_WAIT_CODE":
                return re.search("\d+", sms_code).group()
            time.sleep(6)
        return False

    def cancel_phone(self, phone_id):
        self.sms_api.setStatus(phone_id, status=8)

    def find_element_by_xpath(self, driver, xpath, timeout=3):
        """
        通过 xpath 选择元素
        :param driver:
        :param xpath:
        :param timeout:
        :return:
        """
        try:
            element = WebDriverWait(driver, timeout).until(lambda x: x.find_element(AppiumBy.XPATH, xpath))
            return element
        except (TimeoutException,):
            return False
        except Exception as e:
            logger.warning(xpath + "\n" + str(e))

    def click_ok(self, driver):
        """
        点击 ok 通用方法
        :return:
        """
        ok_xpath = "//*[@text='OK']"
        ok_element = self.find_element_by_xpath(driver, ok_xpath)
        if ok_element:
            ok_element.click()

    def click_permitted(self, driver):
        """
        点击 允许 通用方法
        :return:
        """
        permitted_xpath = "//*[@text='允许']"
        permitted_element = self.find_element_by_xpath(driver, permitted_xpath)
        if permitted_element:
            permitted_element.click()

    def click_done(self, driver):
        """
        点击 确认 通用方法
        :return:
        """
        done_xpath = '//*[@resource-id="org.thunderdog.challegram:id/btn_done"]'
        done_element = self.find_element_by_xpath(driver, done_xpath)
        if done_element:
            done_element.click()

    def click_back(self, driver, number=1):
        """
        点击 确认 通用方法
        :return:
        """
        for _ in range(number):
            driver.keyevent(4)

    def enter_phone_number(self, driver, phone_number):
        """
        输入手机号
        :param driver:
        :param phone_number:  手机号
        :return:
        """
        country_xpath = '//*[@resource-id="org.thunderdog.challegram:id/login_code"]'
        phone_xpath = '//*[@resource-id="org.thunderdog.challegram:id/login_phone"]'
        area_code = phone_number[0:1]
        phone_number = phone_number[1:]
        area_element = self.find_element_by_xpath(driver, country_xpath)
        phone_element = self.find_element_by_xpath(driver, phone_xpath)
        if area_element and phone_element:
            area_element.clear()
            phone_element.clear()
            area_element.send_keys(area_code)
            phone_element.send_keys(phone_number)
            self.click_done(driver)
            return True
        else:
            logger.error("enter_phone_number error")
            return False

    def check_phone_status(self, driver):
        """
        判断手机号状态
        :return:
        """
        detection_number_element = self.find_element_by_xpath(driver, '//*[contains(@text, "Error")]')
        if detection_number_element:
            print(detection_number_element.text)
            return False
        else:
            banned_number_element = self.find_element_by_xpath(driver, '//*[contains(@text, "is banned")]')
            if banned_number_element:
                print(banned_number_element.text)
                return False
            unable_to_send_element = self.find_element_by_xpath(driver, '//*[contains(@text, "Unable to send")]')
            if unable_to_send_element:
                print(unable_to_send_element.text)
                self.click_back(driver, 2)
                return False
            other_device_element = self.find_element_by_xpath(driver, '//*[contains(@text, "other device")]')
            if other_device_element:
                print(other_device_element.text)
                self.click_back(driver)
                return False
            return True

    def enter_sms_code(self, driver, sms_code):
        """
        填入短信验证码
        :param driver:
        :param sms_code:
        :return:
        """
        sms_code_xpath = '//*[@text="Code"]/preceding-sibling::android.widget.EditText'
        sms_code_element = self.find_element_by_xpath(driver, sms_code_xpath)
        if sms_code_element:
            sms_code_element.send_keys(sms_code)

    def fill_information(self, driver):
        """
        填写资料
        :return:
        """
        first_name = self.rw.random_word()
        last_name = self.rw.random_word()

        first_name_element = self.find_element_by_xpath(driver, '//*[@resource-id="org.thunderdog.challegram:id/edit_first_name"]//android.widget.EditText')
        if first_name_element:
            first_name_element.send_keys(first_name)

        last_name_element = self.find_element_by_xpath(driver, '//*[@resource-id="org.thunderdog.challegram:id/edit_last_name"]//android.widget.EditText')
        if last_name_element:
            last_name_element.send_keys(last_name)
        self.click_done(driver)
        self.find_element_by_xpath(driver, '//*[@text="AGREE"]').click()
        self.find_element_by_xpath(driver, '//*[@text="CONTINUE"]').click()
        self.click_permitted(driver)

    def set_2fa(self, driver, password):
        """
        设置二级验证码
        :param driver:
        :param password:
        :return:
        """
        menu_element = self.find_element_by_xpath('//*[@resource-id="org.thunderdog.challegram:id/menu_main"]/preceding-sibling::android.view.View')
        try:
            menu_element.click()
            settings_element = self.find_element_by_xpath(driver, '//*[@resource-id="org.thunderdog.challegram:id/btn_settings"]')
            settings_element.click()
            privacy_settings_element = self.find_element_by_xpath(driver, '//*[@resource-id="org.thunderdog.challegram:id/btn_privacySettings"]')
            privacy_settings_element.click()
            btn_2fa_element = self.find_element_by_xpath(driver, '//*[@resource-id="org.thunderdog.challegram:id/btn_2fa"]')
            btn_2fa_element.click()
            set_element = self.find_element_by_xpath(driver, '//*[@resource-id="org.thunderdog.challegram:id/btn_setPassword"]')
            set_element.click()
            pwd_element = self.find_element_by_xpath(driver, '//*[@resource-id="org.thunderdog.challegram:id/nav_wrapper"]//android.widget.EditText')
            pwd_element.send_keys(password)
            self.click_done(driver)
            set_element = self.find_element_by_xpath(driver, '//*[@resource-id="org.thunderdog.challegram:id/nav_wrapper"]//android.widget.EditText')
            set_element.send_keys(password)
            self.click_done(driver)
            self.click_done(driver)
            forgot_element = self.find_element_by_xpath(driver, '//*[@resource-id="org.thunderdog.challegram:id/btn_forgotPassword"]')
            forgot_element.click()
            self.find_element_by_xpath(driver, '//*[@text="OK"]').click()
            self.click_back(driver, 4)
            logger.info("set_2fa success")
        except (Exception,) as e:
            logger.error(f"set_2fa err {e}")

    def get_app_login_code(self, driver):
        """
        获取 app中的 登录短信
        :return:
        """
        while True:
            # 定位元素
            msg = self.find_element_by_xpath('//*[@resource-id="org.thunderdog.challegram:id/msg_list"]//android.view.View[last()]')
            if msg:
                msg.click()
                driver.tap([(150, 1750)], 500)
                time.sleep(2)
                msg_text = pyperclip.paste()
                login_code_group = re.search("(?<=Login code: ).*?(?=\.)", msg_text)
                if login_code_group:
                    login_code = login_code_group.group()
                    return login_code

    def start_registration(self, udid, version, proxy):
        """
        开始注册
        :return:
        """
        while True:
            driver = self.init_driver(self.tg_package_name, self.tg_activity_name, udid, version)
            # 点击开始
            start_messaging_element = self.find_element_by_xpath(driver, "//*[@text='Start Messaging']")
            if start_messaging_element:
                start_messaging_element.click()
            phone_info = self.get_phone()
            if phone_info is False:
                continue
            phone_number = phone_info["phoneNumber"]
            phone_id = phone_info["activationId"]
            # 输入手机号
            enter_status = self.enter_phone_number(driver, phone_number)
            if enter_status is False:
                continue
            # 检测输入的手机号是否正常
            phone_status = self.check_phone_status(driver)
            if phone_status is False:
                # cancel_tiger_phone(phone_id)
                self.click_ok(driver)
                continue
            sms_code = self.get_sms_code(phone_id)
            if sms_code:
                self.enter_sms_code(driver, sms_code)
                self.fill_information(driver)
                password = phone_number[-6:]
                self.set_2fa(driver, password)
                account_info = {"phone": phone_number, "password": password, "proxy": proxy}
                print(account_info)
                while True:
                    dialog_box = self.find_element_by_xpath(driver, '//*[@resource-id="org.thunderdog.challegram:id/chat"]')
                    if dialog_box:
                        dialog_box.click()
                        break
                    else:
                        self.click_back(driver)
                self.create_string_session(account_info)
            else:
                # cancel_tiger_phone(phone_id)
                continue

    def create_string_session(self, account_info):
        """
        生成 StringSession
        :param account_info:     账号密码信息
        :return:
        """
        phone = account_info['phone']
        password = account_info['password']
        ip = account_info['proxy']
        proxy = (python_socks.ProxyType.HTTP, ip, 2023)
        proxy_dict = {"ip": ip, "port": 2023}
        try:
            client = TelegramClient(f'{phone}.session', api_id=api_id, api_hash=api_hash, proxy=proxy)
            client.start(phone=phone, password=password, code_callback=self.get_app_login_code)
            is_connected = client.is_connected()
            logger.info(f'client是否连接：{is_connected}')
            if is_connected:
                redis_key = account_key.format(phone)
                session = StringSession.save(client.session)
                temp_dict = {"phoneNum": phone, "session": session, "proxy": proxy_dict}
                logger.info(temp_dict)
                self.redis_client.sadd(redis_key, json.dumps(temp_dict))
        except (Exception,) as e:
            logger.error(f"create_string_session err {e}")

    def get_connected_devices(self):
        devices_output = subprocess.check_output(["adb", "devices"]).decode("utf-8").strip("List of devices attached").split("\n")
        for device in devices_output:
            if device is None or device == "":
                pass
            else:
                device_name = device.strip('\tdevice')
                if device_name.endswith("offlin"):
                    continue
                # android_version = subprocess.check_output(["adb", "-s", device_name, "shell", "getprop", "ro.build.version.release"])
                self.connected_devices.append({"udid": device_name, "version": "9"})
        return self.connected_devices

    def set_proxy(self, udid, version, add):
        package = "com.v2ray.ang"
        activated = "com.v2ray.ang.ui.MainActivity"
        device = self.init_driver(package, activated, udid, version)
        settings = self.find_element_by_xpath(device, '//android.widget.Button[@content-desc="添加配置"]')
        if settings:
            settings.click()
        proxy_info = {"add": add, "aid": "234", "alpn": "", "fp": "", "host": "", "id": "af0c2d5b-0c59-475d-8446-b594bd4c21ae", "net": "ws", "path": "", "port": "2030", "ps": f"test_{add}", "scy": "auto", "sni": "", "tls": "", "type": "", "v": "2"}
        proxy_text = "vmess://" + base64.b64encode(json.dumps(proxy_info, ensure_ascii=False).encode()).decode()
        device.set_clipboard_text(proxy_text)
        input = self.find_element_by_xpath(device, '//*[@text="从剪贴板导入"]')
        if input:
            input.click()
        open_em = self.find_element_by_xpath(device, '//*[@resource-id="com.v2ray.ang:id/fab"]')
        if open_em:
            open_em.click()
        determine_em = self.find_element_by_xpath(device, '//*[@text="确定"]')
        if determine_em:
            determine_em.click()

    def start(self):
        self.get_connected_devices()
        ips = ["47.89.133.82"]
        for index, devices in enumerate(self.connected_devices):
            udid = devices["udid"]
            version = devices["version"]
            add = ips[index]
            self.set_proxy(udid, version, add)
            self.start_registration(udid, version, add)


if __name__ == '__main__':
    registration = telegramXregisterForAppium()
    registration.start()
