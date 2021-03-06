#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
import threading
import time
import SocketServer
import BaseHTTPServer
import SimpleHTTPServer
from lib import env
from lib import general
from lib import server
from lib import users
def web_open(name, mode="r", buffering=True, base=env.WEB_DIR):
	return open(name, mode, buffering, base)
SocketServer.open = web_open
SocketServer.file = web_open
BaseHTTPServer.open = web_open
BaseHTTPServer.file = web_open
SimpleHTTPServer.open = web_open
SimpleHTTPServer.file = web_open
#do_GET(...) -> send_head(...) -> open(...) -> copyfile(..., wfile)

def parse_post(string):
	post_dict = {}
	for s in filter(None, string.split("&")):
		i = s.find("=")
		if i == -1: continue
		key = s[:i]
		value = ""
		buf = None
		for j in s[i+1:]:
			if buf != None:
				if len(buf) < 2:
					buf += j
					continue
				else:
					value += buf.decode("hex")
					buf = None
			if j != "%":
				value += j
			else:
				buf = ""
		if buf != None and len(buf) == 2:
			value += buf.decode("hex")
		post_dict[key] = value
	return post_dict

class WebHandle(SimpleHTTPServer.SimpleHTTPRequestHandler):
	def translate_path(self, path):
		if path.find("..") != -1:
			return ""
		path = env.WEB_DIR+"/"+path
		if not os.path.realpath(path).startswith(os.path.realpath(env.WEB_DIR)):
			return ""
		return path
	
	def log_message(self, *args):
		pass
	
	def do_POST(self):
		self.send_response(200)
		self.end_headers()
		post = parse_post(self.rfile.read(int(self.headers["Content-Length"])))
		if self.path.find(env.REG_USER_PAGE_PATH) != -1:
			self.wfile.write(self.reg_user(post))
		elif self.path.find(env.DEL_USER_PAGE_PATH) != -1:
			self.wfile.write(self.del_user(post))
		elif self.path.find(env.MODIFY_PASSWORD_PAGE_PATH) != -1:
			self.wfile.write(self.modify_password(post))
		else:
			self.wfile("page not found.")
	
	def reg_user(self, post):
		user_name = post.get("user_name")
		password = post.get("password")
		password_confirm = post.get("password_confirm")
		delete_password = post.get("delete_password")
		delete_password_confirm = post.get("delete_password_confirm")
		if not user_name:
			return "please input user name"
		elif not password:
			return "please input password"
		elif not password_confirm:
			return "please input password confirm"
		elif not delete_password:
			return "please input delete password"
		elif not delete_password_confirm:
			return "please input delete password confirm"
		elif not user_name.isalnum():
			return "reg error: user name not alphanumeric"
		elif user_name.find("..") != -1:
			return "reg error: user name include .."
		elif len(user_name) > 30:
			return "reg error: user name too long"
		elif password != password_confirm:
			return "reg error: password != password_confirm"
		elif delete_password != delete_password_confirm:
			return "reg error: delete_password != delete_password_confirm"
		if users.make_new_user(user_name, password, delete_password):
			return "reg success"
		else:
			return "reg error: user name used"
	
	def del_user(self, post):
		user_name = post.get("user_name")
		password = post.get("password")
		delete_password = post.get("delete_password")
		if not user_name:
			return "please input user name"
		elif not password:
			return "please input password"
		elif not delete_password:
			return "please input delete password"
		elif not user_name.isalnum():
			return "del error: user name not alphanumeric"
		elif user_name.find("..") != -1:
			return "del error: user name include .."
		elif len(user_name) > 30:
			return "del error: user name too long"
		result = users.delete_user(user_name, password, delete_password)
		if result == 0x01:
			return "del error: user name not exist"
		elif result == 0x02:
			return "del error: password error"
		elif result == 0x00:
			return "del success"
		else:
			return "del error: unknow error"
	
	def modify_password(self, post):
		user_name = post.get("user_name")
		old_password = post.get("old_password")
		old_delete_password = post.get("old_delete_password")
		password = post.get("password")
		password_confirm = post.get("password_confirm")
		delete_password = post.get("delete_password")
		delete_password_confirm = post.get("delete_password_confirm")
		if not user_name:
			return "please input user name"
		elif not old_password:
			return "please input old password"
		elif not old_delete_password:
			return "please input old delete password"
		elif not password:
			return "please input password"
		elif not password_confirm:
			return "please input password confirm"
		elif not delete_password:
			return "please input delete password"
		elif not delete_password_confirm:
			return "please input delete password confirm"
		elif not user_name.isalnum():
			return "modify password error: user name not alphanumeric"
		elif user_name.find("..") != -1:
			return "modify password error: user name include .."
		elif len(user_name) > 30:
			return "modify password error: user name too long"
		elif password != password_confirm:
			return "modify password error: password != password_confirm"
		elif delete_password != delete_password_confirm:
			return "modify password error: delete_password != delete_password_confirm"
		result = users.modify_password(user_name,
			old_password, old_delete_password, password, delete_password)
		if result == 0x01:
			return "modify password error: user name not exist"
		elif result == 0x02:
			return "modify password error: password error"
		elif result == 0x00:
			return "modify password success"
		else:
			return "modify password error: unknow error"

class ThreadingWebServer(SocketServer.ThreadingMixIn,
	BaseHTTPServer.HTTPServer, threading.Thread):
	def __init__(self, *args):
		threading.Thread.__init__(self)
		BaseHTTPServer.HTTPServer.__init__(self, *args)
		self.setDaemon(True)
		self.start()
	def run(self):
		while True:
			self.handle_request()
			time.sleep(0.1)

def load():
	global webserver
	webserver_bind_addr = (env.SERVER_BIND_ADDR, env.WEB_SERVER_PORT)
	general.log("[ web ] start web server with\t%s:%d"%webserver_bind_addr)
	webserver = ThreadingWebServer(webserver_bind_addr, WebHandle)