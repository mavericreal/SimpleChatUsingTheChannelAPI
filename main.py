#!/usr/bin/env python
"""
	The Chat Handlers
	
	Copyright 2010 Netgamix LLC
	License: http://netgamix.com/information/terms/
	
"""
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template
from google.appengine.api import channel
from django.utils import simplejson as json
from google.appengine.ext import db
from util.sessions import Session
import os,datetime,random,logging

class User(db.Model):
	nick=db.StringProperty(default="")
	channel_id=db.StringProperty(default="")
	
class Message(db.Model):
	text=db.StringProperty(default="")
	user=db.ReferenceProperty(User)
	
	
class MainHandler(webapp.RequestHandler):
	def get(self):
		self.session = Session()
		error = self.session['error'] if 'error' in self.session else ""
		template_vars={'error':error}
		temp = os.path.join(os.path.dirname(__file__),'templates/main.html')
		outstr = template.render(temp, template_vars)
		self.response.out.write(outstr)
		
class ChatHandler(webapp.RequestHandler):
	def get(self):
		self.redirect('/')
		
	def post(self):
		# Some session from http://gaeutilities.appspot.com/
		self.session = Session()
		# obtain the nick
		nick = self.request.get('nick')
		if not nick:
			self.redirect('/')
		# check if a user with that nick already exists
		user = User.all().filter('nick =', nick).get()
		if user:
			self.session['error']='That nickname is taken'
			self.redirect('/')
			return
		# generate a unique id for the channel api
		channel_id=str(random.randint(1,10000))+str(datetime.datetime.now())
		chat_token = channel.create_channel(channel_id)
		# save the user
		user = User(nick=nick,channel_id=channel_id)
		user.put()
		# obtain all the messages
		messages=Message.all().fetch(1000)
		# generate the template and answer back to the user
		template_vars={'nick':nick,'messages':messages,'channel_id':channel_id,'chat_token':chat_token}
		temp = os.path.join(os.path.dirname(__file__),'templates/chat.html')
		outstr = template.render(temp, template_vars)
		self.response.out.write(outstr)
		
		
class NewMessageHandler(webapp.RequestHandler):
	
	def post(self):
		# Get the parameters
		nick = self.request.get('nick')
		text = self.request.get('text')
		channel_id = self.request.get('channel_id')
		# Save the message sent by the user
		user = User.all().filter('nick =',nick).get()
		message=Message(user=user,text=text)
		message.put()
		# Generate the template with the message
		messages=[message]
		template_vars={'messages':messages}
		temp = os.path.join(os.path.dirname(__file__),'templates/messages.html')
		outstr = template.render(temp, template_vars)
		# Send the message to all the connected users
		users = User.all().fetch(1000)
		for user in users:
			if user.nick != nick:
				channel_msg = json.dumps({'success':True,"html":outstr})
				channel.send_message(user.channel_id, channel_msg)
		# Reply to the user request
		self.response.out.write(outstr)
		
def main():
	application = webapp.WSGIApplication([
		('/chat/', ChatHandler),
		('/newMessage/',NewMessageHandler),
		('/', MainHandler)
		],debug=True)
	util.run_wsgi_app(application)


if __name__ == '__main__':
	main()
