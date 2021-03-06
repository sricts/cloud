import requests
import json
import datetime

from django.conf import settings

import keystoneclient.v2_0.client as ksclient
from muranoclient.v1 import client as v1_client    
from muranoclient.v1 import shell as v1_shell

from oslo_log import log as logging
LOG = logging.getLogger(__name__)



ip = settings.MURANO_CONNECT['ip']
tenantname = settings.MURANO_CONNECT['tenantname']
username = settings.MURANO_CONNECT['username']
password = settings.MURANO_CONNECT['password']
admin_token = settings.MURANO_CONNECT['admin_token']
env_name_prefix = settings.MURANO_CONNECT['env_name_prefix']
endpoint = "http://"+ip+":8082/"
key_name = settings.MURANO_KEY_PAIR_NAME

'''
    Create auth_token
'''
def get_auth_token():   
    
    '''
    #Using REST API
    data = {"auth": {"tenantName": tenantname, "passwordCredentials": {"username": username, "password": password}}}
    headers = {'Content-type': 'application/json','Accept':'application/json'}
    data_json = json.dumps(data)
    response = requests.post('http://'+ ip +':5000/v2.0/tokens', data=data_json, headers=headers)   
    response = response.json()
    auth_token = response["access"]["token"]["id"]    
    return auth_token
    '''    
    #Using Keystone
    keystone = ksclient.Client(auth_url="http://"+ip+":35357/v2.0",
                           username=username,
                           password=password,
                           tenant_name=tenantname)
    
    return keystone.auth_token

'''    
    Create  environment

'''
def create_environment():
    
    auth_token = get_auth_token()
        
    utc_datetime = datetime.datetime.utcnow()
    formated_string = utc_datetime.strftime("%Y-%m-%d-%H%M%SZ") 
    headers = {'Content-type': 'application/json','Accept':'application/json','X-Auth-Token': auth_token}
    payload = { 'name': env_name_prefix+str(formated_string)}    
    resp_env = requests.post('http://'+ip+':8082/v1/environments',data=json.dumps(payload),headers=headers)    
    resp_env = resp_env.json()     
    #environment Id 
    #env_id = resp_env["id"]     
    return resp_env


def import_application_package(repo_url,package_name):
    
    try:
        auth_token = get_auth_token()
        #initializing MuranoClient
        mc = v1_client.Client(endpoint=endpoint, token= auth_token,timeout = 600)
        #mc.environments.list()
        #mc.environments.get(environment_id='b93d63bde2b3423cb1f8d5e54aeb99a3')
        
        args = InitArgs()    
        ###filename is URL###
        #args.filename = {"http://storage.apps.openstack.org/apps/io.murano.apps.apache.ApacheHttpServer.zip"}
        args.murano_repo_url = ''
        
        ###filename is name and repo_url###
        #args.filename = {"io.murano.apps.apache.ApacheHttpServer"}
        #args.murano_repo_url = 'http://storage.apps.openstack.org/'    
        args.filename = {package_name}
        args.murano_repo_url = repo_url
        
        ###filename is localpath###
        #args.filename = {"C:/Users/admin/Downloads/io.murano.apps.apache.ApacheHttpServer.zip"}
        #args.murano_repo_url = ''    
        args.categories = None
        args.is_public = False
        args.package_version = ''    
        args.exists_action = 's' #(s)kip, (u)pdate, (a)bort    
        
        
        response = v1_shell.do_package_import(mc, args)
        
        '''
            Check whether the package imported properly
        '''        
        
        package_generator = mc.packages.filter(fqn = package_name)
        #pp = mc.packages.list()
        package_obj =  package_generator.next()        
        package_info = package_obj.__dict__
        print package_info
        #print package_info['id']
        #print package_info['class_definitions']['id']
        
        if package_info['id']: 
            return {'status': 'success', 'msg': 'Package imported successfully','response':package_info}       
        else:
            return {'status': 'failed', 'msg': 'Error occurred,while importing the package'}
        
    except Exception as e:
        LOG.error("Error  occurred,"
                          " while importing the package".format(e))
        return {'status': 'failed', 'msg': 'Error Occurred,while importing the package'}
        #raise   
    
    return {'status': 'success', 'msg': 'Package imported successfully'}

   
  
'''
Create a configuration session  
'''
def create_session(env_id):
    
    auth_token = get_auth_token()
    headers = {'Content-type': 'application/json','Accept':'application/json','X-Auth-Token': auth_token}      
    resp_config = requests.post('http://'+ip+':8082/v1/environments/'+env_id+'/configure',headers=headers)    
    resp_config = resp_config.json()   
    #environment Id 
    #session_id = resp_config["id"]     
    return resp_config

'''
    Add applications to an environment
'''

