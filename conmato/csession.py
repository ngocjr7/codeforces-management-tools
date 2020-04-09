from __future__ import absolute_import
from pyquery import PyQuery as pq
from .parameters import *
from .utils import *
import requests
import pandas as pd
import re, os
import datetime

class CSession(requests.Session):
	"""
		is_manager: check if use is manger of codeforces group
		get_csrf_token: get csrf_token

	"""
	csrf_token=None

	def get_csrf_token(self):
		return self.csrf_token

	def get(self, URL):
		response = super().get(URL)
		if response.url == 'http://codeforces.com/' or response.url == 'https://codeforces.com/':
			logger.error("get: Codeforces rejected request,\n\
				It could be due to too many requests or you don't have permission to request.\n\
				You should be slower or check your permission again")
		return response

	def get_logged_username(self):
		"""
			Return username if it's logged, otherwise, return None
		"""
		response = self.get(CODEFORCES_URI)
		doc = pq(response.text)
		username = doc('div').filter('.lang-chooser').children().eq(1).children().eq(0).text()
		if username == 'Enter':
			return None
		else:
			return username

	def login(self, username='', password=''):
		'''
			usage: 	You should only log in once for a session
					ss = CSession.Session()
					ss.login(username, password)
			return: 
				"Please provide username and password before using."
				'Login failed, wrong username or password'
				'Login failed while logger in by defalut user'
				"Login successfully"
		'''
		if username == '' or password == '':
			logger.warning("login:Please provide username and password before using.")
			return

		payload = {
			"handleOrEmail": username,
			"password": password,
			"csrf_token": "",
			"bfaa": '1ef059a32710a29f84fbde5b5500d49c',
			"action": 'enter',
			"ftaa": 'uf8qxh8b5vphq6wna4',
			"remember": 'on',
			"_tta": 569
		}
		self.cookies.clear()

		response = self.get(LOGIN_URL)
		doc = pq(response.text)
		payload['csrf_token'] = doc('input').attr('value')
		payload['handleOrEmail'] = username
		payload['password'] = password
		self.csrf_token = payload['csrf_token']

		response = self.post(
			LOGIN_URL, 
			data = payload, 
			headers = dict(referer=LOGIN_URL)
		)

		doc = pq(response.text)
		username_again = doc('div').filter('.lang-chooser').children().eq(1).children().eq(0).text()
		if username_again == 'Enter' or username_again.lower() != username.lower():
			logger.warning('login:Login failed while logging in')

		# logger.info("login:Login successfully")