# based on  http://nyquistrate.com/django/facebook-connect/
from django.conf                import settings
from django.contrib.auth        import authenticate, login, logout
from django.contrib.auth.models import User
from django.utils               import simplejson
from gazjango.accounts.models   import UserProfile, UserKind
from gazjango.misc.view_helpers import get_ip

import md5
import urllib, urllib2
import time
import datetime

API_KEY = settings.FACEBOOK_LOGIN_API_KEY
API_SECRET = settings.FACEBOOK_LOGIN_SECRET
REST_SERVER = 'http://api.facebook.com/restserver.php'

PROBLEM_ERROR = 'There was a problem. Try again later.'
ACCOUNT_DISABLED_ERROR = 'Your account is not active.'
ACCOUNT_PROBLEM_ERROR = 'There is a problem with your account.'

class FacebookConnectMiddleware(object):
    delete_fb_cookies = False
    facebook_user_is_authenticated = False
    
    def logout(self, request):
        logout(request)
        self.delete_fb_cookies = True
        return None
    
    def hash(self, thing):
        return md5.new(thing + settings.SECRET_KEY).hexdigest()
    
    def cookie(self, request, key):
        return request.COOKIES[API_KEY + key]
    
    # Generates signatures for FB requests/cookies
    def get_facebook_signature(self, values_dict, is_cookie_check=False):
        signature_keys = []
        for key in sorted(values_dict.keys()):
            if is_cookie_check and key.startswith(API_KEY + '_'):
                signature_keys.append(key)
            elif is_cookie_check is False:
                signature_keys.append(key)
        
        if is_cookie_check:
            signature_string = ''.join('%s=%s' % (x.replace(API_KEY + '_',''), values_dict[x])
                                       for x in signature_keys)
        else:
            signature_string = ''.join('%s=%s' % (x, values_dict[x]) for x in signature_keys)
        
        return md5.new(signature_string + API_SECRET).hexdigest()
    
    def process_request(self, request):
        try:
            # Set the facebook message to empty. This message can be used to
            # display info from the middleware on a Web page.
            request.facebook_message = None
            
            if request.user.is_authenticated():
                if API_KEY in request.COOKIES: # using FB Connect
                    # check for presence and correctness of ip cookie
                    real_ip = get_ip(request)
                    if request.COOKIES.get('fb_ip', None) != self.hash(real_ip + API_SECRET):
                        return self.logout(request)
                
            else: # not logged in
                if API_KEY in request.COOKIES: # using FB Connect
                    
                    # check the hash of the cookie values, to prevent forgery
                    signature_hash = self.get_facebook_signature(request.COOKIES, True)
                    if signature_hash != request.COOKIES[API_KEY]:
                        return self.logout(request)
                    
                    # check expiry
                    expiry_key = float(self.cookie(request, '_expires'))
                    if (datetime.datetime.fromtimestamp(expiry) <= datetime.datetime.now()):
                        return self.logout(request)
                    
                    try: # check whether an account exists
                        User.objects.get(username=self.cookie(request, '_user'))
                    except User.DoesNotExist:
                        # make the user
                        user_info_params = {
                            'method': 'Users.getInfo',
                            'api_key': API_KEY,
                            'call_id': time.time(),
                            'v': '1.0',
                            'uids': self.cookie(request, '_user'),
                            'fields': 'first_name,last_name,affiliations',
                            'format': 'json',
                        }
                        user_info_params['sig'] = self.get_facebook_signature(user_info_params)
                        user_info_params = urllib.urlencode(user_info_params)
                        user_info_r = simplejson.load(urllib2.urlopen(REST_SERVER, user_info_params))
                        user_info = user_info_r[0]
                        
                        user = User.objects.create_user(self.cookie(request, '_user'),
                                                        '',
                                                        self.hash(self.cookie(request, '_user')))
                        user_profile = user.userprofile_set.create()
                        
                        user.first_name = user_info['first_name']
                        user.last_name = user_info['last_name']
                        
                        if user_info['affiliations']:
                            for affiliation in user_info['affiliations']:
                                if affiliation['name'] == 'Swarthmore':
                                    user_profile.from_swat = True
                                    user_profile.kind, created = UserKind.objects.get_or_create(
                                        kind='s' if affiliation['status'] == 'Undergrad' else 'a',
                                        year=affiliation['year']
                                    )
                        
                        user.save()
                        user_profile.save()
                    
                    # now the account definitely exists: log in to it
                    user = authenticate(username=self.cookie(request, '_user'),
                                        password=self.hash(self.cookie(request, '_user')))
                    if user is None:
                        request.facebook_message = ACCOUNT_PROBLEM_ERROR
                        self.delete_fb_cookies = True
                    else:
                        if user.is_active:
                            login(request, user)
                            self.facebook_user_is_authenticated = True
                        else:
                            request.facebook_message = ACCOUNT_DISABLED_ERROR
                            self.delete_fb_cookies = True
        
        # something went wrong. make sure user doesn't have site access until problem is fixed.
        except:
            request.facebook_message = PROBLEM_ERROR
            logout(request)
            self.delete_fb_cookies = True
    
    def process_response(self, request, response):
        # delete FB Connect cookies -- the js might add them again, but
        # we want them gone if not
        if self.delete_fb_cookies is True:
            response.delete_cookie(API_KEY + '_user')
            response.delete_cookie(API_KEY + '_session_key')
            response.delete_cookie(API_KEY + '_expires')
            response.delete_cookie(API_KEY + '_ss')
            response.delete_cookie(API_KEY)
            response.delete_cookie('fbsetting_' + API_KEY)
        
        self.delete_fb_cookies = False
        
        if self.facebook_user_is_authenticated is True:
            real_ip = get_ip(request)
            response.set_cookie('fb_ip', self.hash(real_ip + API_SECRET))
        
        return response
    
