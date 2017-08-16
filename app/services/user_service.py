import oauth2 as oauth
import json
import requests
import datetime
from app.models import db
from sqlalchemy.exc import SQLAlchemyError
from oauth2client import client, crypt

from app.models.access_token import AccessToken
from app.models.user import User
from app.models.booth import Booth  # noqa
from app.models.attendee import Attendee  # noqa
from app.models.speaker import Speaker  # noqa
from app.models.client import Client
from app.configs.constants import ROLE  # noqa
from werkzeug.security import generate_password_hash


class UserService:

    def register(self, payloads):

        # payloads validation
        if not isinstance(payloads['role'], int):
            return {
                'error': True,
                'data': 'payload not valid'
            }

        self.model_user = User()
        self.model_user.first_name = payloads['first_name']
        self.model_user.last_name = payloads['last_name']
        self.model_user.email = payloads['email']
        self.model_user.username = payloads['username']
        self.model_user.role_id = payloads['role']
        self.model_user.social_id = payloads['social_id']
        self.model_user.hash_password(payloads['password'])

        db.session.add(self.model_user)

        try:
            db.session.commit()
            data = self.model_user.as_dict()
            return {
                'error': False,
                'data': data
            }
        except SQLAlchemyError as e:
            data = e.orig.args
            return {
                'error': True,
                'data': data
            }

    def get_user(self, username):
        self.model_user = db.session.query(
            User).filter_by(username=username).first()
        return self.model_user

    def social_sign_in(self, provider, social_token, token_secret=''):
        if (provider == 'google'):
            # check token integrity
            try:
                # get client id
                CLIENT_ID = db.session.query(Client).filter_by(app_name=provider).first()
                idinfo = client.verify_id_token(social_token, CLIENT_ID.client_id)
                if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                    raise crypt.AppIdentityError("Wrong issuer.")
            except crypt.AppIdentityError:
                # Invalid token
                return None
            # user id valid, load it.
            userid = idinfo['sub'] 
            return userid

        elif(provider == 'facebook'):
            # check token integrity
            try:
                CLIENT_ID = db.session.query(Client).filter_by(app_name=provider).first()
                facebook_endpoint = 'https://graph.facebook.com/debug_token?input_token=' + social_token + '&access_token=' + CLIENT_ID.client_id + '|' + CLIENT_ID.client_secret
                result = requests.get(facebook_endpoint)
                payload = result.json()
                if(payload['data']['is_valid']):
                    userid = payload['data']['user_id']
                return userid
            except Exception as e:
                return None
        elif(provider == 'twitter'):
            # check token integrity
            try:
                CLIENT_ID = db.session.query(Client).filter_by(app_name=provider).first()                
                consumer = oauth.Consumer(key=CLIENT_ID.client_id, secret=CLIENT_ID.client_secret)
                access_token = oauth.Token(key=social_token, secret=token_secret)

                client = oauth.Client(consumer, access_token)
                account_endpoint = "https://api.twitter.com/1.1/account/verify_credentials.json"
                response, data = client.request(account_endpoint)
                payload = json.loads(data)
                if('id' in payload):
                    userid = payload['id_str']
                else:
                    return None
                # check if error exist in data
            except Exception as e:
                return None
            return userid

    def check_social_account(self, provider, social_id):
        # check if social id exist in user table
        self.model_user = db.session.query(User).filter_by(social_id=social_id).first()
        print(self.model_user.as_dict())
        if self.model_user is not None:
            # user with social_id exist
            # return the user
            return self.model_user
        else:
            return None

    def save_token(self, provider='password_grant'):
        token_exist = db.session.query(AccessToken).filter_by(user_id=self.model_user.id).first()
        if not token_exist:
            self.model_access_token = AccessToken()
            payload = self.model_access_token.init_token(self.model_user.generate_auth_token(), self.model_user.generate_refresh_token(), self.model_user.id)
            db.session.add(payload)
            db.session.commit()
            return {
                'error': False,
                'data': payload
            }
        token_exist.access_token = self.model_user.generate_auth_token()
        token_exist.refresh_token = self.model_user.generate_refresh_token()
        # get id of client app
        client = db.session.query(Client).filter_by(app_name=provider).first()
        token_exist.client_id = client.id

        db.session.commit()
        return{
            'error': True,
            'data': token_exist
        }

    def change_name(self, payloads):
        try:
            self.model_user = db.session.query(User).filter_by(id=payloads['user']['id'])
            self.model_user.update({
                'first_name': payloads['first_name'],
                'last_name': payloads['last_name'],
                'updated_at': datetime.datetime.now()
            })  
            db.session.commit()
            data = self.model_user.first().as_dict()
            return {
                'error': False,
                'data': data
            }
        except SQLAlchemyError as e:
            data = e.orig.args
            return {
                'error': True,
                'data': data
            }

    def change_password(self, payloads):
        user = self.get_user(payloads['user']['username'])
        try:
            if user.verify_password(payloads['old_password']):
                self.model_user = db.session.query(User).filter_by(id=payloads['user']['id'])
                self.model_user.update({
                    'password': generate_password_hash(payloads['new_password']),
                    'updated_at': datetime.datetime.now()
                })
                db.session.commit()
                data = self.model_user.first().as_dict()
                return {
                    'error': False,
                    'data': data
                }
            return {
                'error': True,
                'data': "Invalid password"
            }
        except SQLAlchemyError as e:
            data = e.orig.args
            return {
                'error': True,
                'data': data
            }
