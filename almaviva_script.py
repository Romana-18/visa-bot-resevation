from asyncio.log import logger
from datetime import datetime
import time
import threading
import requests

import json
import asyncio

from .Document import Document
from playwright import *
from playwright.async_api import async_playwright
from .colors import *
from customtkinter import CTkInputDialog

from .sheet_management import *
import webbrowser
from .utility import rotate_proxy, resource_path
from . import secretvars
from .Countdown import Countdown
import time
import aiohttp
from aiohttp_socks import ProxyConnector
import asyncio
SIGN_IN_URL = 'https://egyiam.almaviva-visa.it/realms/oauth2-visaSystem-realm-pkce/protocol/openid-connect/auth?response_type=code&client_id=aa-visasys-public&state=dDF5U0ZtZ0VVbDFUT2VVMjlOYXd3SWRvLmVyeUpOVy0zYW9zbV8yYnRNdWll&redirect_uri=https%3A%2F%2Fegy.almaviva-visa.it%2F&scope=openid%20profile%20email&code_challenge=DGqFJkz70cuSjv8tiajECZNahV4AhAhPauxkp3Q4rZc&code_challenge_method=S256&nonce=dDF5U0ZtZ0VVbDFUT2VVMjlOYXd3SWRvLmVyeUpOVy0zYW9zbV8yYnRNdWll'
MAIN_PAGE = 'https://egy.almaviva-visa.it/'
capsolver.api_key = 'CAP-C00F3CDADDD84311E2252F31AE7CDD42'
with open(resource_path('open_id_config.json')) as f:
    open_id_config = json.load(f)
with open(resource_path('config.json')) as f:
    config = json.load(f)