def add_application(env_id,session_id,app_info):
    
    auth_token = get_auth_token() 
    
    utc_datetime = datetime.datetime.utcnow()
    formated_string = utc_datetime.strftime("%Y-%m-%d-%H%M%SZ")    
   
    #securityGroupName
    #"securityGroupName" :"test_grp",
    #"availabilityZone": "nova",
    
    instance_json = {
      "instance": {
        "flavor": "m1.small",
        "keyname": key_name,        
        "assignFloatingIp": "true",   
        "availabilityZone": "nova",    
        "image": "ubuntu14.04-x64-docker",
        "?": {
          "type": "io.murano.resources.LinuxMuranoInstance",
          "id": generate_uuid()
        },
        "name": "inst_"+str(formated_string)
      },
      "name": str(app_info['response']['name']),
      "?": {        
        "type": str(app_info['response']['fully_qualified_name']),
        "id": str(app_info['response']['id'])
      }
      
    } 
    
    #print instance_json
    headers = {'Content-type': 'application/json','Accept':'application/json','X-Auth-Token': auth_token,'X-Configuration-Session':session_id}
    resp_app = requests.post('http://'+ip+':8082/v1/environments/'+env_id+'/services',data=json.dumps(instance_json),headers=headers)
    
    #resp_app = resp_app.json()     
    #print resp_app    
    return resp_app.__dict__

'''
  Depoly session

'''
def deploy_session(env_id,session_id):
    
    auth_token = get_auth_token()
    
    #headers = {'Content-type': 'application/json','Accept':'application/json','X-Auth-Token': auth_token,'X-Configuration-Session':session_id}
    headers = {'Content-type': 'application/json','Accept':'application/json','X-Auth-Token': auth_token}
    resp_deploy = requests.post('http://'+ip+':8082/v1/environments/'+env_id+'/sessions/'+session_id+'/deploy',headers=headers)    
    #print resp_deploy
    #resp_deploy = resp_deploy.json()  
    #print resp_deploy.__dict__  
    
        
    '''
    #initializing MuranoClient
    mc = v1_client.Client(endpoint=endpoint, token= auth_token,timeout = 6000)
   
    args = InitArgs()    
    
    args.id = env_id
    args.session_id = session_id    
    response = v1_shell.do_environment_deploy(mc, args)
    
    print resp_deploy
    print resp_deploy.__dict__
    '''
      
    return resp_deploy.__dict__



def get_deployment_status(env_id):
    
    # ='1a5cb9ba73a94c95af20bd2f4d5d6c9a'
    auth_token = get_auth_token()
    headers = {'Content-type': 'application/json', 'Accept': 'application/json', 'X-Auth-Token': auth_token}
    resp_deploy = requests.get('http://' + ip + ':8082/v1/environments/' + env_id , headers=headers)
    #print resp_config
    resp_deploy = resp_deploy.json()
    
    #print resp_deploy
    
    if(resp_deploy['status']):
        return resp_deploy
    else:
        return False
    
    
'''
 Fetch session details
'''

def get_session_deatils(env_id,session_id):
    
    try:
        auth_token = get_auth_token()
        #print env_id
        #print session_id
        
        headers = {'Content-type': 'application/json','Accept':'application/json','X-Auth-Token': auth_token}
        resp_sess = requests.get('http://'+ip+':8082/v1/environments/'+env_id+'/sessions/'+session_id,headers=headers)    
        print resp_sess
        print resp_sess.__dict__['status_code']
        if(resp_sess.__dict__['status_code'] == 200):
            return resp_sess.json() 
        else:
            return False
    except Exception as e:
        return False 





def list_deployments(env_id):    
    
    auth_token = get_auth_token()
    headers = {'Content-type': 'application/json','Accept':'application/json','X-Auth-Token': auth_token}
    resp_dep = requests.get('http://'+ip+':8082/v1/environments/'+env_id+'/deployments/',headers=headers)  
    print resp_dep
    print resp_dep.__dict__

'''
 Test function
 
'''
def check_test_ok(env_id):
    
    auth_token = get_auth_token()
    headers = {'Content-type': 'application/json','Accept':'application/json','X-Auth-Token': auth_token}
    
    app_id = ""
    
    #resp_app = requests.get('http://'+ip+':8082/v1//environments/'+env_id+'/services/'+app_id,headers=headers)  
    
    #resp_app = requests.get('http://'+ip+':8082/v1/images/detail',headers=headers)    
    #print
    
    #resp_app = resp_app.json()  
    
    #v1/images/detail
    
    #from muranoclient.glance import client as gl_client
    
    #gl_client.Client(endpoint=endpoint, type_name ="" , type_version="")
    
    #auth_token = get_auth_token()
        #initializing MuranoClient
    #mc = v1_client.Client(endpoint=endpoint, token= auth_token,timeout = 60)
        #mc.environmen
    
    #print resp_app.__dict__
    
    keystone = ksclient.Client(auth_url="http://"+ip+":35357/v2.0",
                           username=username,
                           password=password,
                           tenant_name=tenantname)
    
    import glanceclient.v2.client as glclient
    
    glance_endpoint = keystone.service_catalog.url_for(service_type='image',endpoint_type='publicURL')
    
    print glance_endpoint
    
    glance = glclient.Client(endpoint, token=keystone.auth_token)
    
    images = glance.images.list()
    
    print images.next()   
    #return keystone.auth_token    
    
    
    return images   


def generate_uuid():
    import uuid
    """Generate uuid for objects."""
    return uuid.uuid4().hex
    
    
class InitArgs(object):
    pass
    
    


