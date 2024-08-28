from dataclasses import dataclass
import dill
import json
import numpy as np
from pydantic import BaseModel
import requests

@dataclass
class Argument:
    name: str
    version: int
    lb: tuple[int, ...]
    ub: tuple[int, ...]
    namespace:str = None

class RegistryHandle(BaseModel):
    namespace: str
    parameters: dict

def _bounds_to_box(lb, ub):
    if len(lb) != len(ub):
        raise TypeError('lb and ub must have same dimensionality.')
    box = {}
    box['bounds'] = [{'start': l, 'span': (u-l)+1} for l,u in zip(lb,ub)]
    for dim in box['bounds']:
        if dim['span'] < 0:
            raise TypeError('ub must be greater than lb in all dimensions.')
    return(box)

def _shape_to_box(shape: tuple[int, ...], offset: tuple[int, ...]):
    if len(shape) != len(offset):
        raise TypeError('shape and offset must have same dimensionality')
    box = {}
    box['bounds'] = []
    for s, o in zip(shape, offset):
        if s < 0:
            raise TypeError('offset must not be negative.')
        box['bounds'].append({'start': o, 'span':s})
    return(box)

class DXSpacesClient:
    def __init__(self, socket, debug = False):
        self.socket = socket
        self.debug = debug

    def _req_url(self, url):
        return(f'{self.socket}/{url}')

    def _do_method(self, method, url, debug_str = None, **kwargs):
        req_url = self._req_url(url)
        if self.debug:
           print(f"{debug_str} {req_url}")
        response = method(req_url, **kwargs)
        if response.status_code == 404:
            return None
        if not response.ok:
            content = json.loads(response.content)
            err_msg = content['detail']
            raise RuntimeError(f'request to server failed with {response.status_code}: {err_msg}.')
        return(response)

    def _put(self, url, **kwargs):
        return(self._do_method(requests.put, url, "PUT", **kwargs))

    def _post(self, url, **kwargs):
        return(self._do_method(requests.post, url, "POST", **kwargs))

    def _get(self, url):
        return(self._do_method(requests.get, url))

    def _get_body(self, url):
        response = self._get(url)
        return(json.loads(response.content))

    def GetNDArray(self, name, version, lb, ub, nspace = None):
        box = _bounds_to_box(lb, ub)
        url = f'dspaces/obj/{name}/{version}/'
        if nspace:
            url = url + f'?namespace={nspace}'
        print(box)
        response = self._post(url, json=box)
        if response is None:
            if self.debug:
                print("could not find requested object in DXSpacesClient.GetNDArray()")
            return None
        dims = tuple([int(x) for x in response.headers['x-ds-dims'].split(',')])
        tag = int(response.headers['x-ds-tag'])
        dtype = np.sctypeDict[tag]
        arr = np.ndarray(dims, dtype=dtype, buffer=response.content)
        return(arr)

    def PutNDArray(self, arr, name, version, offset, nspace = None):
        box = _shape_to_box(arr.shape, offset)
        data = {'box': json.dumps(box)}
        files = {'data': arr.tobytes()}
        url = f'dspaces/obj/{name}/{version}?element_size={arr.itemsize}&element_type={arr.dtype.num}'
        if nspace:
            url = url + f'&namespace={nspace}'
        response = self._put(url, data=data, files=files)
        if response is None:
            raise RuntimeError(f'put request failed due to internal fault.')

    def Exec(self, args, fn):
        objs = []
        for obj in args:
            box = _bounds_to_box(obj.lb, obj.ub)
            objs.append({
                'name': obj.name,
                'version': obj.version,
                'bounds': box['bounds']})
            if obj.namespace:
                objs[-1]['namespace'] = obj.namespace
        data = {'requests': json.dumps({'requests': objs})}
        files = {'fn': dill.dumps(fn)}
        url = f'dspaces/exec/'
        response = self._post(url, data=data, files=files)
        if response is None:
            raise RuntimeError(f'put request failed due to internal fault.')
        return(dill.loads(response.content))

    def GetVars(self):
        return(self._get_body('dspaces/var/'))

    def GetVarObjs(self, name):
        return(self._get_body(f'dspaces/var/{name}/'))

    def Register(self, type, name, data):
        url = f'dspaces/register/{type}/{name}'
        response = self._post(url, data=json.dumps(data))
        if response is None:
            if self.debug:
                print("could not find requested object in DXSpacesClient.Register()")
            return None
        handle_dict = json.loads(response.content)
        return(RegistryHandle(**handle_dict))
