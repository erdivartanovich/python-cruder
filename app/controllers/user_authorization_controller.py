# parent class imports
from app.controllers.base_controller import BaseController
from app.services import userservice


class UserAuthorizationController(BaseController):

	@staticmethod
	def login(request):
		provider = request.json['provider'] if 'provider' in request.json else None
		if provider is not None:
			# social sign in
			social_token = request.json['token'] if 'token' in request.json else None
			if(provider == 'twitter'):
				token_secret = request.json['token_secret'] if 'token_secret' in request.json else None
				user_social_id = userservice.social_sign_in(provider, social_token, token_secret)
			else:
				user_social_id = userservice.social_sign_in(provider, social_token)
			if (user_social_id is not None):
				user = userservice.check_social_account(provider, user_social_id)
				if user is not None:
					token = userservice.save_token(provider)
					return BaseController.send_response_api({'access_token': token['data'].access_token.decode(), 'refresh_token': token['data'].refresh_token}, 'User logged in successfully')
			else:
				return BaseController.send_error_api(None, 'token is invalid'); 
		else:
			username = request.json['username'] if 'username' in request.json else None
			password = request.json['password'] if 'password' in request.json else None
			if username and password:
				# check if user exist
				user = userservice.get_user(username)
				if user is not None:
					if user.verify_password(password):
						token = userservice.save_token()
						return BaseController.send_response_api({'access_token': token['data'].access_token.decode(), 'refresh_token': token['data'].refresh_token}, 'User logged in successfully')
					else:
						return BaseController.send_error_api(None, 'wrong credentials')
				else:
					return BaseController.send_error_api(None, 'username not found')
			return BaseController.send_error_api(None, 'username and password required')

	@staticmethod
	def register(request):
		firstname = request.json['first_name'] if 'first_name' in request.json else None
		lastname = request.json['last_name'] if 'last_name' in request.json else ''
		email = request.json['email'] if 'email' in request.json else None
		username = request.json['username'] if 'username' in request.json else None
		role = request.json['role'] if 'role' in request.json else None
		password = request.json['password'] if 'password' in request.json else None
		social_id = request.json['social_id'] if 'social_id' in request.json else None

		# if social_id = None then normal registration

		if firstname and email and username and role and password:
			payloads = {
				'first_name': firstname,
				'last_name': lastname,
				'email': email,
				'username': username,
				'role': role,
				'password': password,
				'social_id': social_id
			}
		else:
			return BaseController.send_response_api(None, 'payloads not valid')
		result = userservice.register(payloads)
		if not result['error']:
			return BaseController.send_response_api(result['data'], 'user succesfully registered')
		else:
			return BaseController.send_error_api(None, result['data'])