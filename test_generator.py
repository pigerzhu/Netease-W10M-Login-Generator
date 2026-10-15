"""Offline tests: synthetic credentials only; never opens private backups."""
import ctypes
import struct
import subprocess
import sys
import tempfile
import unittest
import winreg
from ctypes import wintypes as W
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read_hive(path, security=False):
    api=ctypes.WinDLL('advapi32')
    api.RegLoadAppKeyW.argtypes=[W.LPCWSTR,ctypes.POINTER(W.HANDLE),W.DWORD,W.DWORD,W.DWORD]
    api.RegLoadAppKeyW.restype=W.LONG
    handle=W.HANDLE()
    status=api.RegLoadAppKeyW(str(path),ctypes.byref(handle),winreg.KEY_READ,0,0)
    if status:
        raise ctypes.WinError(status)
    result={}
    def walk(key,path):
        children,values,_=winreg.QueryInfoKey(key)
        for i in range(values):
            name,value,kind=winreg.EnumValue(key,i)
            result[(path,name)]=(kind,value)
        for i in range(children):
            name=winreg.EnumKey(key,i)
            with winreg.OpenKey(key,name) as child:
                walk(child,path+'\\'+name)
    try:
        if security:
            get=api.RegGetKeySecurity
            get.argtypes=[W.HANDLE,W.DWORD,ctypes.c_void_p,ctypes.POINTER(W.DWORD)]
            size=W.DWORD();get(handle,4,None,ctypes.byref(size))
            buffer=ctypes.create_string_buffer(size.value)
            status=get(handle,4,buffer,ctypes.byref(size))
            if status:raise ctypes.WinError(status)
            convert=api.ConvertSecurityDescriptorToStringSecurityDescriptorW
            convert.argtypes=[ctypes.c_void_p,W.DWORD,W.DWORD,ctypes.POINTER(W.LPWSTR),ctypes.c_void_p]
            text=W.LPWSTR()
            if not convert(buffer,1,4,ctypes.byref(text),None):raise ctypes.WinError()
            try:return text.value
            finally:
                kernel=ctypes.WinDLL('kernel32');kernel.LocalFree.argtypes=[ctypes.c_void_p]
                kernel.LocalFree(ctypes.cast(text,ctypes.c_void_p))
        walk(handle.value,'')
    finally:
        winreg.CloseKey(handle.value)
    return result


class GeneratorTests(unittest.TestCase):
    def test_blank_hive_grants_inheritable_appcontainer_access(self):
        self.assertIn('(A;CI;KA;;;AC)',read_hive(ROOT/'blank.dat',security=True))

    def run_generator(self, output, *args):
        return subprocess.run([sys.executable,str(ROOT/'generate_settings.py'),'--out',str(output),*args],capture_output=True)

    def test_generates_independent_hive_for_supplied_account_and_long_cookie(self):
        original=(ROOT/'blank.dat').read_bytes()
        for length in (1,802,834,4096):
            with self.subTest(length=length),tempfile.TemporaryDirectory() as temp:
                output=Path(temp)/'settings.dat'
                result=self.run_generator(output,'--musicu','A'*length,'--userid','123456789')
                self.assertEqual(result.returncode,0,result.stdout.decode(errors='replace')+result.stderr.decode(errors='replace'))
                values=read_hive(output)
                for key in ('account','profile'):
                    name='id' if key=='account' else 'userid'
                    kind,raw=values[('\\LocalState\\usersettings\\'+key,name)]
                    self.assertEqual(kind,0x05f5e106)
                    self.assertEqual(struct.unpack('<q',raw[:-8])[0],123456789)
                kind,raw=values[('\\LocalState\\usersettings','cookies')]
                self.assertEqual(kind,0x05f5e10c)
                self.assertEqual(raw[:-8].decode('utf-16-le').rstrip('\0'),'MUSIC_U='+'A'*length+'; __remember_me=true')
                kind,raw=values[('\\LocalState\\usersettings\\profile','nickname')]
                self.assertEqual(raw[:-8].decode('utf-16-le').rstrip('\0'),'')
                self.assertNotIn('A'*32,result.stdout.decode(errors='replace'))
        self.assertEqual((ROOT/'blank.dat').read_bytes(),original)
        self.assertEqual(read_hive(ROOT/'blank.dat'),{})

    def test_full_cookie_preserved_and_required_inputs_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp)/'settings.dat'
            supplied='NMTID=synthetic; __csrf='+'B'*32+'; MUSIC_U='+'C'*834
            result=self.run_generator(output,'--musicu',supplied,'--userid','987654321')
            self.assertEqual(result.returncode,0,result.stdout.decode(errors='replace'))
            _,raw=read_hive(output)[('\\LocalState\\usersettings','cookies')]
            actual=raw[:-8].decode('utf-16-le').rstrip('\0')
            self.assertIn('NMTID=synthetic',actual)
            self.assertIn('__csrf='+'B'*32,actual)
            for uid,token in (('0','A'*834),('not-id','A'*834),('123','not-a-token')):
                result=self.run_generator(Path(temp)/'invalid.dat','--musicu',token,'--userid',uid)
                self.assertNotEqual(result.returncode,0)
                self.assertFalse((Path(temp)/'invalid.dat').exists())

if __name__=='__main__':
    unittest.main()
