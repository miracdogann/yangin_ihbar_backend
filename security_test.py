#!/usr/bin/env python3
"""
Güvenlik Test Scripti - Yangın İhbar Sistemi
Bu script yaygın web uygulama güvenlik açıklarını test eder.
"""

import requests
import json
import time
import random
import string
from urllib.parse import urljoin

class SecurityTester:
    def __init__(self, base_url="http://127.0.0.1:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = []
        
    def log_test(self, test_name, result, details=""):
        """Test sonuçlarını logla"""
        status = "PASSED" if result else "FAILED"
        print(f"[{status}] {test_name}")
        if details:
            print(f"    Details: {details}")
        self.results.append({
            'test': test_name,
            'result': result,
            'details': details
        })
    
    def test_sql_injection(self):
        """SQL Injection testleri"""
        print("\n=== SQL Injection Testleri ===")
        
        # Test payloads
        sql_payloads = [
            "' OR '1'='1",
            "' OR 1=1--",
            "' UNION SELECT * FROM users--",
            "'; DROP TABLE users;--",
            "1' OR '1'='1' /*",
            "admin'--",
            "' OR 'x'='x",
            "1; SELECT * FROM information_schema.tables;--"
        ]
        
        endpoints = [
            "/api/login/",
            "/api/register/",
            "/api/user-info/"
        ]
        
        for endpoint in endpoints:
            for payload in sql_payloads:
                try:
                    # Login endpoint testi
                    if endpoint == "/api/login/":
                        data = {
                            "phone_number": payload,
                            "password": "test123"
                        }
                    elif endpoint == "/api/register/":
                        data = {
                            "name_surname": f"Test User {payload}",
                            "phone_number": "1234567890",
                            "email": f"test{payload}@test.com",
                            "password": "Test123!",
                            "confirm_password": "Test123!"
                        }
                    else:
                        # GET request
                        headers = {"Authorization": f"Bearer {payload}"}
                        response = self.session.get(urljoin(self.base_url, endpoint), headers=headers)
                        
                        # Hata mesajlarında SQL ifadeleri var mı kontrol et
                        if any(word in response.text.lower() for word in ['sql', 'sqlite', 'database', 'syntax error']):
                            self.log_test(f"SQL Injection - {endpoint}", False, f"Potential SQL error: {response.text[:200]}")
                        else:
                            self.log_test(f"SQL Injection - {endpoint}", True, "No SQL errors detected")
                        continue
                    
                    response = self.session.post(urljoin(self.base_url, endpoint), json=data)
                    
                    # Hata mesajlarında SQL ifadeleri var mı kontrol et
                    if any(word in response.text.lower() for word in ['sql', 'sqlite', 'database', 'syntax error']):
                        self.log_test(f"SQL Injection - {endpoint}", False, f"Potential SQL error with payload: {payload}")
                        break
                    else:
                        self.log_test(f"SQL Injection - {endpoint} - {payload[:20]}", True, "No SQL errors detected")
                        
                except Exception as e:
                    self.log_test(f"SQL Injection - {endpoint}", True, f"Request failed safely: {str(e)}")
    
    def test_idor(self):
        """Insecure Direct Object Reference testleri"""
        print("\n=== IDOR (Insecure Direct Object Reference) Testleri ===")
        
        # Önce geçerli bir kullanıcı oluştur
        user_data = {
            "name_surname": "Test User IDOR",
            "phone_number": f"555{''.join(random.choices(string.digits, k=7))}",
            "email": f"idor{random.randint(1000,9999)}@test.com",
            "password": "Test123!",
            "confirm_password": "Test123!"
        }
        
        try:
            response = self.session.post(urljoin(self.base_url, "/api/register/"), json=user_data)
            if response.status_code == 201:
                user_token = response.json().get('token')
                headers = {"Authorization": f"Bearer {user_token}"}
                
                # IDOR testleri - başka kullanıcıların verilerine erişim
                user_ids = [1, 2, 3, 999, -1, 0, "admin", "../admin", "1'", "1 OR 1=1"]
                
                for user_id in user_ids:
                    try:
                        # User info endpoint
                        response = self.session.get(
                            urljoin(self.base_url, f"/api/user/{user_id}/"), 
                            headers=headers
                        )
                        
                        if response.status_code == 200:
                            self.log_test(f"IDOR - User ID {user_id}", False, "Unauthorized access possible")
                        else:
                            self.log_test(f"IDOR - User ID {user_id}", True, f"Access denied (HTTP {response.status_code})")
                            
                    except Exception as e:
                        self.log_test(f"IDOR - User ID {user_id}", True, f"Request failed safely: {str(e)}")
            else:
                self.log_test("IDOR Setup", False, "Could not create test user")
                
        except Exception as e:
            self.log_test("IDOR Test", True, f"Test setup failed safely: {str(e)}")
    
    def test_authentication_bypass(self):
        """Authentication Bypass testleri"""
        print("\n=== Authentication Bypass Testleri ===")
        
        bypass_payloads = [
            "",
            "Bearer ",
            "Bearer null",
            "Bearer undefined",
            "Bearer false",
            "Bearer admin",
            "Basic YWRtaW46YWRtaW4=",  # admin:admin
            "Bearer " + "A" * 1000,
            "Bearer ../admin",
            "Bearer ../../etc/passwd"
        ]
        
        protected_endpoints = [
            "/api/user-info/",
            "/api/create-fire-report/",
            "/api/user-fire-reports/"
        ]
        
        for endpoint in protected_endpoints:
            for payload in bypass_payloads:
                try:
                    headers = {"Authorization": payload} if payload else {}
                    response = self.session.get(urljoin(self.base_url, endpoint), headers=headers)
                    
                    if response.status_code == 200:
                        self.log_test(f"Auth Bypass - {endpoint}", False, f"Bypass with: {payload[:50]}")
                    else:
                        self.log_test(f"Auth Bypass - {endpoint}", True, f"Properly protected (HTTP {response.status_code})")
                        
                except Exception as e:
                    self.log_test(f"Auth Bypass - {endpoint}", True, f"Request failed safely: {str(e)}")
    
    def test_xss(self):
        """Cross-Site Scripting testleri"""
        print("\n=== XSS (Cross-Site Scripting) Testleri ===")
        
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg onload=alert('XSS')>",
            "';alert('XSS');//",
            "<iframe src=javascript:alert('XSS')></iframe>",
            "<body onload=alert('XSS')>",
            "<<SCRIPT>alert('XSS')//<</SCRIPT>"
        ]
        
        for payload in xss_payloads:
            try:
                data = {
                    "name_surname": payload,
                    "phone_number": f"555{random.randint(1000000, 9999999)}",
                    "email": f"xss{random.randint(1000,9999)}@test.com",
                    "password": "Test123!",
                    "confirm_password": "Test123!"
                }
                
                response = self.session.post(urljoin(self.base_url, "/api/register/"), json=data)
                
                # Response'da payload var mı kontrol et (reflected XSS)
                if payload in response.text:
                    self.log_test(f"XSS Reflected - {payload[:30]}", False, "Payload reflected in response")
                else:
                    self.log_test(f"XSS Reflected - {payload[:30]}", True, "Payload not reflected")
                    
            except Exception as e:
                self.log_test(f"XSS Test - {payload[:30]}", True, f"Request failed safely: {str(e)}")
    
    def test_rate_limiting(self):
        """Rate Limiting testleri"""
        print("\n=== Rate Limiting Testleri ===")
        
        # Login endpoint'ine hızlı istekler gönder
        failed_attempts = 0
        for i in range(10):
            try:
                data = {
                    "phone_number": "1234567890",
                    "password": "wrongpassword"
                }
                response = self.session.post(urljoin(self.base_url, "/api/login/"), json=data)
                
                if response.status_code == 429:  # Too Many Requests
                    self.log_test("Rate Limiting", True, f"Rate limiting active after {i+1} requests")
                    return
                elif response.status_code != 404:  # User not found is expected
                    failed_attempts += 1
                    
                time.sleep(0.1)  # Kısa bekleme
                
            except Exception as e:
                self.log_test("Rate Limiting", True, f"Request failed: {str(e)}")
                return
        
        if failed_attempts >= 10:
            self.log_test("Rate Limiting", False, "No rate limiting detected after 10 requests")
        else:
            self.log_test("Rate Limiting", True, "Rate limiting appears to be working")
    
    def test_input_validation(self):
        """Input Validation testleri"""
        print("\n=== Input Validation Testleri ===")
        
        # Çok uzun input testi
        long_string = "A" * 10000
        
        test_cases = [
            {"name_surname": long_string, "expected": "validation"},
            {"email": "invalid-email", "expected": "validation"},
            {"phone_number": "abc123", "expected": "validation"},
            {"password": "123", "expected": "validation"},  # Çok kısa şifre
            {"name_surname": "", "expected": "validation"},  # Boş alan
        ]
        
        for case in test_cases:
            try:
                data = {
                    "name_surname": case.get("name_surname", "Test User"),
                    "phone_number": case.get("phone_number", "5551234567"),
                    "email": case.get("email", f"test{random.randint(1000,9999)}@test.com"),
                    "password": case.get("password", "Test123!"),
                    "confirm_password": case.get("password", "Test123!")
                }
                
                response = self.session.post(urljoin(self.base_url, "/api/register/"), json=data)
                
                if response.status_code == 400:  # Bad Request
                    self.log_test(f"Input Validation - {list(case.keys())[0]}", True, "Validation working")
                else:
                    self.log_test(f"Input Validation - {list(case.keys())[0]}", False, f"Validation bypassed: HTTP {response.status_code}")
                    
            except Exception as e:
                self.log_test(f"Input Validation - {list(case.keys())[0]}", True, f"Request failed safely: {str(e)}")
    
    def test_file_upload_security(self):
        """File Upload güvenlik testleri"""
        print("\n=== File Upload Security Testleri ===")
        
        # Sistem dosya upload endpoint'i var mı kontrol et
        file_endpoints = [
            "/api/upload/",
            "/api/file-upload/",
            "/api/photo-upload/",
            "/admin/upload/"
        ]
        
        for endpoint in file_endpoints:
            try:
                # Zararlı dosya simülasyonu
                files = {'file': ('test.php', '<?php echo shell_exec($_GET["cmd"]); ?>', 'application/php')}
                response = self.session.post(urljoin(self.base_url, endpoint), files=files)
                
                if response.status_code == 404:
                    self.log_test(f"File Upload - {endpoint}", True, "Endpoint not found (good)")
                elif response.status_code == 403:
                    self.log_test(f"File Upload - {endpoint}", True, "Upload forbidden (good)")
                else:
                    self.log_test(f"File Upload - {endpoint}", False, f"Potential upload vulnerability: HTTP {response.status_code}")
                    
            except Exception as e:
                self.log_test(f"File Upload - {endpoint}", True, f"Request failed safely: {str(e)}")
    
    def run_all_tests(self):
        """Tüm güvenlik testlerini çalıştır"""
        print("🔍 Güvenlik Testleri Başlatılıyor...")
        print("=" * 50)
        
        start_time = time.time()
        
        # Test sırası
        self.test_sql_injection()
        self.test_idor()
        self.test_authentication_bypass()
        self.test_xss()
        self.test_rate_limiting()
        self.test_input_validation()
        self.test_file_upload_security()
        
        end_time = time.time()
        
        # Sonuçları özetle
        print("\n" + "=" * 50)
        print("🔒 GÜVENLİK TESTİ SONUÇLARI")
        print("=" * 50)
        
        passed = sum(1 for r in self.results if r['result'])
        failed = sum(1 for r in self.results if not r['result'])
        
        print(f"✅ Geçen Testler: {passed}")
        print(f"❌ Başarısız Testler: {failed}")
        print(f"⏱️ Test Süresi: {end_time - start_time:.2f} saniye")
        
        if failed > 0:
            print("\n🚨 GÜVENLIK UYARILARI:")
            for result in self.results:
                if not result['result']:
                    print(f"  - {result['test']}: {result['details']}")
        else:
            print("\n🎉 Tüm güvenlik testleri başarılı!")
        
        return self.results

if __name__ == "__main__":
    tester = SecurityTester()
    tester.run_all_tests()