class Bot:
    pass
    pass
    pass
    pass
    pass
    def __init__(self, window, applicant, documents, office_id=1, visa_id=3, mode=0, serviceLevel=1, countdown=0):
        self.window = window
        self.applicant = applicant
        self.documents = documents
        self.accounts = []
        self.token = ''
        self.recaptcha = ''
        # self.otp = ''
        self.slots = []
        self.session = requests.Session()
        self.driver = None
        self.main_thread_flag = 1
        self.username = ''
        self.password = ''
        self.visa_id = visa_id
        self.office_id = 1 if office_id == 'Cairo' else 2
        # self.proxy = rotate_proxy()
        self.payment_link = ''
        self.mode = mode
        self.availability = False
        self.serviceLevel = serviceLevel
        self.countdown = countdown
        self.tokens = []
        self.FLAG = 1
        self.threads = []
        self.booked = 0
        self.accepted_accounts = []
        self.target_h = 8
        self.target_min = 59
        self.target_sec = 52
        with open(resource_path('open_id_config.json')) as f:
            self.open_id_config = json.load(f)
        with open(resource_path('config.json')) as f:
            self.config = json.load(f)

    def add_applicant(self, applicant):
        applicant.set_bot(self)
        self.applicant = applicant

    # def get_otp(self):
    #     self.window.print_in_log('جاري الحصول على الكود... OTP', color=warning)
    #     otp = CTkInputDialog(text='Enter OTP', title='OTP')
    #     self.otp = otp.get_input()
    #     return otp

    # def verify_otp(self):
    #     try:
    #         self.window.print_in_log('جاري التحقق من الكود... OTP', color=warning)
    #         api_url = f'https://egyapi.almaviva-visa.it/reservation-manager//api/otp/v1/{self.otp}'
    #         headers = {'Accept': 'application/json, text/plain, */*', 'Authorization': f'Bearer {self.token}', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36', 'Origin': 'https://egy.almaviva-visa.it', 'Referer': 'https://egy.almaviva-visa.it/', 'Sec-Fetch-Dest': 'empty', 'Sec-Fetch-Mode': 'cors', 'Sec-Fetch-Site': 'same-site', 'sec-ch-ua-mobile': '?0', 'sec-ch-ua-platform': 'Windows'}
    #         data = {}
    #         # response = self.session.post(api_url, headers=headers, json=data, proxies=self.proxy)
    #         response = self.session.post(api_url, headers=headers, json=data)

    #         if response.status_code == 200:
    #             self.window.print_in_log('تم التحقق من الكود... OTP', color=success)
    #     except Exception as e:
    #         self.window.print_in_log('يوجد خطأ في التحقق من الكود... OTP')
    #         return None

    # async def get_recaptcha(self):
    #     try:
    #         self.window.print_in_log('جاري التحقق من كابتشا...', color=warning)
    #         response = capsolver.solve({'type': 'ReCaptchaV2TaskProxyLess', 'websiteURL': 'https://egy.almaviva-visa.it/appointment', 'websiteKey': '6LewmsUpAAAAAOJYsdlzBrXXYzKvMwTqzrw-H-qP', 'isInvisible': True})
    #         self.recaptcha = response['gRecaptchaResponse']
    #     except Exception as e:
    #         print(e)
    #         self.window.print_in_log('يوجد خطأ في الكابتشا...', color=danger)

    async def get_recaptcha(self) -> str:
      
        """Open browser for user to solve hCaptcha and return the token using network interception."""
        url = "https://accounts.hcaptcha.com/demo?sitekey=c4c0a5b8-7934-4172-9306-d67c5788aaa8"
        token_holder = {"token": None}
        proxy_address = "pr.oxylabs.io:7777"  # Proxy server and port
        proxy_username = "customer-Cheaser_Jv8mG-cc-IT"  # Proxy username
        proxy_password = "Ftmahm474279+"  # Proxy password

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False, 
            #                                   proxy={
            #     "server": "http://pr.oxylabs.io:7777",
            #     "username": proxy_username,
            #     "password": proxy_password
            # }
            )
            context = await browser.new_context()

            async def handle_response(response):
                if "https://api.hcaptcha.com/checkcaptcha" in response.url and response.request.method == "POST":
                    try:
                        json_data = await response.json()
                        token = json_data.get("generated_pass_UUID")
                        if token:
                            token_holder["token"] = token
                    except Exception as e:
                        logger.error(f"❌ Error parsing response: {e}")

            page = await context.new_page()
            page.on("response", handle_response)

            await page.goto(url)

            # Wait for user to solve captcha and click the buttons
            while not token_holder["token"]:
                try:
                    await page.get_by_role("button", name="Copy P1 token").click(timeout=2000)
                except Exception:
                    pass
                try:
                    await page.get_by_role("button", name="Submit").click(timeout=2000)
                except Exception:
                    pass
                await page.wait_for_timeout(2000)

            await browser.close()
            self.recaptcha 
        return token_holder["token"]

    def write_payment_link(self, payment_link=None, token=None):
        if not payment_link:
            payment_link = self.payment_link
        if not token:
            token = self.token
        user = self.get_user(token)[0] if not self.username else self.username
        webbrowser.open(f'https://eu.gateway.mastercard.com/checkout/pay/{payment_link}?checkoutVersion=1.0.0')
        self.window.print_in_log('رابط بوابة الدفع', color=success)
        self.window.print_in_log(f'https://eu.gateway.mastercard.com/checkout/pay/{payment_link}?checkoutVersion=1.0.0', color=success, url=f'https://eu.gateway.mastercard.com/checkout/pay/{payment_link}?checkoutVersion=1.0.0')
        self.window.print_in_log('تم انتهاء المهمة بنجاح...', color=success)
        threading.Thread(target=payment_gate_link, args=(f'https://eu.gateway.mastercard.com/checkout/pay/{payment_link}?checkoutVersion=1.0.0',)).start()
        with open('payment_link.txt', 'a+') as f:
            f.write(f'https://eu.gateway.mastercard.com/checkout/pay/{payment_link}?checkoutVersion=1.0.0 - {user}\n')

    def login(self):
        self.window.print_in_log('جاري تسجيل الدخول...', color=warning)
        # auth = Authenticator(window=self.window, proxies=self.proxy)
        auth = Authenticator(window=self.window)

        # self.token = auth.login_and_get_token(self.username, self.password)
        self.token = asyncio.run(auth.login_and_get_token(self.username, self.password))

        if not auth.login_permission:
            if len(self.accounts) > 1:
                self.change_account()
            else:  # inserted
                self.window.print_in_log('عذرا يوجد مستخدم واحد فقط لذلك سيتوقف البرنامج', color=danger)
                self.main_thread_flag = 0
                secretvars.MAIN_FLAG = 0

    def check_connection(self):
        try:
            return self.session.get(SIGN_IN_URL).status_code
        except Exception as e:
            return 400 + (None, e)
        else:  # inserted
            pass

    def get_user(self, token):
        return self.accounts[self.tokens.index(token)]

    async def async_get_available_slots(self, session, token):
        try:
            self.window.print_in_log('جاري الحصول علي اماكن للحجز', color=warning)
            api_url = f'https://egyapi.almaviva-visa.it/reservation-manager/api/slots/v1/free?officeId={self.office_id}&quantity=1&date=2024-06-30&type=WEB'
            headers = {'Accept': 'application/json, text/plain, */*', 'Authorization': f'Bearer {token}', 'Accept-Language': 'en', 'Accept-Encoding': 'gzip, deflate, br, zstd', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36', 'Host': 'egyapi.almaviva-visa.it', 'Origin': 'https://egy.almaviva-visa.it', 'Referer': 'https://egy.almaviva-visa.it/', 'Sec-Fetch-Dest': 'empty', 'Sec-Fetch-Mode': 'cors', 'Sec-Fetch-Site': 'same-site', 'sec-ch-ua-mobile': '?0', 'sec-ch-ua-platform': 'Windows'}
            response = await session.get(api_url, headers=headers)
            self.window.print_in_log('تم الحصول علي اماكن للحجز', color=success)
            return await response.json()
        except Exception as e:
            print(e)
            self.window.print_in_log('يوجد خطأ في الحصول علي اماكن للحجز', color=danger)
            return None

    # async def async_send_otp(self, session, token):
    #     try:
    #         self.window.print_in_log('جاري ارسال الكود... OTP', color=warning)
    #         api_url = 'https://egy.almaviva-visa.it/reservation-manager//api/otp/v1'
    #         headers = {'Accept': 'application/json, text/plain, */*', 'Authorization': f'Bearer {token}', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36', 'Origin': 'https://egy.almaviva-visa.it', 'Referer': 'https://egy.almaviva-visa.it/', 'Sec-Fetch-Dest': 'empty', 'Sec-Fetch-Mode': 'cors', 'Sec-Fetch-Site': 'same-site', 'sec-ch-ua-mobile': '?0', 'sec-ch-ua-platform': 'Windows'}
    #         data = {}
    #         response = await session.post(api_url, headers=headers, data=json.dumps(data))
    #     except Exception as e:
    #             self.window.print_in_log('تم ارسال الكود... OTP', color=success)
    #             self.window.print_in_log('يوجد خطأ في الارسال الكود... OTP', color=danger)

    async def async_upload_documents(self, session, token):
        self.window.print_in_log('جاري تحميل المستندات...', color=warning)
        print('جاري تحميل المستندات...')
        for doc in self.documents:
            print(f"docs len is {len(self.documents)} ")
            document = Document(self.documents[doc][1], self.documents[doc][0])
            document.upload_document(token, self.session)
            print(f"Document uploaded with file_name: {document.file_name}")
            self.window.print_in_log('تم تحميل المستندات', color=success)

            self.applicant.add_document(document)
        self.window.print_in_log('تم تحميل المستندات', color=success)

    async def async_get_account_data(self, session, token):
        api_url = 'https://egyiam.almaviva-visa.it/realms/oauth2-visaSystem-realm-pkce/protocol/openid-connect/userinfo'
        headers = {'Accept': 'application/json, text/plain, */*', 'Authorization': f'Bearer {token}', 'Accept-Language': 'en', 'Accept-Encoding': 'gzip, deflate, br, zstd', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36', 'Connection': 'keep-alive', 'Host': 'egyiam.almaviva-visa.it', 'Origin': 'https://egy.almaviva-visa.it', 'Referer': 'https://egy.almaviva-visa.it/', 'Sec-Fetch-Dest': 'empty', 'Sec-Fetch-Mode': 'cors', 'Sec-Fetch-Site': 'same-site'}
        self.window.print_in_log('جاري تحميل بيانات الحساب', color=warning)
        response = await session.get(api_url, headers=headers)
        recieved_data = await response.json()
        data = {'name': recieved_data['given_name'], 'family_name': recieved_data['family_name'], 'email': recieved_data['email'], 'phone': recieved_data['phone_number']}
        self.window.print_in_log('تم تحميل بيانات الحساب', color=success)
        self.applicant.set_new_data(data)
        print(f"Account data received: {data}")


    async def async_book(self, slot, session, token):
        user = self.get_user(token) if not self.username else [self.username, self.password]
        print(f"Booking for user: {user[0]} at slot: {slot}")
        # headers = {'Authorization': f'Bearer {token}', 'Recaptcha': self.recaptcha, 'Accept-Language': 'en', 'Content-Type': 'application/json', 'Accept': 'application/json, text/plain, */*', 'DeviceOperatingSystem': 'web', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'}
        # body = {'officeId': self.office_id, 'tripDate': '2024-06-30', 'tripDestination': 'roma', 'termandcond': True, 'idServiceLevel': self.serviceLevel, 'applicants': [self.applicant.get_applicant_json()], 'slotStartDate': slot, 'source': 'WEB', 'otp': self.otp}


        token2 = await self.get_recaptcha()
        print(f"application: {self.applicant.get_applicant_json()}")
        headers = {'Authorization': f'Bearer {token}',
                    'Recaptcha': token2,
                      'Accept-Language': 'en',
                        'Content-Type': 'application/json',
                          'Accept': 'application/json, text/plain, */*',
                            'DeviceOperatingSystem': 'web', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'}
        
        body = {'officeId': self.office_id, 
                'tripDate': '2025-08-25',
                  'tripDestination': 'milano',
                    'termandcond': True,
                      'idServiceLevel': self.serviceLevel,
                      "privacyPolicy": True,
                        'applicants': [self.applicant.get_applicant_json()],  
                        'slotStartDate': slot, 
                        'source': 'WEB',
                        'family': False,
                        'housekeeper': False
                        
                        
                        }



        URL = 'https://egyapi.almaviva-visa.it/reservation-manager/api/visa-applications/v1/checkout?paymentProvider=MASTERCARD'
        print('test')
        print('=======================================')
        # print(body)
        print('=======================================')


        response = await session.post(URL, headers=headers, data=json.dumps(body))
        self.window.print_in_log('جاري الحجز...', color=warning)

        print(response.status, await response.text())
        if response.status == 201:
            self.booked = 1
            data = await response.json()

            if self.visa_id==3:
                self.window('videop link', color=success)
                vidoLink = f'https://egy.almaviva-visa.it/appointment/videocall?id={data["visaApplicationId"]}'
                self.window.print_in_log(f'رابط الفيديو: {vidoLink}', color=videolinkColor)
                
                


            # threading.Thread(target=start_excution, args=(user[0], user[1])).start()
            # threading.Thread(target=update_login_status, args=('جاري الحجز...',))
            # threading.Thread(target=update_operation_status, args=('تم الحجز بنجاح',)).start()
            self.window.print_in_log('تم الحجز بنجاح', color=success)
            self.payment_link = data['sessionId']
            self.main_thread_flag = 0
            secretvars.MAIN_FLAG == 0
            return data['sessionId']

    async def async_after_confirmation(self, session, token):
        # tasks = [self.async_get_available_slots(session, token), self.async_get_account_data(session, token), self.async_send_otp(session, token), self.async_upload_documents(session, token), self.get_recaptcha()]
        tasks = [self.async_get_available_slots(session, token), self.async_get_account_data(session, token), self.async_upload_documents(session, token)]

        if self.availability and (not self.booked):
            responses = await asyncio.gather(*tasks)
            slots = responses[0]

            if not slots:
                self.window.print_in_log('لم يتم العثور على أماكن متاحة للحجز (slots is None)', color=danger)
                return
            self.applicant.set_bot(self)
            for date in slots:
                if self.booked:
                    return
                payment_link = await self.async_book(slot=date, session=session, token=token)
                if payment_link:
                    self.write_payment_link(payment_link)
                if self.main_thread_flag == 0 or secretvars.MAIN_FLAG == 0:
                    break
        else:  # inserted
            self.window.print_in_log('عذرا لا يوجد مواعيد متاحة للحجز...برجاء المحاولة مرة اخري', color=danger)

    async def async_check_for_availabilty(self, token):
        user = self.get_user(token)[0] if not self.username else self.username
        checking_FLAG = 1
        print(f"Checking for availability for user: {user} at {datetime.now().strftime('%H:%M:%S:%f')}")
        api_url = f'https://egy.almaviva-visa.it/reservation-manager/api/planning/v1/checks?officeId={self.office_id}&visaId={self.visa_id}&serviceLevelId={self.serviceLevel}'
        headers = {'Accept': 'application/json, text/plain, */*', 'Authorization': f'Bearer {token}', 'Accept-Language': 'en', 'Accept-Encoding': 'gzip, deflate, br, zstd', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36', 'Connection': 'keep-alive', 'DeviceOperatingSystem': 'web', 'Host': 'egyapi.almaviva-visa.it', 'Origin': 'https://egy.almaviva-visa.it', 'Referer': 'https://egy.almaviva-visa.it/', 'Sec-Fetch-Dest': 'empty', 'Sec-Fetch-Mode': 'cors', 'Sec-Fetch-Site': 'same-site'}

        
        
        try:
            # connector = ProxyConnector.from_url(rotate_proxy(True))
            async with aiohttp.ClientSession() as session:
                self.countdown = False
                if self.countdown:
                    countdown = Countdown(self.target_h, self.target_min, self.target_sec)
                    await asyncio.sleep(countdown.get_remaining_seconds())

                while self.FLAG and self.main_thread_flag and secretvars.MAIN_FLAG and checking_FLAG:
                    print("Inside while loop")  
                    tasks = [session.get(api_url, headers=headers) for _ in range(1)]
                    responses = await asyncio.gather(*tasks)
                    response = responses[0]
                    if not checking_FLAG:
                        break
                    print(f"{datetime.now().strftime('%H:%M:%S:%f')} - Result of checking is '{(await response.text()).upper()}' Status code: '{response.status}' for user '{user}'")
                    if response.status == 200:
                        if await response.text() == 'true':
                            self.window.print_in_log(f'تم الحصول علي مواعيد للمستخدم ... {user}', color=success)
                            self.availability = True
                            self.FLAG = 0
                            self.accepted_accounts.append(token)
                            if not self.token or self.username:
                                self.token = token
                                await self.async_after_confirmation(session=session, token=token)
                                return
                        else:
                            if not self.mode:
                                return
                            else:
                                await asyncio.sleep(0.1)
                    if response.status == 429:
                        self.window.print_in_log(f'لا يوجد مواعيد للمستخدم حاليا... {user}', color=danger)
                        checking_FLAG = 0
        except Exception as e:
            print(e)
            await self.async_check_for_availabilty(token)

    async def async_login_handler(self, account):
        print(f"Logging in for account: {account[0]} at {datetime.now().strftime('%H:%M:%S:%f')}")
        # connector = ProxyConnector.from_url(rotate_proxy(True))
        async with aiohttp.ClientSession() as session:
            auth = Authenticator(window=self.window, open_id_config=self.open_id_config, config=self.config, session=session)
            token =  auth.login_and_get_token(account[0], account[1])
            if not auth.login_permission:
                self.accounts.remove(account)
                return
            else:  # inserted
                self.tokens.append(token)

    async def login_handler(self):
        tasks = []
        for account in self.accounts:
            tasks.append(asyncio.create_task(self.async_login_handler(account)))
        await asyncio.gather(*tasks)

    async def async_run_tasks(self):
        tasks = []
        try:
            await self.login_handler()
        except Exception as e:
                for token in self.tokens:
                    tasks.append(asyncio.create_task(self.async_check_for_availabilty(token)))
                if self.countdown:
                    countdown = Countdown(self.target_h, self.target_min, self.target_sec)
                    self.window.print_in_log(f'في انتظار الساعة {countdown} للاستعلام عن المواعيد ...', color=warning)
                await asyncio.gather(*tasks)
                print('GOT ERRORED: ', e)
                print(e)

    def start_booking(self):
        try:
            if self.mode:
                asyncio.run(self.async_run_tasks())
            else:  # inserted
                if not self.username or not self.password:
                    self.username = self.accounts[0][0]
                    self.password = self.accounts[0][1]
                asyncio.run(self.async_login_handler([self.username, self.password]))
                if len(self.tokens) > 0:
                    self.token = self.tokens[0]
                    
                    asyncio.run(self.async_check_for_availabilty(self.token))
                if len(self.tokens) == 0:
                    print('No tokens available')
                    self.window.print_in_log('لا يوجد حسابات متاحة للحجز', color=danger)
                    return None
            if self.main_thread_flag == 0 or secretvars.MAIN_FLAG == 0:
                self.window.print_in_log('تم ايقاف البرنامج بنجاح', color=success)
            else:  # inserted
                self.window.print_in_log('تم انهاء البرنامج بنجاح لانتهاء جميع الحسابات من الوظيفة', color=success)
        except Exception as e:
            print(e)
            

            self.window.print_in_log('حدث خطأ في البرنامج جاري اعادة المحاولة', color=danger)
            while True:
                # Add stop condition here
                if not secretvars.MAIN_FLAG or self.main_thread_flag == 0:
                    self.window.print_in_log('تم ايقاف البرنامج من قبل المستخدم', color=warning)
                    return None
                if self.check_connection() == 200:
                    break
                else:
                    self.window.print_in_log('يوجد مشكلة بالموقع حاليا... برجاء الانتظار حتي تتم معالجة المشكلة', color=danger)
                    time.sleep(5)
            # Check stop flag before restarting
            if not secretvars.MAIN_FLAG or self.main_thread_flag == 0:
                self.window.print_in_log('تم ايقاف البرنامج من قبل المستخدم', color=warning)
                return None
            self.start_booking()
            
            self.window.print_in_log('حدث خطأ في البرنامج جاري اعادة المحاولة', color=danger)
            return None
        

