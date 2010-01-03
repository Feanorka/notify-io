import wsgiref.handlers
import hashlib, time, os

from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.api import urlfetch
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import login_required
from django.utils import simplejson

from models import Account, Notification, Channel, Outlet
from app import RequestHandler, DashboardHandler
from config import API_HOST, API_VERSION
import outlet_types

template.register_template_library('app')

class MainHandler(RequestHandler):
    def get(self):
        self.render('templates/main.html', locals())

class GetStartedHandler(RequestHandler):
    def get(self):
        if self.account:
            start_outlet = self.account.get_default_outlet()
        self.render('templates/getstarted.html', locals())
        
class SourcesAvailableHandler(RequestHandler):
    def get(self):
        self.render('templates/sources_available.html', locals())

class SettingsHandler(DashboardHandler):
    @login_required
    def get(self):
        self.render('templates/settings.html', locals())
    
    def post(self):
        if self.request.get('source_enabled', None):
            self.account.source_enabled = True
            self.account.source_name = self.request.get('source_name', None)
            self.account.source_url = self.request.get('source_url', None)
            self.account.source_icon = self.request.get('source_icon', None)
        else:
            self.account.source_enabled = False
        self.account.put()
        self.redirect('/settings')

class HistoryHandler(DashboardHandler):
    @login_required
    def get(self):
        notifications = Notification.get_history_by_target(self.account).fetch(100)
        self.render('templates/history.html', locals())

class SourcesHandler(DashboardHandler):
    @login_required
    def get(self):
        outlets = Outlet.all().filter('target =', self.account)
        if len(self.request.path.split('/')) > 2:
            source = Account.get_by_hash(self.request.path.split('/')[-1])
            channel = Channel.get_by_source_and_target(source, self.account)
            self.render('templates/source.html', locals())
        else:
            enabled_channels = Channel.get_all_by_target(self.account).filter('status =', 'enabled')
            self.render('templates/sources.html', locals())
    
    def post(self):
        action = self.request.get('action')
        source = Account.get_by_hash(self.request.get('source'))
        channel = Channel.get_by_source_and_target(source, self.account)
        if action == 'approve':
            channel.status = 'enabled'
            channel.put()
        elif action == 'disable':
            channel.status = 'disabled'
            # hmm?
        elif action == 'route':
            outlet = Outlet.get_by_hash(self.request.get('outlet'))
            channel.outlet = outlet
            channel.put()
            
        if 'return' in self.request.query_string:
            self.redirect('/sources/%s' % self.request.get('source'))
        else:
            self.redirect('/sources')

class OutletsHandler(DashboardHandler):
    @login_required
    def get(self):
        if self.request.path.endswith('.ListenURL'):
            filename = self.request.path.split('/')[-1]
            outlet = filename.split('.')[0]
            
            self.account.started = True
            self.account.put()

            self.response.headers['Content-Type'] = 'text/plain'
            self.response.headers['Content-disposition'] = 'attachment; filename=%s.ListenURL' % outlet
            self.response.out.write("http://%s/%s/listen/%s\n" % (API_HOST, API_VERSION, outlet))
        else:
            types = outlet_types.all
            outlets = Outlet.all().filter('target =', self.account)
            self.render('templates/outlets.html', locals())
    
    def post(self):
        action = self.request.get('action')
        if action == 'add':
            o = Outlet(target=self.account, type_name=self.request.get('type'))
            o.set_params(self.request.POST)
            o.set_name()
            o.put()
        elif action == 'remove':
            o = Outlet.get_by_hash(self.request.get('outlet'))
            o.delete()
        self.redirect('/outlets')

def main():
    application = webapp.WSGIApplication([
        ('/', MainHandler), 
        ('/getstarted', GetStartedHandler),
        ('/sources/available', SourcesAvailableHandler),
        ('/settings', SettingsHandler),
        ('/history', HistoryHandler),
        ('/sources.*', SourcesHandler),
        ('/outlets.*', OutletsHandler),
        ], debug=True)
    wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
    main()
